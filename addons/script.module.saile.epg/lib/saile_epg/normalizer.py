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


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(character for character in normalized if not unicodedata.combining(character))


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
