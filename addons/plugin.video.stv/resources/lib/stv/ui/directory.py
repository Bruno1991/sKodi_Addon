"""Manipulador de diretórios e itens de interface do Kodi com suporte nativo ao modo InfoWall."""
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
    """Adiciona um item ao diretório Kodi com o padrão de slot e enquadramento de VOD e Séries da v0.2.6."""
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

    art: dict[str, str] = {
        "icon": icon,
        "thumb": icon,
    }

    if fanart:
        art["fanart"] = fanart
        art["landscape"] = landscape or fanart
    elif landscape:
        art["landscape"] = landscape

    if poster:
        art["poster"] = poster
    elif not is_folder and media_type in {"movie", "tvshow", "season"} and icon:
        art["poster"] = icon

    if clearlogo:
        art["clearlogo"] = clearlogo
    elif icon:
        art["clearlogo"] = icon

    if banner:
        art["banner"] = banner

    item.setArt(art)

    info_dict = {
        "title": label,
        "plot": plot or label,
        "mediatype": media_type if not is_folder else "video",
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

    for key, value in (properties or {}).items():
        item.setProperty(str(key), str(value))

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=item, isFolder=is_folder)


def init_directory(handle: int, content: str = "movies") -> None:
    """Inicializa o diretório definindo o tipo de conteúdo antes de adicionar itens."""
    import xbmcplugin

    try:
        xbmcplugin.setContent(handle, content)
    except Exception:
        pass


def finish_directory(
    handle: int,
    content: str = "movies",
    view_mode: int = INFOWALL_VIEW_MODE,
) -> None:
    """Finaliza qualquer diretório e reaplica o contrato universal InfoWall 54."""
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
        xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)

    if view_mode:
        xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
