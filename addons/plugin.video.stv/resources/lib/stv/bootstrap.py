from __future__ import annotations

import sys

from stv.navigation_contract import HOME_ENTRIES, SECTION_FIXED_ENTRIES, VALID_SECTIONS
from stv.routing import Request
from stv.app.services import AppContainer
from stv.app.sync import ensure_categories_loaded, ensure_streams_loaded


def _icon(scope: str, filename: str) -> str:
    from saile_core.artwork import artwork_path

    return artwork_path(scope, filename)


def _show_home(request: Request, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory

    for label, action, section, scope, filename in HOME_ENTRIES:
        url = request.url(action=action, section=section) if section else request.url(action=action)
        add_folder(request.handle, label, url, _icon(scope, filename), fanart)
    finish_directory(request.handle, "videos")


def _show_section(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory

    # 1. Fixed navigation items
    for label, action, scope, filename in SECTION_FIXED_ENTRIES:
        add_folder(
            request.handle,
            label,
            request.url(action=action, section=section),
            _icon(scope, filename),
            fanart,
        )
        
    # 2. Dynamic categories from database
    ensure_categories_loaded(app, section)
    categories = app.catalog.get_categories(section)
    for cat in categories:
        add_folder(
            request.handle,
            cat.name,
            request.url(action="category", section=section, category_id=cat.category_id),
            _icon("common", "folder.png"),
            fanart,
        )

    finish_directory(request.handle, "videos")


def _show_category(request: Request, app: AppContainer, section: str, category_id: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory

    ensure_streams_loaded(app, section, category_id)
    items = app.catalog.get_media_items(section, category_id)
    for item in items:
        url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension)
        icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})")
        ]
        
        add_folder(
            request.handle,
            item.name,
            url,
            icon_url,
            item.fanart or fanart,
            is_folder=False,
            context_menu=context_menu
        )

    finish_directory(request.handle, "videos")


def _show_search(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    import xbmc
    from stv.ui.directory import add_folder, finish_directory
    
    keyboard = xbmc.Keyboard("", "Buscar...")
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        query = keyboard.getText()
        items = app.catalog.search_media(section, query)
        for item in items:
            url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension)
            icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
            fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
            enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
            context_menu = [
                ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
                ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})")
            ]
            
            add_folder(
                request.handle,
                item.name,
                url,
                icon_url,
                item.fanart or fanart,
                is_folder=False,
                context_menu=context_menu
            )
            
    finish_directory(request.handle, "videos")


def _show_favorites(request: Request, app: AppContainer, section: str, fanart: str) -> None:
    from stv.ui.directory import add_folder, finish_directory
    
    items = app.catalog.get_favorites(section)
    for item in items:
        url = request.url(action="play", section=section, stream_id=item.item_id, extension=item.extension)
        icon_url = item.icon if item.icon.startswith("http") else _icon("common", "check.png")
        fav_action = request.url(action="toggle_fav", section=section, stream_id=item.item_id)
        enrich_action = request.url(action="enrich", section=section, stream_id=item.item_id, title=item.name)
        context_menu = [
            ("Adicionar/Remover Favoritos", f"RunPlugin({fav_action})"),
            ("Atualizar Metadados (TMDB)", f"RunPlugin({enrich_action})")
        ]
        
        add_folder(
            request.handle,
            item.name,
            url,
            icon_url,
            item.fanart or fanart,
            is_folder=False,
            context_menu=context_menu
        )
        
    finish_directory(request.handle, "videos")


def _play_item(app: AppContainer, section: str, stream_id: str, extension: str) -> None:
    from stv.ui.player import play_video
    
    url = app.xtream.stream_url(section, stream_id, extension)
    play_video(app, section, stream_id, url)


def run(argv: list[str]) -> None:
    """Entrypoint estrutural com o contrato oficial de navegação do sTv."""
    import xbmcaddon

    from saile_core.notifications import notify_info
    from stv.app.services import AppContainer

    request = Request.from_argv(argv)
    addon = xbmcaddon.Addon()
    fanart = addon.getAddonInfo("fanart")

    settings = {
        "xtream_url": addon.getSetting("xtream_url"),
        "xtream_username": addon.getSetting("xtream_username"),
        "xtream_password": addon.getSetting("xtream_password"),
        "tmdb_bearer_token": addon.getSetting("tmdb_bearer_token"),
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
        if section in VALID_SECTIONS and category_id:
            _show_category(request, app, section, category_id, fanart)
            return

    if request.action == "play":
        section = request.params.get("section", "")
        stream_id = request.params.get("stream_id", "")
        extension = request.params.get("extension", "")
        if section in VALID_SECTIONS and stream_id:
            _play_item(app, section, stream_id, extension)
            return

    if request.action == "sync":
        notify_info("sTv", "Sincronização LAN manual ainda não implementada")
        _show_home(request, fanart)
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
