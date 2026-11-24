from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _get_storage_path() -> Path:
    """Retorna o caminho seguro para armazenamento de favoritos no perfil Kodi."""
    try:
        from saile_core.paths import addon_profile

        dest_dir = Path(addon_profile("plugin.audio.sradio"))
    except Exception:
        dest_dir = Path.home() / ".kodi_sradio"

    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / "favorites.json"


class FavoritesManager:
    """Gerencia as rádios favoritadas pelo usuário com persistência JSON."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or _get_storage_path()
        self._cache: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if self.file_path.is_file():
            try:
                with open(self.file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._cache = {
                            item["guide_id"]: item for item in data if "guide_id" in item
                        }
                    elif isinstance(data, dict):
                        self._cache = data
            except Exception:
                self._cache = {}
        self._loaded = True

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(list(self._cache.values()), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_all(self) -> list[dict[str, Any]]:
        self._load()
        return list(self._cache.values())

    def is_favorite(self, guide_id: str) -> bool:
        self._load()
        return guide_id in self._cache

    def toggle(self, station: dict[str, Any]) -> bool:
        """Adiciona ou remove a estação dos favoritos. Retorna True se adicionada."""
        self._load()
        guide_id = station.get("guide_id", "")
        if not guide_id:
            return False

        if guide_id in self._cache:
            del self._cache[guide_id]
            self._save()
            return False

        self._cache[guide_id] = station
        self._save()
        return True
