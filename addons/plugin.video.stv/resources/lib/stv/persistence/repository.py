from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Sequence

from stv.domain.models import Category, EpgProgram, MediaItem
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
            media_type, item_id, category_id, name, icon, fanart, plot, extension, generation_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (media_type, item_id) DO UPDATE SET
            category_id = excluded.category_id,
            name = excluded.name,
            icon = CASE WHEN excluded.icon != '' THEN excluded.icon ELSE media_items.icon END,
            fanart = CASE WHEN excluded.fanart != '' THEN excluded.fanart ELSE media_items.fanart END,
            plot = CASE WHEN excluded.plot != '' THEN excluded.plot ELSE media_items.plot END,
            extension = excluded.extension,
            generation_id = excluded.generation_id,
            updated_at = CURRENT_TIMESTAMP
        """
        data = [
            (i.media_type, i.item_id, i.category_id, i.name, i.icon, i.fanart, i.plot, i.extension, i.generation_id)
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
        if media_type == "vod" and hasattr(tmdb_client, "search_movie"):
            data = tmdb_client.search_movie(title)
        elif media_type == "series" and hasattr(tmdb_client, "search_tv"):
            data = tmdb_client.search_tv(title)
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
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def search_media(self, media_type: str, query: str) -> list[MediaItem]:
        """Pesquisa itens de mídia usando FTS5 com fallback para LIKE."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        # 1. Tentar busca via FTS5
        fts_sql = """
        SELECT m.* FROM media_items m
        JOIN media_items_fts f ON m.rowid = f.rowid
        WHERE f.media_type = ? AND media_items_fts MATCH ?
        ORDER BY rank
        LIMIT 100
        """
        try:
            # Formata query para FTS5 com prefix matching
            fts_query = " ".join(f'"{token}"*' for token in cleaned_query.split())
            with self.db.connect() as connection:
                rows = connection.execute(fts_sql, (media_type, fts_query)).fetchall()
                if rows:
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
                            generation_id=row["generation_id"],
                        )
                        for row in rows
                    ]
        except Exception:
            pass

        # 2. Fallback resiliente com LIKE
        fallback_sql = "SELECT * FROM media_items WHERE media_type = ? AND name LIKE ? ORDER BY name COLLATE NOCASE LIMIT 100"
        with self.db.connect() as connection:
            rows = connection.execute(fallback_sql, (media_type, f"%{cleaned_query}%")).fetchall()

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
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

    def get_favorites(self, media_type: str) -> list[MediaItem]:
        """Recupera todos os itens marcados como favoritos em ordem cronológica reversa."""
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
                generation_id=row["generation_id"],
            )
            for row in rows
        ]

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

    def clean_obsolete_categories(self, media_type: str, current_generation: int) -> int:
        """Remove categorias de gerações anteriores que não existem mais no servidor."""
        sql = "DELETE FROM categories WHERE media_type = ? AND generation_id < ?"
        with self.db.connect() as connection:
            cursor = connection.execute(sql, (media_type, current_generation))
            return cursor.rowcount

    def clean_obsolete_items(self, media_type: str, current_generation: int) -> int:
        """Remove itens obsoletos e sincroniza estritamente os favoritos."""
        sql = "DELETE FROM media_items WHERE media_type = ? AND generation_id < ?"
        clean_favs_sql = """
        DELETE FROM favorites WHERE media_type = ? AND item_id NOT IN (
            SELECT item_id FROM media_items WHERE media_type = ?
        )
        """
        with self.db.connect() as connection:
            cursor = connection.execute(sql, (media_type, current_generation))
            deleted_items = cursor.rowcount
            connection.execute(clean_favs_sql, (media_type, media_type))
            return deleted_items

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

    def upsert_epg_programs(self, programs: Sequence[EpgProgram]) -> None:
        """Insere ou atualiza programas de EPG no SQLite."""
        if not programs:
            return
        sql = """
        INSERT INTO epg_programs (
            channel_key, title, start_time, end_time, synopsis, duration, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (channel_key, start_time) DO UPDATE SET
            title = excluded.title,
            end_time = excluded.end_time,
            synopsis = excluded.synopsis,
            duration = excluded.duration,
            updated_at = CURRENT_TIMESTAMP
        """
        data = [
            (p.channel_key, p.title, p.start_time, p.end_time, p.synopsis, p.duration_minutes)
            for p in programs
        ]
        with self.db.connect() as connection:
            connection.executemany(sql, data)

    def get_current_and_next_program(
        self,
        channel_key: str,
        ref_time: datetime | None = None,
    ) -> tuple[EpgProgram | None, EpgProgram | None]:
        """Recupera o programa atualmente no ar e o próximo programa para um canal."""
        now = ref_time or datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")

        # 1. Programa NO AR: start_time <= now_str e (end_time > now_str ou start_time mais recente <= now)
        current_sql = """
        SELECT * FROM epg_programs
        WHERE channel_key = ? AND start_time <= ? AND end_time > ?
        ORDER BY start_time DESC
        LIMIT 1
        """
        
        current_sql_fallback = """
        SELECT * FROM epg_programs
        WHERE channel_key = ? AND start_time <= ?
        ORDER BY start_time DESC
        LIMIT 1
        """

        # 2. Próximo Programa: start_time > agora
        next_sql = """
        SELECT * FROM epg_programs
        WHERE channel_key = ? AND start_time > ?
        ORDER BY start_time ASC
        LIMIT 1
        """

        with self.db.connect() as connection:
            row_current = connection.execute(current_sql, (channel_key, now_str, now_str)).fetchone()
            if not row_current:
                row_current = connection.execute(current_sql_fallback, (channel_key, now_str)).fetchone()

            current_prog = None
            if row_current:
                current_prog = EpgProgram(
                    channel_key=row_current["channel_key"],
                    title=row_current["title"],
                    start_time=row_current["start_time"],
                    end_time=row_current["end_time"],
                    synopsis=row_current["synopsis"],
                    duration_minutes=int(row_current["duration"]),
                )

            next_ref = current_prog.end_time if (current_prog and current_prog.end_time) else now_str
            row_next = connection.execute(next_sql, (channel_key, next_ref)).fetchone()
            if not row_next and current_prog and current_prog.start_time:
                row_next = connection.execute(next_sql, (channel_key, current_prog.start_time)).fetchone()

            next_prog = None
            if row_next:
                next_prog = EpgProgram(
                    channel_key=row_next["channel_key"],
                    title=row_next["title"],
                    start_time=row_next["start_time"],
                    end_time=row_next["end_time"],
                    synopsis=row_next["synopsis"],
                    duration_minutes=int(row_next["duration"]),
                )

        return (current_prog, next_prog)

    def is_epg_cache_valid(self, channel_key: str, ttl_hours: int = 4) -> bool:
        """Verifica se o cache de EPG para o canal está dentro do TTL configurado (padrão 4h)."""
        sql = "SELECT max(updated_at) as last_update FROM epg_programs WHERE channel_key = ?"
        with self.db.connect() as connection:
            row = connection.execute(sql, (channel_key,)).fetchone()
            if not row or not row["last_update"]:
                return False

            check_sql = "SELECT (julianday('now') - julianday(?)) * 24 as diff_hours"
            diff_row = connection.execute(check_sql, (row["last_update"],)).fetchone()
            if diff_row and diff_row["diff_hours"] is not None and diff_row["diff_hours"] <= ttl_hours:
                return True
            return False

    def clean_expired_epg(self, before_iso: str | None = None) -> int:
        """Remove registros antigos de EPG cuja exibição já encerrou há mais de 12h."""
        if before_iso:
            cutoff = before_iso
        else:
            cutoff = (datetime.now() - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M")

        sql = "DELETE FROM epg_programs WHERE end_time != '' AND end_time < ?"
        with self.db.connect() as connection:
            cursor = connection.execute(sql, (cutoff,))
            return cursor.rowcount

