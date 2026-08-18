from __future__ import annotations

from pathlib import Path

from saile_epg.database import EpgDatabase
from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.providers.xmltv import XmltvProvider
from saile_epg.providers.xtream import RequestCallable, XtreamEpgProvider
from saile_epg.repository import EpgRepository

DEFAULT_PROVIDER_ID = "xtream"


class EpgService:
    def __init__(self, database_path: str | Path) -> None:
        self.database = EpgDatabase(database_path)
        self.database.initialize()
        self.repository = EpgRepository(self.database)

    @classmethod
    def for_profile(cls, profile_path: str | Path) -> "EpgService":
        return cls(Path(profile_path) / "epg.db")

    @classmethod
    def for_kodi(cls) -> "EpgService":
        from saile_core.paths import addon_data_path

        return cls(addon_data_path("script.module.saile.epg", "epg.db"))

    def _store_snapshot(self, snapshot: EpgSnapshot, source: str) -> dict[str, object]:
        try:
            self.repository.replace_snapshot(snapshot)
        except Exception as exc:
            raise EpgSyncError(
                "EPG-STORE",
                "Não foi possível gravar o guia no cache local",
            ) from exc
        return {
            "channel_count": len(snapshot.channels),
            "program_count": len(snapshot.programs),
            "synced_at_utc": snapshot.fetched_at_utc,
            "source": source,
        }

    def sync_xmltv(self, url: str, provider_id: str = DEFAULT_PROVIDER_ID) -> dict[str, object]:
        snapshot = XmltvProvider(url=url, provider_id=provider_id).fetch()
        return self._store_snapshot(snapshot, "XMLTV")

    def sync_xtream(
        self,
        request: RequestCallable,
        live_streams: object,
        provider_id: str = DEFAULT_PROVIDER_ID,
    ) -> dict[str, object]:
        snapshot = XtreamEpgProvider(
            request=request,
            live_streams=live_streams,
            provider_id=provider_id,
        ).fetch()
        return self._store_snapshot(snapshot, "Xtream API")

    def get_now_next(
        self,
        epg_id: str,
        channel_name: str,
        provider_id: str = DEFAULT_PROVIDER_ID,
        at_utc: int | None = None,
    ) -> tuple[EpgProgram | None, EpgProgram | None]:
        return self.repository.get_now_next(provider_id, epg_id, channel_name, at_utc)

    def list_channels(
        self,
        provider_id: str = DEFAULT_PROVIDER_ID,
    ) -> tuple[EpgChannel, ...]:
        return self.repository.list_channels(provider_id)

    def resolve_channel(
        self,
        epg_id: str,
        channel_name: str,
        provider_id: str = DEFAULT_PROVIDER_ID,
    ) -> EpgChannel | None:
        return self.repository.resolve_channel(provider_id, epg_id, channel_name)

    def status(self, provider_id: str = DEFAULT_PROVIDER_ID) -> dict[str, int] | None:
        return self.repository.sync_status(provider_id)

    def clear(self, provider_id: str = DEFAULT_PROVIDER_ID) -> None:
        self.repository.clear(provider_id)
