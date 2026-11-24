"""Lógica de domínio e operações puras sobre o catálogo IPTV."""

from __future__ import annotations


def first_backdrop(value: object) -> str:
    """Primeiro backdrop do campo `backdrop_path` do Xtream (lista ou string)."""
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return ""
