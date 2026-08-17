from __future__ import annotations


def add_folder(
    handle: int,
    label: str,
    url: str,
    icon: str = "",
    fanart: str = "",
    is_folder: bool = True,
    context_menu: list[tuple[str, str]] | None = None,
    plot: str = "",
    is_playable: bool = False,
    media_type: str = "video",
) -> None:
    """Adiciona um item ao diretório Kodi com suporte completo a WideList, posters e metadata."""
    import xbmcgui
    import xbmcplugin

    if is_folder and not icon:
        from saile_core.artwork import common_art
        icon = common_art("folder.png")

    item = xbmcgui.ListItem(label=label)
    
    # Preenchimento completo de arte para WideList, Poster, Banner e Wall views
    art = {
        "icon": icon,
        "thumb": icon,
        "poster": icon,
        "banner": icon,
        "clearlogo": icon,
        "landscape": fanart or icon,
        "fanart": fanart or icon,
    }
    item.setArt(art)

    # Preenchimento de informações para visualizações com sinopse/plot
    info = {
        "title": label,
        "plot": plot or label,
        "mediatype": media_type if not is_folder else "video",
    }
    try:
        item.setInfo("video", info)
    except Exception:
        pass

    if is_playable:
        item.setProperty("IsPlayable", "true")

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=item, isFolder=is_folder)


def finish_directory(handle: int, content: str = "videos", view_mode: int | None = None) -> None:
    """Finaliza o diretório Kodi configurando métodos de ordenação e exibição."""
    import xbmc
    import xbmcplugin

    try:
        xbmcplugin.setContent(handle, content)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    except Exception:
        pass

    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
    
    if view_mode:
        xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
