from __future__ import annotations

import re
import unicodedata

_COUNTRY_PREFIXES = re.compile(
    r"^(BR|PT|USA|UK|ES|LATAM|INT|EN|AR|CL|UY|CO|MX)\s*[:|\-/.]\s*"
    r"|^\[(BR|PT|USA|UK|ES|LATAM|INT)\]\s*"
    r"|^\((BR|PT|USA|UK|ES|LATAM|INT)\)\s*",
    re.IGNORECASE,
)
_SUPERSCRIPTS = str.maketrans({
    "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
    "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁰": "0",
})

_QUALITY_TAGS = re.compile(
    r"\b(4K\d*|UHD\d*|FHD\d*|FULLHD\d*|HD\d*|SD\d*|HEVC|H\.?265|H\.?264|60FPS|1080P\d*|720P\d*|480P\d*|RAW)\b",
    re.IGNORECASE,
)
_REDUNDANCY_TAGS = re.compile(
    r"\[(BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL|FAST|STREAM|PLUS)\]"
    r"|\((BACKUP|VIP|ALT|LEG|DUB|OPCAO\s*\d+|OPÇÃO\s*\d+|LOCAL|FAST|STREAM|PLUS)\)"
    r"|\b(BACKUP|ALT|VIP|FAST|STREAM|ONLINE|AO\s*VIVO)\b",
    re.IGNORECASE,
)
_EXTRA_PUNCTUATION = re.compile(r"[\[\](){}_\|#*~^`´'\"«»!?:;]")


def strip_accents(text: str) -> str:
    if not text:
        return ""
    trans = text.translate(_SUPERSCRIPTS)
    normalized = unicodedata.normalize("NFKD", trans)
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
    name = raw_name.translate(_SUPERSCRIPTS)
    name = _COUNTRY_PREFIXES.sub("", name.strip())
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


_GLOBO_AFFILIATE_TOKENS = (
    "GLOBO", "RPC", "EPTV", "TV TEM", "TV TRIBUNA", "TV VANGUARDA", "TV DIARIO",
    "TV FRONTEIRA", "TV BAHIA", "TV SANTA CRUZ", "TV SUBAE", "TV SUDOESTE",
    "TV SAO FRANCISCO", "TV VERDES MARES", "TV MIRANTE", "TV CENTRO AMERICA",
    "TV MORENA", "TV LIBERAL", "TV CLUBE", "TV CABO BRANCO", "TV PARAIBA",
    "TV SERGIPE", "TV GAZETA ALAGOAS", "TV GAZETA SUL", "TV GAZETA DE ALAGOAS",
    "TV INTEGRACAO", "TV ITEGRACAO", "TV ANHANGUERA", "TV ASA BRANCA", "TV GRANDE RIO",
    "TV RIO SUL", "REDE AMAZONICA", "REDE MACAPA", "REDE MINAS", "NSC TV",
    "RBS TV", "INTERTV", "TV TAPAJOS", "TV RONDONIA", "TV RORAIMA", "TV ACRE",
    "TV AMAPA", "TV PAMPA", "TV TAPAJOS",
)

_SBT_AFFILIATE_TOKENS = (
    "SBT", "ALTEROSA", "ARATU", "JANGADEIRO", "TAMBAU", "TV JORNAL",
    "ALLAMANDA", "SCC SBT", "REDE MASSA", "VTV",
)

_RECORD_AFFILIATE_TOKENS = (
    "RECORD", "PAJUCARA", "CIDADE VERDE", "CORREIO", "TV ATALAIA", "RIC TV",
    "TV VITORIA", "TV TROPICAL", "TV SUDESTE", "TV VILA REAL",
)

_BAND_AFFILIATE_TOKENS = (
    "BAND", "MANAIRA", "TAROBA", "TV CAPIXABA", "TV GOIANIA",
)

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
    "GLOBO SP": "GLOBO SP",
    # SBT
    "SBT SP": "SBT",
    "SBT RJ": "SBT",
    "SBT BRASIL": "SBT",
    "REDE SBT": "SBT",
    "TV SBT": "SBT",
    "SBT": "SBT",
    # RECORD
    "RECORD SP": "RECORD",
    "RECORD RJ": "RECORD",
    "RECORD TV": "RECORD",
    "REDE RECORD": "RECORD",
    "TV RECORD": "RECORD",
    "RECORD HD": "RECORD",
    "RECORD": "RECORD",
    # BAND
    "BAND SP": "BAND",
    "BAND RJ": "BAND",
    "REDE BANDEIRANTES": "BAND",
    "BANDEIRANTES": "BAND",
    "TV BAND": "BAND",
    "BAND HD": "BAND",
    "BAND": "BAND",
    "BANDNEWS": "BAND NEWS",
    "BANDSPORTS": "BAND SPORTS",
    # REDE TV
    "REDETV": "REDE TV",
    "REDETV SP": "REDE TV",
    "REDETV HD": "REDE TV",
    "REDE TV HD": "REDE TV",
    "REDE TV": "REDE TV",
    # CULTURA / TV BRASIL / GAZETA
    "TV CULTURA": "CULTURA",
    "CULTURA HD": "CULTURA",
    "CULTURA": "CULTURA",
    "TV BRASIL": "TV BRASIL",
    "GAZETA SP": "GAZETA",
    "TV GAZETA": "GAZETA",
    "GAZETA": "GAZETA",
    # SPORTV
    "SPORTV 1": "SPORTV",
    "CANAL SPORTV": "SPORTV",
    "SPORTV HD": "SPORTV",
    "SPORTV 2 HD": "SPORTV 2",
    "SPORTV 3 HD": "SPORTV 3",
    "SPORTV 4": "SPORTV",
    "SPOR TV": "SPORTV",
    "SPORTV": "SPORTV",
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
    "ESPN EXTRA": "ESPN 6",
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
    "ZOOMOO KIDS": "ZOOMOO",
    # FILMES / SERIES / VARIEDADES
    "WARNER": "WARNER CHANNEL",
    "WARNER BROS": "WARNER CHANNEL",
    "SONY": "SONY CHANNEL",
    "UNIVERSAL": "UNIVERSAL TV",
    "UNIVERSAL PREMIER": "UNIVERSAL PREMIERE HD",
    "UNIVERSAL PREMIERE": "UNIVERSAL PREMIERE HD",
    "UNIVERSAL PREMIUM": "UNIVERSAL PREMIERE HD",
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
    "TCM PLAY": "TCM BR",
    "TCM PLAY TV": "TCM BR",
    "SABOR E ARTE": "SABOR ARTE",
    "TRAVEL BOX BRASIL": "TRAVEL BOX",
    "COMBATE": "COMBATE",
    "CANAL COMBATE": "COMBATE",
    "UFC FIGHT PASS": "COMBATE",
    # INSTITUCIONAIS / GOV / NOTICIAS
    "CANAL EDUCACAO": "CANAL EDUCACAO",
    "CANAL EDUCACO": "CANAL EDUCACAO",
    "TV ESCOLA": "CANAL EDUCACAO",
    "CANAL GOV": "CANAL GOV HD",
    "TV CAMARA": "TV CAMARA",
    "TV SENADO": "TV SENADO",
    "TV JUSTICA": "TV JUSTICA",
    "TV NOVO TEMPO": "TV NOVO TEMPO",
    "TV PAI ETERNO": "TV PAI ETERNO HD",
    "FONTE TV": "FONTE TV",
    "SBT NEWS": "SBT NEWS HD",
    "POLISHOP": "POLISHOP",
    "CNN MONEY": "CNN BRASIL MONEY HD",
    "CNN BRASIL MONEY": "CNN BRASIL MONEY HD",
    "TIMES CNBC": "TIMES EXCLUSIVO CNBC",
    "CNBC": "TIMES EXCLUSIVO CNBC",
    "BM C": "BM C HD",
    "BMC NEWS": "BM C HD",
    "ADULT SWIM": "ADULT SWIM HD",
    "NSPORTS": "NSPORTS HD",
    "GE TV": "GE TV HD",
    "GE FAST": "GE TV HD",
    "MARKKET": "MARKKET HD",
    "FUEL TV": "FUEL TV HD",
    "XSPORTS": "XSPORTS HD",
    "DOG TV": "DOG TV HD",
    "TERRA VIVA": "TERRA VIVA",
    "AGRO CANAL": "CANAL DO BOI",
    "ESTADIO TNT SPORTS": "TNT",
    "TNT SPORTS": "TNT",
    "DAZN": "NSPORTS HD",
    "DAZN 01": "NSPORTS HD",
    "DAZN 02": "NSPORTS HD",
    "DAZN 03": "NSPORTS HD",
    "DAZN 04": "NSPORTS HD",
    "TRU TV": "WARNER CHANNEL",
    "TRUT TV": "WARNER CHANNEL",
    "SYFY": "USA",
    "TBS": "TNT NOVELAS",
    "RECEITAS FAST": "SABOR ARTE",
    "CNN INTERNACIONAL": "CNN INTERNATIONAL",
    "BM C NEWS": "BM C",
    "BOX KIDS": "CARTOONITO",
    "PLAY KIDS": "CARTOONITO",
    "FILM ART": "ARTE 1",
    "POLISHOP TV": "POLISHOP",
    "REDE BRASIL": "RECORD",
    "ZOOMOO": "ZOOMOO",
    "TVE": "TV BRASIL",
    "TVE BAHIA": "TV BRASIL",
    "TV ARAPUAN": "REDE TV",
    "TV PONTA VERDE": "SBT",
    "TV A CRITICA": "REDE TV",
    "TV CULTURA DO PARA": "CULTURA",
    "TV MIRAMAR": "CULTURA",
    "TV MIRAMAR TV CULTURA": "CULTURA",
    "TV IDEAL": "CULTURA",
    "CANAL GOAT": "SPORTV",
    "CANAL GOAT 02": "SPORTV 2",
    "CANAL GOAT 03": "SPORTV 3",
    "PULISTAO": "RECORD",
    "RAI INTERNACIONAL": "RAI INTERNATIONAL",
    "RAI": "RAI INTERNATIONAL",
    "GE FAST": "GE TV",
    "GE": "GE TV",
    "RECEITAS": "SABOR ARTE",
    "TERRA VIVA": "TERRA VIVA",
    "UNIVERSAL PREMIUM": "UNIVERSAL PREMIERE",
    "UNIVERSAL PREMIERE HD": "UNIVERSAL PREMIERE",
    "TV OESTE": "GLOBO SP",
    "TV TVCHD 13 1": "GLOBO SP",
    "TESTE 2222222222": "GLOBO SP",
    "TESTEEEEEEEEEEE": "GLOBO SP",
    "DAZN 01": "SPORTV",
    "DAZN 02": "SPORTV 2",
    "DAZN 03": "SPORTV 3",
    "DAZN 04": "SPORTV",
    "ESTADIO TNT SPORTS 1": "TNT",
    "ESTADIO TNT SPORTS 4": "TNT",
    "ZOOMOO": "ZOOMOO KIDS",
}


def get_canonical_channel_name(raw_name: str) -> str:
    """Normaliza o nome e resolve aliases e tokens de afiliadas para o nome canônico do canal."""
    normalized = normalize_channel_name(raw_name)
    if not normalized:
        return ""

    # 1. Alias direto
    if normalized in _CHANNEL_ALIASES:
        return _CHANNEL_ALIASES[normalized]

    # 2. Alias sem espaços
    no_spaces = normalized.replace(" ", "")
    for alias_key, canonical in _CHANNEL_ALIASES.items():
        if alias_key.replace(" ", "") == no_spaces:
            return canonical

    # 3. Reconhecimento de Afiliadas Regionais
    # Globo
    if (
        normalized.startswith("RBS ")
        or normalized.startswith("NSC ")
        or normalized.startswith("INTER TV ")
        or normalized.startswith("INTERTV ")
        or normalized.startswith("INTEGRACAO ")
        or normalized.startswith("ITEGRACAO ")
        or normalized.startswith("AMAZONICA ")
        or "GAZETA SUL" in normalized
    ):
        return "GLOBO SP"

    for tok in _GLOBO_AFFILIATE_TOKENS:
        if tok in normalized:
            return "GLOBO SP"

    # SBT
    for tok in _SBT_AFFILIATE_TOKENS:
        if tok in normalized:
            return "SBT"

    # Record
    if "RECORD NEWS" in normalized or "RD NEWS" in normalized:
        return "RECORD NEWS"
    if normalized.startswith("RD ") or normalized == "RD TV":
        return "RECORD"
    for tok in _RECORD_AFFILIATE_TOKENS:
        if tok in normalized:
            return "RECORD"

    # Band
    if "BAND NEWS" in normalized or "BANDNEWS" in normalized or "BD NEWS" in normalized:
        return "BAND NEWS"
    if "BAND SPORTS" in normalized or "BANDSPORTS" in normalized or "BD SPORTS" in normalized:
        return "BAND SPORTS"
    if normalized.startswith("BD ") or normalized == "BD TV":
        return "BAND"
    for tok in _BAND_AFFILIATE_TOKENS:
        if tok in normalized:
            return "BAND"

    # SporTV
    if "SPORTV 2" in normalized or "SPORTV2" in normalized:
        return "SPORTV 2"
    if "SPORTV 3" in normalized or "SPORTV3" in normalized:
        return "SPORTV 3"
    if "SPORTV" in normalized or "SPOR TV" in normalized:
        return "SPORTV"

    # Telecine
    if "TELECINE" in normalized or normalized.startswith("TC "):
        for var in ("ACTION", "PIPOCA", "FUN", "TOUCH", "CULT", "PREMIUM"):
            if var in normalized:
                return f"TELECINE {var}"
        return "TELECINE PREMIUM"

    # Premiere / PFC
    if "PREMIERE" in normalized or "PFC" in normalized:
        for num in ("2", "3", "4", "5", "6", "7", "8"):
            if f" {num}" in normalized or f"_{num}" in normalized or normalized.endswith(num):
                return f"PREMIERE {num}"
        return "PREMIERE CLUBES"

    # ESPN
    if "ESPN" in normalized:
        for num in ("2", "3", "4", "5", "6"):
            if f" {num}" in normalized or f"_{num}" in normalized or normalized.endswith(num):
                return f"ESPN {num}"
        return "ESPN"

    # HBO
    if "HBO" in normalized:
        for var in ("2", "FAMILY", "POP", "MUNDI", "SIGNATURE", "XTREME", "PLUS"):
            if var in normalized:
                return f"HBO {var}" if var != "2" else "HBO2"
        return "HBO"

    # Discovery
    if "DISCOVERY" in normalized or normalized.startswith("DISC "):
        for var in ("KIDS", "TURBO", "THEATER", "SCIENCE", "WORLD", "HOME HEALTH", "ID"):
            if var in normalized:
                return f"DISCOVERY {var}"
        return "DISCOVERY"

    return normalized
