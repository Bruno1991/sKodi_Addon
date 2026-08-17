from __future__ import annotations

import os


def addon_profile(addon_id: str) -> str:
    """Diretório gravável e isolado por perfil Kodi."""
    import xbmcvfs

    path = xbmcvfs.translatePath(f"special://profile/addon_data/{addon_id}")
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def addon_data_path(addon_id: str, *parts: str) -> str:
    return os.path.join(addon_profile(addon_id), *parts)
