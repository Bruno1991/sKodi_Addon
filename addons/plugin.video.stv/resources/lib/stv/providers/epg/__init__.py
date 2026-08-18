"""Módulo de provedores e processamento de EPG (Guia de Programação)."""
from __future__ import annotations

from stv.providers.epg.claro import ClaroEpgClient
from stv.providers.epg.normalizer import clean_channel_title, normalize_channel_name

__all__ = ["ClaroEpgClient", "clean_channel_title", "normalize_channel_name"]
