from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EpgChannel:
    provider_id: str
    channel_key: str
    epg_id: str
    display_name: str
    normalized_name: str
    icon_url: str = ""


@dataclass(frozen=True)
class EpgProgram:
    provider_id: str
    channel_key: str
    title: str
    start_utc: int
    end_utc: int
    description: str = ""
    category: str = ""
    icon_url: str = ""


@dataclass(frozen=True)
class EpgSnapshot:
    provider_id: str
    channels: tuple[EpgChannel, ...]
    programs: tuple[EpgProgram, ...]
    fetched_at_utc: int
