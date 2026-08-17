from __future__ import annotations

from saile_core.artwork import common_art


def notify_error(title: str, message: str, duration_ms: int = 5000) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("erro.png"), duration_ms, True)


def notify_success(title: str, message: str, duration_ms: int = 3500) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("check.png"), duration_ms, False)


def notify_info(title: str, message: str, duration_ms: int = 4500) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("sync.png"), duration_ms, False)
