from __future__ import annotations

import json
import os
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def normalize_text(text: str) -> str:
    """Remove acentos e converte para minúsculas para buscas insensíveis."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower().strip()


class TuneInAPI:
    """Cliente oficial da API RadioTime / TuneIn extraída por engenharia reversa do APK."""

    BASE_URL = "http://opml.radiotime.com"
    PARTNER_ID = "xwhZkVKi"
    PARTNER_KEY = "kJ3B0f1qvBAU"
    USER_AGENT = "TuneIn/31.0 (Android; Mobile; rv:120.0)"

    @classmethod
    def _build_url(cls, endpoint_or_url: str, params: Optional[Dict[str, str]] = None) -> str:
        """Garante que render=json e partnerId=xwhZkVKi estejam sempre presentes na URL."""
        if not (endpoint_or_url.startswith("http://") or endpoint_or_url.startswith("https://")):
            endpoint_or_url = f"{cls.BASE_URL}/{endpoint_or_url.lstrip('/')}"

        parsed = urllib.parse.urlparse(endpoint_or_url)
        query_dict = dict(urllib.parse.parse_qsl(parsed.query))
        if params:
            query_dict.update(params)
        query_dict.setdefault("render", "json")
        query_dict.setdefault("partnerId", cls.PARTNER_ID)
        new_query = urllib.parse.urlencode(query_dict)
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

    @classmethod
    def _fetch_json(cls, url: str, timeout: int = 8) -> Optional[Dict[str, Any]]:
        """Realiza requisição HTTP GET com tratamento robusto de erros e decodificação UTF-8."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": cls.USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return None

    @classmethod
    def _parse_outlines(cls, outlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processa a árvore de outlines OPML da API TuneIn."""
        items: List[Dict[str, Any]] = []

        for outline in outlines:
            elem_type = outline.get("type", "")
            guide_id = outline.get("guide_id") or outline.get("guideId")
            text = outline.get("text", "")
            children = outline.get("children")

            # Se for um container de agrupamento com filhos (ex: 'Stations', 'Shows')
            if children and isinstance(children, list):
                items.extend(cls._parse_outlines(children))
                continue

            if elem_type == "audio" or (guide_id and str(guide_id).startswith("s")):
                subtext = outline.get("subtext") or outline.get("playing") or ""
                image = outline.get("image") or ""
                bitrate = outline.get("bitrate")
                formats = outline.get("formats") or "mp3,aac"
                tune_url = outline.get("URL") or f"{cls.BASE_URL}/Tune.ashx?id={guide_id}&render=json&partnerId={cls.PARTNER_ID}"

                items.append({
                    "is_folder": False,
                    "guide_id": str(guide_id or ""),
                    "name": text,
                    "subtext": subtext,
                    "logo": image,
                    "category": outline.get("genre_id", ""),
                    "bitrate": bitrate,
                    "declared_formats": formats,
                    "direct_stream_url": "",  # resolvido dinamicamente no play
                    "tune_url": tune_url,
                })
            elif elem_type == "link" or outline.get("URL"):
                target_url = outline.get("URL", "")
                if target_url:
                    items.append({
                        "is_folder": True,
                        "title": text,
                        "url": target_url,
                        "key": outline.get("key", ""),
                        "logo": outline.get("image", ""),
                        "subtext": outline.get("subtext", ""),
                    })

        return items

    @classmethod
    def browse(cls, endpoint_or_url: str = "Browse.ashx", timeout: int = 8) -> List[Dict[str, Any]]:
        """Navega hierarquicamente por categorias e pastas da API TuneIn."""
        full_url = cls._build_url(endpoint_or_url)
        data = cls._fetch_json(full_url, timeout=timeout)
        if not data or not isinstance(data, dict):
            return []

        body = data.get("body", [])
        if not isinstance(body, list):
            return []

        return cls._parse_outlines(body)

    @classmethod
    def search(cls, query: str, timeout: int = 8) -> List[Dict[str, Any]]:
        """Pesquisa em tempo real em mais de 100.000 rádios de todo o mundo via Search.ashx."""
        if not query.strip():
            return []

        search_url = cls._build_url("Search.ashx", {"query": query.strip()})
        data = cls._fetch_json(search_url, timeout=timeout)
        if not data or not isinstance(data, dict):
            return []

        body = data.get("body", [])
        if not isinstance(body, list):
            return []

        return cls._parse_outlines(body)

    @classmethod
    def resolve_stream(cls, guide_id: str, timeout: int = 8, preferred_bitrate: str = "highest") -> Optional[Dict[str, Any]]:
        """Resolve o link direto de áudio em tempo real via Tune.ashx com tokens CDN frescos."""
        if not guide_id:
            return None

        tune_url = cls._build_url("Tune.ashx", {"id": guide_id})
        data = cls._fetch_json(tune_url, timeout=timeout)
        if not data or not isinstance(data, dict):
            return None

        body = data.get("body", [])
        if not isinstance(body, list) or not body:
            return None

        valid_streams: List[Dict[str, Any]] = []
        for stream in body:
            url = stream.get("url")
            if url and (url.startswith("http://") or url.startswith("https://")):
                valid_streams.append(stream)

        if not valid_streams:
            return None

        prefer_lowest = preferred_bitrate == "lowest"

        def stream_score(s: Dict[str, Any]) -> Tuple[int, int]:
            reliability = int(s.get("reliability", 0) or 0)
            bitrate = int(s.get("bitrate", 0) or 0)
            bitrate_key = -bitrate if prefer_lowest else bitrate
            return (reliability, bitrate_key)

        best_stream = max(valid_streams, key=stream_score)
        return {
            "url": best_stream.get("url"),
            "bitrate": best_stream.get("bitrate"),
            "media_type": best_stream.get("media_type", "mp3"),
            "reliability": best_stream.get("reliability", 100),
        }


class RadioCatalog:
    """Gerenciador unificado do catálogo de rádios (TuneIn dinâmico + cache offline)."""

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            base_dir = Path(__file__).resolve().parents[2]
            data_path = str(base_dir / "data" / "radios.json")

        self.data_path = data_path
        self._stations: List[Dict[str, Any]] = []
        self._station_map: Dict[str, Dict[str, Any]] = {}
        self._loaded = False
        self.api = TuneInAPI

    def load(self) -> None:
        if self._loaded:
            return

        if os.path.isfile(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
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

    def get_station(self, guide_id: str) -> Optional[Dict[str, Any]]:
        self.load()
        return self._station_map.get(guide_id)

    def get_all(self) -> List[Dict[str, Any]]:
        self.load()
        return list(self._stations)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Pesquisa primeiro na API global TuneIn; se falhar ou estiver offline, busca no cache local."""
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

        results = []
        for station in self._stations:
            name_norm = normalize_text(station.get("name", ""))
            subtext_norm = normalize_text(station.get("subtext", ""))
            cat_norm = normalize_text(station.get("category", ""))
            if norm_q in name_norm or norm_q in subtext_norm or norm_q in cat_norm:
                results.append(station)

        return results

    def resolve_station_stream(
        self,
        guide_id: str,
        fallback_station: Optional[Dict[str, Any]] = None,
        preferred_bitrate: str = "highest",
    ) -> Optional[Dict[str, Any]]:
        """Resolve link de streaming fresco em tempo real com fallback automático para cache."""
        if guide_id:
            try:
                resolved = self.api.resolve_stream(guide_id, preferred_bitrate=preferred_bitrate)
                if resolved and resolved.get("url"):
                    return resolved
            except Exception:
                pass

        station = fallback_station or self.get_station(guide_id)
        if station:
            url = None
            bitrate = None
            media_type = "mp3"

            all_s = station.get("all_streams", [])
            if all_s and isinstance(all_s, list):
                valid = [s for s in all_s if s.get("url")]
                if valid:
                    prefer_lowest = preferred_bitrate == "lowest"

                    def fallback_score(s: Dict[str, Any]) -> Tuple[int, int]:
                        rel = int(s.get("reliability", 0) or 0)
                        br = int(s.get("bitrate", 0) or 0)
                        br_key = -br if prefer_lowest else br
                        return (rel, br_key)

                    chosen = max(valid, key=fallback_score)
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

    def get_featured(self) -> List[Dict[str, Any]]:
        """Retorna rádios de destaque do cache ou API."""
        self.load()
        featured = []
        for s in self._stations:
            cat = s.get("category", "")
            if "Featured" in cat or "Melhores" in cat or "Em Alta" in cat:
                featured.append(s)

        return featured if featured else self._stations[:50]

    def get_brazil_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa rádios brasileiras por cidade/estado no catálogo em cache."""
        self.load()
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for s in self._stations:
            cat = s.get("category", "")
            if "Brasil >" in cat:
                parts = [p.strip() for p in cat.split(">")]
                city = parts[1] if len(parts) > 1 else "Outras"
                if city not in groups:
                    groups[city] = []
                groups[city].append(s)

        return dict(sorted(groups.items()))

    def get_genre_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa rádios por gêneros musicais no catálogo em cache."""
        self.load()
        genres: Dict[str, List[Dict[str, Any]]] = {}

        for s in self._stations:
            cat = s.get("category", "")
            sub = s.get("subtext", "")
            name = s.get("name", "")

            found_genre = None
            for g_name in ["Rock", "Pop", "Sertanejo", "Pagode", "Forró", "Jazz", "Hip Hop", "Eletrônica", "Dance", "Gospel", "Católica", "Notícias", "Esportes", "MPB", "Clássica"]:
                if g_name.lower() in cat.lower() or g_name.lower() in sub.lower() or f"({g_name.lower()})" in name.lower():
                    found_genre = g_name
                    break

            if not found_genre and "Música >" in cat:
                parts = [p.strip() for p in cat.split(">")]
                found_genre = parts[1] if len(parts) > 1 else "Música Geral"

            if found_genre:
                if found_genre not in genres:
                    genres[found_genre] = []
                genres[found_genre].append(s)

        return dict(sorted(genres.items()))

    def get_international_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa rádios internacionais por país/região no catálogo em cache."""
        self.load()
        intl: Dict[str, List[Dict[str, Any]]] = {}

        for s in self._stations:
            cat = s.get("category", "")
            if "Internacional >" in cat:
                parts = [p.strip() for p in cat.split(">")]
                region = parts[1] if len(parts) > 1 else "Mundo"
                if region not in intl:
                    intl[region] = []
                intl[region].append(s)

        return dict(sorted(intl.items()))
