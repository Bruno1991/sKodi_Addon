from __future__ import annotations

from typing import Sequence

from stv.domain.catalog import sanitize_title_for_search
from stv.domain.models import Category, MediaItem
from stv.persistence.database import Database



class CatalogRepository:
    """Encapsula operações de leitura e escrita do banco de dados local do sTv."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_categories(self, categories: Sequence[Category]) -> None:
        """Insere ou atualiza categorias preservando integridade."""
        if not categories:
            return
        sql = """
        INSERT INTO categories (media_type, category_id, name, parent_id, generation_id, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (media_type, category_id) DO UPDATE SET
            name = excluded.name,
            parent_id = excluded.parent_id,
            generation_id = excluded.generation_id,
            updated_at = CURRENT_TIMESTAMP
        """
        data = [
            (c.media_type, c.category_id, c.name, c.parent_id, c.generation_id)
            for c in categories
        ]
        with self.db.connect() as connection:
            connection.executemany(sql, data)

    def upsert_media_items(self, items: Sequence[MediaItem]) -> None:
        """Insere ou atualiza canais, filmes ou séries em lote."""
        if not items:
            return
        sql = """
        INSERT INTO media_items (
            media_type, item_id, category_id, name, icon, fanart, plot,
            extension, epg_id, source_name, normalized_name, generation_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (media_type, item_id) DO UPDATE SET
            category_id = excluded.category_id,
            name = excluded.name,
            icon = CASE WHEN excluded.icon != '' THEN excluded.icon ELSE media_items.icon END,
            fanart = CASE WHEN excluded.fanart != '' THEN excluded.fanart ELSE media_items.fanart END,
            plot = CASE WHEN excluded.plot != '' THEN excluded.plot ELSE media_items.plot END,
            extension = excluded.extension,
            epg_id = excluded.epg_id,
            source_name = excluded.source_name,
            normalized_name = excluded.normalized_name,
            generation_id = excluded.generation_id,
            updated_at = CURRENT_TIMESTAMP
        """
        data = [
            (
                i.media_type,
                i.item_id,
                i.category_id,
                i.name,
                i.icon,
                i.fanart,
                i.plot,
                i.extension,
                i.epg_id,
                i.source_name or i.name,
                i.normalized_name,
                i.generation_id,
            )
            for i in items
        ]
        with self.db.connect() as connection:
            connection.executemany(sql, data)

    def enrich_media_item(
        self,
        media_type: str,
        item_id: str,
        plot: str | None = None,
        fanart: str | None = None,
    ) -> None:
        """Atualiza metadados adicionais obtidos do TMDB para um item."""
        updates: list[str] = []
        params: list[object] = []
        if plot:
            updates.append("plot = ?")
            params.append(plot)
        if fanart:
            updates.append("fanart = ?")
            params.append(fanart)

        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        sql = f"UPDATE media_items SET {', '.join(updates)} WHERE media_type = ? AND item_id = ?"
        params.extend([media_type, item_id])

        with self.db.connect() as connection:
            connection.execute(sql, params)

    def enrich_item(
        self,
        tmdb_client: object,
        media_type: str,
        item_id: str,
        title: str,
    ) -> bool:
        """Busca metadados estendidos no TMDB para um item específico e salva no SQLite."""
        search_title = sanitize_title_for_search(title)
        if not search_title:
            return False
        if media_type == "vod" and hasattr(tmdb_client, "search_movie"):
            data = tmdb_client.search_movie(search_title)
        elif media_type == "series" and hasattr(tmdb_client, "search_tv"):
            data = tmdb_client.search_tv(search_title)
        else:
            return False

        if not data or not isinstance(data, dict):
            return False

        plot = data.get("overview")
        backdrop_path = data.get("backdrop_path")
        poster_path = data.get("poster_path")

        fanart = ""
        if backdrop_path:
            fanart = f"https://image.tmdb.org/t/p/w1280{backdrop_path}"
        elif poster_path:
            fanart = f"https://image.tmdb.org/t/p/w500{poster_path}"

        self.enrich_media_item(
            media_type,
            item_id,
            plot=plot,
            fanart=fanart if fanart else None,
        )
        return True

    def get_categories(self, media_type: str) -> list[Category]:
        """Recupera todas as categorias ordenadas pelo nome."""
        sql = "SELECT * FROM categories WHERE media_type = ? ORDER BY name COLLATE NOCASE"
        with self.db.connect() as connection:
            rows = connection.execute(sql, (media_type,)).fetchall()

        return [
            Category(
                category_id=row["category_id"],
                name=row["name"],
                parent_id=row["parent_id"],
                media_type=row["media_type"],
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def get_media_items(self, media_type: str, category_id: str) -> list[MediaItem]:
        """Recupera itens de mídia associados a uma categoria específica."""
        sql = "SELECT * FROM media_items WHERE media_type = ? AND category_id = ? ORDER BY name COLLATE NOCASE"
        with self.db.connect() as connection:
            rows = connection.execute(sql, (media_type, category_id)).fetchall()

        return [
            MediaItem(
                media_type=row["media_type"],
                item_id=row["item_id"],
                name=row["name"],
                category_id=row["category_id"],
                icon=row["icon"],
                fanart=row["fanart"],
                plot=row["plot"],
                extension=row["extension"],
                epg_id=row["epg_id"],
                source_name=row["source_name"],
                normalized_name=row["normalized_name"],
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def search_media(self, media_type: str, query: str) -> list[MediaItem]:
        """Pesquisa itens de mídia usando FTS5 e busca normalizada insensível a acentos."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        import re
        from saile_epg import normalize_channel_name, normalize_search_term

        normalized_query = (
            normalize_channel_name(cleaned_query)
            if media_type == "live"
            else normalize_search_term(cleaned_query)
        )
        unaccented_query = normalize_search_term(cleaned_query)

        results_by_id: dict[tuple[str, str], MediaItem] = {}

        # 1. Tentar busca via FTS5 (com prefix matching e tokens higienizados)
        fts_sql = """
        SELECT m.* FROM media_items m
        JOIN media_items_fts f ON m.rowid = f.rowid
        WHERE f.media_type = ? AND media_items_fts MATCH ?
        ORDER BY rank
        LIMIT 100
        """
        try:
            tokens = re.findall(r"\w+", cleaned_query)
            if tokens:
                fts_query = " ".join(f'"{token}"*' for token in tokens)
                with self.db.connect() as connection:
                    rows = connection.execute(fts_sql, (media_type, fts_query)).fetchall()
                    for row in rows:
                        item = MediaItem(
                            media_type=row["media_type"],
                            item_id=row["item_id"],
                            name=row["name"],
                            category_id=row["category_id"],
                            icon=row["icon"],
                            fanart=row["fanart"],
                            plot=row["plot"],
                            extension=row["extension"],
                            epg_id=row["epg_id"],
                            source_name=row["source_name"],
                            normalized_name=row["normalized_name"],
                            generation_id=row["generation_id"],
                        )
                        results_by_id[(item.media_type, item.item_id)] = item
        except Exception:
            pass

        # 2. Busca e complemento resiliente com LIKE sobre campos originais e normalizados (sem acentos)
        fallback_sql = """
        SELECT * FROM media_items
        WHERE media_type = ?
          AND (
            name LIKE ?
            OR source_name LIKE ?
            OR (? != '' AND normalized_name LIKE ?)
            OR (? != '' AND normalized_name LIKE ?)
          )
        ORDER BY name COLLATE NOCASE LIMIT 100
        """
        try:
            with self.db.connect() as connection:
                rows = connection.execute(
                    fallback_sql,
                    (
                        media_type,
                        f"%{cleaned_query}%",
                        f"%{cleaned_query}%",
                        normalized_query,
                        f"%{normalized_query}%",
                        unaccented_query,
                        f"%{unaccented_query}%",
                    ),
                ).fetchall()
                for row in rows:
                    key = (str(row["media_type"]), str(row["item_id"]))
                    if key not in results_by_id:
                        results_by_id[key] = MediaItem(
                            media_type=row["media_type"],
                            item_id=row["item_id"],
                            name=row["name"],
                            category_id=row["category_id"],
                            icon=row["icon"],
                            fanart=row["fanart"],
                            plot=row["plot"],
                            extension=row["extension"],
                            epg_id=row["epg_id"],
                            source_name=row["source_name"],
                            normalized_name=row["normalized_name"],
                            generation_id=row["generation_id"],
                        )
        except Exception:
            pass

        return list(results_by_id.values())[:100]

    def get_favorites(self, media_type: str) -> list[MediaItem]:
        sql = """
        SELECT m.* FROM media_items m
        JOIN favorites f ON m.media_type = f.media_type AND m.item_id = f.item_id
        WHERE m.media_type = ?
        ORDER BY f.created_at DESC
        """
        with self.db.connect() as connection:
            rows = connection.execute(sql, (media_type,)).fetchall()

        return [
            MediaItem(
                media_type=row["media_type"],
                item_id=row["item_id"],
                name=row["name"],
                category_id=row["category_id"],
                icon=row["icon"],
                fanart=row["fanart"],
                plot=row["plot"],
                extension=row["extension"],
                epg_id=row["epg_id"],
                source_name=row["source_name"],
                normalized_name=row["normalized_name"],
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def get_all_media_items(self, media_type: str) -> list[MediaItem]:
        """Recupera o catálogo local completo de uma seção sem alterar categorias."""
        sql = "SELECT * FROM media_items WHERE media_type = ? ORDER BY name COLLATE NOCASE"
        with self.db.connect() as connection:
            rows = connection.execute(sql, (media_type,)).fetchall()
        return [
            MediaItem(
                media_type=row["media_type"],
                item_id=row["item_id"],
                name=row["name"],
                category_id=row["category_id"],
                icon=row["icon"],
                fanart=row["fanart"],
                plot=row["plot"],
                extension=row["extension"],
                epg_id=row["epg_id"],
                source_name=row["source_name"],
                normalized_name=row["normalized_name"],
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def get_favorite_ids(self, media_type: str) -> list[str]:
        """Retorna o estado de favoritos mesmo quando o catálogo estiver temporariamente vazio."""
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT item_id FROM favorites WHERE media_type = ? ORDER BY created_at",
                (media_type,),
            ).fetchall()
        return [str(row["item_id"]) for row in rows]

    def toggle_favorite(self, media_type: str, item_id: str) -> bool:
        """Adiciona aos favoritos se não existir, ou remove se já existir. Retorna True se adicionado."""
        check_sql = "SELECT 1 FROM favorites WHERE media_type = ? AND item_id = ?"
        with self.db.connect() as connection:
            exists = connection.execute(check_sql, (media_type, item_id)).fetchone()
            if exists:
                connection.execute("DELETE FROM favorites WHERE media_type = ? AND item_id = ?", (media_type, item_id))
                return False
            else:
                connection.execute("INSERT INTO favorites (media_type, item_id) VALUES (?, ?)", (media_type, item_id))
                return True

    def add_favorite(self, media_type: str, item_id: str) -> None:
        """Adiciona um favorito de modo idempotente, sem remover registros existentes."""
        with self.db.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO favorites (media_type, item_id) VALUES (?, ?)",
                (media_type, item_id),
            )

    def get_favorite_channel_keys(self) -> list[str]:
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT channel_key FROM live_channel_favorites ORDER BY created_at"
            ).fetchall()
        return [str(row["channel_key"]) for row in rows]

    def toggle_channel_favorite(
        self,
        channel_key: str,
        legacy_item_ids: Sequence[str] = (),
    ) -> bool:
        with self.db.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM live_channel_favorites WHERE channel_key = ?",
                (channel_key,),
            ).fetchone()
            legacy_exists = False
            if legacy_item_ids:
                placeholders = ",".join("?" for _item_id in legacy_item_ids)
                legacy_exists = connection.execute(
                    f"""
                    SELECT 1 FROM favorites
                    WHERE media_type = 'live' AND item_id IN ({placeholders})
                    LIMIT 1
                    """,
                    tuple(legacy_item_ids),
                ).fetchone() is not None
            if exists or legacy_exists:
                connection.execute(
                    "DELETE FROM live_channel_favorites WHERE channel_key = ?",
                    (channel_key,),
                )
                if legacy_item_ids:
                    placeholders = ",".join("?" for _item_id in legacy_item_ids)
                    connection.execute(
                        f"""
                        DELETE FROM favorites
                        WHERE media_type = 'live' AND item_id IN ({placeholders})
                        """,
                        tuple(legacy_item_ids),
                    )
                return False
            connection.execute(
                "INSERT INTO live_channel_favorites(channel_key) VALUES (?)",
                (channel_key,),
            )
            return True

    def clean_obsolete_categories(self, media_type: str, current_generation: int) -> int:
        """Remove categorias de gerações anteriores que não existem mais no servidor."""
        sql = "DELETE FROM categories WHERE media_type = ? AND generation_id < ?"
        with self.db.connect() as connection:
            cursor = connection.execute(sql, (media_type, current_generation))
            return cursor.rowcount

    def clean_obsolete_items(self, media_type: str, current_generation: int) -> int:
        """Remove itens obsoletos sem apagar o estado de favoritos do usuário."""
        sql = "DELETE FROM media_items WHERE media_type = ? AND generation_id < ?"
        with self.db.connect() as connection:
            cursor = connection.execute(sql, (media_type, current_generation))
            return cursor.rowcount

    def mark_catalog_synced(self, media_type: str, generation_id: int) -> None:
        with self.db.connect() as connection:
            connection.execute(
                """
                INSERT INTO catalog_sync_state(media_type, generation_id, completed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(media_type) DO UPDATE SET
                    generation_id = excluded.generation_id,
                    completed_at = CURRENT_TIMESTAMP
                """,
                (media_type, generation_id),
            )

    def begin_catalog_sync(self, media_types: Sequence[str]) -> None:
        if not media_types:
            return
        placeholders = ",".join("?" for _media_type in media_types)
        with self.db.connect() as connection:
            connection.execute(
                f"DELETE FROM catalog_sync_state WHERE media_type IN ({placeholders})",
                tuple(media_types),
            )

    def is_catalog_complete(self, media_type: str) -> bool:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM catalog_sync_state WHERE media_type = ?",
                (media_type,),
            ).fetchone()
        return row is not None

    def update_playback_progress(self, media_type: str, item_id: str, position: float, total: float) -> None:
        """Registra o progresso de reprodução em segundos."""
        sql = """
        INSERT INTO playback_progress (media_type, item_id, position, total, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (media_type, item_id) DO UPDATE SET
            position = excluded.position,
            total = excluded.total,
            updated_at = CURRENT_TIMESTAMP
        """
        with self.db.connect() as connection:
            connection.execute(sql, (media_type, item_id, position, total))

    def get_playback_progress(self, media_type: str, item_id: str) -> dict[str, float] | None:
        """Recupera o progresso de reprodução (posição e duração total)."""
        sql = "SELECT position, total FROM playback_progress WHERE media_type = ? AND item_id = ?"
        with self.db.connect() as connection:
            row = connection.execute(sql, (media_type, item_id)).fetchone()
            if row:
                return {"position": float(row["position"]), "total": float(row["total"])}
            return None

    def is_cache_valid(self, media_type: str, ttl_hours: int = 12) -> bool:
        """Verifica se o cache local de uma seção ainda está dentro do TTL configurado."""
        sql = "SELECT max(updated_at) as last_update FROM categories WHERE media_type = ?"
        with self.db.connect() as connection:
            row = connection.execute(sql, (media_type,)).fetchone()
            if not row or not row["last_update"]:
                return False

            check_sql = "SELECT (julianday('now') - julianday(?)) * 24 as diff_hours"
            diff_row = connection.execute(check_sql, (row["last_update"],)).fetchone()
            if diff_row and diff_row["diff_hours"] is not None and diff_row["diff_hours"] <= ttl_hours:
                return True
            return False

    def get_preference(self, key: str, default: str = "") -> str:
        """Recupera uma preferência persistida no banco local."""
        sql = "SELECT value FROM user_preferences WHERE key = ?"
        with self.db.connect() as connection:
            row = connection.execute(sql, (key,)).fetchone()
            if row:
                return str(row["value"])
            return default

    def set_preference(self, key: str, value: str) -> None:
        """Salva ou atualiza uma preferência no banco local."""
        sql = """
        INSERT INTO user_preferences (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """
        with self.db.connect() as connection:
            connection.execute(sql, (key, str(value)))

    def get_tmdb_season_cache(
        self,
        series_name: str,
        season_num: int | str,
        ttl_hours: int = 168,
    ) -> dict[int, dict[str, object]] | None:
        """Recupera metadados enriquecidos de episódios do cache local SQLite se válido."""
        import json

        sql = """
        SELECT payload_json, updated_at,
               (julianday('now') - julianday(updated_at)) * 24 as diff_hours
        FROM tmdb_season_cache
        WHERE series_name = ? AND season_num = ?
        """
        with self.db.connect() as connection:
            row = connection.execute(
                sql, (str(series_name).strip(), int(season_num))
            ).fetchone()
            if (
                row
                and row["diff_hours"] is not None
                and row["diff_hours"] <= ttl_hours
            ):
                try:
                    data = json.loads(row["payload_json"])
                    return {int(k): v for k, v in data.items()}
                except Exception:
                    return None
            return None

    def set_tmdb_season_cache(
        self,
        series_name: str,
        season_num: int | str,
        episodes_map: dict[int, dict[str, object]],
    ) -> None:
        """Salva metadados enriquecidos de episódios de uma temporada no cache local SQLite."""
        import json

        sql = """
        INSERT INTO tmdb_season_cache (series_name, season_num, payload_json, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (series_name, season_num) DO UPDATE SET
            payload_json = excluded.payload_json,
            updated_at = CURRENT_TIMESTAMP
        """
        with self.db.connect() as connection:
            connection.execute(
                sql,
                (
                    str(series_name).strip(),
                    int(season_num),
                    json.dumps(episodes_map, ensure_ascii=False),
                ),
            )

    def optimize(self) -> None:
        """Executa otimização de estatísticas e query planner no SQLite."""
        self.db.optimize()

