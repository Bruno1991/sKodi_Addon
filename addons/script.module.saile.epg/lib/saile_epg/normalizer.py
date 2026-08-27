from __future__ import annotations

import re
import unicodedata

_COUNTRY_PREFIXES = re.compile(
    r"^(BR|PT|USA|UK|ES|LATAM|INT|EN|AR|CL|UY|CO|MX)\s*[:|\-/.]\s*"
    r"|^\[(BR|PT|USA|UK|ES|LATAM|INT)\]\s*"
    r"|^\((BR|PT|USA|UK|ES|LATAM|INT)\)\s*",
    re.IGNORECASE,
)
_QUALITY_TAGS = re.compile(
    r"\b(4K|UHD|FHD|HD|SD|HEVC|H\.?265|H\.?264|60FPS|1080P|720P|480P|RAW)\b",
    re.IGNORECASE,
)
_REDUNDANCY_TAGS = re.compile(
    r"\[(BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL)\]"
    r"|\((BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL)\)"
    r"|\b(BACKUP|ALT|VIP)\b",
    re.IGNORECASE,
)
_EXTRA_PUNCTUATION = re.compile(r"[\[\](){}_\|#*~]")


def strip_accents(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _strip_accents(text: str) -> str:
    return strip_accents(text)


def normalize_search_term(text: str) -> str:
    """Normaliza texto para busca insensível a acentos, maiúsculas e pontuação."""
    if not text:
        return ""
    cleaned = strip_accents(text).upper()
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_channel_title(raw_name: str) -> str:
    if not raw_name:
        return ""
    name = _COUNTRY_PREFIXES.sub("", raw_name.strip())
    name = _REDUNDANCY_TAGS.sub("", name)
    name = _QUALITY_TAGS.sub("", name)
    name = _EXTRA_PUNCTUATION.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" -:.")
    if not name:
        return raw_name.strip()

    acronyms = {
        "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "DF", "GO", "ES",
        "MT", "MS", "PA", "AM", "HBO", "ESPN", "CNN", "TNT", "AXN", "GNT", "BIS",
        "OFF", "TLC", "MTV", "SBT", "BBC", "FX", "ID", "E!", "USA", "VIVA", "MAX",
        "DMAX", "AMC", "SYFY",
    }
    branded = {
        "SPORTV": "SporTV",
        "BANDNEWS": "BandNews",
        "GLOOB": "Gloob",
        "GLOOBINHO": "Gloobinho",
        "MEGAPIX": "Megapix",
        "CARTOONITO": "Cartoonito",
        "CINEMAX": "Cinemax",
        "TELECINE": "Telecine",
    }
    return " ".join(
        branded.get(word.upper(), word.upper() if word.upper() in acronyms else word.capitalize())
        for word in name.split()
    )


def normalize_channel_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    cleaned = _strip_accents(raw_name).upper()
    cleaned = _COUNTRY_PREFIXES.sub("", cleaned)
    cleaned = _REDUNDANCY_TAGS.sub("", cleaned)
    cleaned = _QUALITY_TAGS.sub("", cleaned)
    cleaned = _EXTRA_PUNCTUATION.sub(" ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


_CHANNEL_ALIASES: dict[str, str] = {
    # GLOBO
    "GLOBO": "GLOBO SP",
    "REDE GLOBO": "GLOBO SP",
    "TV GLOBO": "GLOBO SP",
    "GLOBO SAO PAULO": "GLOBO SP",
    "GLOBO RIO": "GLOBO SP",
    "GLOBO RJ": "GLOBO SP",
    "GLOBO MINAS": "GLOBO SP",
    "GLOBO MG": "GLOBO SP",
    "GLOBO BRASILIA": "GLOBO SP",
    "GLOBO DF": "GLOBO SP",
    "GLOBO RS": "GLOBO SP",
    "GLOBO BAHIA": "GLOBO SP",
    "GLOBO BA": "GLOBO SP",
    "GLOBO PE": "GLOBO SP",
    "GLOBO NORDESTE": "GLOBO SP",
    "GLOBO PARANA": "GLOBO SP",
    "GLOBO PR": "GLOBO SP",
    # SBT
    "SBT SP": "SBT",
    "SBT RJ": "SBT",
    "SBT BRASIL": "SBT",
    "REDE SBT": "SBT",
    "TV SBT": "SBT",
    # RECORD
    "RECORD SP": "RECORD",
    "RECORD RJ": "RECORD",
    "RECORD TV": "RECORD",
    "REDE RECORD": "RECORD",
    "TV RECORD": "RECORD",
    "RECORD HD": "RECORD",
    # BAND
    "BAND SP": "BAND",
    "BAND RJ": "BAND",
    "REDE BANDEIRANTES": "BAND",
    "BANDEIRANTES": "BAND",
    "TV BAND": "BAND",
    "BAND HD": "BAND",
    "BANDNEWS": "BAND NEWS",
    "BANDSPORTS": "BAND SPORTS",
    # REDE TV
    "REDETV": "REDE TV",
    "REDETV SP": "REDE TV",
    "REDETV HD": "REDE TV",
    "REDE TV HD": "REDE TV",
    # CULTURA / TV BRASIL
    "TV CULTURA": "CULTURA",
    "CULTURA HD": "CULTURA",
    # SPORTV
    "SPORTV 1": "SPORTV",
    "CANAL SPORTV": "SPORTV",
    "SPORTV HD": "SPORTV",
    "SPORTV 2 HD": "SPORTV 2",
    "SPORTV 3 HD": "SPORTV 3",
    # TELECINE
    "TC PREMIUM": "TELECINE PREMIUM",
    "TC ACTION": "TELECINE ACTION",
    "TC TOUCH": "TELECINE TOUCH",
    "TC FUN": "TELECINE FUN",
    "TC PIPOCA": "TELECINE PIPOCA",
    "TC CULT": "TELECINE CULT",
    # PREMIERE / PFC
    "PFC CLUBES": "PREMIERE CLUBES",
    "PFC 1": "PREMIERE CLUBES",
    "PREMIERE 1": "PREMIERE CLUBES",
    "PFC 2": "PREMIERE 2",
    "PFC 3": "PREMIERE 3",
    "PFC 4": "PREMIERE 4",
    "PFC 5": "PREMIERE 5",
    "PFC 6": "PREMIERE 6",
    "PFC 7": "PREMIERE 7",
    "PFC 8": "PREMIERE 8",
    "PREMIERE 1 HD": "PREMIERE CLUBES",
    # ESPN
    "ESPN BRASIL": "ESPN",
    "ESPN 1": "ESPN",
    "ESPN 1 HD": "ESPN",
    "FOX SPORTS": "ESPN 4",
    "FOX SPORTS 1": "ESPN 4",
    "FOX SPORTS 2": "ESPN 5",
    # HBO
    "HBO 1": "HBO",
    "HBO 2": "HBO2",
    "HBO PLUS": "HBO",
    "HBO HD": "HBO",
    # DISCOVERY
    "DISCOVERY CHANNEL": "DISCOVERY",
    "DISC CHANNEL": "DISCOVERY",
    "DISC KIDS": "DISCOVERY KIDS",
    "DISC TURBO": "DISCOVERY TURBO",
    "DISC THEATER": "DISCOVERY THEATER",
    "DISC SCIENCE": "DISCOVERY SCIENCE",
    "DISC WORLD": "DISCOVERY WORLD",
    "DISC HOME HEALTH": "DISCOVERY HOME HEALTH",
    "DISC H HEALTH": "DISCOVERY HOME HEALTH",
    "DISC H AND HEALTH": "DISCOVERY HOME HEALTH",
    "DISCOVERY H H": "DISCOVERY HOME HEALTH",
    "DISCOVERY HOME E HEALTH": "DISCOVERY HOME HEALTH",
    "DISCOVERY HOME HEALTH": "DISCOVERY HOME HEALTH",
    "DISC ID": "ID",
    "INVESTIGATION DISCOVERY": "ID",
    "INVESTIGACAO DISCOVERY": "ID",
    # INFANTIL
    "CARTOON NETWORK": "CARTOON",
    "NICK": "NICKELODEON",
    "NICK JR HD": "NICK JR",
    # FILMES / SERIES / VARIEDADES
    "WARNER": "WARNER CHANNEL",
    "WARNER BROS": "WARNER CHANNEL",
    "SONY": "SONY CHANNEL",
    "UNIVERSAL": "UNIVERSAL TV",
    "PARAMOUNT": "PARAMOUNT NETWORK",
    "CANAL OFF": "OFF",
    "CANAL GNT": "GNT",
    "CANAL BIS": "BIS",
    "CANAL MULTISHOW": "MULTISHOW",
    "CANAL VIVA": "VIVA",
    "CANAL BRASIL HD": "CANAL BRASIL",
    "MEGAPIX HD": "MEGAPIX",
    "STUDIO UNIVERSAL HD": "STUDIO UNIVERSAL",
    "CINEMAX HD": "CINEMAX",
    "SPACE HD": "SPACE",
    "TNT HD": "TNT",
    "AXN HD": "AXN",
    "HISTORY CHANNEL": "HISTORY",
    "HISTORY 2 HD": "HISTORY 2",
    "H2": "HISTORY 2",
    "AE": "A E",
    "A AND E": "A E",
    "A E": "A E",
    "TCM": "TCM BR",
    "SABOR E ARTE": "SABOR ARTE",
    "TRAVEL BOX BRASIL": "TRAVEL BOX",
    "COMBATE": "COMBATE",
    "CANAL COMBATE": "COMBATE",
}


def get_canonical_channel_name(raw_name: str) -> str:
    """Normaliza o nome e resolve aliases para o nome canônico do canal."""
    normalized = normalize_channel_name(raw_name)
    if not normalized:
        return ""
    if normalized in _CHANNEL_ALIASES:
        return _CHANNEL_ALIASES[normalized]
    no_spaces = normalized.replace(" ", "")
    for alias_key, canonical in _CHANNEL_ALIASES.items():
        if alias_key.replace(" ", "") == no_spaces:
            return canonical
    return normalized
