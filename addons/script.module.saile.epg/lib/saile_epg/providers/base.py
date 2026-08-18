from __future__ import annotations

from typing import Protocol

from saile_epg.models import EpgSnapshot


class EpgProvider(Protocol):
    provider_id: str

    def fetch(self) -> EpgSnapshot: ...
