from __future__ import annotations

import sqlite3
import time

from saile_epg.database import EpgDatabase
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import get_canonical_channel_name, normalize_channel_name


class EpgRepository:
    def __init__(self, database: EpgDatabase) -> None:
        self.database = database

    def replace_snapshot(self, snapshot: EpgSnapshot, *, wipe_all: bool = False) -> None:
        if not snapshot.channels:
            raise ValueError("Snapshot EPG sem canais; cache atual preservado")

        with self.database.connect() as connection:
            if wipe_all:
                connection.execute("DELETE FROM epg_programs")
                connection.execute("DELETE FROM epg_channels")
                connection.execute("DELETE FROM epg_sync_state")
            else:
                connection.execute(
                    "DELETE FROM epg_programs WHERE provider_id = ?",
                    (snapshot.provider_id,),
                )
                connection.execute(
                    "DELETE FROM epg_channels WHERE provider_id = ?",
                    (snapshot.provider_id,),
                )

            connection.executemany(
                """
                INSERT OR REPLACE INTO epg_channels (
                    provider_id,
                    channel_key,
                    epg_id,
                    display_name,
                    normalized_name,
                    icon_url,
                    updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        channel.provider_id,
                        channel.channel_key,
                        channel.epg_id,
                        channel.display_name,
                        channel.normalized_name,
                        channel.icon_url,
                        snapshot.fetched_at_utc,
                    )
                    for channel in snapshot.channels
                ],
            )
            connection.executemany(
                """
                INSERT OR REPLACE INTO epg_programs (
                    provider_id,
                    channel_key,
                    start_utc,
                    end_utc,
                    title,
                    description,
                    category,
                    icon_url,
                    fetched_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        program.provider_id,
                        program.channel_key,
                        program.start_utc,
                        program.end_utc,
                        program.title,
                        program.description,
                        program.category,
                        program.icon_url,
                        snapshot.fetched_at_utc,
                    )
                    for program in snapshot.programs
                ],
            )
            connection.execute(
                """
                INSERT INTO epg_sync_state (
                    provider_id, synced_at_utc, channel_count, program_count
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    synced_at_utc = excluded.synced_at_utc,
                    channel_count = excluded.channel_count,
                    program_count = excluded.program_count
                """,
                (
                    snapshot.provider_id,
                    snapshot.fetched_at_utc,
                    len(snapshot.channels),
                    len(snapshot.programs),
                ),
            )
        self.database.optimize()

    @staticmethod
    def _channel_from_row(row: sqlite3.Row) -> EpgChannel:
        return EpgChannel(
            provider_id=row["provider_id"],
            channel_key=row["channel_key"],
            epg_id=row["epg_id"],
            display_name=row["display_name"],
            normalized_name=row["normalized_name"],
            icon_url=row["icon_url"],
        )

    @staticmethod
    def _program_from_row(row: sqlite3.Row) -> EpgProgram:
        return EpgProgram(
            provider_id=row["provider_id"],
            channel_key=str(row["channel_key"]),
            title=row["title"],
            start_utc=int(row["start_utc"]),
            end_utc=int(row["end_utc"]),
            description=row["description"],
            category=row["category"],
            icon_url=row["icon_url"],
        )

    def list_channels(self, provider_id: str = "") -> tuple[EpgChannel, ...]:
        with self.database.connect() as connection:
            if provider_id:
                rows = connection.execute(
                    """
                    SELECT * FROM epg_channels
                    WHERE provider_id = ?
                    ORDER BY display_name COLLATE NOCASE, channel_key
                    """,
                    (provider_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM epg_channels
                    ORDER BY display_name COLLATE NOCASE, channel_key
                    """,
                ).fetchall()
        return tuple(self._channel_from_row(row) for row in rows)

    def resolve_channel(
        self,
        provider_id: str,
        epg_id: str,
        channel_name: str,
    ) -> EpgChannel | None:
        with self.database.connect() as connection:

            def _query_one(
                condition: str, value: str, order_by: str = "channel_key"
            ) -> EpgChannel | None:
                if provider_id:
                    sql = (
                        "SELECT * FROM epg_channels "
                        f"WHERE provider_id = ? AND {condition} ORDER BY {order_by} LIMIT 1"
                    )
                    row = connection.execute(sql, (provider_id, value)).fetchone()
                else:
                    sql = (
                        "SELECT * FROM epg_channels "
                        f"WHERE {condition} ORDER BY provider_id, {order_by} LIMIT 1"
                    )
                    row = connection.execute(sql, (value,)).fetchone()
                return self._channel_from_row(row) if row else None

            # 1. Busca por epg_id explícito
            clean_epg_id = (epg_id or "").strip()
            if clean_epg_id:
                matched = _query_one("epg_id = ? COLLATE NOCASE", clean_epg_id)
                if matched:
                    return matched

            # 2. Busca por nome canônico com tabela de aliases
            canonical = get_canonical_channel_name(channel_name)
            if canonical:
                matched = _query_one("normalized_name = ?", canonical)
                if matched:
                    return matched

            # 3. Busca por nome normalizado direto
            normalized = normalize_channel_name(channel_name)
            if normalized and normalized != canonical:
                matched = _query_one("normalized_name = ?", normalized)
                if matched:
                    return matched

            # 4. Busca sem espaços
            if normalized:
                matched = _query_one(
                    "REPLACE(normalized_name, ' ', '') = ?", normalized.replace(" ", "")
                )
                if matched:
                    return matched

        return None

    def _resolve_channel_key(self, provider_id: str, epg_id: str, channel_name: str) -> str:
        channel = self.resolve_channel(provider_id, epg_id, channel_name)
        return channel.channel_key if channel else ""

    def get_now_next(
        self,
        provider_id: str,
        epg_id: str,
        channel_name: str,
        at_utc: int | None = None,
    ) -> tuple[EpgProgram | None, EpgProgram | None]:
        channel_key = self._resolve_channel_key(provider_id, epg_id, channel_name)
        if not channel_key:
            return (None, None)
        reference = int(time.time()) if at_utc is None else int(at_utc)

        provider_clause = "provider_id = ? AND " if provider_id else ""
        prefix_params: tuple[object, ...] = (provider_id,) if provider_id else ()

        with self.database.connect() as connection:
            current = connection.execute(
                f"""
                SELECT * FROM epg_programs
                WHERE {provider_clause}channel_key = ?
                  AND start_utc <= ? AND end_utc > ?
                ORDER BY start_utc DESC LIMIT 1
                """,
                (*prefix_params, channel_key, reference, reference),
            ).fetchone()
            next_row = connection.execute(
                f"""
                SELECT * FROM epg_programs
                WHERE {provider_clause}channel_key = ? AND start_utc > ?
                ORDER BY start_utc LIMIT 1
                """,
                (*prefix_params, channel_key, reference),
            ).fetchone()

        return (
            self._program_from_row(current) if current is not None else None,
            self._program_from_row(next_row) if next_row is not None else None,
        )

    def get_now_next_many(
        self,
        provider_id: str,
        channel_keys: tuple[str, ...],
        at_utc: int | None = None,
    ) -> dict[str, tuple[EpgProgram | None, EpgProgram | None]]:
        """Carrega Agora/Próximo de vários canais sem consultas N+1."""
        unique_keys = tuple(dict.fromkeys(key for key in channel_keys if key))
        if not unique_keys:
            return {}
        reference = int(time.time()) if at_utc is None else int(at_utc)
        provider_clause = "provider_id = ? AND " if provider_id else ""
        prefix_params: tuple[object, ...] = (provider_id,) if provider_id else ()

        rows: list[sqlite3.Row] = []
        with self.database.connect() as connection:
            for offset in range(0, len(unique_keys), 400):
                chunk = unique_keys[offset : offset + 400]
                placeholders = ",".join("?" for _key in chunk)
                rows.extend(
                    connection.execute(
                        f"""
                        SELECT * FROM epg_programs
                        WHERE {provider_clause}channel_key IN ({placeholders})
                          AND end_utc > ?
                        ORDER BY channel_key, start_utc
                        """,
                        (*prefix_params, *chunk, reference),
                    ).fetchall()
                )

        result: dict[str, tuple[EpgProgram | None, EpgProgram | None]] = {
            key: (None, None) for key in unique_keys
        }
        for row in rows:
            program = self._program_from_row(row)
            current, next_program = result.get(program.channel_key, (None, None))
            if program.start_utc <= reference < program.end_utc:
                if current is None or program.start_utc > current.start_utc:
                    current = program
            elif program.start_utc > reference and next_program is None:
                next_program = program
            result[program.channel_key] = (current, next_program)
        return result

    def sync_status(self, provider_id: str) -> dict[str, int] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM epg_sync_state WHERE provider_id = ?",
                (provider_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "synced_at_utc": int(row["synced_at_utc"]),
            "channel_count": int(row["channel_count"]),
            "program_count": int(row["program_count"]),
        }

    def clear(self, provider_id: str = "") -> None:
        with self.database.connect() as connection:
            if provider_id:
                connection.execute("DELETE FROM epg_programs WHERE provider_id = ?", (provider_id,))
                connection.execute("DELETE FROM epg_channels WHERE provider_id = ?", (provider_id,))
                connection.execute(
                    "DELETE FROM epg_sync_state WHERE provider_id = ?", (provider_id,)
                )
            else:
                connection.execute("DELETE FROM epg_programs")
                connection.execute("DELETE FROM epg_channels")
                connection.execute("DELETE FROM epg_sync_state")

    def clear_all(self) -> None:
        """Limpa completamente todo o banco de dados do EPG."""
        self.clear("")

    def optimize(self) -> None:
        self.database.optimize()
