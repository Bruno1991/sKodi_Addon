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
    def tmdb(self) -> 'TmdbClient':
        from stv.providers.tmdb.client import TmdbClient
        lang = self.settings.get("tmdb_language", "pt-BR")
        return TmdbClient(language=lang)

    @property
    def epg(self) -> 'ClaroEpgClient':
        from stv.providers.epg.claro import ClaroEpgClient
        return ClaroEpgClient()

    def get_channel_epg(self, channel_name: str) -> tuple['EpgProgram' | None, 'EpgProgram' | None]:
        """Obtém os programas 'No Ar' e 'A Seguir' de um canal com cache local de 4h."""
        if self.settings.get("epg_enabled", "true").lower() == "false":
            return (None, None)

        from stv.providers.epg.normalizer import normalize_channel_name
        channel_key = normalize_channel_name(channel_name)
        if not channel_key:
            return (None, None)

        try:
            ttl_hours = int(self.settings.get("epg_cache_hours", "4"))
        except (ValueError, TypeError):
            ttl_hours = 4

        if not self.catalog.is_epg_cache_valid(channel_key, ttl_hours=ttl_hours):
            programs = self.epg.fetch_channel_programs(channel_name)
            if programs:
                self.catalog.upsert_epg_programs(programs)

        return self.catalog.get_current_and_next_program(channel_key)

