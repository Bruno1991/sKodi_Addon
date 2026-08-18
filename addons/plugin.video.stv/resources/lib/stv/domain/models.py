"""Modelos de domínio do add-on sTv (IPTV)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """Representa uma categoria de mídia (TV ao Vivo, VOD ou Séries)."""

    category_id: str
    name: str
    parent_id: str = "0"
    media_type: str = "live"
    generation_id: int = 0


@dataclass(frozen=True)
class MediaItem:
    """Representa um canal de TV, filme ou série do provedor Xtream."""

    media_type: str
    item_id: str
    name: str
    category_id: str = ""
    icon: str = ""
    fanart: str = ""
    plot: str = ""
    extension: str = ""
    generation_id: int = 0


@dataclass(frozen=True)
class EpgProgram:
    """Representa um programa do Guia de Programação Eletrônico (EPG)."""

    channel_key: str
    title: str
    start_time: str
    end_time: str
    synopsis: str = ""
    duration_minutes: int = 0

