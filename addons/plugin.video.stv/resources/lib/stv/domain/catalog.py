"""Lógica de domínio e operações puras sobre o catálogo IPTV."""
from __future__ import annotations


def first_backdrop(value: object) -> str:
    """Primeiro backdrop do campo `backdrop_path` do Xtream (lista ou string)."""
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    if isinstance(value, str):
        return value.strip()
    return ""


def sanitize_title_for_search(title: str) -> str:
    """Limpa ruídos e sufixos comuns em nomes de canais/filmes para busca."""
    if not title:
        return ""
    # Remove tags comuns de resolução ou idioma
    noise = ["[FHD]", "[HD]", "[SD]", "[4K]", "(LEG)", "(DUB)", "|", "★", "★ "]
    cleaned = title
    for tag in noise:
        cleaned = cleaned.replace(tag, " ")
    return " ".join(cleaned.split()).strip()
