from __future__ import annotations


def add_folder(
    handle: int,
    label: str,
    url: str,
    icon: str = "",
    fanart: str = "",
    is_folder: bool = True,
    context_menu: list[tuple[str, str]] | None = None,
) -> None:
    import xbmcgui
    import xbmcplugin

    if is_folder and not icon:
        from saile_core.artwork import common_art

        icon = common_art("folder.png")
    item = xbmcgui.ListItem(label=label)
    item.setArt({"icon": icon, "thumb": icon, "fanart": fanart})
    
    if context_menu:
        item.addContextMenuItems(context_menu)
        
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=item, isFolder=is_folder)


def finish_directory(handle: int, content: str) -> None:
    import xbmc
    import xbmcplugin

    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
    xbmc.executebuiltin("Container.SetViewMode(54)")
