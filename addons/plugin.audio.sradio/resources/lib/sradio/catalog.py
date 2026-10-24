from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_text(text: str) -> str:
    """Remove acentos e converte para minúsculas para buscas insensíveis."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower().strip()


class RadioCatalog:
    """Gerenciador do catálogo de mais de 1.500 estações de rádio."""

    def __init__(self, data_path: Optional[str] = None):
        if data_path is None:
            base_dir = Path(__file__).resolve().parents[2]
            data_path = str(base_dir / "data" / "radios.json")

        self.data_path = data_path
        self._stations: List[Dict[str, Any]] = []
        self._station_map: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

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

    def get_featured(self) -> List[Dict[str, Any]]:
        """Retorna rádios de destaque, melhores e em alta."""
        self.load()
        featured = []
        for s in self._stations:
            cat = s.get("category", "")
            if "Featured" in cat or "Melhores" in cat or "Em Alta" in cat:
                featured.append(s)

        # Fallback se a categoria estiver vazia
        return featured if featured else self._stations[:50]

    def get_brazil_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa rádios brasileiras por cidade/estado."""
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

        # Ordenar cidades por relevância/alfabética
        return dict(sorted(groups.items()))

    def get_genre_groups(self) -> Dict[str, List[Dict[str, Any]]]:
        """Agrupa rádios por gêneros musicais."""
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
        """Agrupa rádios internacionais por país/região."""
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
