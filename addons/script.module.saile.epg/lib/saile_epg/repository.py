from __future__ import annotations

import time

from saile_epg.database import EpgDatabase
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import normalize_channel_name


class EpgRepository:
    def __init__(self, database: EpgDatabase) -> None:
        self.database = database

    def replace_snapshot(self, snapshot: EpgSnapshot) -> None:
        if not snapshot.channels:
            raise ValueError("Snapshot EPG sem canais; cache atual preservado")

        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM epg_channels WHERE provider_id = ?",
                (snapshot.provider_id,),
            )
            connection.executemany(
                """
                INSERT INTO epg_channels (
                    provider_id, channel_key, epg_id, display_name,
                    normalized_name, icon_url, updated_at_utc
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
                INSERT INTO epg_programs (
                    provider_id, channel_key, start_utc, end_utc, title,
                    description, category, icon_url, fetched_at_utc
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
                ) VALUES (?, ?, ?, ?)
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
    def _channel_from_row(row: object) -> EpgChannel:
        return EpgChannel(
            provider_id=row["provider_id"],
            channel_key=row["channel_key"],
            epg_id=row["epg_id"],
            display_name=row["display_name"],
            normalized_name=row["normalized_name"],
            icon_url=row["icon_url"],
        )

    def list_channels(self, provider_id: str) -> tuple[EpgChannel, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM epg_channels
                WHERE provider_id = ?
                ORDER BY display_name COLLATE NOCASE, channel_key
                """,
                (provider_id,),
            ).fetchall()
        return tuple(self._channel_from_row(row) for row in rows)

    def resolve_channel(
        self,
        provider_id: str,
        epg_id: str,
        channel_name: str,
    ) -> EpgChannel | None:
        with self.database.connect() as connection:
            if epg_id.strip():
                row = connection.execute(
                    """
                    SELECT * FROM epg_channels
                    WHERE provider_id = ? AND epg_id = ? COLLATE NOCASE
                    LIMIT 1
                    """,
                    (provider_id, epg_id.strip()),
                ).fetchone()
                if row:
                    return self._channel_from_row(row)

            normalized_name = normalize_channel_name(channel_name)
            if normalized_name:
                rows = connection.execute(
                    """
                    SELECT * FROM epg_channels
                    WHERE provider_id = ? AND normalized_name = ?
                    ORDER BY channel_key
                    """,
                    (provider_id, normalized_name),
                ).fetchall()
                if len(rows) == 1:
                    return self._channel_from_row(rows[0])
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

        with self.database.connect() as connection:
            current = connection.execute(
                """
                SELECT * FROM epg_programs
                WHERE provider_id = ? AND channel_key = ?
                  AND start_utc <= ? AND end_utc > ?
                ORDER BY start_utc DESC LIMIT 1
                """,
                (provider_id, channel_key, reference, reference),
            ).fetchone()
            next_row = connection.execute(
                """
                SELECT * FROM epg_programs
                WHERE provider_id = ? AND channel_key = ? AND start_utc > ?
                ORDER BY start_utc LIMIT 1
                """,
                (provider_id, channel_key, reference),
            ).fetchone()

        def convert(row: object) -> EpgProgram | None:
            if row is None:
                return None
            return EpgProgram(
                provider_id=row["provider_id"],
                channel_key=row["channel_key"],
                title=row["title"],
                start_utc=int(row["start_utc"]),
                end_utc=int(row["end_utc"]),
                description=row["description"],
                category=row["category"],
                icon_url=row["icon_url"],
            )

        return (convert(current), convert(next_row))

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
        rows: list[object] = []
        with self.database.connect() as connection:
            for offset in range(0, len(unique_keys), 400):
                chunk = unique_keys[offset : offset + 400]
                placeholders = ",".join("?" for _key in chunk)
                rows.extend(
                    connection.execute(
                        f"""
                        SELECT * FROM epg_programs
                        WHERE provider_id = ?
                          AND channel_key IN ({placeholders})
                          AND end_utc > ?
                        ORDER BY channel_key, start_utc
                        """,
                        (provider_id, *chunk, reference),
                    ).fetchall()
                )

        result: dict[str, tuple[EpgProgram | None, EpgProgram | None]] = {
            key: (None, None) for key in unique_keys
        }
        for row in rows:
            key = str(row["channel_key"])
            current, next_program = result.get(key, (None, None))
            program = EpgProgram(
                provider_id=row["provider_id"],
                channel_key=key,
                title=row["title"],
                start_utc=int(row["start_utc"]),
                end_utc=int(row["end_utc"]),
                description=row["description"],
                category=row["category"],
                icon_url=row["icon_url"],
            )
            if program.start_utc <= reference < program.end_utc:
                if current is None or program.start_utc > current.start_utc:
                    current = program
            elif program.start_utc > reference and next_program is None:
                next_program = program
            result[key] = (current, next_program)
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

    def clear(self, provider_id: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM epg_channels WHERE provider_id = ?", (provider_id,))
            connection.execute("DELETE FROM epg_sync_state WHERE provider_id = ?", (provider_id,))

    def optimize(self) -> None:
        self.database.optimize()
