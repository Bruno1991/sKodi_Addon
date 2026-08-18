"""Normalizador inteligente de nomes de canais para casamento com EPG e exibição limpa."""
from __future__ import annotations

import re
import unicodedata

# Padrões de ruídos a remover
_COUNTRY_PREFIXES = re.compile(
    r"^(BR|PT|USA|UK|ES|LATAM|INT|EN|AR|CL|UY|CO|MX)\s*[:\|\-/\.]\s*|^\[(BR|PT|USA|UK|ES|LATAM|INT)\]\s*|^\((BR|PT|USA|UK|ES|LATAM|INT)\)\s*",
    re.IGNORECASE,
)

_QUALITY_TAGS = re.compile(
    r"\b(4K|UHD|FHD|HD|SD|HEVC|H\.?265|H\.?264|60FPS|1080P|720P|480P|RAW)\b",
    re.IGNORECASE,
)


_REDUNDANCY_TAGS = re.compile(
    r"\[(BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL)\]|\((BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL)\)|\b(BACKUP|ALT|VIP)\b",
    re.IGNORECASE,
)

_EXTRA_PUNCTUATION = re.compile(r"[\[\]\(\)\{\}_\|#\*\~]")


def _strip_accents(text: str) -> str:
    """Remove acentos e diacríticos mantendo caracteres ASCII base."""
    nfkd_form = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd_form if not unicodedata.combining(c))


def clean_channel_title(raw_name: str) -> str:
    """Gera um título visualmente limpo e elegante para o card do canal no Kodi.

    Exemplo:
        'BR | GLOBO SP FHD [4K]' -> 'Globo SP'
        'BR: SPORTV 1 HD (BACKUP)' -> 'SporTV 1'
        'TELECINE PREMIUM 4K HEVC' -> 'Telecine Premium'
    """
    if not raw_name:
        return ""

    name = raw_name.strip()

    # 1. Remove prefixo de país
    name = _COUNTRY_PREFIXES.sub("", name)

    # 2. Remove tags de redundância
    name = _REDUNDANCY_TAGS.sub("", name)

    # 3. Remove tags de qualidade
    name = _QUALITY_TAGS.sub("", name)

    # 4. Remove pontuações residuais
    name = _EXTRA_PUNCTUATION.sub(" ", name)

    # 5. Normaliza espaços múltiplos
    name = re.sub(r"\s+", " ", name).strip(" -:.")

    if not name:
        return raw_name.strip()

    # Formata capitalização elegante preservando siglas conhecidas
    words = name.split()
    formatted_words: list[str] = []
    acronyms = {
        "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "PE", "CE", "DF", "GO", "ES", "MT", "MS", "PA", "AM",
        "HBO", "ESPN", "CNN", "TNT", "AXN", "GNT", "BIS", "OFF", "TLC", "MTV", "SBT", "BBC", "FX",
        "ID", "E!", "USA", "VIVA", "MAX", "DMAX", "AMC", "SYFY"
    }

    for word in words:
        upper_word = word.upper()
        if upper_word in acronyms:
            formatted_words.append(upper_word)
        elif upper_word == "SPORTV":
            formatted_words.append("SporTV")
        elif upper_word == "BANDNEWS":
            formatted_words.append("BandNews")
        elif upper_word == "GLOOB":
            formatted_words.append("Gloob")
        elif upper_word == "GLOOBINHO":
            formatted_words.append("Gloobinho")
        elif upper_word == "MEGAPIX":
            formatted_words.append("Megapix")
        elif upper_word == "CARTOONITO":
            formatted_words.append("Cartoonito")
        elif upper_word == "CINEMAX":
            formatted_words.append("Cinemax")
        elif upper_word == "TELECINE":
            formatted_words.append("Telecine")
        elif len(word) <= 2 and word.isupper():
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word.capitalize())

    return " ".join(formatted_words)


def normalize_channel_name(raw_name: str) -> str:
    """Normaliza o nome do canal em uma chave canônica alfanumérica para cruzamento com o EPG.

    Exemplo:
        'BR | GLOBO SP FHD' -> 'GLOBO' (ou 'GLOBO SP' dependendo do canal)
        'BR: SPORTV 1 HD' -> 'SPORTV'
        'TELECINE PIPOCA FHD' -> 'TELECINE PIPOCA'
        'DISCOVERY KIDS 720P' -> 'DISCOVERY KIDS'
    """
    if not raw_name:
        return ""

    cleaned = _strip_accents(raw_name).upper()
    cleaned = _COUNTRY_PREFIXES.sub("", cleaned)
    cleaned = _REDUNDANCY_TAGS.sub("", cleaned)
    cleaned = _QUALITY_TAGS.sub("", cleaned)
    cleaned = _EXTRA_PUNCTUATION.sub(" ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return ""

    # Normalização de redes abertas e variações regionais para a matriz nacional
    if cleaned.startswith("GLOBO"):
        # Se for Globo regional (SP, RJ, MINAS, etc.), mapeia para GLOBO para garantir casamento com a grade principal
        tokens = cleaned.split()
        if len(tokens) >= 2 and tokens[0] == "GLOBO":
            return "GLOBO"
    elif cleaned.startswith("RECORD"):
        tokens = cleaned.split()
        if len(tokens) >= 2 and tokens[0] == "RECORD" and tokens[1] not in {"NEWS"}:
            return "RECORD"
    elif cleaned.startswith("SBT"):
        return "SBT"
    elif cleaned.startswith("BAND") and not cleaned.startswith("BANDNEWS") and not cleaned.startswith("BANDSPORTS"):
        return "BAND"
    elif cleaned == "SPORTV 1" or cleaned == "SPORTV1":
        return "SPORTV"
    elif cleaned == "ESPN BRASIL":
        return "ESPN"

    return cleaned
