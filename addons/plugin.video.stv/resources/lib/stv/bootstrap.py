from __future__ import annotations

import sys

from stv.domain.live_channels import LiveChannelGroup
from stv.domain.models import MediaItem
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


def _add_promoted_live_channel(
    request: Request,
    app: AppContainer,
    group: LiveChannelGroup,
    fanart: str,
    now_next: tuple[object | None, object | None] | None = None,
) -> None:
    from stv.ui.directory import add_folder

    channel = group.channel
    variant = group.variants[0]
    icon_url = _item_icon("live", channel.icon_url or variant.icon)
    if now_next is None:
        now_next = app.get_channel_epg(channel.display_name, epg_id=channel.epg_id)
    live_plot, label2, epg_properties = _format_epg_card(
        channel.display_name,
        variant.plot,
        now_next[0],
        now_next[1],
    )
    favorite_action = request.url(
        action="toggle_channel_fav",
        channel_key=channel.channel_key,
    )
    context_menu = [
        ("Adicionar/Remover Favoritos", f"RunPlugin({favorite_action})"),
        ("Configurações de reprodução", f"RunPlugin({request.url(action='open_settings')})"),
    ]
    url = request.url(
        action="play_channel",
        channel_key=channel.channel_key,
        title=channel.display_name,
    )
    add_folder(
        request.handle,
        channel.display_name,
        url,
        icon=icon_url,
        clearlogo=icon_url,
        landscape=icon_url,
        fanart=variant.fanart or fanart,
        is_folder=False,
        is_playable=True,
        context_menu=context_menu,
        plot=live_plot,
        media_type="video",
        label2=label2,
        properties=epg_properties,
    )


def _add_unmatched_live_item(
    request: Request,
    app: AppContainer,
    item: MediaItem,
    fanart: str,
) -> None:
    from stv.ui.directory import add_folder

    icon_url = _item_icon("live", item.icon)
    favorite_action = request.url(
        action="toggle_fav",
        section="live",
        stream_id=item.item_id,
    )
    add_folder(
        request.handle,
        item.name,
        request.url(
            action="play",
            section="live",
            stream_id=item.item_id,
            extension=item.extension,
            title=item.name,
        ),
        icon=icon_url,
        clearlogo=icon_url,
        landscape=icon_url,
        fanart=item.fanart or fanart,
        is_folder=False,
        is_playable=True,
        context_menu=[("Adicionar/Remover Favoritos", f"RunPlugin({favorite_action})")],
        plot=item.plot,
        media_type="video",
    )


def _normalize_tmdb_still_url(url: str) -> str:
    """Converte URLs cortadas de pôster vertical do TMDB em frames 16:9 autênticos."""
    if not url:
        return ""
    if "image.tmdb.org/t/p/w600_and_h900" in url:
        return url.replace("w600_and_h900_bestv2", "w500").replace("w600_and_h900", "w500")
    if "image.tmdb.org/t/p/w185" in url or "image.tmdb.org/t/p/w300" in url:
        return url.replace("/w185/", "/w500/").replace("/w300/", "/w500/")
    return url


def _episode_thumbnail(
    episode: dict[str, object],
    series_cover: str = "",
    tmdb_ep_meta: dict[str, object] | None = None,
) -> str:
    """Prioriza um frame real 16:9 do episódio (TMDB / Xtream) e usa a capa da série apenas como fallback."""
    if tmdb_ep_meta and tmdb_ep_meta.get("still_url"):
        return str(tmdb_ep_meta["still_url"])

    raw_info = episode.get("info")
    info = raw_info if isinstance(raw_info, dict) else {}
    raw_thumb = str(
        info.get("still_path")
        or info.get("movie_image")
        or info.get("image")
        or info.get("cover_big")
        or episode.get("still_path")
        or episode.get("movie_image")
        or episode.get("thumbnail")
        or episode.get("cover_big")
        or ""
    ).strip()

    if raw_thumb:
        normalized = _normalize_tmdb_still_url(raw_thumb)
        return _item_icon("series", normalized)

    return _item_icon("series", series_cover or "")



def _format_live_channel_metadata(
    app: AppContainer,
    channel_raw_name: str,
    default_plot: str = "",
    epg_id: str = "",
) -> tuple[str, str]:
    """Retorna (label_limpo, plot_formatado_com_epg) para o canal de TV ao vivo."""
    from saile_epg.normalizer import clean_channel_title

    clean_title = clean_channel_title(channel_raw_name)
    now_prog, next_prog = app.get_channel_epg(channel_raw_name, epg_id=epg_id)
    plot, _label2, _properties = _format_epg_card(
        clean_title, default_plot, now_prog, next_prog
    )
    return clean_title, plot


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
        plot_parts.append(
            f"{prefix}[B]A SEGUIR[/B]  {next_start} — {next_end}\n{next_prog.title}"
        )
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


def _show_home(request: Request, app: AppContainer, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "movies", view_mode=view_mode)

    for label, action, section, scope, filename in HOME_ENTRIES:
        url = request.url(action=action, section=section) if section else request.url(action=action)
        icon_path = _icon(scope, filename)
        is_folder = action == "section"
        add_folder(
            request.handle,
            label,
            url,
            icon=icon_path,
            fanart=fanart,
            is_folder=is_folder,
            media_type="video",
        )
    finish_directory(request.handle, content="movies", view_mode=view_mode)


def _show_section(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

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
    if section == "live":
        live_catalog = app.get_live_catalog()
        schedule = app.get_live_schedule(
            tuple(group.channel.channel_key for group in live_catalog.groups)
        )
        for group in live_catalog.groups:
            _add_promoted_live_channel(
                request,
                app,
                group,
                fanart,
                now_next=schedule.get(group.channel.channel_key, (None, None)),
            )

        visible_category_ids = live_catalog.visible_category_ids(
            [category.category_id for category in categories],
            catalog_complete=app.catalog.is_catalog_complete("live"),
        )
        categories = [
            category
            for category in categories
            if category.category_id in visible_category_ids
        ]
    folder_icon = _icon("common", "folder.png")
    for cat in categories:
        add_folder(
            request.handle,
            cat.name,
            request.url(action="category", section=section, category_id=cat.category_id, title=cat.name),
            icon=folder_icon,
            fanart=fanart,
            is_folder=True,
            media_type="video",
        )

    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_category(request: Request, app: AppContainer, section: str, category_id: str, fanart: str, category_name: str = "") -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory

    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    # Verificação de Controle Parental para a Categoria
    if is_restricted(category_name=category_name):
        import xbmcaddon
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=category_name or "Categoria Adulta"):
            finish_directory(request.handle, content=content_type, view_mode=view_mode)
            return

    ensure_streams_loaded(app, section, category_id)
    items = app.catalog.get_media_items(section, category_id)
    if section == "live":
        items = list(app.get_live_catalog().unmatched_in_category(category_id))

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
            # TV ao vivo: apresentação limpa no InfoWall com EPG local do provedor.
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
                clearlogo=icon_url,
                landscape=icon_url,
                fanart=item.fanart or fanart,
                is_folder=False,
                is_playable=True,
                context_menu=context_menu,
                plot=live_plot,
                media_type="video",
            )

    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_series_seasons(request: Request, app: AppContainer, series_id: str, series_title: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    from saile_core.notifications import notify_error

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "seasons", view_mode=view_mode)

    # Verificação de Controle Parental para Séries Adultas
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
                media_type="season",
            )
    except Exception as exc:
        notify_error("sTv", f"Erro ao obter temporadas: {exc}")

    finish_directory(request.handle, content="seasons", view_mode=view_mode)


def _show_series_episodes(request: Request, app: AppContainer, series_id: str, season_num: str, series_title: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    from saile_core.notifications import notify_error

    view_mode = getattr(app, "preferred_view_mode", 54)
    init_directory(request.handle, "episodes", view_mode=view_mode)

    # Verificação de Controle Parental para Séries Adultas
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
        series_cover = info.get("cover") or fanart
        series_plot = info.get("plot", "")
        episodes = episodes_by_season.get(str(season_num), [])

        # Enriquecimento com TMDB para frames 16:9 reais e sinopses dos episódios
        tmdb_id = info.get("tmdb_id")
        clean_series_name = info.get("name") or series_title
        tmdb_episodes = app.get_season_episodes_metadata(
            clean_series_name,
            season_num,
            tmdb_id=tmdb_id,
        )

        for ep in episodes:
            if not isinstance(ep, dict):
                continue
            ep_id = str(ep.get("id", ""))
            raw_ep_num = ep.get("episode_num", "1")
            ep_num = str(raw_ep_num)
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
            ep_thumb = _episode_thumbnail(ep, series_cover, tmdb_ep_meta=tmdb_meta)
            label = f"T{str(season_num).zfill(2)}E{ep_num.zfill(2)} - {ep_title}"

            url = request.url(action="play", section="series", stream_id=ep_id, extension=ep_ext, title=ep_title)
            add_folder(
                request.handle,
                label,
                url,
                icon=ep_thumb,
                thumb=ep_thumb,
                landscape=ep_thumb,
                poster="",
                fanart=series_cover if (series_cover.startswith("http") or series_cover.startswith("/")) else fanart,
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
    from stv.ui.directory import add_folder, finish_directory, init_directory
    
    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    keyboard = xbmc.Keyboard("", "Buscar...")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        query = keyboard.getText().strip()
        items = app.catalog.search_media(section, query)

        if section == "live":
            result_ids = {item.item_id for item in items}
            live_catalog = app.get_live_catalog()
            for group in live_catalog.groups:
                if any(variant.item_id in result_ids for variant in group.variants):
                    _add_promoted_live_channel(request, app, group, fanart)
            for item in live_catalog.unmatched_items:
                if item.item_id in result_ids:
                    _add_unmatched_live_item(request, app, item, fanart)
            finish_directory(request.handle, content=content_type, view_mode=view_mode)
            return

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
                # TV ao vivo: preserva a proporção natural da logo e usa o EPG local.
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
                landscape=icon_url if section == "live" else "",
                fanart=item.fanart or fanart,
                is_folder=is_folder,
                is_playable=is_playable,
                context_menu=context_menu,
                plot=item_plot if section == "live" else item.plot,
                media_type=media_type,
            )
            
    finish_directory(request.handle, content=content_type, view_mode=view_mode)


def _show_favorites(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory, init_directory
    
    view_mode = getattr(app, "preferred_view_mode", 54)
    content_type = "tvshows" if section == "series" else "movies"
    init_directory(request.handle, content_type, view_mode=view_mode)

    items = app.catalog.get_favorites(section)

    if section == "live":
        live_catalog = app.get_live_catalog()
        favorite_variant_ids = {item.item_id for item in items}
        favorite_channel_keys = set(app.catalog.get_favorite_channel_keys())
        for group in live_catalog.groups:
            if (
                group.channel.channel_key in favorite_channel_keys
                or any(variant.item_id in favorite_variant_ids for variant in group.variants)
            ):
                _add_promoted_live_channel(request, app, group, fanart)
        for item in live_catalog.unmatched_items:
            if item.item_id in favorite_variant_ids:
                _add_unmatched_live_item(request, app, item, fanart)
        finish_directory(request.handle, content=content_type, view_mode=view_mode)
        return

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
            # TV ao vivo: preserva a proporção natural da logo e usa o EPG local.
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
            landscape=icon_url if section == "live" else "",
            fanart=item.fanart or fanart,
            is_folder=is_folder,
            is_playable=is_playable,
            context_menu=context_menu,
            plot=item_plot if section == "live" else item.plot,
            media_type=media_type,
        )
        
    finish_directory(request.handle, content=content_type, view_mode=view_mode)


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


def _play_live_channel(
    request: Request,
    app: AppContainer,
    channel_key: str,
    title: str,
) -> None:
    from stv.ui.player import play_video
    import xbmcaddon

    if is_restricted(name=title):
        addon = xbmcaddon.Addon()
        if not verify_parental_pin(addon, reason=title or "Conteúdo Restrito"):
            return
    from stv.domain.live_channels import variant_quality

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
        "cache_ttl_hours": addon.getSetting("cache_ttl_hours") or "12",
        "live_max_quality": addon.getSetting("live_max_quality") or "auto",
        "live_bandwidth_limit_mbps": addon.getSetting("live_bandwidth_limit_mbps") or "0",
        "preferred_view_mode": addon.getSetting("preferred_view_mode"),
        "profile_path": __import__("xbmcvfs").translatePath(addon.getAddonInfo("profile")),
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

    if request.action == "play_channel":
        channel_key = request.params.get("channel_key", "")
        title = request.params.get("title", "Canal")
        if channel_key:
            _play_live_channel(request, app, channel_key, title)
            return

    if request.action in {"settings", "open_settings"}:
        if request.handle >= 0:
            import xbmcplugin
            xbmcplugin.endOfDirectory(request.handle, succeeded=False, updateListing=False, cacheToDisc=False)
        if verify_settings_access(addon):
            addon.openSettings()
        return

    if request.action == "sync":
        if request.handle >= 0:
            import xbmcplugin
            xbmcplugin.endOfDirectory(request.handle, succeeded=True, updateListing=False, cacheToDisc=False)
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

    if request.action == "toggle_channel_fav":
        channel_key = request.params.get("channel_key", "")
        if channel_key:
            import xbmc
            from saile_core.notifications import notify_success

            group = app.get_live_catalog().get_group(channel_key)
            legacy_item_ids = (
                tuple(variant.item_id for variant in group.variants)
                if group is not None
                else ()
            )
            added = app.catalog.toggle_channel_favorite(channel_key, legacy_item_ids)
            notify_success(
                "sTv",
                "Adicionado aos Favoritos" if added else "Removido dos Favoritos",
            )
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

    _show_home(request, app, fanart)
