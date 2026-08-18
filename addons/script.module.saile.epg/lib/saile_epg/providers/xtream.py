from __future__ import annotations

import base64
import binascii
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Callable

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import clean_channel_title, normalize_channel_name

RequestCallable = Callable[..., object]


def _decode_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        padded = text + ("=" * (-len(text) % 4))
        decoded = base64.b64decode(padded, validate=True).decode("utf-8").strip()
        return decoded or text
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return text


def _timestamp(listing: dict[str, object], numeric_key: str, text_key: str) -> int:
    raw_numeric = str(listing.get(numeric_key) or "").strip()
    if raw_numeric:
        try:
            return int(float(raw_numeric))
        except ValueError:
            pass
    raw_text = str(listing.get(text_key) or "").strip()
    if not raw_text:
        return 0
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(
                datetime.strptime(raw_text[:19], pattern)
                .replace(tzinfo=timezone.utc)
                .timestamp()
            )
        except ValueError:
            continue
    return 0


class XtreamEpgProvider:
    """Fallback de EPG curto via player_api, independente da UI e do sTv."""

    def __init__(
        self,
        request: RequestCallable,
        live_streams: object,
        provider_id: str = "xtream",
        listing_limit: int = 12,
        max_channels: int = 500,
    ) -> None:
        self.request = request
        self.live_streams = live_streams
        self.provider_id = provider_id
        self.listing_limit = listing_limit
        self.max_channels = max_channels

    def _representatives(self) -> list[list[dict[str, object]]]:
        if not isinstance(self.live_streams, list):
            return []
        representatives: dict[str, list[dict[str, object]]] = {}
        for raw in self.live_streams:
            if not isinstance(raw, dict):
                continue
            stream_id = str(raw.get("stream_id") or "").strip()
            epg_id = str(raw.get("epg_channel_id") or raw.get("tvg_id") or "").strip()
            name = str(raw.get("name") or "").strip()
            if stream_id and epg_id and name:
                representatives.setdefault(epg_id.casefold(), []).append(raw)
            if len(representatives) >= self.max_channels:
                break
        return list(representatives.values())

    def _fetch_channel(
        self,
        stream: dict[str, object],
        fetched_at: int,
    ) -> tuple[EpgChannel, list[EpgProgram]] | None:
        stream_id = str(stream.get("stream_id") or "").strip()
        epg_id = str(stream.get("epg_channel_id") or stream.get("tvg_id") or "").strip()
        raw_name = str(stream.get("name") or "").strip()
        response = self.request(
            "get_short_epg",
            stream_id=stream_id,
            limit=self.listing_limit,
            request_timeout=8,
        )
        if not isinstance(response, dict):
            return None
        raw_listings = response.get("epg_listings")
        if not isinstance(raw_listings, list):
            return None

        minimum = fetched_at - (12 * 3600)
        maximum = fetched_at + (48 * 3600)
        programs = []
        for raw_listing in raw_listings:
            if not isinstance(raw_listing, dict):
                continue
            start_utc = _timestamp(raw_listing, "start_timestamp", "start")
            end_utc = _timestamp(raw_listing, "stop_timestamp", "end")
            title = _decode_text(raw_listing.get("title"))
            if (
                title
                and start_utc > 0
                and end_utc > start_utc
                and end_utc >= minimum
                and start_utc <= maximum
            ):
                programs.append(
                    EpgProgram(
                        provider_id=self.provider_id,
                        channel_key=epg_id,
                        title=title,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        description=_decode_text(raw_listing.get("description")),
                    )
                )
        if not programs:
            return None
        display_name = clean_channel_title(raw_name)
        channel = EpgChannel(
            provider_id=self.provider_id,
            channel_key=epg_id,
            epg_id=epg_id,
            display_name=display_name,
            normalized_name=normalize_channel_name(display_name),
            icon_url=str(stream.get("stream_icon") or "").strip(),
        )
        return (channel, programs)

    def _fetch_group(
        self,
        streams: list[dict[str, object]],
        fetched_at: int,
    ) -> tuple[EpgChannel, list[EpgProgram]] | None:
        last_error: Exception | None = None
        for stream in streams:
            try:
                result = self._fetch_channel(stream, fetched_at)
            except Exception as exc:
                last_error = exc
                continue
            if result is not None:
                return result
        if last_error is not None:
            raise last_error
        return None

    def fetch(self) -> EpgSnapshot:
        representatives = self._representatives()
        if not representatives:
            raise EpgSyncError(
                "EPG-XTREAM-CHANNELS",
                "O provedor não informou canais vinculados ao EPG",
            )
        fetched_at = int(time.time())
        results = []
        first_error: Exception | None = None

        with ThreadPoolExecutor(max_workers=8, thread_name_prefix="saile-epg") as executor:
            futures = [
                executor.submit(self._fetch_group, streams, fetched_at)
                for streams in representatives
            ]
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    if first_error is None:
                        first_error = exc
                    result = None
                if result is not None:
                    results.append(result)
        if not results:
            if first_error is not None:
                raise EpgSyncError(
                    "EPG-XTREAM-UNAVAILABLE",
                    "A API de EPG do provedor não respondeu",
                ) from first_error
            raise EpgSyncError(
                "EPG-XTREAM-EMPTY",
                "O provedor não retornou programação pela API Xtream",
            )

        results.sort(key=lambda result: result[0].channel_key)
        channels = tuple(result[0] for result in results)
        deduplicated: dict[tuple[str, int], EpgProgram] = {}
        for _channel, programs in results:
            for program in programs:
                deduplicated[(program.channel_key, program.start_utc)] = program
        return EpgSnapshot(
            provider_id=self.provider_id,
            channels=channels,
            programs=tuple(
                sorted(
                    deduplicated.values(),
                    key=lambda program: (program.channel_key, program.start_utc),
                )
            ),
            fetched_at_utc=fetched_at,
        )
