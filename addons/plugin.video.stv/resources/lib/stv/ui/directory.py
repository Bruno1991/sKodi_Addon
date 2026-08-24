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
    is_folder: bool = True,
    context_menu: list[tuple[str, str]] | None = None,
    plot: str = "",
    is_playable: bool = False,
    media_type: str = "movie",
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

    primary_poster = poster or icon or fanart
    primary_icon = icon or poster or fanart
    primary_fanart = fanart or landscape or primary_poster
    primary_landscape = landscape or fanart or primary_poster

    art: dict[str, str] = {
        "icon": primary_icon,
        "thumb": primary_poster or primary_icon,
        "poster": primary_poster or primary_icon,
        "tvshow.poster": primary_poster or primary_icon,
        "season.poster": primary_poster or primary_icon,
        "fanart": primary_fanart,
        "landscape": primary_landscape,
        "clearlogo": clearlogo or primary_icon,
        "banner": banner or primary_landscape or primary_poster,
        "keyart": primary_poster or primary_icon,
    }

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
