from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

from .catalog import RadioCatalog
from .favorites import FavoritesManager
from .routing import Request


def _icon(scope: str, filename: str) -> str:
    try:
        from saile_core.artwork import artwork_path
        return artwork_path(scope, filename)
    except Exception:
        return ""


def _add_directory_item(
    handle: int,
    label: str,
    url: str,
    icon: str = "",
    fanart: str = "",
    thumb: str = "",
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
    if fanart:
        art["fanart"] = fanart

    item.setArt(art)

    info = {
        "title": title or label,
        "artist": artist,
        "genre": genre,
        "comment": plot,
    }
    item.setInfo("music", info)

    if is_playable:
        item.setProperty("IsPlayable", "true")

    if context_menu:
        item.addContextMenuItems(context_menu)

    xbmcplugin.addDirectoryItem(handle, url, item, isFolder=is_folder)


def _finish_directory(handle: int, content: str = "songs") -> None:
    import xbmcplugin
    xbmcplugin.setContent(handle, content)
    xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True)


def _render_station_item(request: Request, station: Dict[str, Any], favorites: FavoritesManager, fanart: str) -> None:
    guide_id = station.get("guide_id", "")
    name = station.get("name", "Rádio")
    subtext = station.get("subtext", "")
    logo = station.get("logo") or _icon("common", "folder.png")
    cat = station.get("category", "")
    bitrate = station.get("stream_bitrate") or station.get("declared_bitrate")
    fmt = station.get("stream_media_type") or station.get("declared_formats")

    badge = f" [{fmt.upper()} {bitrate}k]" if fmt and bitrate else ""
    label = f"{name}{badge}"

    is_fav = favorites.is_favorite(guide_id)
    fav_text = "Remover dos Favoritos" if is_fav else "Adicionar aos Favoritos"
    fav_action = request.url(action="toggle_fav", guide_id=guide_id)

    context_menu = [
        (fav_text, f"RunPlugin({fav_action})"),
    ]

    play_url = request.url(action="play", guide_id=guide_id)
    _add_directory_item(
        handle=request.handle,
        label=label,
        url=play_url,
        icon=logo,
        thumb=logo,
        fanart=fanart,
        is_folder=False,
        is_playable=True,
        title=name,
        artist=subtext or cat,
        genre=cat,
        plot=f"{subtext}\n\nCategoria: {cat}\nFormato: {fmt}\nBitrate: {bitrate} kbps",
        context_menu=context_menu,
    )


def show_home(request: Request, catalog: RadioCatalog, favorites: FavoritesManager, fanart: str) -> None:
    total = catalog.total_count

    # 1. Buscar
    _add_directory_item(
        request.handle,
        "Buscar Rádio",
        request.url(action="search"),
        icon=_icon("common", "search.png"),
        fanart=fanart,
        plot="Pesquise estações de rádio por nome, gênero ou cidade.",
    )

    # 2. Favoritos
    fav_count = len(favorites.get_all())
    _add_directory_item(
        request.handle,
        f"Favoritos ({fav_count})",
        request.url(action="favorites"),
        icon=_icon("stv", "favoritos.png"),
        fanart=fanart,
        plot="Suas emissoras de rádio favoritas salvas.",
    )

    # 3. Melhores & Em Alta
    _add_directory_item(
        request.handle,
        "Melhores & Em Alta",
        request.url(action="featured"),
        icon=_icon("stv", "live.png"),
        fanart=fanart,
        plot="As emissoras mais ouvidas e populares do momento.",
    )

    # 4. Brasil por Cidades & Estados
    _add_directory_item(
        request.handle,
        "Brasil (Cidades & Estados)",
        request.url(action="brazil_menu"),
        icon=_icon("common", "folder.png"),
        fanart=fanart,
        plot="Estações de São Paulo, Rio de Janeiro, Minas, Curitiba e todo o Brasil.",
    )

    # 5. Gêneros Musicais
    _add_directory_item(
        request.handle,
        "Gêneros Musicais",
        request.url(action="genres_menu"),
        icon=_icon("common", "folder.png"),
        fanart=fanart,
        plot="Rock, Pop, Sertanejo, Pagode, Jazz, Hip Hop, Notícias e mais.",
    )

    # 6. Rádios Internacionais
    _add_directory_item(
        request.handle,
        "Rádios Internacionais",
        request.url(action="intl_menu"),
        icon=_icon("common", "folder.png"),
        fanart=fanart,
        plot="Emissoras da Europa, América do Norte e América do Sul.",
    )

    # 7. Catálogo Completo
    _add_directory_item(
        request.handle,
        f"Todas as Estações ({total})",
        request.url(action="all_stations"),
        icon=_icon("common", "folder.png"),
        fanart=fanart,
        plot=f"Lista completa com todas as {total} emissoras catalogadas.",
    )

    _finish_directory(request.handle, content="music")


def show_brazil_menu(request: Request, catalog: RadioCatalog, fanart: str) -> None:
    groups = catalog.get_brazil_groups()
    folder_icon = _icon("common", "folder.png")

    for city, stations in groups.items():
        _add_directory_item(
            request.handle,
            f"{city} ({len(stations)})",
            request.url(action="list_city", city=city),
            icon=folder_icon,
            fanart=fanart,
            plot=f"Estações de rádio em {city}.",
        )

    _finish_directory(request.handle, content="music")


def show_genres_menu(request: Request, catalog: RadioCatalog, fanart: str) -> None:
    genres = catalog.get_genre_groups()
    folder_icon = _icon("common", "folder.png")

    for genre, stations in genres.items():
        _add_directory_item(
            request.handle,
            f"{genre} ({len(stations)})",
            request.url(action="list_genre", genre=genre),
            icon=folder_icon,
            fanart=fanart,
            plot=f"Estações do gênero {genre}.",
        )

    _finish_directory(request.handle, content="music")


def show_intl_menu(request: Request, catalog: RadioCatalog, fanart: str) -> None:
    intl = catalog.get_international_groups()
    folder_icon = _icon("common", "folder.png")

    for region, stations in intl.items():
        _add_directory_item(
            request.handle,
            f"{region} ({len(stations)})",
            request.url(action="list_intl", region=region),
            icon=folder_icon,
            fanart=fanart,
            plot=f"Estações internacionais em {region}.",
        )

    _finish_directory(request.handle, content="music")


def show_station_list(request: Request, stations: List[Dict[str, Any]], favorites: FavoritesManager, fanart: str) -> None:
    for s in stations:
        _render_station_item(request, s, favorites, fanart)
    _finish_directory(request.handle, content="songs")


def handle_play(request: Request, catalog: RadioCatalog) -> None:
    import xbmcgui
    import xbmcplugin

    guide_id = request.params.get("guide_id", "")
    station = catalog.get_station(guide_id)
    if not station:
        xbmcplugin.setResolvedUrl(request.handle, False, xbmcgui.ListItem())
        return

    stream_url = station.get("direct_stream_url")
    if not stream_url:
        all_s = station.get("all_streams", [])
        if all_s:
            stream_url = all_s[0].get("url")

    if not stream_url:
        from saile_core.notifications import notify_error
        notify_error("sRadio", "Stream indisponível para esta estação")
        xbmcplugin.setResolvedUrl(request.handle, False, xbmcgui.ListItem())
        return

    name = station.get("name", "Rádio")
    subtext = station.get("subtext", "")
    logo = station.get("logo", "")

    item = xbmcgui.ListItem(label=name, path=stream_url)
    item.setArt({"icon": logo, "thumb": logo})
    item.setInfo("music", {
        "title": name,
        "artist": subtext or station.get("category", ""),
        "genre": station.get("category", ""),
    })
    item.setProperty("IsPlayable", "true")

    xbmcplugin.setResolvedUrl(request.handle, True, item)


def handle_toggle_fav(request: Request, catalog: RadioCatalog, favorites: FavoritesManager) -> None:
    import xbmc
    from saile_core.notifications import notify_success

    guide_id = request.params.get("guide_id", "")
    station = catalog.get_station(guide_id)
    if not station:
        return

    added = favorites.toggle(station)
    msg = f"{station.get('name')} adicionada aos Favoritos" if added else f"{station.get('name')} removida dos Favoritos"
    notify_success("sRadio", msg)
    xbmc.executebuiltin("Container.Refresh")


def handle_search(request: Request, catalog: RadioCatalog, favorites: FavoritesManager, fanart: str) -> None:
    import xbmcgui
    dialog = xbmcgui.Dialog()
    query = dialog.input("Buscar Rádio (Nome, Cidade ou Gênero):", type=xbmcgui.INPUT_ALPHANUM)
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
    fanart = _icon("stv", "fanart.jpg")

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

    if action == "favorites":
        favs = favorites.get_all()
        show_station_list(request, favs, favorites, fanart)
        return

    if action == "featured":
        show_station_list(request, catalog.get_featured(), favorites, fanart)
        return

    if action == "brazil_menu":
        show_brazil_menu(request, catalog, fanart)
        return

    if action == "list_city":
        city = request.params.get("city", "")
        groups = catalog.get_brazil_groups()
        stations = groups.get(city, [])
        show_station_list(request, stations, favorites, fanart)
        return

    if action == "genres_menu":
        show_genres_menu(request, catalog, fanart)
        return

    if action == "list_genre":
        genre = request.params.get("genre", "")
        genres = catalog.get_genre_groups()
        stations = genres.get(genre, [])
        show_station_list(request, stations, favorites, fanart)
        return

    if action == "intl_menu":
        show_intl_menu(request, catalog, fanart)
        return

    if action == "list_intl":
        region = request.params.get("region", "")
        intl = catalog.get_international_groups()
        stations = intl.get(region, [])
        show_station_list(request, stations, favorites, fanart)
        return

    if action == "all_stations":
        show_station_list(request, catalog.get_all(), favorites, fanart)
        return

    show_home(request, catalog, favorites, fanart)
