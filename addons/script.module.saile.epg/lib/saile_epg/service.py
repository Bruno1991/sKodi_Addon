from __future__ import annotations

from pathlib import Path

from saile_epg.database import EpgDatabase
from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.providers.claro import ClaroEpgProvider
from saile_epg.providers.xmltv import XmltvProvider
from saile_epg.providers.xtream import (
    RequestCallable,
    XtreamEpgProvider,
    extract_xtream_channels,
)
from saile_epg.repository import EpgRepository

DEFAULT_PROVIDER_ID = ""


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

    def sync_claro(
        self,
        provider_id: str = "claro",
        window_hours: int = 24,
        wipe_legacy: bool = True,
    ) -> dict[str, object]:
        """Sincroniza o guia oficial da Claro TV+ diretamente via API oficial com logos em alta resolução."""
        if wipe_legacy:
            self.repository.clear_all()
        snapshot = ClaroEpgProvider(provider_id=provider_id).fetch(window_hours=window_hours)
        return self._store_snapshot(snapshot, "Claro TV+ Oficial")

    def sync_xmltv(
        self,
        url: str,
        provider_id: str = "xmltv",
        live_streams: object | None = None,
    ) -> dict[str, object]:
        snapshot = XmltvProvider(url=url, provider_id=provider_id).fetch()
        source = "XMLTV"
        if live_streams is not None:
            by_epg_id = {
                channel.epg_id.casefold(): channel for channel in snapshot.channels
            }
            before = len(by_epg_id)
            for channel in extract_xtream_channels(live_streams, provider_id):
                by_epg_id.setdefault(channel.epg_id.casefold(), channel)
            if len(by_epg_id) > before:
                source = "XMLTV + catálogo Xtream"
                snapshot = EpgSnapshot(
                    provider_id=snapshot.provider_id,
                    channels=tuple(
                        sorted(
                            by_epg_id.values(),
                            key=lambda channel: (
                                channel.display_name.casefold(),
                                channel.channel_key.casefold(),
                            ),
                        )
                    ),
                    programs=snapshot.programs,
                    fetched_at_utc=snapshot.fetched_at_utc,
                )
        return self._store_snapshot(snapshot, source)

    def sync_xtream(
        self,
        request: RequestCallable,
        live_streams: object,
        provider_id: str = "xtream",
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

    def get_now_next_many(
        self,
        channel_keys: tuple[str, ...],
        provider_id: str = DEFAULT_PROVIDER_ID,
        at_utc: int | None = None,
    ) -> dict[str, tuple[EpgProgram | None, EpgProgram | None]]:
        return self.repository.get_now_next_many(provider_id, channel_keys, at_utc)

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

    def status(self, provider_id: str = "claro") -> dict[str, int] | None:
        return self.repository.sync_status(provider_id)

    def clear(self, provider_id: str = "claro") -> None:
        self.repository.clear(provider_id)

    def optimize(self) -> None:
        self.repository.optimize()
