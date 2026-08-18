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


def _item_icon(section: str, icon_str: str) -> str:
    """Retorna uma URL de imagem válida ou o ícone oficial da respectiva seção."""
    if icon_str and (icon_str.startswith(("http://", "https://", "special://", "/")) or "\\" in icon_str):
        return icon_str.strip()
    section_map = {
        "live": "live.png",
        "vod": "vod.png",
        "series": "series.png",
    }
    filename = section_map.get(section, "folder.png")
    return _icon("stv" if section in section_map else "common", filename)


def _episode_thumbnail(episode: dict[str, object], series_cover: str = "") -> str:
    """Prioriza um frame real do episódio e usa a capa da série apenas como fallback."""
    raw_info = episode.get("info")
    info = raw_info if isinstance(raw_info, dict) else {}
    raw_thumb = str(
        info.get("movie_image")
        or info.get("cover_big")
        or info.get("still_path")
        or info.get("image")
        or episode.get("movie_image")
        or episode.get("cover_big")
        or episode.get("thumbnail")
        or series_cover
        or ""
    )
    return _item_icon("series", raw_thumb)


def _format_live_channel_metadata(
    app: AppContainer,
    channel_raw_name: str,
    default_plot: str = "",
    epg_id: str = "",
) -> tuple[str, str]:
    """Retorna (label_limpo, plot_formatado_com_epg) para o canal de TV ao vivo."""
    from datetime import datetime

    from saile_epg.normalizer import clean_channel_title

    clean_title = clean_channel_title(channel_raw_name)

    now_prog, next_prog = app.get_channel_epg(channel_raw_name, epg_id=epg_id)
    if not now_prog and not next_prog:
        return clean_title, default_plot or clean_title

    plot_parts: list[str] = []
    if now_prog:
        start_label = datetime.fromtimestamp(now_prog.start_utc).strftime("%H:%M")
        end_label = datetime.fromtimestamp(now_prog.end_utc).strftime("%H:%M")
        plot_parts.append(f"[B]NO AR[/B] ({start_label} - {end_label}): {now_prog.title}")
        if now_prog.description:
            plot_parts.append(f"\n{now_prog.description}")

    if next_prog:
        next_start = datetime.fromtimestamp(next_prog.start_utc).strftime("%H:%M")
        next_end = datetime.fromtimestamp(next_prog.end_utc).strftime("%H:%M")
        prefix = "\n\n" if plot_parts else ""
        plot_parts.append(
            f"{prefix}[B]A SEGUIR[/B] ({next_start} - {next_end}): {next_prog.title}"
        )
        if next_prog.description and not now_prog:
            plot_parts.append(f"\n{next_prog.description}")

    full_plot = "".join(plot_parts).strip()
    return clean_title, full_plot or default_plot or clean_title


def _show_home(request: Request, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    init_directory(request.handle, "movies")

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
            media_type="movie",
        )
    finish_directory(request.handle, content="movies", view_mode=54)


def _show_section(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type)

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
            media_type="tvshow" if section == "series" else "movie",
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
            media_type="tvshow" if section == "series" else "movie",
        )

    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_category(request: Request, app: AppContainer, section: str, category_id: str, fanart: str, category_name: str = "") -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type)

    # Verificação de Controle Parental para a Categoria
    if is_restricted(category_name=category_name):
        import xbmcaddon
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=category_name or "Categoria Adulta"):
            finish_directory(request.handle, content=content_type, view_mode=54)
            return

    ensure_streams_loaded(app, section, category_id)
    items = app.catalog.get_media_items(section, category_id)

    if not items:
        # Item informativo para manter o container no modo InfoWall mesmo se a categoria estiver sem itens
        empty_msg = "Nenhum canal/conteúdo disponível"
        add_folder(
            request.handle,
            empty_msg,
            "",
            icon=_item_icon(section, ""),
            fanart=fanart,
            is_folder=False,
            media_type="video",
        )

    for item in items:
        icon_url = _item_icon(section, item.icon)
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})"),
        ]

        if section == "series":
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
            # Canais Live TV: apresentação limpa no InfoWall 54 com metadados EPG da Claro
            display_title, live_plot = _format_live_channel_metadata(
                app,
                item.name,
                default_plot=item.plot,
                epg_id=item.epg_id,
            )
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            add_folder(
                request.handle,
                display_title,
                url,
                icon=icon_url,
                fanart=item.fanart or fanart,
                is_folder=False,
                is_playable=True,
                context_menu=context_menu,
                plot=live_plot,
                media_type="video",
            )

    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_series_seasons(request: Request, app: AppContainer, series_id: str, series_title: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    from saile_core.notifications import notify_error

    init_directory(request.handle, "tvshows")

    # Verificação de Controle Parental para Séries Adultas
    if is_restricted(name=series_title):
        import xbmcaddon
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=series_title):
            finish_directory(request.handle, content="tvshows", view_mode=54)
            return

    try:
        data = app.xtream.get_series_info(series_id)
        episodes_by_season = data.get("episodes", {})
        info = data.get("info", {})
        series_cover = info.get("cover") or fanart
        series_plot = info.get("plot", "")
        seasons_meta = {str(s.get("season_number", "")): s for s in data.get("seasons", []) if isinstance(s, dict)}

        sorted_season_keys = sorted(
            episodes_by_season.keys(),
            key=lambda k: int(k) if str(k).isdigit() else 999
        )

        for season_num in sorted_season_keys:
            episodes = episodes_by_season[season_num]
            if not isinstance(episodes, list) or not episodes:
                continue

            season_info = seasons_meta.get(str(season_num), {})
            season_name = season_info.get("name") or f"Temporada {season_num}"
            raw_cover = str(season_info.get("cover") or series_cover or "")
            season_cover = _item_icon("series", raw_cover)
            season_plot = season_info.get("overview") or series_plot
            label = f"{season_name} ({len(episodes)} episódios)"

            url = request.url(
                action="series_episodes",
                section="series",
                series_id=series_id,
                season_num=str(season_num),
                title=series_title,
            )
            add_folder(
                request.handle,
                label,
                url,
                icon=season_cover,
                poster=season_cover,
                fanart=series_cover if (series_cover.startswith("http") or series_cover.startswith("/")) else fanart,
                is_folder=True,
                plot=season_plot,
                media_type="tvshow",
            )
    except Exception as exc:
        notify_error("sTv", f"Erro ao obter temporadas: {exc}")

    finish_directory(request.handle, content="tvshows", view_mode=54)


def _show_series_episodes(request: Request, app: AppContainer, series_id: str, season_num: str, series_title: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    from saile_core.notifications import notify_error

    init_directory(request.handle, "episodes")

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
        episodes = episodes_by_season.get(str(season_num), [])

        for ep in episodes:
            if not isinstance(ep, dict):
                continue
            ep_id = str(ep.get("id", ""))
            ep_num = str(ep.get("episode_num", "1"))
            ep_title = str(ep.get("title") or f"Episódio {ep_num}").strip()
            ep_ext = str(ep.get("container_extension", "mp4"))
            ep_plot = str(ep.get("info", {}).get("plot") or series_plot)
            ep_thumb = _episode_thumbnail(ep, series_cover)
            label = f"T{str(season_num).zfill(2)}E{ep_num.zfill(2)} - {ep_title}"

            url = request.url(action="play", section="series", stream_id=ep_id, extension=ep_ext, title=ep_title)
            add_folder(
                request.handle,
                label,
                url,
                icon=ep_thumb,
                poster=ep_thumb,
                fanart=series_cover if (series_cover.startswith("http") or series_cover.startswith("/")) else fanart,
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
    from stv.ui.directory import add_folder, finish_directory, init_directory
    
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type)

    keyboard = xbmc.Keyboard("", "Buscar...")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        query = keyboard.getText().strip()
        items = app.catalog.search_media(section, query)

        for item in items:
            icon_url = _item_icon(section, item.icon)
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
                # Live TV: sem forçar poster para manter a proporção natural da logo + EPG Claro
                display_title, live_plot = _format_live_channel_metadata(
                    app,
                    item.name,
                    default_plot=item.plot,
                    epg_id=item.epg_id,
                )
                url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
                is_folder = False
                is_playable = True
                media_type = "video"
                poster_val = ""
                item_label = display_title
                item_plot = live_plot

            add_folder(
                request.handle,
                item_label if section == "live" else item.name,
                url,
                icon=icon_url,
                poster=poster_val,
                clearlogo=icon_url if section == "live" else "",
                fanart=item.fanart or fanart,
                is_folder=is_folder,
                is_playable=is_playable,
                context_menu=context_menu,
                plot=item_plot if section == "live" else item.plot,
                media_type=media_type,
            )
            
    finish_directory(request.handle, content=content_type, view_mode=54)


def _show_favorites(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type)

    items = app.catalog.get_favorites(section)

    for item in items:
        icon_url = _item_icon(section, item.icon)
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
            # Live TV: sem forçar poster para manter a proporção natural da logo + EPG Claro
            display_title, live_plot = _format_live_channel_metadata(
                app,
                item.name,
                default_plot=item.plot,
                epg_id=item.epg_id,
            )
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension, title=item.name)
            is_folder = False
            is_playable = True
            media_type = "video"
            poster_val = ""
            item_label = display_title
            item_plot = live_plot

        add_folder(
            request.handle,
            item_label if section == "live" else item.name,
            url,
            icon=icon_url,
            poster=poster_val,
            clearlogo=icon_url if section == "live" else "",
            fanart=item.fanart or fanart,
            is_folder=is_folder,
            is_playable=is_playable,
            context_menu=context_menu,
            plot=item_plot if section == "live" else item.plot,
            media_type=media_type,
        )
        
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
    import xbmcvfs

    request = Request.from_argv(argv)
    addon = xbmcaddon.Addon()
    fanart = addon.getAddonInfo("fanart")
    epg_addon = xbmcaddon.Addon("script.module.saile.epg")

    settings = {
        "xtream_url": addon.getSetting("xtream_url"),
        "xtream_username": addon.getSetting("xtream_username"),
        "xtream_password": addon.getSetting("xtream_password"),
        "tmdb_language": addon.getSetting("tmdb_language"),
        "epg_enabled": addon.getSetting("epg_enabled") or "true",
        "cache_ttl_hours": addon.getSetting("cache_ttl_hours") or "12",
        "profile_path": __import__("xbmcvfs").translatePath(addon.getAddonInfo("profile")),
        "epg_profile_path": xbmcvfs.translatePath(epg_addon.getAddonInfo("profile")),
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

    if request.action in {"series_info", "series_seasons"}:
        series_id = request.params.get("series_id", "")
        title = request.params.get("title", "Série")
        if series_id:
            _show_series_seasons(request, app, series_id, title, fanart)
            return

    if request.action == "series_episodes":
        series_id = request.params.get("series_id", "")
        season_num = request.params.get("season_num", "1")
        title = request.params.get("title", "Série")
        if series_id:
            _show_series_episodes(request, app, series_id, season_num, title, fanart)
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
