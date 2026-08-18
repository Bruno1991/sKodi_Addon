from __future__ import annotations

import time

from saile_epg.database import EpgDatabase
from saile_epg.models import EpgProgram, EpgSnapshot
from saile_epg.normalizer import normalize_channel_name


class EpgRepository:
    def __init__(self, database: EpgDatabase) -> None:
        self.database = database

    def replace_snapshot(self, snapshot: EpgSnapshot) -> None:
        if not snapshot.channels or not snapshot.programs:
            raise ValueError("Snapshot XMLTV vazio; cache atual preservado")

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

    def _resolve_channel_key(self, provider_id: str, epg_id: str, channel_name: str) -> str:
        with self.database.connect() as connection:
            if epg_id.strip():
                row = connection.execute(
                    """
                    SELECT channel_key FROM epg_channels
                    WHERE provider_id = ? AND epg_id = ? COLLATE NOCASE
                    LIMIT 1
                    """,
                    (provider_id, epg_id.strip()),
                ).fetchone()
                if row:
                    return str(row["channel_key"])

            normalized_name = normalize_channel_name(channel_name)
            if normalized_name:
                row = connection.execute(
                    """
                    SELECT channel_key FROM epg_channels
                    WHERE provider_id = ? AND normalized_name = ?
                    ORDER BY channel_key
                    LIMIT 1
                    """,
                    (provider_id, normalized_name),
                ).fetchone()
                if row:
                    return str(row["channel_key"])
        return ""

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
