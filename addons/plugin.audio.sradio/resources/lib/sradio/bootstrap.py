from __future__ import annotations

from typing import Any

from .catalog import RadioCatalog
from .favorites import FavoritesManager
from .routing import Request

_FOLDER_ICON_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (("music",), ("música", "musica"), "musica.png"),
    (("podcast",), ("podcast",), "podcast.png"),
    (("sport",), ("esporte",), "esportes.png"),
    (("talk",), ("notícia", "noticia"), "noticias.png"),
    (("local",), ("local",), "local.png"),
    (("best",), ("alta",), "alta.png"),
    (("lang",), ("idioma",), "idioma.png"),
    (("r101223",), ("brasil",), "brasil.png"),
    (("r0",), ("localização", "mundo"), "mundo.png"),
)

_HOME_BROWSE_ENTRIES: tuple[tuple[str, str, str, str], ...] = (
    (
        "Rádios Locais",
        "Browse.ashx?c=local",
        "local.png",
        "Emissoras locais sintonizadas na sua região.",
    ),
    (
        "Melhores & Em Alta",
        "Browse.ashx?c=best",
        "alta.png",
        "As estações mais populares e recomendadas pela rede TuneIn.",
    ),
    (
        "Brasil (Cidades & Estados)",
        "Browse.ashx?id=r101223",
        "brasil.png",
        "Todas as estações do Brasil organizadas por estados, capitais e cidades do interior.",
    ),
    (
        "Música por Gênero",
        "Browse.ashx?c=music",
        "musica.png",
        "Rock, Pop, Sertanejo, Pagode, Jazz, Hip Hop, Eletrônica, Clássica e muito mais.",
    ),
    (
        "Notícias & Conversas",
        "Browse.ashx?c=talk",
        "noticias.png",
        "Jornalismo, debates, economia e notícias do Brasil e do mundo.",
    ),
    (
        "Esportes ao Vivo",
        "Browse.ashx?c=sports",
        "esportes.png",
        "Transmissões de futebol, automobilismo e programas esportivos.",
    ),
    (
        "Por Localização (Mundo Inteiro)",
        "Browse.ashx?id=r0",
        "mundo.png",
        "Emissoras da América do Sul, América do Norte, Europa, Ásia, África e Oceania.",
    ),
    (
        "Por Idioma",
        "Browse.ashx?c=lang",
        "idioma.png",
        "Estações de rádio transmitindo em Português, Inglês, Espanhol e outros idiomas.",
    ),
    (
        "Podcasts & Programas",
        "Browse.ashx?c=podcast",
        "podcast.png",
        "Podcasts, entrevistas e episódios gravados dos principais programas de rádio.",
    ),
)

_STREAM_MIMETYPES = {
    "mp3": "audio/mpeg",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "hls": "application/x-mpegURL",
}


def _icon(scope: str, filename: str) -> str:
    try:
        from saile_core.artwork import artwork_path

        return artwork_path(scope, filename)
    except Exception:
        return ""


def _sradio_fanart() -> str:
    import os

    try:
        import xbmcaddon
        import xbmcvfs

        addon = xbmcaddon.Addon("plugin.audio.sradio")
        path = os.path.join(addon.getAddonInfo("path"), "fanart.jpg")
        return xbmcvfs.translatePath(path)
    except Exception:
        return os.path.join("addons", "plugin.audio.sradio", "fanart.jpg")


def _folder_icon_for(url: str, title: str) -> str:
    low_url = (url or "").lower()
    low_title = (title or "").lower()
    for url_tokens, title_tokens, icon_name in _FOLDER_ICON_RULES:
        if any(tok in low_url for tok in url_tokens) or any(
            tok in low_title for tok in title_tokens
        ):
            return _icon("common", icon_name)
    return _icon("common", "folder.png")


def _station_plot(
    name: str,
    subtext: str = "",
    category: str = "",
    fmt: Any = "",
    bitrate: Any = "",
    live_stream: bool = False,
) -> str:
    lines = [name]
    if subtext:
        lines.append(subtext)
    details: list[str] = []
    if live_stream:
        details.append("Transmissão oficial ao vivo.")
    if category and not live_stream:
        details.append(f"Categoria: {category}")
    if fmt:
        details.append(f"Formato: {str(fmt).upper() if live_stream else fmt}")
    if bitrate:
        details.append(f"Bitrate: {bitrate} kbps")
    if details:
        lines.append("")
        lines.extend(details)
    return "\n".join(lines)


def _set_video_metadata(
    item: Any,
    title: str,
    artist: str = "",
    genre: str = "",
    plot: str = "",
) -> None:
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
        info: dict[str, Any] = {
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
    context_menu: list[tuple[str, str]] | None = None,
) -> None:
    import xbmcgui
    import xbmcplugin

    item = xbmcgui.ListItem(label=label, offscreen=True)
    art: dict[str, str] = {}
    if icon:
        art["icon"] = icon
    if thumb or icon:
        art["thumb"] = thumb or icon
    if poster or icon:
        art["poster"] = poster or icon
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
    station: dict[str, Any],
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    guide_id = station.get("guide_id", "")
    name = station.get("name", "Rádio")
    subtext = station.get("subtext", "")
    logo = station.get("logo") or _icon("common", "radio.png")
    cat = station.get("category", "")
    bitrate = (
        station.get("bitrate") or station.get("stream_bitrate") or station.get("declared_bitrate")
    )
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
        plot=_station_plot(name, subtext, cat, fmt, bitrate),
        context_menu=[(fav_text, f"RunPlugin({fav_action})")],
    )


def show_home(
    request: Request,
    catalog: RadioCatalog,
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    total = catalog.total_count

    _add_directory_item(
        request.handle,
        "Buscar Rádio (Global)",
        request.url(action="search"),
        icon=_icon("common", "search.png"),
        fanart=fanart,
        plot=(
            "Pesquise em tempo real em mais de 100.000 rádios de todo o planeta "
            "por nome, cidade ou frequência."
        ),
    )

    fav_count = len(favorites.get_all())
    _add_directory_item(
        request.handle,
        f"Favoritos ({fav_count})",
        request.url(action="favorites"),
        icon=_icon("common", "favoritos.png"),
        fanart=fanart,
        plot="Suas emissoras de rádio favoritas salvas.",
    )

    for label, browse_url, icon_name, plot in _HOME_BROWSE_ENTRIES:
        _add_directory_item(
            request.handle,
            label,
            request.url(action="browse", url=browse_url),
            icon=_icon("common", icon_name),
            fanart=fanart,
            plot=plot,
        )

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
    stations: list[dict[str, Any]],
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    for station in stations:
        _render_station_item(request, station, favorites, fanart)
    _finish_directory(request.handle, content="videos")


def stream_mimetype(media_type: str) -> str:
    """Mimetype do stream TuneIn; vazio quando o tipo é desconhecido (o Kodi detecta)."""
    return _STREAM_MIMETYPES.get((media_type or "").strip().lower(), "")


def _open_fullscreen_player(player: Any) -> None:
    """Abre o player em tela cheia com o OSD frontal quando a reprodução já começou.

    setResolvedUrl/play retornam antes do stream abrir, e o Kodi recusa a janela de tela
    cheia sem reprodução ativa ou com o diálogo modal "Carregando" aberto (visto no
    kodi.log do emulador); por isso espera as duas condições por até 15 s.
    """
    import xbmc

    monitor = xbmc.Monitor()
    for _ in range(60):
        if player.isPlaying() and not xbmc.getCondVisibility("System.HasActiveModalDialog"):
            break
        if monitor.waitForAbort(0.25):
            return
    else:
        return
    window = "fullscreenvideo" if player.isPlayingVideo() else "visualisation"
    xbmc.executebuiltin(f"ActivateWindow({window})")


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
    logo = (
        param_logo
        or (fallback_station.get("logo") if fallback_station else "")
        or _icon("common", "radio.png")
    )
    cat = param_cat or (fallback_station.get("category") if fallback_station else "Rádio")

    try:
        import xbmcaddon

        addon = xbmcaddon.Addon("plugin.audio.sradio")
        preferred_bitrate = str(addon.getSetting("preferred_bitrate") or "highest")
    except Exception:
        preferred_bitrate = "highest"

    stream_info = catalog.resolve_station_stream(
        guide_id,
        fallback_station,
        preferred_bitrate=preferred_bitrate,
    )

    if not stream_info or not stream_info.get("url"):
        from saile_core.notifications import notify_error

        notify_error("sRadio", f"Stream indisponível para {name}")
        if request.handle >= 0:
            xbmcplugin.setResolvedUrl(request.handle, False, xbmcgui.ListItem(offscreen=True))
        return

    stream_url = stream_info["url"]
    bitrate = stream_info.get("bitrate") or ""
    media_type = stream_info.get("media_type") or "mp3"
    fanart_path = _sradio_fanart()

    item = xbmcgui.ListItem(label=name, path=stream_url, offscreen=True)
    mimetype = stream_mimetype(media_type)
    if mimetype:
        item.setContentLookup(False)
        item.setMimeType(mimetype)
    item.setArt(
        {
            "icon": logo,
            "thumb": logo,
            "poster": logo,
            "fanart": fanart_path,
            "clearlogo": logo,
        }
    )

    _set_video_metadata(
        item=item,
        title=name,
        artist=subtext or cat,
        genre=cat,
        plot=_station_plot(name, subtext, cat, media_type, bitrate, live_stream=True),
    )
    item.setProperty("IsPlayable", "true")
    item.setProperty("KeepAlive", "true")

    player = xbmc.Player()
    if request.handle >= 0:
        xbmcplugin.setResolvedUrl(request.handle, True, item)
    else:
        player.play(stream_url, item)

    _open_fullscreen_player(player)


def handle_toggle_fav(
    request: Request,
    catalog: RadioCatalog,
    favorites: FavoritesManager,
) -> None:
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
    action_label = "adicionada aos" if added else "removida dos"
    notify_success("sRadio", f"{station.get('name')} {action_label} Favoritos")
    if request.handle >= 0:
        import xbmcplugin

        xbmcplugin.endOfDirectory(request.handle, succeeded=True)
    xbmc.executebuiltin("Container.Refresh")


def handle_search(
    request: Request,
    catalog: RadioCatalog,
    favorites: FavoritesManager,
    fanart: str,
) -> None:
    query = request.params.get("query", "").strip()
    if not query:
        import xbmcgui

        dialog = xbmcgui.Dialog()
        query = dialog.input(
            "Buscar Rádio (Nome, Cidade ou Frequência):",
            type=xbmcgui.INPUT_ALPHANUM,
        )
        if query and request.handle >= 0:
            import xbmc
            import xbmcplugin

            xbmcplugin.endOfDirectory(request.handle, succeeded=False)
            xbmc.executebuiltin(f"Container.Update({request.url(action='search', query=query)})")
            return
    if not query:
        if request.handle >= 0:
            import xbmcplugin

            xbmcplugin.endOfDirectory(request.handle, succeeded=False)
        return

    results = catalog.search(query)
    if not results:
        from saile_core.notifications import notify_error

        notify_error("sRadio", f"Nenhuma rádio encontrada para '{query}'")
        show_home(request, catalog, favorites, fanart)
        return

    show_station_list(request, results, favorites, fanart)


def run(argv: list[str]) -> None:
    request = Request.from_argv(argv)
    catalog = RadioCatalog()
    favorites = FavoritesManager()
    fanart = _sradio_fanart()

    action = request.action
    if action == "play":
        handle_play(request, catalog)
    elif action == "toggle_fav":
        handle_toggle_fav(request, catalog, favorites)
    elif action == "search":
        handle_search(request, catalog, favorites, fanart)
    elif action == "browse":
        show_browse_directory(request, catalog, favorites, fanart)
    elif action == "favorites":
        show_station_list(request, favorites.get_all(), favorites, fanart)
    elif action == "all_stations":
        show_station_list(request, catalog.get_all(), favorites, fanart)
    else:
        show_home(request, catalog, favorites, fanart)
