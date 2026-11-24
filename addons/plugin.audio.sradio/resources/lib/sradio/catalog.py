from __future__ import annotations

import json
import os
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def normalize_text(text: str) -> str:
    """Remove acentos e converte para minúsculas para buscas insensíveis."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower().strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pick_best_stream(
    streams: list[dict[str, Any]],
    preferred_bitrate: str = "highest",
) -> dict[str, Any]:
    prefer_lowest = preferred_bitrate == "lowest"

    def score(stream: dict[str, Any]) -> tuple[int, int]:
        reliability = _safe_int(stream.get("reliability"), 0)
        bitrate = _safe_int(stream.get("bitrate"), 0)
        return (reliability, -bitrate if prefer_lowest else bitrate)

    return max(streams, key=score)


class TuneInAPI:
    """Cliente da API pública RadioTime / TuneIn."""

    BASE_URL = "http://opml.radiotime.com"
    PARTNER_ID = "xwhZkVKi"
    USER_AGENT = "TuneIn/31.0 (Android; Mobile; rv:120.0)"

    @classmethod
    def _build_url(cls, endpoint_or_url: str, params: dict[str, str] | None = None) -> str:
        """Garante que render=json e partnerId=xwhZkVKi estejam sempre presentes na URL."""
        if not endpoint_or_url.startswith(("http://", "https://")):
            endpoint_or_url = f"{cls.BASE_URL}/{endpoint_or_url.lstrip('/')}"

        parsed = urllib.parse.urlparse(endpoint_or_url)
        query_dict = dict(urllib.parse.parse_qsl(parsed.query))
        if params:
            query_dict.update(params)
        query_dict.setdefault("render", "json")
        query_dict.setdefault("partnerId", cls.PARTNER_ID)
        new_query = urllib.parse.urlencode(query_dict)
        return urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    @classmethod
    def _fetch_json(cls, url: str, timeout: int = 8) -> dict[str, Any] | None:
        """Realiza requisição HTTP GET com tratamento robusto de erros e decodificação UTF-8."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": cls.USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return None

    @classmethod
    def _parse_outlines(cls, outlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Processa a árvore de outlines OPML da API TuneIn."""
        items: list[dict[str, Any]] = []

        for outline in outlines:
            elem_type = outline.get("type", "")
            guide_id = outline.get("guide_id") or outline.get("guideId")
            text = outline.get("text", "")
            children = outline.get("children")

            if children and isinstance(children, list):
                items.extend(cls._parse_outlines(children))
                continue

            if elem_type == "audio" or (guide_id and str(guide_id).startswith("s")):
                subtext = outline.get("subtext") or outline.get("playing") or ""
                image = outline.get("image") or ""
                bitrate = outline.get("bitrate")
                formats = outline.get("formats") or "mp3,aac"
                default_tune = (
                    f"{cls.BASE_URL}/Tune.ashx?id={guide_id}&render=json&partnerId={cls.PARTNER_ID}"
                )
                tune_url = outline.get("URL") or default_tune

                items.append(
                    {
                        "is_folder": False,
                        "guide_id": str(guide_id or ""),
                        "name": text,
                        "subtext": subtext,
                        "logo": image,
                        "category": outline.get("genre_id", ""),
                        "bitrate": bitrate,
                        "declared_formats": formats,
                        "direct_stream_url": "",
                        "tune_url": tune_url,
                    }
                )
            elif elem_type == "link" or outline.get("URL"):
                target_url = outline.get("URL", "")
                if target_url:
                    items.append(
                        {
                            "is_folder": True,
                            "title": text,
                            "url": target_url,
                            "key": outline.get("key", ""),
                            "logo": outline.get("image", ""),
                            "subtext": outline.get("subtext", ""),
                        }
                    )

        return items

    @classmethod
    def _fetch_outlines(
        cls,
        endpoint_or_url: str,
        params: dict[str, str] | None = None,
        timeout: int = 8,
    ) -> list[dict[str, Any]]:
        full_url = cls._build_url(endpoint_or_url, params)
        data = cls._fetch_json(full_url, timeout=timeout)
        if not isinstance(data, dict):
            return []
        body = data.get("body", [])
        return cls._parse_outlines(body) if isinstance(body, list) else []

    @classmethod
    def browse(cls, endpoint_or_url: str = "Browse.ashx", timeout: int = 8) -> list[dict[str, Any]]:
        """Navega hierarquicamente por categorias e pastas da API TuneIn."""
        return cls._fetch_outlines(endpoint_or_url, timeout=timeout)

    @classmethod
    def search(cls, query: str, timeout: int = 8) -> list[dict[str, Any]]:
        """Pesquisa em tempo real em mais de 100.000 rádios via Search.ashx."""
        if not query.strip():
            return []
        return cls._fetch_outlines("Search.ashx", {"query": query.strip()}, timeout=timeout)

    @classmethod
    def resolve_stream(
        cls,
        guide_id: str,
        timeout: int = 8,
        preferred_bitrate: str = "highest",
    ) -> dict[str, Any] | None:
        """Resolve o link direto de áudio em tempo real via Tune.ashx com tokens CDN frescos."""
        if not guide_id:
            return None

        tune_url = cls._build_url("Tune.ashx", {"id": guide_id})
        data = cls._fetch_json(tune_url, timeout=timeout)
        if not isinstance(data, dict):
            return None

        body = data.get("body", [])
        if not isinstance(body, list) or not body:
            return None

        valid_streams = [
            stream
            for stream in body
            if isinstance(stream, dict)
            and str(stream.get("url") or "").startswith(("http://", "https://"))
        ]
        if not valid_streams:
            return None

        best_stream = _pick_best_stream(valid_streams, preferred_bitrate)
        return {
            "url": best_stream.get("url"),
            "bitrate": best_stream.get("bitrate"),
            "media_type": best_stream.get("media_type", "mp3"),
            "reliability": best_stream.get("reliability", 100),
        }


class RadioCatalog:
    """Gerenciador unificado do catálogo de rádios (TuneIn dinâmico + cache offline)."""

    def __init__(self, data_path: str | None = None) -> None:
        if data_path is None:
            base_dir = Path(__file__).resolve().parents[2]
            data_path = str(base_dir / "data" / "radios.json")

        self.data_path = data_path
        self._stations: list[dict[str, Any]] = []
        self._station_map: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self.api = TuneInAPI

    def load(self) -> None:
        if self._loaded:
            return

        if os.path.isfile(self.data_path):
            try:
                with open(self.data_path, encoding="utf-8") as f:
                    payload = json.load(f)
                    self._stations = payload.get("stations", [])
            except Exception:
                self._stations = []

        self._station_map = {s.get("guide_id", ""): s for s in self._stations if s.get("guide_id")}
        self._loaded = True

    @property
    def total_count(self) -> int:
        self.load()
        return len(self._stations)

    def get_station(self, guide_id: str) -> dict[str, Any] | None:
        self.load()
        return self._station_map.get(guide_id)

    def get_all(self) -> list[dict[str, Any]]:
        self.load()
        return list(self._stations)

    def search(self, query: str) -> list[dict[str, Any]]:
        """Pesquisa primeiro na API global TuneIn; se falhar ou offline, busca no cache local."""
        try:
            live_results = self.api.search(query)
            if live_results:
                stations = [item for item in live_results if not item.get("is_folder")]
                if stations:
                    return stations
        except Exception:
            pass

        self.load()
        norm_q = normalize_text(query)
        if not norm_q:
            return []

        return [
            station
            for station in self._stations
            if norm_q in normalize_text(station.get("name", ""))
            or norm_q in normalize_text(station.get("subtext", ""))
            or norm_q in normalize_text(station.get("category", ""))
        ]

    def resolve_station_stream(
        self,
        guide_id: str,
        fallback_station: dict[str, Any] | None = None,
        preferred_bitrate: str = "highest",
    ) -> dict[str, Any] | None:
        """Resolve link de streaming fresco em tempo real com fallback automático para cache."""
        if guide_id:
            try:
                resolved = self.api.resolve_stream(guide_id, preferred_bitrate=preferred_bitrate)
                if resolved and resolved.get("url"):
                    return resolved
            except Exception:
                pass

        station = fallback_station or self.get_station(guide_id)
        if not station:
            return None

        url = None
        bitrate = None
        media_type = "mp3"

        all_s = station.get("all_streams", [])
        if isinstance(all_s, list):
            valid = [s for s in all_s if isinstance(s, dict) and s.get("url")]
            if valid:
                chosen = _pick_best_stream(valid, preferred_bitrate)
                url = chosen.get("url")
                bitrate = chosen.get("bitrate")
                media_type = chosen.get("media_type") or "mp3"

        if not url:
            url = station.get("direct_stream_url")
            bitrate = station.get("stream_bitrate") or station.get("declared_bitrate")
            media_type = station.get("stream_media_type") or "mp3"

        if url:
            return {
                "url": url,
                "bitrate": bitrate,
                "media_type": media_type,
            }
        return None
