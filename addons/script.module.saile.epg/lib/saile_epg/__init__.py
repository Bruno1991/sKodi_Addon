"""API pública do módulo EPG local do ecossistema SAILE."""

from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import clean_channel_title, normalize_channel_name
from saile_epg.service import EpgService

__all__ = [
    "EpgChannel",
    "EpgProgram",
    "EpgService",
    "EpgSnapshot",
    "EpgSyncError",
    "clean_channel_title",
    "normalize_channel_name",
]
__version__ = "1.2.0"
