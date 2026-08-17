from __future__ import annotations

import sys

from stv.navigation_contract import HOME_ENTRIES, SECTION_FIXED_ENTRIES, VALID_SECTIONS
from stv.parental import is_restricted, verify_parental_pin, verify_settings_access
from stv.routing import Request
from stv.app.services import AppContainer
from stv.app.sync import ensure_categories_loaded, ensure_streams_loaded
from stv.ui.dialogs import show_sync_dialog


def _icon(scope: str, filename: str) -> str:
    from saile_core.artwork import artwork_path

    return artwork_path(scope, filename)


def _show_home(request: Request, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory

    for label, action, section, scope, filename in HOME_ENTRIES:
        url = request.url(action=action, section=section) if section else request.url(action=action)
        icon_path = _icon(scope, filename)
        add_folder(
            request.handle,
            label,
            url,
            icon=icon_path,
            fanart=fanart,
            is_folder=True,
            media_type="video",
        )
    finish_directory(request.handle, content="videos", view_mode=54)


def _show_section(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory

    # 1. Fixed navigation items (Buscar e Favoritos)
    for label, action, scope, filename in SECTION_FIXED_ENTRIES:
        icon_path = _icon(scope, filename)
        add_folder(
            request.handle,
            label,
            request.url(action=action, section=section),
            icon=icon_path,
            fanart=fanart,
            is_folder=True,
            media_type="video",
        )
        
    # 2. Dynamic categories from database / Xtream
    ensure_categories_loaded(app, section)
    categories = app.catalog.get_categories(section)
    folder_icon = _icon("common", "folder.png")
    for cat in categories:
        add_folder(
            request.handle,
            cat.name,
            request.url(action="category", section=section, category_id=cat.category_id, title=cat.name),
            icon=folder_icon,
            fanart=fanart,
            is_folder=True,
            media_type="movie" if section == "vod" else "tvshow" if section == "series" else "video",
        )

    content_type = "movies" if section == "vod" else "tvshows" if section == "series" else "videos"
    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_category(request: Request, app: AppContainer, section: str, category_id: str, fanart: str, category_name: str = "") -> None:
    from stv.ui.directory import add_folder, finish_directory

    # Verificação de Controle Parental para a Categoria
    if is_restricted(category_name=category_name):
        import xbmcaddon
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=category_name or "Categoria Adulta"):
            finish_directory(request.handle, content="videos", view_mode=54)
            return

    ensure_streams_loaded(app, section, category_id)
    items = app.catalog.get_media_items(section, category_id)
    for item in items:
        icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})"),
        ]

        if section == "series":
            # Séries recebem poster vertical 2:3
            url = request.url(action="series_info", section=section, series_id=item.item_id, title=item.name)
            add_folder(
                request.handle,
                item.name,
                url,
                icon=icon_url,
                poster=icon_url,
                fanart=item.fanart or fanart,
                is_folder=True,
                context_menu=context_menu,
                plot=item.plot,
                media_type="tvshow",
            )
        elif section == "vod":
            # Filmes VOD recebem poster vertical 2:3
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            add_folder(
                request.handle,
                item.name,
                url,
                icon=icon_url,
                poster=icon_url,
                fanart=item.fanart or fanart,
                is_folder=False,
                is_playable=True,
                context_menu=context_menu,
                plot=item.plot,
                media_type="movie",
            )
        else:
            # Canais Live TV recebem poster no mesmo estilo de VOD
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            add_folder(
                request.handle,
                item.name,
                url,
                icon=icon_url,
                poster=icon_url,
                clearlogo=icon_url,
                fanart=item.fanart or fanart,
                is_folder=False,
                is_playable=True,
                context_menu=context_menu,
                plot=item.plot,
                media_type="movie",
            )

    content_type = "movies" if section in {"vod", "live"} else "tvshows" if section == "series" else "videos"
    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_series_info(request: Request, app: AppContainer, series_id: str, series_title: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory
    from saile_core.notifications import notify_error

    # Verificação de Controle Parental para Séries Adultas
    if is_restricted(name=series_title):
        import xbmcaddon
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=series_title):
            finish_directory(request.handle, content="episodes", view_mode=54)
            return

    try:
        data = app.xtream.get_series_info(series_id)
        episodes_by_season = data.get("episodes", {})
        info = data.get("info", {})
        series_cover = info.get("cover") or fanart
        series_plot = info.get("plot", "")

        for season_num, episodes in episodes_by_season.items():
            if not isinstance(episodes, list):
                continue
            for ep in episodes:
                if not isinstance(ep, dict):
                    continue
                ep_id = str(ep.get("id", ""))
                ep_title = str(ep.get("title") or f"Episódio {ep.get('episode_num', '')}").strip()
                ep_ext = str(ep.get("container_extension", "mp4"))
                ep_plot = str(ep.get("info", {}).get("plot") or series_plot)
                ep_thumb = str(ep.get("info", {}).get("movie_image") or series_cover)
                season_label = f"T{season_num.zfill(2)}E{str(ep.get('episode_num', '1')).zfill(2)} - {ep_title}"

                url = request.url(action="play", section="series", stream_id=ep_id, extension=ep_ext, title=ep_title)
                add_folder(
                    request.handle,
                    season_label,
                    url,
                    icon=ep_thumb,
                    poster=series_cover,
                    fanart=series_cover,
                    landscape=ep_thumb,
                    is_folder=False,
                    is_playable=True,
                    plot=ep_plot,
                    media_type="episode",
                )
    except Exception as exc:
        notify_error("sTv", f"Erro ao obter episódios: {exc}")

    finish_directory(request.handle, content="episodes", view_mode=54)


def _show_search(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    import xbmc
    from stv.ui.directory import add_folder, finish_directory
    
    keyboard = xbmc.Keyboard("", "Buscar...")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        query = keyboard.getText().strip()
        items = app.catalog.search_media(section, query)
        for item in items:
            icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
            fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
            enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
            context_menu = [
                ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
                ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})"),
            ]
            
            if section == "series":
                url = request.url(action="series_info", section=section, series_id=item.item_id, title=item.name)
                is_folder = True
                is_playable = False
                media_type = "tvshow"
                poster_val = icon_url
            elif section == "vod":
                url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
                is_folder = False
                is_playable = True
                media_type = "movie"
                poster_val = icon_url
            else:
                url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
                is_folder = False
                is_playable = True
                media_type = "movie"
                poster_val = icon_url

            add_folder(
                request.handle,
                item.name,
                url,
                icon=icon_url,
                poster=poster_val,
                clearlogo=icon_url if section == "live" else "",
                fanart=item.fanart or fanart,
                is_folder=is_folder,
                is_playable=is_playable,
                context_menu=context_menu,
                plot=item.plot,
                media_type=media_type,
            )
            
    content_type = "movies" if section in {"vod", "live"} else "tvshows" if section == "series" else "videos"
    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_favorites(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory
    
    items = app.catalog.get_favorites(section)
    for item in items:
        icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})"),
        ]

        if section == "series":
            url = request.url(action="series_info", section=section, series_id=item.item_id, title=item.name)
            is_folder = True
            is_playable = False
            media_type = "tvshow"
            poster_val = icon_url
        elif section == "vod":
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            is_folder = False
            is_playable = True
            media_type = "movie"
            poster_val = icon_url
        else:
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            is_folder = False
            is_playable = True
            media_type = "movie"
            poster_val = icon_url

        add_folder(
            request.handle,
            item.name,
            url,
            icon=icon_url,
            poster=poster_val,
            clearlogo=icon_url if section == "live" else "",
            fanart=item.fanart or fanart,
            is_folder=is_folder,
            is_playable=is_playable,
            context_menu=context_menu,
            plot=item.plot,
            media_type=media_type,
        )
        
    content_type = "movies" if section in {"vod", "live"} else "tvshows" if section == "series" else "videos"
    finish_directory(request.handle, content=content_type, view_mode=54)


def _play_item(request: Request, app: AppContainer, section: str, stream_id: str, extension: str, title: str = "") -> None:
    from stv.ui.player import play_video
    import xbmcaddon

    # Verificação de Controle Parental para Reprodução de Conteúdo Restrito
    if is_restricted(name=title):
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=title or "Conteúdo Restrito"):
            return
    
    url = app.xtream.stream_url(section, stream_id, extension)
    play_video(request.handle, app, section, stream_id, url)


def run(argv: list[str]) -> None:
    """Entrypoint estrutural com o contrato oficial de navegação do sTv."""
    import xbmcaddon

    request = Request.from_argv(argv)
    addon = xbmcaddon.Addon()
    fanart = addon.getAddonInfo("fanart")

    settings = {
        "xtream_url": addon.getSetting("xtream_url"),
        "xtream_username": addon.getSetting("xtream_username"),
        "xtream_password": addon.getSetting("xtream_password"),
        "tmdb_language": addon.getSetting("tmdb_language"),
        "profile_path": __import__("xbmcvfs").translatePath(addon.getAddonInfo("profile")),
    }
    app = AppContainer(settings)

    if request.action in {"", "home"}:
        _show_home(request, fanart)
        return

    if request.action == "section":
        section = request.params.get("section", "")
        if section in VALID_SECTIONS:
            _show_section(request, app, section, fanart)
            return

    if request.action == "category":
        section = request.params.get("section", "")
        category_id = request.params.get("category_id", "")
        title = request.params.get("title", "")
        if section in VALID_SECTIONS and category_id:
            _show_category(request, app, section, category_id, fanart, category_name=title)
            return

    if request.action == "series_info":
        series_id = request.params.get("series_id", "")
        title = request.params.get("title", "Série")
        if series_id:
            _show_series_info(request, app, series_id, title, fanart)
            return

    if request.action == "play":
        section = request.params.get("section", "")
        stream_id = request.params.get("stream_id", "")
        extension = request.params.get("extension", "")
        title = request.params.get("title", "")
        if section in VALID_SECTIONS and stream_id:
            _play_item(request, app, section, stream_id, extension, title=title)
            return

    if request.action in {"settings", "open_settings"}:
        if verify_settings_access(addon):
            addon.openSettings()
        return

    if request.action == "sync":
        show_sync_dialog(app)
        return

    if request.action == "search":
        section = request.params.get("section", "")
        if section in VALID_SECTIONS:
            _show_search(request, app, section, fanart)
            return

    if request.action == "favorites":
        section = request.params.get("section", "")
        if section in VALID_SECTIONS:
            _show_favorites(request, app, section, fanart)
            return

    if request.action == "toggle_fav":
        section = request.params.get("section", "")
        stream_id = request.params.get("stream_id", "")
        if section in VALID_SECTIONS and stream_id:
            import xbmc
            from saile_core.notifications import notify_success
            added = app.catalog.toggle_favorite(section, stream_id)
            msg = "Adicionado aos Favoritos" if added else "Removido dos Favoritos"
            notify_success("sTv", msg)
            xbmc.executebuiltin("Container.Refresh")
            return

    if request.action == "enrich":
        section = request.params.get("section", "")
        stream_id = request.params.get("stream_id", "")
        title = request.params.get("title", "")
        if section in {"vod", "series"} and stream_id and title:
            import xbmc
            from saile_core.notifications import notify_success, notify_error
            success = app.catalog.enrich_item(app.tmdb, section, stream_id, title)
            if success:
                notify_success("TMDB", "Metadados atualizados")
                xbmc.executebuiltin("Container.Refresh")
            else:
                notify_error("TMDB", "Nenhum metadado encontrado")
            return

    _show_home(request, fanart)
