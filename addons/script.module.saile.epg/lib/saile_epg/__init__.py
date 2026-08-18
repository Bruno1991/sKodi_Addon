"""API pública do módulo EPG local do ecossistema SAILE."""

from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.service import EpgService

__all__ = ["EpgChannel", "EpgProgram", "EpgService", "EpgSnapshot"]
__version__ = "1.0.0"
