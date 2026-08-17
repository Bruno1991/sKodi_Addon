"""Manipulador de diretórios e itens de interface do Kodi com suporte nativo ao modo InfoWall."""
from __future__ import annotations


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
    media_type: str = "movie",
    year: int | str | None = None,
    rating: float | None = None,
    duration: int | None = None,
) -> None:
    """Adiciona um item ao diretório Kodi com as mesmas características de slot de VOD e Séries para todo o add-on."""
    import xbmcgui
    import xbmcplugin

    if is_folder and not icon:
        from saile_core.artwork import common_art
        icon = common_art("folder.png")

    item = xbmcgui.ListItem(label=label, offscreen=True)

    resolved_poster = poster or icon
    resolved_fanart = fanart or icon
    resolved_landscape = landscape or resolved_fanart

    art: dict[str, str] = {
        "icon": icon,
        "thumb": icon or resolved_poster,
        "poster": resolved_poster,
        "fanart": resolved_fanart,
        "landscape": resolved_landscape,
    }
    if clearlogo or icon:
        art["clearlogo"] = clearlogo or icon
    if banner:
        art["banner"] = banner

    item.setArt(art)

    # Metadados para o painel lateral do InfoWall
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

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=item, isFolder=is_folder)


def finish_directory(handle: int, content: str = "movies", view_mode: int = 54) -> None:
    """Finaliza o diretório e trava a visualização no modo InfoWall (54)."""
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

    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)

    if view_mode:
        xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
