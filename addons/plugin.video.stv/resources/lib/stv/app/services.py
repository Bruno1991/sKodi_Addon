"""Application services coordinate providers, persistence and UI ports.

Keep Kodi imports out of this package so services remain unit-testable.
"""
from __future__ import annotations

import os

from stv.persistence.database import Database
from stv.persistence.repository import CatalogRepository
from stv.providers.xtream.client import XtreamClient


class AppContainer:
    """Dependency injection container for the application."""

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
        """Atualiza TV, tenta XMLTV e usa a API curta Xtream como fallback."""
        live_streams: object | None = None
        if refresh_live_catalog:
            from stv.app.sync import sync_live_catalog

            live_streams = self.xtream.request("get_live_streams")
            sync_live_catalog(self, raw_streams=live_streams)
        try:
            if live_streams is None:
                return self.epg.sync_xmltv(self.xtream.xmltv_url())
            return self.epg.sync_xmltv(
                self.xtream.xmltv_url(),
                live_streams=live_streams,
            )
        except Exception:
            # O XMLTV de alguns painéis passa por proxies que devolvem formatos
            # incompatíveis ou provocam erros fora do parser. A sincronização é
            # manual, portanto ainda tentamos a API curta oficial do Xtream.
            if live_streams is None:
                live_streams = self.xtream.request("get_live_streams")
            return self.epg.sync_xtream(self.xtream.request, live_streams)

    def get_live_catalog(self) -> 'LiveCatalog':
        from stv.domain.live_channels import build_live_catalog

        return build_live_catalog(
            self.epg.list_channels(),
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

