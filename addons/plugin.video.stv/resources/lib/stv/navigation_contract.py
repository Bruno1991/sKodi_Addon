from __future__ import annotations

# Ordem fixa; não ordenar alfabeticamente nem misturar com conteúdo dinâmico.
HOME_ENTRIES = (
    ("TV ao Vivo", "section", "live", "stv", "live.png"),
    ("VOD", "section", "vod", "stv", "vod.png"),
    ("Séries", "section", "series", "stv", "series.png"),
    ("Sincronizar Dados", "sync", "", "common", "sync.png"),
)

SECTION_FIXED_ENTRIES = (
    ("Buscar", "search", "common", "search.png"),
    ("Favoritos", "favorites", "stv", "favoritos.png"),
)

VALID_SECTIONS = frozenset({"live", "vod", "series"})
