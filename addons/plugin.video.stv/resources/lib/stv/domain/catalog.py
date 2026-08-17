"""Lógica de domínio e operações puras sobre o catálogo IPTV."""
from __future__ import annotations

from typing import Sequence
from stv.domain.models import Category, MediaItem


def filter_categories_by_parent(categories: Sequence[Category], parent_id: str = "0") -> list[Category]:
    """Filtra categorias pelo ID da categoria pai (para hierarquia)."""
    return [c for c in categories if c.parent_id == str(parent_id)]


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
