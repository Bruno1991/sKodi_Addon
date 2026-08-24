"""Manipulador de diretórios e itens de interface do Kodi com suporte nativo e forçado ao modo InfoWall / Poster."""
from __future__ import annotations

INFOWALL_VIEW_MODE = 54


def add_folder(
    handle: int,
    label: str,
    url: str,
    icon: str = "",
    fanart: str = "",
    poster: str = "",
    banner: str = "",
    clearlogo: str = "",
    landscape: str = "",
    thumb: str = "",
    is_folder: bool = True,
    context_menu: list[tuple[str, str]] | None = None,
    plot: str = "",
    is_playable: bool = False,
    media_type: str = "video",
    year: int | str | None = None,
    rating: float | None = None,
    duration: int | None = None,
    label2: str = "",
    properties: dict[str, str] | None = None,
) -> None:
    """Adiciona um item ao diretório Kodi garantindo que poster e thumb estejam 100% preenchidos para InfoWall."""
    import xbmcgui
    import xbmcplugin

    if is_folder and not icon:
        from saile_core.artwork import common_art
        icon = common_art("folder.png")

    try:
        item = xbmcgui.ListItem(label=label, label2=label2, offscreen=True)
    except TypeError:
        item = xbmcgui.ListItem(label=label, offscreen=True)
        if label2:
            try:
                item.setLabel2(label2)
            except Exception:
                pass

    art: dict[str, str] = {}
    if icon:
        art["icon"] = icon

    effective_thumb = thumb or icon or poster
    if effective_thumb:
        art["thumb"] = effective_thumb

    if poster:
        art["poster"] = poster
        art["keyart"] = poster
        if media_type in {"tvshow", "season", "episode"}:
            art["tvshow.poster"] = poster
            art["season.poster"] = poster
    elif media_type in {"movie", "tvshow", "season"} and icon:
        art["poster"] = icon
        art["keyart"] = icon
        if media_type in {"tvshow", "season"}:
            art["tvshow.poster"] = icon
            art["season.poster"] = icon

    if fanart:
        art["fanart"] = fanart
    if landscape:
        art["landscape"] = landscape
    elif fanart:
        art["landscape"] = fanart

    if clearlogo:
        art["clearlogo"] = clearlogo
    elif icon and not poster and media_type == "video":
        art["clearlogo"] = icon

    if banner:
        art["banner"] = banner

    item.setArt(art)

    info_dict = {
        "title": label,
        "plot": plot or label,
        "mediatype": media_type,
    }
    if year:
        try:
            info_dict["year"] = int(year)
        except Exception:
            pass
    if rating:
        try:
            info_dict["rating"] = float(rating)
        except Exception:
            pass
    if duration:
        try:
            info_dict["duration"] = int(duration)
        except Exception:
            pass

    try:
        item.setInfo("video", info_dict)
    except Exception:
        pass

    if is_playable:
        item.setProperty("IsPlayable", "true")

    # Propriedades de skin para fixar visualização InfoWall / Poster
    item.setProperty("widget", "true")
    item.setProperty("skin.infowall", "true")

    for key, value in (properties or {}).items():
        item.setProperty(str(key), str(value))

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=item, isFolder=is_folder)


def init_directory(handle: int, content: str = "movies", view_mode: int = INFOWALL_VIEW_MODE) -> None:
    """Inicializa o diretório definindo o tipo de conteúdo e o modo de visualização antes de adicionar itens."""
    import xbmc
    import xbmcplugin

    try:
        xbmcplugin.setContent(handle, content)
    except Exception:
        pass

    if view_mode:
        try:
            xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
        except Exception:
            pass


def finish_directory(
    handle: int,
    content: str = "movies",
    view_mode: int = INFOWALL_VIEW_MODE,
) -> None:
    """Finaliza qualquer diretório e reaplica o contrato universal InfoWall 54 com preservação de cache de navegação."""
    import xbmc
    import xbmcplugin

    try:
        xbmcplugin.setContent(handle, content)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_GENRE)
    except Exception:
        pass

    if view_mode:
        try:
            xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
        except Exception:
            pass

    # Usar cacheToDisc=True permite que o Kodi guarde a pilha de diretórios navegados sem reconstruir para o modo List no retorno (Back button)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=True)

    if view_mode:
        try:
            xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
        except Exception:
            pass


def ensure_infowall_in_kodi_db(path_pattern: str = "plugin://plugin.video.stv%") -> None:
    """Garante que o banco ViewModes6.db do Kodi tenha todas as rotas gravadas como 131126 (InfoWall 54)."""
    import os
    import sqlite3
    from pathlib import Path

    try:
        candidates = []
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(
                Path(local_app_data)
                / "Packages"
                / "XBMCFoundation.Kodi_4n2hpmxwrvr6p"
                / "LocalCache"
                / "Roaming"
                / "Kodi"
                / "userdata"
                / "Database"
                / "ViewModes6.db"
            )
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            candidates.append(
                Path(app_data) / "Kodi" / "userdata" / "Database" / "ViewModes6.db"
            )

        for db_path in candidates:
            if db_path.exists():
                conn = sqlite3.connect(db_path, timeout=1.0)
                conn.execute(
                    "UPDATE view SET viewMode = 131126 WHERE path LIKE ? AND viewMode != 131126",
                    (path_pattern,),
                )
                conn.commit()
                conn.close()
    except Exception:
        pass

