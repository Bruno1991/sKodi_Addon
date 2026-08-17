from __future__ import annotations

import os

ARTWORK_ADDON_ID = "resource.images.saile"
_ALLOWED_SCOPES = frozenset({"common", "stv"})


def _resource_root() -> str:
    return "resource://resource.images.saile/media"


def artwork_path(scope: str, filename: str) -> str:
    """Retorna o caminho absoluto no sistema de arquivos para uma arte compartilhada."""
    return artwork_absolute_path(scope, filename)


def artwork_absolute_path(scope: str, filename: str) -> str:
    """Retorna o caminho absoluto de um asset no sistema de arquivos usando Kodi VFS."""
    if scope not in _ALLOWED_SCOPES:
        raise ValueError(f"Escopo de artwork inválido: {scope}")
    clean_name = os.path.basename(filename)

    try:
        import xbmcaddon
        import xbmcvfs
        addon_path = xbmcaddon.Addon(ARTWORK_ADDON_ID).getAddonInfo("path")
        full_path = os.path.join(addon_path, "resources", "media", scope, clean_name)
        return xbmcvfs.translatePath(full_path)
    except Exception:
        # Fallback para ambiente de teste fora do Kodi
        return os.path.join("addons", ARTWORK_ADDON_ID, "resources", "media", scope, clean_name)


def common_art(filename: str) -> str:
    """Retorna uma arte do escopo comum."""
    return artwork_path("common", filename)


def stv_art(filename: str) -> str:
    """Retorna uma arte do escopo do sTv."""
    return artwork_path("stv", filename)
