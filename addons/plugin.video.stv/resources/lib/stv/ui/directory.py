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
    media_type: str = "video",
    year: int | str | None = None,
    rating: float | None = None,
    duration: int | None = None,
) -> None:
    """Adiciona um item ao diretório Kodi com enquadramento de arte proporcional e nítido para InfoWall (54) e WideList."""
    import xbmcgui
    import xbmcplugin

    if is_folder and not icon:
        from saile_core.artwork import common_art
        icon = common_art("folder.png")

    item = xbmcgui.ListItem(label=label, offscreen=True)

    # 1. Enquadramento de Arte Sem Distorção e Sem Zoom
    # - Pastas, Menus e Canais: usam 'icon', 'thumb' e 'clearlogo' sem forçar 'poster' 2:3 (evita zoom/corte)
    # - Filmes (VOD) e Séries: recebem 'poster' 2:3 vertical nativo
    # - Episódios: recebem 'thumb' e 'landscape' 16:9
    art: dict[str, str] = {
        "icon": icon,
        "thumb": icon,
    }

    if fanart:
        art["fanart"] = fanart
        art["landscape"] = landscape or fanart
    elif landscape:
        art["landscape"] = landscape

    # 'poster' só é atribuído quando for filme/série com capa vertical real
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

    # 2. Metadados para Painel Lateral do InfoWall
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


def finish_directory(handle: int, content: str = "videos", view_mode: int = 54) -> None:
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

    # Trava a visualização no modo InfoWall (54) de forma consistente
    if view_mode:
        xbmc.executebuiltin(f"Container.SetViewMode({view_mode})")
