from __future__ import annotations

from collections.abc import Sequence

from stv.app.services import AppContainer
from stv.app.sync import ensure_categories_loaded, ensure_streams_loaded
from stv.domain.catalog import first_backdrop
from stv.domain.models import MediaItem
from stv.navigation_contract import HOME_ENTRIES, SECTION_FIXED_ENTRIES, VALID_SECTIONS
from stv.parental import is_restricted, verify_parental_pin, verify_settings_access
from stv.routing import Request
from stv.ui.dialogs import show_sync_dialog


def _icon(scope: str, filename: str) -> str:
    from saile_core.artwork import artwork_path

    return artwork_path(scope, filename)


def _item_icon(section: str, icon_str: str) -> str:
    """Retorna uma URL de imagem válida ou o ícone oficial da respectiva seção."""
    if icon_str and (
        icon_str.startswith(("http://", "https://", "special://", "/")) or "\\" in icon_str
    ):
        return icon_str.strip()
    section_map = {
        "live": "live.png",
        "vod": "vod.png",
        "series": "series.png",
    }
    filename = section_map.get(section, "folder.png")
    return _icon("stv" if section in section_map else "common", filename)


def _normalize_tmdb_still_url(url: str) -> str:
    """Converte URLs cortadas de pôster vertical do TMDB em frames 16:9 autênticos."""
    if not url:
        return ""
    if "image.tmdb.org/t/p/w600_and_h900" in url:
        return url.replace("w600_and_h900_bestv2", "w500").replace("w600_and_h900", "w500")
    if "image.tmdb.org/t/p/w185" in url or "image.tmdb.org/t/p/w300" in url:
        return url.replace("/w185/", "/w500/").replace("/w300/", "/w500/")
    return url


def _series_artwork(info: dict[str, object], fanart: str) -> tuple[str, str, str]:
    """Capa, backdrop 16:9 e fanart de fundo de uma série a partir do get_series_info do Xtream."""
    cover = str(info.get("cover") or "")
    backdrop = first_backdrop(info.get("backdrop_path"))
    cover_url = cover if _is_remote_or_absolute(cover) else ""
    return cover, backdrop, backdrop or fanart or cover_url


def _is_remote_or_absolute(path: str) -> bool:
    return path.startswith(("http", "/"))


def _episode_thumbnail(
    episode: dict[str, object],
    series_backdrop: str = "",
    tmdb_ep_meta: dict[str, object] | None = None,
) -> str:
    """Prioriza um frame real 16:9 do episódio (TMDB / Xtream) e nunca a capa vertical."""
    if tmdb_ep_meta and tmdb_ep_meta.get("still_url"):
        return str(tmdb_ep_meta["still_url"])

    raw_info = episode.get("info")
    info = raw_info if isinstance(raw_info, dict) else {}

    raw_thumb = str(
        info.get("still_path")
        or info.get("movie_image")
        or info.get("image")
        or episode.get("still_path")
        or episode.get("movie_image")
        or episode.get("image")
        or ""
    ).strip()

    if raw_thumb:
        normalized = _normalize_tmdb_still_url(raw_thumb)
        return _item_icon("series", normalized)

    if series_backdrop and _is_remote_or_absolute(series_backdrop):
        return series_backdrop

    return _item_icon("series", "")


def _format_epg_card(
    channel_title: str,
    default_plot: str,
    now_prog: object | None,
    next_prog: object | None,
) -> tuple[str, str, dict[str, str]]:
    """Formata um card de canal com Agora/Próximo e progresso reutilizável."""
    import time
    from datetime import datetime

    if not now_prog and not next_prog:
        return (
            default_plot or f"{channel_title}\n\nProgramação indisponível",
            "Programação indisponível",
            {"EPG.Status": "unavailable", "EPG.Progress": "0"},
        )

    plot_parts: list[str] = []
    properties = {"EPG.Status": "available", "EPG.Progress": "0"}
    label2 = "Programação indisponível"
    if now_prog:
        start_label = datetime.fromtimestamp(now_prog.start_utc).strftime("%H:%M")
        end_label = datetime.fromtimestamp(now_prog.end_utc).strftime("%H:%M")
        plot_parts.append(
            f"[B][COLOR=FF4FC3F7]AGORA[/COLOR][/B]  {start_label} — {end_label}\n"
            f"[B]{now_prog.title}[/B]"
        )
        label2 = f"{start_label}  {now_prog.title}"
        duration = max(1, now_prog.end_utc - now_prog.start_utc)
        progress = max(
            0,
            min(100, int(((int(time.time()) - now_prog.start_utc) / duration) * 100)),
        )
        properties.update(
            {
                "EPG.NowTitle": now_prog.title,
                "EPG.NowStart": start_label,
                "EPG.NowEnd": end_label,
                "EPG.Progress": str(progress),
            }
        )
        if now_prog.description:
            plot_parts.append(f"\n{now_prog.description}")

    if next_prog:
        next_start = datetime.fromtimestamp(next_prog.start_utc).strftime("%H:%M")
        next_end = datetime.fromtimestamp(next_prog.end_utc).strftime("%H:%M")
        prefix = "\n\n" if plot_parts else ""
        plot_parts.append(f"{prefix}[B]A SEGUIR[/B]  {next_start} — {next_end}\n{next_prog.title}")
        properties.update(
            {
                "EPG.NextTitle": next_prog.title,
                "EPG.NextStart": next_start,
                "EPG.NextEnd": next_end,
            }
        )
        if not now_prog:
            label2 = f"A seguir {next_start}  {next_prog.title}"
        if next_prog.description and not now_prog:
            plot_parts.append(f"\n{next_prog.description}")

    full_plot = "".join(plot_parts).strip()
    return full_plot or default_plot or channel_title, label2, properties


def _render_media_items(
    request: Request,
    app: AppContainer,
    section: str,
    items: Sequence[MediaItem],
    fanart: str,
) -> None:
    """Renderiza cards padronizados de canais, filmes ou séries (Categorias, Busca e Favoritos)."""
    from stv.ui.directory import add_folder

    if not items:
        return

    epg_schedule = (
        app.get_items_epg_schedule(items)
        if (section == "live" and hasattr(app, "get_items_epg_schedule"))
        else {}
    )
    clean_channel_title = None
    if section == "live":
        from saile_epg.normalizer import clean_channel_title as _clean_channel_title

        clean_channel_title = _clean_channel_title

    for item in items:
        icon_url = _item_icon(section, item.icon)
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(
            action="enrich",
            section=section,
            stream_id=item.item_id,
            title=item.name,
        )
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})"),
        ]

        if section == "series":
            url = request.url(
                action="series_info",
                section=section,
                series_id=item.item_id,
                title=item.name,
            )
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
            url = request.url(
                action="play",
                section=section,
                stream_id=item.item_id,
                extension=item.extension,
                title=item.name,
            )
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
            display_title = clean_channel_title(item.name) if clean_channel_title else item.name
            now_prog, next_prog = (
                epg_schedule[item.item_id]
                if item.item_id in epg_schedule
                else app.get_channel_epg(item.name, epg_id=item.epg_id)
            )
            plot, label2, epg_props = _format_epg_card(
                display_title,
                item.plot,
                now_prog,
                next_prog,
            )
            url = request.url(
                action="play",
                section=section,
                stream_id=item.item_id,
                extension=item.extension,
                title=item.name,
            )
            add_folder(
                request.handle,
                display_title,
                url,
                icon=icon_url,
                clearlogo=icon_url,
                landscape=icon_url,
                fanart=item.fanart or fanart,
                is_folder=False,
                is_playable=True,
                context_menu=context_menu,
                plot=plot,
                media_type="video",
                label2=label2,
                properties=epg_props,
            )


def _show_home(request: Request, app: AppContainer, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    if hasattr(app, "trigger_background_epg_sync_if_expired"):
        app.trigger_background_epg_sync_if_expired()
    if hasattr(app, "trigger_background_catalog_sync_if_expired"):
        app.trigger_background_catalog_sync_if_expired()
    if hasattr(app, "trigger_background_lan_sync"):
        app.trigger_background_lan_sync()

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "movies", view_mode=view_mode)

    for label, action, section, scope, filename in HOME_ENTRIES:
        url = request.url(action=action, section=section) if section else request.url(action=action)
        add_folder(
            request.handle,
            label,
            url,
            icon=_icon(scope, filename),
            fanart=fanart,
            is_folder=action == "section",
            media_type="video",
        )
    finish_directory(request.handle, content="movies", view_mode=view_mode)


def _show_section(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    if section == "live" and hasattr(app, "trigger_background_epg_sync_if_expired"):
        app.trigger_background_epg_sync_if_expired()
    if hasattr(app, "trigger_background_catalog_sync_if_expired"):
        app.trigger_background_catalog_sync_if_expired(section)

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    for label, action, scope, filename in SECTION_FIXED_ENTRIES:
        add_folder(
            request.handle,
            label,
            request.url(action=action, section=section),
            icon=_icon(scope, filename),
            fanart=fanart,
            is_folder=True,
            media_type="video",
        )

    ensure_categories_loaded(app, section)
    categories = app.catalog.get_categories(section)
    folder_icon = _icon("common", "folder.png")
    for cat in categories:
        add_folder(
            request.handle,
            cat.name,
            request.url(
                action="category",
                section=section,
                category_id=cat.category_id,
                category_name=cat.name,
            ),
            icon=folder_icon,
            fanart=fanart,
            is_folder=True,
            media_type="video",
        )

    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_category(
    request: Request,
    app: AppContainer,
    section: str,
    category_id: str,
    fanart: str,
    category_name: str = "",
) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    if section == "live" and hasattr(app, "trigger_background_epg_sync_if_expired"):
        app.trigger_background_epg_sync_if_expired()

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    if is_restricted(category_name=category_name):
        import xbmcaddon

        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=category_name or "Categoria Adulta"):
            finish_directory(request.handle, content=content_type, view_mode=view_mode)
            return

    ensure_streams_loaded(app, section, category_id)
    items = app.catalog.get_media_items(section, category_id)

    if not items:
        add_folder(
            request.handle,
            "Nenhum canal/conteúdo disponível",
            "",
            icon=_item_icon(section, ""),
            fanart=fanart,
            is_folder=False,
            media_type="video",
        )
    else:
        _render_media_items(request, app, section, items, fanart)

    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_series_seasons(
    request: Request,
    app: AppContainer,
    series_id: str,
    series_title: str,
    fanart: str,
) -> None:
    from saile_core.notifications import notify_error

    from stv.ui.directory import add_folder, finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "seasons", view_mode=view_mode)

    if is_restricted(name=series_title):
        import xbmcaddon

        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=series_title):
            finish_directory(request.handle, content="seasons", view_mode=view_mode)
            return

    try:
        data = app.xtream.get_series_info(series_id)
        episodes_by_season = data.get("episodes", {})
        info = data.get("info", {})
        series_cover, _, series_fanart = _series_artwork(info, fanart)
        series_plot = str(info.get("plot", ""))
        seasons_meta = {
            str(s.get("season_number", "")): s
            for s in data.get("seasons", [])
            if isinstance(s, dict)
        }

        sorted_season_keys = sorted(
            episodes_by_season.keys(),
            key=lambda k: int(k) if str(k).isdigit() else 999,
        )

        for season_num in sorted_season_keys:
            episodes = episodes_by_season[season_num]
            if not isinstance(episodes, list) or not episodes:
                continue

            season_info = seasons_meta.get(str(season_num), {})
            season_name = season_info.get("name") or f"Temporada {season_num}"
            raw_cover = str(
                season_info.get("cover") or season_info.get("poster_path") or series_cover or ""
            )
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
                thumb=season_cover,
                landscape=series_fanart,
                fanart=series_fanart,
                is_folder=True,
                plot=season_plot,
                media_type="season",
            )
    except Exception as exc:
        notify_error("sTv", f"Erro ao obter temporadas: {exc}")

    finish_directory(request.handle, content="seasons", view_mode=view_mode)


def _show_series_episodes(
    request: Request,
    app: AppContainer,
    series_id: str,
    season_num: str,
    series_title: str,
    fanart: str,
) -> None:
    from saile_core.notifications import notify_error

    from stv.ui.directory import add_folder, finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "episodes", view_mode=view_mode)

    if is_restricted(name=series_title):
        import xbmcaddon

        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=series_title):
            finish_directory(request.handle, content="episodes", view_mode=view_mode)
            return

    try:
        data = app.xtream.get_series_info(series_id)
        episodes_by_season = data.get("episodes", {})
        info = data.get("info", {})
        _, series_backdrop, series_fanart = _series_artwork(info, fanart)
        series_plot = str(info.get("plot", ""))
        episodes = episodes_by_season.get(str(season_num), [])

        tmdb_id = info.get("tmdb_id")
        clean_series_name = str(info.get("name") or series_title)
        tmdb_episodes = app.get_season_episodes_metadata(
            clean_series_name,
            season_num,
            tmdb_id=tmdb_id,
        )

        for ep in episodes:
            if not isinstance(ep, dict):
                continue
            ep_id = str(ep.get("id", ""))
            ep_num = str(ep.get("episode_num", "1"))
            try:
                ep_int = int(ep_num)
            except (ValueError, TypeError):
                ep_int = 1

            tmdb_meta = tmdb_episodes.get(ep_int)
            ep_title = str(
                (tmdb_meta.get("name") if tmdb_meta else "")
                or ep.get("title")
                or f"Episódio {ep_num}"
            ).strip()
            ep_ext = str(ep.get("container_extension", "mp4"))
            ep_plot = str(
                (tmdb_meta.get("overview") if tmdb_meta else "")
                or ep.get("info", {}).get("plot")
                or series_plot
            )
            ep_thumb = _episode_thumbnail(
                ep,
                series_backdrop=series_backdrop,
                tmdb_ep_meta=tmdb_meta,
            )
            label = f"T{str(season_num).zfill(2)}E{ep_num.zfill(2)} - {ep_title}"

            url = request.url(
                action="play",
                section="series",
                stream_id=ep_id,
                extension=ep_ext,
                title=ep_title,
            )
            add_folder(
                request.handle,
                label,
                url,
                icon=ep_thumb,
                thumb=ep_thumb,
                landscape=ep_thumb,
                poster=ep_thumb,
                fanart=series_fanart,
                is_folder=False,
                is_playable=True,
                plot=ep_plot,
                media_type="episode",
            )
    except Exception as exc:
        notify_error("sTv", f"Erro ao obter episódios: {exc}")

    finish_directory(request.handle, content="episodes", view_mode=view_mode)


def _show_search(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    import xbmc

    from stv.ui.directory import finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"

    query = request.params.get("query", "").strip()
    if not query:
        keyboard = xbmc.Keyboard("", "Buscar...")
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            query = keyboard.getText().strip()
            if query and request.handle >= 0:
                import xbmcplugin

                xbmcplugin.endOfDirectory(request.handle, succeeded=False)
                search_url = request.url(action="search", section=section, query=query)
                xbmc.executebuiltin(f"Container.Update({search_url})")
                return
        if not query:
            if request.handle >= 0:
                import xbmcplugin

                xbmcplugin.endOfDirectory(request.handle, succeeded=False)
            return

    init_directory(request.handle, content_type, view_mode=view_mode)
    items = app.catalog.search_media(section, query)
    _render_media_items(request, app, section, items, fanart)
    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_favorites(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    items = app.catalog.get_favorites(section)
    _render_media_items(request, app, section, items, fanart)
    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _fail_playable(handle: int) -> None:
    if handle >= 0:
        import xbmcgui
        import xbmcplugin

        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem(offscreen=True))


def _play_item(
    request: Request,
    app: AppContainer,
    section: str,
    stream_id: str,
    extension: str,
    title: str = "",
) -> None:
    import xbmcaddon

    from stv.ui.player import play_video

    if is_restricted(name=title):
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=title or "Conteúdo Restrito"):
            _fail_playable(request.handle)
            return

    url = app.xtream.stream_url(section, stream_id, extension)
    play_video(request.handle, app, section, stream_id, url)


def _play_live_channel(
    request: Request,
    app: AppContainer,
    channel_key: str,
    title: str,
) -> None:
    import xbmcaddon

    from stv.domain.live_channels import variant_quality
    from stv.ui.player import play_video

    if is_restricted(name=title):
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=title or "Conteúdo Restrito"):
            _fail_playable(request.handle)
            return

    variant = app.choose_live_variant(channel_key)
    _rank, quality_label = variant_quality(variant)
    url = app.xtream.stream_url("live", variant.item_id, variant.extension)
    play_video(
        request.handle,
        app,
        "live",
        variant.item_id,
        url,
        video_quality=quality_label,
    )


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
        "epg_ttl_hours": addon.getSetting("epg_ttl_hours") or "6",
        "cache_ttl_hours": addon.getSetting("cache_ttl_hours") or "12",
        "live_max_quality": addon.getSetting("live_max_quality") or "auto",
        "live_bandwidth_limit_mbps": addon.getSetting("live_bandwidth_limit_mbps") or "0",
        "preferred_view_mode": addon.getSetting("preferred_view_mode"),
        "lan_sync_enabled": addon.getSetting("lan_sync_enabled") or "true",
        "lan_sync_auto": addon.getSetting("lan_sync_auto") or "true",
        "profile_path": xbmcvfs.translatePath(addon.getAddonInfo("profile")),
        "epg_profile_path": xbmcvfs.translatePath(epg_addon.getAddonInfo("profile")),
    }
    app = AppContainer(settings)

    from stv.ui.directory import ensure_infowall_in_kodi_db

    ensure_infowall_in_kodi_db()

    if request.action in {"", "home"}:
        _show_home(request, app, fanart)
        return

    if request.action == "section":
        section = request.params.get("section", "")
        if section in VALID_SECTIONS:
            _show_section(request, app, section, fanart)
            return

    if request.action == "category":
        section = request.params.get("section", "")
        category_id = request.params.get("category_id", "")
        category_name = request.params.get("category_name") or request.params.get("title", "")
        if section in VALID_SECTIONS and category_id:
            _show_category(
                request,
                app,
                section,
                category_id,
                fanart,
                category_name=category_name,
            )
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

    if request.action == "play_channel":
        channel_key = request.params.get("channel_key", "")
        title = request.params.get("title", "Canal")
        if channel_key:
            _play_live_channel(request, app, channel_key, title)
            return

    if request.action in {"settings", "open_settings"}:
        if request.handle >= 0:
            import xbmcplugin

            xbmcplugin.endOfDirectory(
                request.handle,
                succeeded=False,
                updateListing=False,
                cacheToDisc=False,
            )
        if verify_settings_access(addon):
            addon.openSettings()
        return

    if request.action == "sync":
        if request.handle >= 0:
            import xbmcplugin

            xbmcplugin.endOfDirectory(
                request.handle,
                succeeded=True,
                updateListing=False,
                cacheToDisc=False,
            )
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
            notify_success("sTv", "Adicionado aos Favoritos" if added else "Removido dos Favoritos")
            xbmc.executebuiltin("Container.Refresh")
            return

    if request.action == "toggle_channel_fav":
        channel_key = request.params.get("channel_key", "")
        if channel_key:
            import xbmc
            from saile_core.notifications import notify_success

            group = app.get_live_catalog().get_group(channel_key)
            legacy_item_ids = (
                tuple(variant.item_id for variant in group.variants) if group is not None else ()
            )
            added = app.catalog.toggle_channel_favorite(channel_key, legacy_item_ids)
            notify_success("sTv", "Adicionado aos Favoritos" if added else "Removido dos Favoritos")
            xbmc.executebuiltin("Container.Refresh")
            return

    if request.action == "enrich":
        section = request.params.get("section", "")
        stream_id = request.params.get("stream_id", "")
        title = request.params.get("title", "")
        if section in {"vod", "series"} and stream_id and title:
            import xbmc
            from saile_core.notifications import notify_error, notify_success

            if app.catalog.enrich_item(app.tmdb, section, stream_id, title):
                notify_success("TMDB", "Metadados atualizados")
                xbmc.executebuiltin("Container.Refresh")
            else:
                notify_error("TMDB", "Nenhum metadado encontrado")
            return

    _show_home(request, app, fanart)
