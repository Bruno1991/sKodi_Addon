"""Sincronização otimizada do catálogo Xtream com o banco SQLite local."""
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
        category_id = str(item.get("category_id", "")).strip()
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


def _parse_streams(media_type: str, generation_id: int, data: object, default_category_id: str = "") -> list[MediaItem]:
    if not isinstance(data, list):
        return []

    items = []
    for item in data:
        if not isinstance(item, dict):
            continue

        item_id = str(item.get("stream_id") or item.get("series_id") or "").strip()
        name = str(item.get("name") or item.get("title") or "").strip()
        category_id = str(item.get("category_id") or default_category_id or "").strip()

        icon = str(item.get("stream_icon") or item.get("cover") or "").strip()
        extension = str(item.get("container_extension", "")).strip()
        plot = str(item.get("plot", "")).strip()

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


def _get_category_action(section: str) -> str:
    mapping = {
        "live": "get_live_categories",
        "vod": "get_vod_categories",
        "series": "get_series_categories",
    }
    return mapping.get(section, "")


def _get_stream_action(section: str) -> str:
    mapping = {
        "live": "get_live_streams",
        "vod": "get_vod_streams",
        "series": "get_series",
    }
    return mapping.get(section, "")


def ensure_categories_loaded(app: "AppContainer", section: str) -> None:
    """Carrega sob demanda as categorias da seção para o SQLite se ainda não existirem."""
    existing = app.catalog.get_categories(section)
    if existing:
        return

    if not app.xtream.is_configured:
        from saile_core.notifications import notify_info
        notify_info("sTv", "Configure os dados do Xtream nas configurações")
        return

    action = _get_category_action(section)
    if not action:
        return

    try:
        raw_cats = app.xtream.request(action)
        generation_id = int(time.time())
        parsed = _parse_categories(section, generation_id, raw_cats)
        if parsed:
            app.catalog.upsert_categories(parsed)
    except Exception as exc:
        from saile_core.notifications import notify_error
        notify_error("sTv", f"Erro ao obter categorias: {exc}")


def ensure_streams_loaded(app: "AppContainer", section: str, category_id: str) -> None:
    """Carrega sob demanda as mídias de uma categoria específica para o SQLite."""
    existing = app.catalog.get_media_items(section, category_id)
    if existing:
        return

    if not app.xtream.is_configured:
        return

    action = _get_stream_action(section)
    if not action:
        return

    try:
        raw_streams = app.xtream.request(action, category_id=category_id)
        generation_id = int(time.time())
        parsed = _parse_streams(section, generation_id, raw_streams, default_category_id=category_id)
        if parsed:
            chunk_size = 500
            for i in range(0, len(parsed), chunk_size):
                app.catalog.upsert_media_items(parsed[i : i + chunk_size])
    except Exception as exc:
        from saile_core.notifications import notify_error
        notify_error("sTv", f"Erro ao carregar mídias: {exc}")


def sync_full_catalog(app: "AppContainer") -> bool:
    """Executa a sincronização completa de todas as categorias e canais/filmes/séries com barra de progresso."""
    if not app.xtream.is_configured:
        from saile_core.notifications import notify_error
        notify_error("sTv", "Preencha URL, Usuário e Senha nas configurações")
        return False

    import xbmcgui

    dialog = xbmcgui.DialogProgress()
    dialog.create("sTv", "Sincronizando Catálogo Completo...")

    try:
        generation_id = int(time.time())
        sections = [("live", "TV ao Vivo"), ("vod", "VOD"), ("series", "Séries")]

        for idx, (section, title) in enumerate(sections):
            pct_base = int((idx / len(sections)) * 100)
            dialog.update(pct_base, f"Baixando categorias de {title}...")
            
            cat_action = _get_category_action(section)
            raw_cats = app.xtream.request(cat_action)
            parsed_cats = _parse_categories(section, generation_id, raw_cats)
            if parsed_cats:
                app.catalog.upsert_categories(parsed_cats)

            if dialog.iscanceled():
                return False

            dialog.update(pct_base + 15, f"Baixando lista de {title}...")
            stream_action = _get_stream_action(section)
            raw_streams = app.xtream.request(stream_action)
            parsed_streams = _parse_streams(section, generation_id, raw_streams)
            if parsed_streams:
                chunk_size = 500
                for i in range(0, len(parsed_streams), chunk_size):
                    app.catalog.upsert_media_items(parsed_streams[i : i + chunk_size])

            if dialog.iscanceled():
                return False

        dialog.update(95, "Limpando registros antigos...")
        for section, _ in sections:
            app.catalog.clean_obsolete_categories(section, generation_id)
            app.catalog.clean_obsolete_items(section, generation_id)

        dialog.update(100, "Catálogo sincronizado com sucesso!")
        time.sleep(0.5)
        return True
    except Exception as exc:
        from saile_core.notifications import notify_error
        notify_error("sTv", f"Falha na sincronização: {exc}")
        return False
    finally:
        dialog.close()
