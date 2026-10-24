from __future__ import annotations

import sys
import urllib.parse
from typing import Any, Dict, List, Optional

from .catalog import RadioCatalog, TuneInAPI
from .favorites import FavoritesManager
from .routing import Request


def _icon(scope: str, filename: str) -> str:
    try:
        from saile_core.artwork import artwork_path
        return artwork_path(scope, filename)
    except Exception:
        return ""


def _sradio_fanart() -> str:
    try:
        import os
        import xbmcaddon
        import xbmcvfs
        addon = xbmcaddon.Addon("plugin.audio.sradio")
        path = os.path.join(addon.getAddonInfo("path"), "fanart.jpg")
        return xbmcvfs.translatePath(path)
    except Exception:
        import os
        return os.path.join("addons", "plugin.audio.sradio", "fanart.jpg")


def _folder_icon_for(url: str, title: str) -> str:
    low_url = (url or "").lower()
    low_title = (title or "").lower()
    if "music" in low_url or "música" in low_title or "musica" in low_title:
        return _icon("common", "musica.png")
    if "podcast" in low_url or "podcast" in low_title:
        return _icon("common", "podcast.png")
    if "sport" in low_url or "esporte" in low_title:
        return _icon("common", "esportes.png")
    if "talk" in low_url or "notícia" in low_title or "noticia" in low_title:
        return _icon("common", "noticias.png")
    if "local" in low_url or "local" in low_title:
        return _icon("common", "local.png")
    if "best" in low_url or "alta" in low_title:
        return _icon("common", "alta.png")
    if "lang" in low_url or "idioma" in low_title:
        return _icon("common", "idioma.png")
    if "r101223" in low_url or "brasil" in low_title:
        return _icon("common", "brasil.png")
    if "r0" in low_url or "localização" in low_title or "mundo" in low_title:
        return _icon("common", "mundo.png")
    return _icon("common", "folder.png")


def _set_video_metadata(
    item: Any,
    title: str,
    artist: str = "",
    genre: str = "",
    plot: str = "",
) -> None:
    # Kodi 20/21+ InfoTagVideo nativo com suporte a controles OSD de vídeo
    try:
        tag = item.getVideoInfoTag()
        if hasattr(tag, "setTitle"):
            tag.setTitle(title)
        if artist and hasattr(tag, "setArtists"):
            tag.setArtists([artist])
        if genre and hasattr(tag, "setGenres"):
            tag.setGenres([genre])
        if plot and hasattr(tag, "setPlot"):
            tag.setPlot(plot)
        if hasattr(tag, "setMediaType"):
            tag.setMediaType("video")
        if hasattr(tag, "setTagLine"):
            tag.setTagLine("Rádio ao Vivo - sRadio")
        return
    except Exception:
        pass

    try:
        info: Dict[str, Any] = {
            "title": title,
            "plot": plot,
            "mediatype": "video",
            "tagline": "Rádio ao Vivo - sRadio",
        }
        if artist:
            info["artist"] = [artist]
        if genre:
            info["genre"] = [genre]
        item.setInfo("video", info)
    except Exception:
        pass


def _add_directory_item(
    handle: int,
    label: str,
    url: str,
    icon: str = "",
    fanart: str = "",
    thumb: str = "",
    poster: str = "",
    is_folder: bool = True,
    is_playable: bool = False,
    title: str = "",
    artist: str = "",
    genre: str = "",
    plot: str = "",
    context_menu: Optional[List[tuple[str, str]]] = None,
) -> None:
    import xbmcgui
    import xbmcplugin

    item = xbmcgui.ListItem(label=label, offscreen=True)
    art: Dict[str, str] = {}
    if icon:
        art["icon"] = icon
    if thumb:
        art["thumb"] = thumb
    elif icon:
        art["thumb"] = icon
    if poster:
        art["poster"] = poster
    elif icon:
        art["poster"] = icon
    if fanart:
        art["fanart"] = fanart

    item.setArt(art)

    _set_video_metadata(
        item=item,
        title=title or label,
        artist=artist,
        genre=genre,
        plot=plot,
    )

    if is_playable:
        item.setProperty("IsPlayable", "true")
        item.setProperty("KeepAlive", "true")

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=is_folder)


def _finish_directory(handle: int, content: str = "videos") -> None:
    import xbmcplugin
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True)


def _render_station_item(
    request: Request,
    station: Dict[str, Any],
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    guide_id = station.get("guide_id", "")
    name = station.get("name", "Rádio")
    subtext = station.get("subtext", "")
    logo = station.get("logo") or _icon("common", "radio.png")
    cat = station.get("category", "")
    bitrate = station.get("bitrate") or station.get("stream_bitrate") or station.get("declared_bitrate")
    fmt = station.get("declared_formats") or station.get("stream_media_type")

    badge = f" [{fmt.upper()} {bitrate}k]" if fmt and bitrate else ""
    label = f"{name}{badge}"

    is_fav = favorites.is_favorite(guide_id)
    fav_text = "Remover dos Favoritos" if is_fav else "Adicionar aos Favoritos"
    fav_action = request.url(
        action="toggle_fav",
        guide_id=guide_id,
        name=name,
        subtext=subtext,
        logo=logo,
        cat=cat,
    )

    context_menu = [
        (fav_text, f"RunPlugin({fav_action})"),
    ]

    play_url = request.url(
        action="play",
        guide_id=guide_id,
        name=name,
        subtext=subtext,
        logo=logo,
        cat=cat,
    )
    _add_directory_item(
        handle=request.handle,
        label=label,
        url=play_url,
        icon=logo,
        thumb=logo,
        poster=logo,
        fanart=fanart,
        is_folder=False,
        is_playable=True,
        title=name,
        artist=subtext or cat,
        genre=cat,
        plot=f"{name}\n{subtext}\n\nCategoria: {cat}\nFormato: {fmt}\nBitrate: {bitrate} kbps",
        context_menu=context_menu,
    )


def show_home(request: Request, catalog: RadioCatalog, favorites: FavoritesManager, fanart: str) -> None:
    total = catalog.total_count

    # 1. Buscar Global (TuneIn Live Search)
    _add_directory_item(
        request.handle,
        "Buscar Rádio (Global)",
        request.url(action="search"),
        icon=_icon("common", "search.png"),
        fanart=fanart,
        plot="Pesquise em tempo real em mais de 100.000 rádios de todo o planeta por nome, cidade ou frequência.",
    )

    # 2. Favoritos
    fav_count = len(favorites.get_all())
    _add_directory_item(
        request.handle,
        f"Favoritos ({fav_count})",
        request.url(action="favorites"),
        icon=_icon("common", "favoritos.png"),
        fanart=fanart,
        plot="Suas emissoras de rádio favoritas salvas.",
    )

    # 3. Rádios Locais (TuneIn Local)
    _add_directory_item(
        request.handle,
        "Rádios Locais",
        request.url(action="browse", url="Browse.ashx?c=local"),
        icon=_icon("common", "local.png"),
        fanart=fanart,
        plot="Emissoras locais sintonizadas na sua região.",
    )

    # 4. Melhores & Em Alta (TuneIn Trending)
    _add_directory_item(
        request.handle,
        "Melhores & Em Alta",
        request.url(action="browse", url="Browse.ashx?c=best"),
        icon=_icon("common", "alta.png"),
        fanart=fanart,
        plot="As estações mais populares e recomendadas pela rede TuneIn.",
    )

    # 5. Brasil (Todas as Cidades & Estados via TuneIn)
    _add_directory_item(
        request.handle,
        "Brasil (Cidades & Estados)",
        request.url(action="browse", url="Browse.ashx?id=r101223"),
        icon=_icon("common", "brasil.png"),
        fanart=fanart,
        plot="Todas as estações do Brasil organizadas por estados, capitais e cidades do interior.",
    )

    # 6. Música por Gênero
    _add_directory_item(
        request.handle,
        "Música por Gênero",
        request.url(action="browse", url="Browse.ashx?c=music"),
        icon=_icon("common", "musica.png"),
        fanart=fanart,
        plot="Rock, Pop, Sertanejo, Pagode, Jazz, Hip Hop, Eletrônica, Clássica e muito mais.",
    )

    # 7. Notícias & Conversas (Talk)
    _add_directory_item(
        request.handle,
        "Notícias & Conversas",
        request.url(action="browse", url="Browse.ashx?c=talk"),
        icon=_icon("common", "noticias.png"),
        fanart=fanart,
        plot="Jornalismo, debates, economia e notícias do Brasil e do mundo.",
    )

    # 8. Esportes
    _add_directory_item(
        request.handle,
        "Esportes ao Vivo",
        request.url(action="browse", url="Browse.ashx?c=sports"),
        icon=_icon("common", "esportes.png"),
        fanart=fanart,
        plot="Transmissões de futebol, automobilismo e programas esportivos.",
    )

    # 9. Por Localização (Mundo Inteiro)
    _add_directory_item(
        request.handle,
        "Por Localização (Mundo Inteiro)",
        request.url(action="browse", url="Browse.ashx?id=r0"),
        icon=_icon("common", "mundo.png"),
        fanart=fanart,
        plot="Emissoras da América do Sul, América do Norte, Europa, Ásia, África e Oceania.",
    )

    # 10. Por Idioma (By Language)
    _add_directory_item(
        request.handle,
        "Por Idioma",
        request.url(action="browse", url="Browse.ashx?c=lang"),
        icon=_icon("common", "idioma.png"),
        fanart=fanart,
        plot="Estações de rádio transmitindo em Português, Inglês, Espanhol e outros idiomas.",
    )

    # 11. Podcasts & Programas
    _add_directory_item(
        request.handle,
        "Podcasts & Programas",
        request.url(action="browse", url="Browse.ashx?c=podcast"),
        icon=_icon("common", "podcast.png"),
        fanart=fanart,
        plot="Podcasts, entrevistas e episódios gravados dos principais programas de rádio.",
    )

    # 12. Catálogo em Cache Offline
    _add_directory_item(
        request.handle,
        f"Catálogo em Cache Offline ({total})",
        request.url(action="all_stations"),
        icon=_icon("common", "radio.png"),
        fanart=fanart,
        plot=f"Lista completa pré-sincronizada com {total} estações para reprodução instantânea.",
    )

    _finish_directory(request.handle, content="videos")


def show_browse_directory(
    request: Request,
    catalog: RadioCatalog,
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    """Navega dinamicamente pelas pastas e estações da API TuneIn."""
    browse_url = request.params.get("url", "Browse.ashx")
    items = catalog.api.browse(browse_url)

    if not items:
        from saile_core.notifications import notify_error
        notify_error("sRadio", "Nenhum conteúdo retornado para esta categoria")
        show_home(request, catalog, favorites, fanart)
        return

    folder_icon = _icon("common", "folder.png")
    for item in items:
        if item.get("is_folder"):
            sub_url = item.get("url", "")
            title = item.get("title", "Pasta")
            logo = item.get("logo") or _folder_icon_for(sub_url, title)
            subtext = item.get("subtext", "")
            _add_directory_item(
                request.handle,
                title,
                request.url(action="browse", url=sub_url),
                icon=logo,
                thumb=logo,
                fanart=fanart,
                plot=subtext or f"Explorar {title}.",
            )
        else:
            _render_station_item(request, item, favorites, fanart)

    _finish_directory(request.handle, content="videos")


def show_station_list(
    request: Request,
    stations: List[Dict[str, Any]],
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    for s in stations:
        _render_station_item(request, s, favorites, fanart)
    _finish_directory(request.handle, content="videos")


def handle_play(request: Request, catalog: RadioCatalog) -> None:
    """Resolve stream dinamicamente e ativa o Player OSD frontal em tela cheia (estilo vídeo)."""
    import xbmc
    import xbmcgui
    import xbmcplugin

    guide_id = request.params.get("guide_id", "")
    param_name = request.params.get("name")
    param_subtext = request.params.get("subtext", "")
    param_logo = request.params.get("logo", "")
    param_cat = request.params.get("cat", "")

    fallback_station = catalog.get_station(guide_id)
    name = param_name or (fallback_station.get("name") if fallback_station else "Rádio ao Vivo")
    subtext = param_subtext or (fallback_station.get("subtext") if fallback_station else "")
    logo = param_logo or (fallback_station.get("logo") if fallback_station else "") or _icon("common", "radio.png")
    cat = param_cat or (fallback_station.get("category") if fallback_station else "Rádio")

    try:
        import xbmcaddon
        preferred_bitrate = str(xbmcaddon.Addon("plugin.audio.sradio").getSetting("preferred_bitrate") or "highest")
    except Exception:
        preferred_bitrate = "highest"

    # Resolução dinâmica do stream via Tune.ashx (com tokens frescos) ou fallback para cache
    stream_info = catalog.resolve_station_stream(guide_id, fallback_station, preferred_bitrate=preferred_bitrate)

    if not stream_info or not stream_info.get("url"):
        from saile_core.notifications import notify_error
        notify_error("sRadio", f"Stream indisponível para {name}")
        xbmcplugin.setResolvedUrl(request.handle, False, xbmcgui.ListItem())
        return

    stream_url = stream_info["url"]
    bitrate = stream_info.get("bitrate") or ""
    media_type = stream_info.get("media_type") or "mp3"
    fanart_path = _sradio_fanart()

    item = xbmcgui.ListItem(label=name, path=stream_url, offscreen=True)
    item.setContentLookup(False)
    item.setArt({
        "icon": logo,
        "thumb": logo,
        "poster": logo,
        "fanart": fanart_path,
        "clearlogo": logo,
    })

    _set_video_metadata(
        item=item,
        title=name,
        artist=subtext or cat,
        genre=cat,
        plot=f"{name}\n{subtext}\n\nTransmissão oficial ao vivo.\nFormato: {media_type.upper()}\nBitrate: {bitrate} kbps",
    )
    item.setProperty("IsPlayable", "true")
    item.setProperty("KeepAlive", "true")
    item.setProperty("mimetype", "audio/mpeg" if media_type == "mp3" else "application/x-mpegURL")

    # Resolver URL para o Kodi iniciar a reprodução
    if request.handle > 0:
        xbmcplugin.setResolvedUrl(request.handle, True, item)
    else:
        xbmc.Player().play(stream_url, item)

    # Forçar a abertura da janela do player em tela cheia com barra de controles frontais
    xbmc.executebuiltin("ActivateWindow(fullscreenvideo)")


def handle_toggle_fav(request: Request, catalog: RadioCatalog, favorites: FavoritesManager) -> None:
    import xbmc
    from saile_core.notifications import notify_success

    guide_id = request.params.get("guide_id", "")
    station = catalog.get_station(guide_id)
    if not station:
        station = {
            "guide_id": guide_id,
            "name": request.params.get("name", "Rádio"),
            "subtext": request.params.get("subtext", ""),
            "logo": request.params.get("logo", ""),
            "category": request.params.get("cat", ""),
        }

    added = favorites.toggle(station)
    msg = f"{station.get('name')} adicionada aos Favoritos" if added else f"{station.get('name')} removida dos Favoritos"
    notify_success("sRadio", msg)
    if request.handle >= 0:
        import xbmcplugin
        xbmcplugin.endOfDirectory(request.handle, succeeded=True)
    xbmc.executebuiltin("Container.Refresh")


def handle_search(request: Request, catalog: RadioCatalog, favorites: FavoritesManager, fanart: str) -> None:
    query = request.params.get("query", "").strip()
    if not query:
        import xbmcgui
        dialog = xbmcgui.Dialog()
        query = dialog.input("Buscar Rádio (Nome, Cidade ou Frequência):", type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        show_home(request, catalog, favorites, fanart)
        return

    results = catalog.search(query)
    if not results:
        from saile_core.notifications import notify_error
        notify_error("sRadio", f"Nenhuma rádio encontrada para '{query}'")
        show_home(request, catalog, favorites, fanart)
        return

    show_station_list(request, results, favorites, fanart)


def run(argv: List[str]) -> None:
    request = Request.from_argv(argv)
    catalog = RadioCatalog()
    favorites = FavoritesManager()
    fanart = _sradio_fanart()

    action = request.action

    if action == "play":
        handle_play(request, catalog)
        return

    if action == "toggle_fav":
        handle_toggle_fav(request, catalog, favorites)
        return

    if action == "search":
        handle_search(request, catalog, favorites, fanart)
        return

    if action == "browse":
        show_browse_directory(request, catalog, favorites, fanart)
        return

    if action == "favorites":
        favs = favorites.get_all()
        show_station_list(request, favs, favorites, fanart)
        return

    if action == "featured":
        show_station_list(request, catalog.get_featured(), favorites, fanart)
        return

    if action == "brazil_menu":
        show_browse_directory(request, catalog, favorites, fanart)
        return

    if action == "genres_menu":
        show_browse_directory(request, catalog, favorites, fanart)
        return

    if action == "intl_menu":
        show_browse_directory(request, catalog, favorites, fanart)
        return

    if action == "all_stations":
        show_station_list(request, catalog.get_all(), favorites, fanart)
        return

    show_home(request, catalog, favorites, fanart)
