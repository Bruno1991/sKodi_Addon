"""Application services coordinate providers, persistence and UI ports.

Keep Kodi imports out of this package so services remain unit-testable.
"""
from __future__ import annotations

import os
import threading
import time
from typing import TYPE_CHECKING, Sequence

from stv.persistence.database import Database
from stv.persistence.repository import CatalogRepository
from stv.providers.xtream.client import XtreamClient

if TYPE_CHECKING:
    from saile_epg.models import EpgProgram
    from stv.domain.models import MediaItem


class AppContainer:
    """Dependency injection container for the application."""

    _epg_sync_lock: threading.Lock = threading.Lock()
    _epg_syncing: bool = False

    def __init__(self, settings: dict[str, str]) -> None:
        self.settings = settings
        
        # Lazy initialization
        self._xtream_client: XtreamClient | None = None
        self._database: Database | None = None
        self._catalog_repo: CatalogRepository | None = None
        self._tmdb_client: object | None = None
        self._epg_service: object | None = None

    @property
    def xtream(self) -> XtreamClient:
        if self._xtream_client is None:
            host = self.settings.get("xtream_url", "")
            username = self.settings.get("xtream_username", "")
            password = self.settings.get("xtream_password", "")
            self._xtream_client = XtreamClient(host=host, username=username, password=password)
        return self._xtream_client

    @property
    def database(self) -> Database:
        if self._database is None:
            db_path = os.path.join(self.settings.get("profile_path", ""), "stv.db")
            self._database = Database(db_path)
            self._database.initialize()
        return self._database

    @property
    def catalog(self) -> CatalogRepository:
        if self._catalog_repo is None:
            self._catalog_repo = CatalogRepository(self.database)
        return self._catalog_repo

    @property
    def preferred_view_mode(self) -> int:
        """Retorna o modo de visualização configurado (padrão: 54 - InfoWall)."""
        mode_str = self.settings.get("preferred_view_mode")
        if not mode_str:
            try:
                mode_str = self.catalog.get_preference("view_mode", "54")
            except Exception:
                mode_str = "54"
        try:
            return int(mode_str)
        except Exception:
            return 54

    @property
    def tmdb(self) -> 'TmdbClient':
        from stv.providers.tmdb.client import TmdbClient
        if self._tmdb_client is None:
            lang = self.settings.get("tmdb_language", "pt-BR")
            self._tmdb_client = TmdbClient(language=lang)
        return self._tmdb_client

    @property
    def epg(self) -> 'EpgService':
        from saile_epg import EpgService

        if self._epg_service is None:
            profile_path = self.settings.get("epg_profile_path", "")
            self._epg_service = (
                EpgService.for_profile(profile_path) if profile_path else EpgService.for_kodi()
            )
        return self._epg_service

    def is_epg_cache_valid(self, ttl_hours: int | None = None) -> bool:
        """Verifica se o cache do EPG ainda está dentro do período de validade configurado."""
        if ttl_hours is None:
            try:
                ttl_hours = int(self.settings.get("epg_ttl_hours", "6") or 6)
            except (ValueError, TypeError):
                ttl_hours = 6
        status = self.epg.status("claro")
        if not status or not status.get("synced_at_utc"):
            return False
        age_seconds = int(time.time()) - int(status["synced_at_utc"])
        return age_seconds < (ttl_hours * 3600)

    def trigger_background_epg_sync_if_expired(self) -> bool:
        """Dispara auto-atualização silenciosa em background se o cache do EPG estiver expirado."""
        if self.settings.get("epg_enabled", "true").lower() == "false":
            return False
        if self.is_epg_cache_valid():
            return False

        with AppContainer._epg_sync_lock:
            if AppContainer._epg_syncing:
                return False
            AppContainer._epg_syncing = True

        def _bg_worker() -> None:
            try:
                self.sync_epg(refresh_live_catalog=False)
            except Exception:
                pass
            finally:
                with AppContainer._epg_sync_lock:
                    AppContainer._epg_syncing = False

        thread = threading.Thread(target=_bg_worker, daemon=True, name="sTv-EpgSync")
        thread.start()
        return True

    def get_items_epg_schedule(
        self,
        items: Sequence['MediaItem'],
    ) -> dict[str, tuple['EpgProgram' | None, 'EpgProgram' | None]]:
        """Resolve Agora/Próximo em lote para uma lista de itens/canais em 1 única query SQL."""
        if self.settings.get("epg_enabled", "true").lower() == "false" or not items:
            return {}
        item_to_key: dict[str, str] = {}
        for item in items:
            ch = self.epg.resolve_channel(item.epg_id, item.name)
            if ch and ch.channel_key:
                item_to_key[item.item_id] = ch.channel_key
        unique_keys = tuple(set(item_to_key.values()))
        if not unique_keys:
            return {}
        key_schedule = self.epg.get_now_next_many(unique_keys)
        return {
            item_id: key_schedule.get(key, (None, None))
            for item_id, key in item_to_key.items()
        }

    def get_channel_epg(
        self,
        channel_name: str,
        epg_id: str = "",
    ) -> tuple['EpgProgram' | None, 'EpgProgram' | None]:
        """Consulta Agora/Próximo apenas no cache local do módulo EPG."""
        if self.settings.get("epg_enabled", "true").lower() == "false":
            return (None, None)
        return self.epg.get_now_next(epg_id=epg_id, channel_name=channel_name)

    def sync_epg(self, refresh_live_catalog: bool = False) -> dict[str, object]:
        """Sincroniza o guia oficial da Claro TV+ como fonte oficial da verdade."""
        live_streams: object | None = None
        if refresh_live_catalog:
            from stv.app.sync import sync_live_catalog

            if hasattr(self.xtream, "request"):
                live_streams = self.xtream.request("get_live_streams")
            sync_live_catalog(self, raw_streams=live_streams)

        # 1. Fonte Oficial: Claro TV+ (AVSClient v1.2)
        if hasattr(self.epg, "sync_claro"):
            try:
                return self.epg.sync_claro()
            except Exception:
                pass

        # 2. Fallback: XMLTV
        if hasattr(self.epg, "sync_xmltv") and hasattr(self.xtream, "xmltv_url"):
            try:
                xmltv_url = self.xtream.xmltv_url()
                if live_streams is None:
                    return self.epg.sync_xmltv(xmltv_url)
                return self.epg.sync_xmltv(xmltv_url, live_streams=live_streams)
            except Exception:
                pass

        # 3. Fallback: API curta do Xtream
        if hasattr(self.epg, "sync_xtream") and hasattr(self.xtream, "request"):
            if live_streams is None:
                live_streams = self.xtream.request("get_live_streams")
            return self.epg.sync_xtream(self.xtream.request, live_streams)

        return {"channel_count": 0, "program_count": 0, "source": "Indisponível"}

    def get_live_catalog(self) -> 'LiveCatalog':
        from stv.domain.live_channels import build_live_catalog

        channels = self.epg.list_channels()
        if not channels:
            try:
                self.epg.sync_claro()
                channels = self.epg.list_channels()
            except Exception:
                pass

        return build_live_catalog(
            channels,
            self.catalog.get_all_media_items("live"),
        )

    def get_live_schedule(
        self,
        channel_keys: tuple[str, ...],
    ) -> dict[str, tuple['EpgProgram' | None, 'EpgProgram' | None]]:
        if self.settings.get("epg_enabled", "true").lower() == "false":
            return {key: (None, None) for key in channel_keys}
        return self.epg.get_now_next_many(channel_keys)

    def choose_live_variant(
        self,
        channel_key: str,
    ) -> 'MediaItem':
        from stv.domain.live_channels import choose_live_variant

        group = self.get_live_catalog().get_group(channel_key)
        if group is None:
            raise ValueError("Canal do EPG não encontrado no catálogo local")
        try:
            bandwidth_limit = float(self.settings.get("live_bandwidth_limit_mbps", "0") or 0)
        except (TypeError, ValueError):
            bandwidth_limit = 0.0
        max_quality = self.settings.get("live_max_quality", "auto") or "auto"
        return choose_live_variant(
            group.variants,
            max_quality=max_quality,
            bandwidth_limit_mbps=bandwidth_limit,
            probe=lambda item: self.xtream.probe_stream("live", item.item_id, item.extension),
        )

    def get_season_episodes_metadata(
        self,
        series_name: str,
        season_num: int | str,
        tmdb_id: str | int | None = None,
    ) -> dict[int, dict[str, object]]:
        """Busca metadados enriquecidos e frames 16:9 dos episódios com cache SQLite."""
        try:
            season_int = int(season_num)
        except (ValueError, TypeError):
            season_int = 1

        cached = self.catalog.get_tmdb_season_cache(series_name, season_int)
        if cached:
            return cached

        episodes_meta: dict[int, dict[str, object]] = {}
        try:
            target_id = tmdb_id
            if not target_id:
                show = self.tmdb.search_tv(series_name)
                if show:
                    target_id = show.get("id")

            if target_id:
                episodes_meta = self.tmdb.get_season_episodes(target_id, season_int)
                if episodes_meta:
                    self.catalog.set_tmdb_season_cache(series_name, season_int, episodes_meta)
        except Exception:
            episodes_meta = {}

        return episodes_meta


