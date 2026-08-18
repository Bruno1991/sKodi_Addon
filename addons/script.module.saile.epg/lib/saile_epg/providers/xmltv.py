from __future__ import annotations

import gzip
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import normalize_channel_name

MAX_PROGRAMS = 250_000
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 256 * 1024
SPOOL_MEMORY_BYTES = 8 * 1024 * 1024


def parse_xmltv_timestamp(value: str) -> int:
    compact = value.strip()
    if len(compact) < 12:
        raise ValueError(f"Timestamp XMLTV inválido: {value!r}")
    digits = compact.split()[0]
    if len(digits) == 12:
        digits += "00"
    moment = datetime.strptime(digits[:14], "%Y%m%d%H%M%S")

    remainder = compact[len(compact.split()[0]) :].strip()
    if remainder and remainder.upper() != "Z":
        sign = -1 if remainder.startswith("-") else 1
        offset = remainder.lstrip("+-")[:4]
        if len(offset) != 4 or not offset.isdigit():
            raise ValueError(f"Fuso XMLTV inválido: {value!r}")
        delta = timedelta(hours=int(offset[:2]), minutes=int(offset[2:])) * sign
        moment = moment.replace(tzinfo=timezone(delta))
    else:
        moment = moment.replace(tzinfo=timezone.utc)
    return int(moment.astimezone(timezone.utc).timestamp())


def _local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local_tag(child) == name and child.text:
            return child.text.strip()
    return ""


def _child_icon(element: ET.Element) -> str:
    for child in element:
        if _local_tag(child) == "icon":
            return str(child.attrib.get("src", "")).strip()
    return ""


class XmltvProvider:
    def __init__(
        self,
        url: str,
        provider_id: str = "xtream",
        timeout: int = 30,
        window_before_hours: int = 12,
        window_after_hours: int = 48,
    ) -> None:
        self.url = url
        self.provider_id = provider_id
        self.timeout = timeout
        self.window_before_hours = window_before_hours
        self.window_after_hours = window_after_hours

    def fetch(self) -> EpgSnapshot:
        if not self.url.startswith(("http://", "https://")):
            raise EpgSyncError("EPG-URL", "URL XMLTV inválida")
        request = Request(
            self.url,
            headers={
                "Accept": "application/xml, text/xml, application/gzip",
                "Accept-Encoding": "gzip",
                "User-Agent": "SAILE-EPG/1.0.1",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                with tempfile.SpooledTemporaryFile(
                    max_size=SPOOL_MEMORY_BYTES,
                    mode="w+b",
                ) as buffer:
                    self._download(response, buffer)
                    return self._parse_download(response, buffer)
        except EpgSyncError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # A exceção pública não inclui a URL, que contém credenciais Xtream.
            raise EpgSyncError(
                "EPG-DOWNLOAD",
                "Não foi possível baixar o XMLTV do provedor",
            ) from exc

    @staticmethod
    def _download(response: object, buffer: BinaryIO) -> None:
        read = getattr(response, "read", None)
        if not callable(read):
            raise EpgSyncError(
                "EPG-HTTP-READ",
                "O provedor retornou uma resposta HTTP incompatível",
            )

        downloaded = 0
        try:
            while True:
                chunk = read(DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                if not isinstance(chunk, (bytes, bytearray)):
                    raise EpgSyncError(
                        "EPG-HTTP-DATA",
                        "O provedor retornou dados XMLTV incompatíveis",
                    )
                downloaded += len(chunk)
                if downloaded > MAX_DOWNLOAD_BYTES:
                    raise EpgSyncError(
                        "EPG-DOWNLOAD-LIMIT",
                        "O XMLTV excede o limite seguro de download",
                    )
                buffer.write(chunk)
        except EpgSyncError:
            raise
        except (TimeoutError, OSError, TypeError) as exc:
            raise EpgSyncError(
                "EPG-DOWNLOAD",
                "Não foi possível baixar o XMLTV do provedor",
            ) from exc

        if downloaded == 0:
            raise EpgSyncError("EPG-EMPTY", "O provedor retornou um XMLTV vazio")
        buffer.seek(0)

    def _parse_download(self, response: object, buffer: BinaryIO) -> EpgSnapshot:
        headers = getattr(response, "headers", None)
        get_header = getattr(headers, "get", None)
        encoding = str(get_header("Content-Encoding", "") if callable(get_header) else "").lower()
        magic = buffer.read(2)
        buffer.seek(0)
        is_gzip = "gzip" in encoding or magic == b"\x1f\x8b"

        try:
            if is_gzip:
                with gzip.GzipFile(fileobj=buffer, mode="rb") as stream:
                    return self.parse(stream)
            return self.parse(buffer)
        except EpgSyncError:
            raise
        except (ET.ParseError, EOFError, OSError, TypeError, ValueError) as exc:
            raise EpgSyncError(
                "EPG-PARSE",
                "O XMLTV recebido é inválido ou incompatível",
            ) from exc

    def parse(self, stream: BinaryIO, fetched_at_utc: int | None = None) -> EpgSnapshot:
        fetched_at = int(time.time()) if fetched_at_utc is None else int(fetched_at_utc)
        minimum = fetched_at - (self.window_before_hours * 3600)
        maximum = fetched_at + (self.window_after_hours * 3600)
        channels: dict[str, EpgChannel] = {}
        programs: list[EpgProgram] = []

        for _event, element in ET.iterparse(stream, events=("end",)):
            tag = _local_tag(element)
            if tag == "channel":
                channel_key = str(element.attrib.get("id", "")).strip()
                if channel_key:
                    display_name = _child_text(element, "display-name") or channel_key
                    channels[channel_key] = EpgChannel(
                        provider_id=self.provider_id,
                        channel_key=channel_key,
                        epg_id=channel_key,
                        display_name=display_name,
                        normalized_name=normalize_channel_name(display_name),
                        icon_url=_child_icon(element),
                    )
                element.clear()
                continue

            if tag != "programme":
                continue
            channel_key = str(element.attrib.get("channel", "")).strip()
            try:
                start_utc = parse_xmltv_timestamp(str(element.attrib.get("start", "")))
                end_utc = parse_xmltv_timestamp(str(element.attrib.get("stop", "")))
            except ValueError:
                element.clear()
                continue
            title = _child_text(element, "title")
            if (
                channel_key
                and title
                and end_utc > start_utc
                and end_utc >= minimum
                and start_utc <= maximum
            ):
                programs.append(
                    EpgProgram(
                        provider_id=self.provider_id,
                        channel_key=channel_key,
                        title=title,
                        start_utc=start_utc,
                        end_utc=end_utc,
                        description=_child_text(element, "desc"),
                        category=_child_text(element, "category"),
                        icon_url=_child_icon(element),
                    )
                )
                if len(programs) > MAX_PROGRAMS:
                    raise ValueError("XMLTV excede o limite seguro de programas")
            element.clear()

        referenced = {program.channel_key for program in programs}
        filtered_channels = tuple(
            channel for key, channel in sorted(channels.items()) if key in referenced
        )
        filtered_programs = tuple(
            program for program in programs if program.channel_key in channels
        )
        if not filtered_channels or not filtered_programs:
            raise ValueError("XMLTV não contém canais e programas válidos na janela configurada")
        return EpgSnapshot(
            provider_id=self.provider_id,
            channels=filtered_channels,
            programs=filtered_programs,
            fetched_at_utc=fetched_at,
        )
