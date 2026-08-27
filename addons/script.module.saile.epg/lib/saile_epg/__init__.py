"""API pública do módulo sEPG local do ecossistema sKodi."""

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import (
    clean_channel_title,
    get_canonical_channel_name,
    normalize_channel_name,
    normalize_search_term,
    strip_accents,
)
from saile_epg.service import EpgService

__all__ = [
    "EpgChannel",
    "EpgProgram",
    "EpgService",
    "EpgSnapshot",
    "EpgSyncError",
    "clean_channel_title",
    "get_canonical_channel_name",
    "normalize_channel_name",
    "normalize_search_term",
    "strip_accents",
]
__version__ = "1.4.1"
