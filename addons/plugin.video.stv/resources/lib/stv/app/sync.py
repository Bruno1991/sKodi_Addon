"""Sincronização do catálogo Xtream com o banco SQLite local."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from stv.domain.models import Category, MediaItem

if TYPE_CHECKING:
    from stv.app.services import AppContainer


def _parse_categories(media_type: str, generation_id: int, data: object) -> list[Category]:
    if not isinstance(data, list):
        return []

    categories = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category_id = str(item.get("category_id", ""))
        name = str(item.get("category_name", "")).strip()
        parent_id = str(item.get("parent_id", "0"))

        if category_id and name:
            categories.append(
                Category(
                    category_id=category_id,
                    name=name,
                    parent_id=parent_id,
                    media_type=media_type,
                    generation_id=generation_id,
                )
            )
    return categories


def _parse_streams(media_type: str, generation_id: int, data: object) -> list[MediaItem]:
    if not isinstance(data, list):
        return []

    items = []
    for item in data:
        if not isinstance(item, dict):
            continue

        item_id = str(item.get("stream_id") or item.get("series_id") or "")
        name = str(item.get("name") or item.get("title") or "").strip()
        category_id = str(item.get("category_id", ""))

        icon = str(item.get("stream_icon") or item.get("cover") or "")
        extension = str(item.get("container_extension", ""))
        plot = str(item.get("plot", ""))

        if item_id and name:
            items.append(
                MediaItem(
                    media_type=media_type,
                    item_id=item_id,
                    name=name,
                    category_id=category_id,
                    icon=icon,
                    extension=extension,
                    plot=plot,
                    generation_id=generation_id,
                )
            )
    return items


def _get_actions(section: str) -> tuple[str, str]:
    mapping = {
        "live": ("get_live_categories", "get_live_streams"),
        "vod": ("get_vod_categories", "get_vod_streams"),
        "series": ("get_series_categories", "get_series"),
    }
    return mapping.get(section, ("", ""))


def ensure_section_loaded(app: "AppContainer", section: str, ttl_hours: int = 12) -> None:
    """Verifica o cache local e atualiza do provedor Xtream se expirado."""
    if app.catalog.is_cache_valid(section, ttl_hours=ttl_hours):
        return

    cat_action, stream_action = _get_actions(section)
    if not cat_action or not stream_action:
        return

    try:
        _ = app.xtream.host
    except (ValueError, Exception):
        return

    import xbmcgui

    dialog = xbmcgui.DialogProgress()
    dialog.create("sTv", f"Atualizando catálogo de {section.upper()}...")

    try:
        generation_id = int(time.time())

        dialog.update(20, "Baixando categorias do servidor...")
        raw_cats = app.xtream.request(cat_action)
        if dialog.iscanceled():
            return

        dialog.update(40, "Baixando lista de mídias do servidor...")
        raw_streams = app.xtream.request(stream_action)
        if dialog.iscanceled():
            return

        dialog.update(60, "Salvando categorias localmente...")
        parsed_cats = _parse_categories(section, generation_id, raw_cats)
        if parsed_cats:
            app.catalog.upsert_categories(parsed_cats)

        if dialog.iscanceled():
            return

        dialog.update(80, "Salvando mídias localmente...")
        parsed_streams = _parse_streams(section, generation_id, raw_streams)
        if parsed_streams:
            chunk_size = 500
            for i in range(0, len(parsed_streams), chunk_size):
                app.catalog.upsert_media_items(parsed_streams[i : i + chunk_size])

        dialog.update(95, "Limpando cache antigo...")
        app.catalog.clean_obsolete_categories(section, generation_id)
        app.catalog.clean_obsolete_items(section, generation_id)

        dialog.update(100, "Catálogo atualizado com sucesso!")
        time.sleep(0.3)
    except Exception as exc:
        from saile_core.notifications import notify_error
        notify_error("sTv", f"Erro ao sincronizar: {exc}")
    finally:
        dialog.close()


def ensure_categories_loaded(app: "AppContainer", section: str) -> None:
    """Garante que as categorias da seção estejam no SQLite."""
    ensure_section_loaded(app, section)


def ensure_streams_loaded(app: "AppContainer", section: str, category_id: str) -> None:
    """Garante que as mídias da categoria estejam no SQLite."""
    ensure_section_loaded(app, section)
