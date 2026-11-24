from __future__ import annotations

import re
import time
import unicodedata

_COUNTRY_PREFIXES = re.compile(
    r"^(BR|PT|USA|UK|ES|LATAM|INT|EN|AR|CL|UY|CO|MX)\s*[:|\-/.]\s*"
    r"|^\[(BR|PT|USA|UK|ES|LATAM|INT)\]\s*"
    r"|^\((BR|PT|USA|UK|ES|LATAM|INT)\)\s*",
    re.IGNORECASE,
)
_SUPERSCRIPTS = str.maketrans(
    {
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁰": "0",
    }
)

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

_ACRONYMS = frozenset(
    {
        "SP",
        "RJ",
        "MG",
        "RS",
        "PR",
        "SC",
        "BA",
        "PE",
        "CE",
        "DF",
        "GO",
        "ES",
        "MT",
        "MS",
        "PA",
        "AM",
        "HBO",
        "ESPN",
        "CNN",
        "TNT",
        "AXN",
        "GNT",
        "BIS",
        "OFF",
        "TLC",
        "MTV",
        "SBT",
        "BBC",
        "FX",
        "ID",
        "E!",
        "USA",
        "VIVA",
        "MAX",
        "DMAX",
        "AMC",
        "SYFY",
    }
)
_BRANDED_NAMES = {
    "SPORTV": "SporTV",
    "BANDNEWS": "BandNews",
    "GLOOB": "Gloob",
    "GLOOBINHO": "Gloobinho",
    "MEGAPIX": "Megapix",
    "CARTOONITO": "Cartoonito",
    "CINEMAX": "Cinemax",
    "TELECINE": "Telecine",
}


def strip_accents(text: str) -> str:
    if not text:
        return ""
    trans = text.translate(_SUPERSCRIPTS)
    normalized = unicodedata.normalize("NFKD", trans)
    return "".join(char for char in normalized if not unicodedata.combining(char))


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

    return " ".join(
        _BRANDED_NAMES.get(
            word.upper(),
            word.upper() if word.upper() in _ACRONYMS else word.capitalize(),
        )
        for word in name.split()
    )


def normalize_channel_name(raw_name: str) -> str:
    if not raw_name:
        return ""
    cleaned = strip_accents(raw_name).upper()
    cleaned = _COUNTRY_PREFIXES.sub("", cleaned)
    cleaned = _REDUNDANCY_TAGS.sub("", cleaned)
    cleaned = _QUALITY_TAGS.sub("", cleaned)
    cleaned = _EXTRA_PUNCTUATION.sub(" ", cleaned)
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


_MEDIA_AUDIO_TAGS = re.compile(
    r"\[(DUBLADO|LEGENDADO|DUAL|MULTI|NACIONAL|LEG|DUB|AUDIO\s*\d+|DUAL\s*AUDIO)\]"
    r"|\((DUBLADO|LEGENDADO|DUAL|MULTI|NACIONAL|LEG|DUB|AUDIO\s*\d+|DUAL\s*AUDIO)\)"
    r"|\b(DUBLADO|LEGENDADO|DUAL|MULTI|NACIONAL|LEG|DUB)\b",
    re.IGNORECASE,
)
_MEDIA_SEASON_TAGS = re.compile(
    r"\[(S\d{1,2}(?:\s*-\s*S\d{1,2})?|TEMPORADA\s*\d{1,2}|TEMP\s*\d{1,2}|T\d{1,2}|COMPLETA|COMPLETO)\]"
    r"|\((S\d{1,2}(?:\s*-\s*S\d{1,2})?|TEMPORADA\s*\d{1,2}|TEMP\s*\d{1,2}|T\d{1,2}|COMPLETA|COMPLETO)\)"
    r"|\b(S\d{1,2}(?:\s*-\s*S\d{1,2})?|TEMPORADA\s*\d{1,2}|TEMP\s*\d{1,2}|T\d{1,2}|COMPLETA|COMPLETO)\b",
    re.IGNORECASE,
)
# Ano entre parênteses/colchetes tem prioridade; o último vence ("Blade Runner 2049 (2017)").
_MEDIA_YEAR_BRACKETED = re.compile(r"[\(\[]\s*((?:19|20)\d{2})\s*[\)\]]")
# Ano solto só no fim e depois de outra palavra ("Halloween 2018"); "1917" sozinho é título.
_MEDIA_YEAR_TRAILING = re.compile(r"(?<=\S)[\s\-_.]+((?:19|20)\d{2})\s*$")


def _split_media_year(name: str) -> tuple[str, str]:
    bracketed = list(_MEDIA_YEAR_BRACKETED.finditer(name))
    if bracketed:
        match = bracketed[-1]
        return name[: match.start()] + " " + name[match.end() :], match.group(1)
    match = _MEDIA_YEAR_TRAILING.search(name)
    # Ano futuro faz parte do título ("Blade Runner 2049"), não é ano de lançamento.
    if match and int(match.group(1)) <= time.gmtime().tm_year + 1:
        return name[: match.start()], match.group(1)
    return name, ""


def clean_media_title(raw_name: str) -> tuple[str, str]:
    """Limpa títulos de filmes e séries removendo tags IPTV e extraindo (título_limpo, ano)."""
    if not raw_name:
        return ("", "")
    name = raw_name.translate(_SUPERSCRIPTS)
    name = _COUNTRY_PREFIXES.sub("", name.strip())
    name = _QUALITY_TAGS.sub("", name)
    name = _MEDIA_AUDIO_TAGS.sub("", name)
    name = _MEDIA_SEASON_TAGS.sub("", name)

    name, year = _split_media_year(name)

    name = re.sub(r"[{}\[\]\(\)\-_|#*~^`´\"«»!?:;]", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -:.")
    return (name or raw_name.strip(), year)


_GLOBO_AFFILIATE_TOKENS = (
    "RPC",
    "EPTV",
    "TV TEM",
    "TV TRIBUNA",
    "TV VANGUARDA",
    "TV DIARIO",
    "TV FRONTEIRA",
    "TV BAHIA",
    "TV SANTA CRUZ",
    "TV SUBAE",
    "TV SUDOESTE",
    "TV SAO FRANCISCO",
    "TV VERDES MARES",
    "TV MIRANTE",
    "TV CENTRO AMERICA",
    "TV MORENA",
    "TV LIBERAL",
    "TV CLUBE",
    "TV CABO BRANCO",
    "TV PARAIBA",
    "TV SERGIPE",
    "TV GAZETA ALAGOAS",
    "TV GAZETA SUL",
    "TV GAZETA DE ALAGOAS",
    "TV INTEGRACAO",
    "TV ITEGRACAO",
    "TV ANHANGUERA",
    "TV ASA BRANCA",
    "TV GRANDE RIO",
    "TV RIO SUL",
    "REDE AMAZONICA",
    "REDE MACAPA",
    "REDE MINAS",
    "NSC TV",
    "RBS TV",
    "INTERTV",
    "TV TAPAJOS",
    "TV RONDONIA",
    "TV RORAIMA",
    "TV ACRE",
    "TV AMAPA",
    "TV PAMPA",
)

_SBT_AFFILIATE_TOKENS = (
    "SBT",
    "ALTEROSA",
    "ARATU",
    "JANGADEIRO",
    "TAMBAU",
    "TV JORNAL",
    "ALLAMANDA",
    "SCC SBT",
    "REDE MASSA",
    "VTV",
)

_RECORD_AFFILIATE_TOKENS = (
    "RECORD",
    "PAJUCARA",
    "CIDADE VERDE",
    "CORREIO",
    "TV ATALAIA",
    "RIC TV",
    "TV VITORIA",
    "TV TROPICAL",
    "TV SUDESTE",
    "TV VILA REAL",
)

_BAND_AFFILIATE_TOKENS = (
    "BAND",
    "MANAIRA",
    "TAROBA",
    "TV CAPIXABA",
    "TV GOIANIA",
)

# Todos os alvos devem corresponder a `normalize_channel_name(...)` (sem sufixo "HD").
_CHANNEL_ALIASES: dict[str, str] = {
    # GLOBO NEWS
    "GLOBONEWS": "GLOBONEWS",
    "GLOBO NEWS": "GLOBONEWS",
    "GNEWS": "GLOBONEWS",
    "GN NEWS": "GLOBONEWS",
    # GLOBOPLAY NOVELAS
    "GLOBOPLAY NOVELAS": "GLOBOPLAY NOVELAS",
    "GLOBO PLAY NOVELAS": "GLOBOPLAY NOVELAS",
    "GLOBOPLAY": "GLOBOPLAY NOVELAS",
    "GLOBO NOVELAS": "GLOBOPLAY NOVELAS",
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
    "TV OESTE": "GLOBO SP",
    "TV TVCHD 13 1": "GLOBO SP",
    # SBT
    "SBT SP": "SBT",
    "SBT RJ": "SBT",
    "SBT BRASIL": "SBT",
    "REDE SBT": "SBT",
    "TV SBT": "SBT",
    "SBT": "SBT",
    "SBT NEWS": "SBT NEWS",
    "TV PONTA VERDE": "SBT",
    # RECORD
    "RECORD SP": "RECORD",
    "RECORD RJ": "RECORD",
    "RECORD TV": "RECORD",
    "REDE RECORD": "RECORD",
    "TV RECORD": "RECORD",
    "RECORD": "RECORD",
    "REDE BRASIL": "RECORD",
    "PULISTAO": "RECORD",
    # BAND
    "BAND SP": "BAND",
    "BAND RJ": "BAND",
    "REDE BANDEIRANTES": "BAND",
    "BANDEIRANTES": "BAND",
    "TV BAND": "BAND",
    "BAND": "BAND",
    "BANDNEWS": "BAND NEWS",
    "BANDSPORTS": "BAND SPORTS",
    # REDE TV
    "REDETV": "REDE TV",
    "REDETV SP": "REDE TV",
    "REDE TV": "REDE TV",
    "TV ARAPUAN": "REDE TV",
    "TV A CRITICA": "REDE TV",
    # CULTURA / TV BRASIL / GAZETA
    "TV CULTURA": "CULTURA",
    "CULTURA": "CULTURA",
    "TV CULTURA DO PARA": "CULTURA",
    "TV MIRAMAR": "CULTURA",
    "TV MIRAMAR TV CULTURA": "CULTURA",
    "TV IDEAL": "CULTURA",
    "TVE": "TV BRASIL",
    "TVE BAHIA": "TV BRASIL",
    "GAZETA SP": "GAZETA",
    "TV GAZETA": "GAZETA",
    "GAZETA": "GAZETA",
    # SPORTV
    "SPORTV 1": "SPORTV",
    "CANAL SPORTV": "SPORTV",
    "SPORTV 4": "SPORTV",
    "SPOR TV": "SPORTV",
    "SPORTV": "SPORTV",
    "CANAL GOAT": "SPORTV",
    "CANAL GOAT 02": "SPORTV 2",
    "CANAL GOAT 03": "SPORTV 3",
    "DAZN 01": "SPORTV",
    "DAZN 02": "SPORTV 2",
    "DAZN 03": "SPORTV 3",
    "DAZN 04": "SPORTV",
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
    # ESPN
    "ESPN BRASIL": "ESPN",
    "ESPN 1": "ESPN",
    "ESPN EXTRA": "ESPN 6",
    "FOX SPORTS": "ESPN 4",
    "FOX SPORTS 1": "ESPN 4",
    "FOX SPORTS 2": "ESPN 5",
    # HBO
    "HBO 1": "HBO",
    "HBO 2": "HBO2",
    "HBO PLUS": "HBO",
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
    "ZOOMOO": "ZOOMOO KIDS",
    "ZOOMOO KIDS": "ZOOMOO KIDS",
    "BOX KIDS": "CARTOONITO",
    "PLAY KIDS": "CARTOONITO",
    # FILMES / SERIES / VARIEDADES
    "WARNER": "WARNER CHANNEL",
    "WARNER BROS": "WARNER CHANNEL",
    "TRU TV": "WARNER CHANNEL",
    "TRUT TV": "WARNER CHANNEL",
    "SONY": "SONY CHANNEL",
    "UNIVERSAL": "UNIVERSAL TV",
    "UNIVERSAL PREMIER": "UNIVERSAL PREMIERE",
    "UNIVERSAL PREMIERE": "UNIVERSAL PREMIERE",
    "UNIVERSAL PREMIUM": "UNIVERSAL PREMIERE",
    "PARAMOUNT": "PARAMOUNT NETWORK",
    "CANAL OFF": "OFF",
    "CANAL GNT": "GNT",
    "CANAL BIS": "BIS",
    "CANAL MULTISHOW": "MULTISHOW",
    "CANAL VIVA": "VIVA",
    "HISTORY CHANNEL": "HISTORY",
    "H2": "HISTORY 2",
    "AE": "A E",
    "A AND E": "A E",
    "A E": "A E",
    "TCM": "TCM BR",
    "TCM PLAY": "TCM BR",
    "TCM PLAY TV": "TCM BR",
    "SABOR E ARTE": "SABOR ARTE",
    "RECEITAS FAST": "SABOR ARTE",
    "RECEITAS": "SABOR ARTE",
    "TRAVEL BOX BRASIL": "TRAVEL BOX",
    "COMBATE": "COMBATE",
    "CANAL COMBATE": "COMBATE",
    "UFC FIGHT PASS": "COMBATE",
    "ESTADIO TNT SPORTS": "TNT",
    "ESTADIO TNT SPORTS 1": "TNT",
    "ESTADIO TNT SPORTS 4": "TNT",
    "TNT SPORTS": "TNT",
    "SYFY": "USA",
    "TBS": "TNT NOVELAS",
    "FILM ART": "ARTE 1",
    # INSTITUCIONAIS / GOV / NOTICIAS / ESPORTES
    "CANAL EDUCACO": "CANAL EDUCACAO",
    "TV ESCOLA": "CANAL EDUCACAO",
    "CANAL GOV": "CANAL GOV",
    "TV PAI ETERNO": "TV PAI ETERNO",
    "POLISHOP TV": "POLISHOP",
    "CNN MONEY": "CNN BRASIL MONEY",
    "CNN BRASIL MONEY": "CNN BRASIL MONEY",
    "CNN INTERNACIONAL": "CNN INTERNATIONAL",
    "TIMES CNBC": "TIMES EXCLUSIVO CNBC",
    "CNBC": "TIMES EXCLUSIVO CNBC",
    "BM C": "BM C",
    "BMC NEWS": "BM C",
    "BM C NEWS": "BM C",
    "ADULT SWIM": "ADULT SWIM",
    "NSPORTS": "NSPORTS",
    "DAZN": "NSPORTS",
    "GE TV": "GE TV",
    "GE FAST": "GE TV",
    "GE": "GE TV",
    "MARKKET": "MARKKET",
    "FUEL TV": "FUEL TV",
    "XSPORTS": "XSPORTS",
    "DOG TV": "DOG TV",
    "AGRO CANAL": "CANAL DO BOI",
    "RAI INTERNACIONAL": "RAI INTERNATIONAL",
    "RAI": "RAI INTERNATIONAL",
}

_CHANNEL_ALIASES_COMPACT: dict[str, str] = {
    alias_key.replace(" ", ""): canonical for alias_key, canonical in _CHANNEL_ALIASES.items()
}


def get_canonical_channel_name(raw_name: str) -> str:
    """Normaliza o nome e resolve aliases e afiliadas para o nome canônico do canal."""
    normalized = normalize_channel_name(raw_name)
    if not normalized:
        return ""

    # 1. Alias direto (O(1))
    direct = _CHANNEL_ALIASES.get(normalized)
    if direct:
        return direct

    # 2. Alias sem espaços pré-computado (O(1))
    compact = _CHANNEL_ALIASES_COMPACT.get(normalized.replace(" ", ""))
    if compact:
        return compact

    # 3. Reconhecimento de Afiliadas Regionais e Canais Específicos
    if (
        "GLOBONEWS" in normalized
        or "GLOBO NEWS" in normalized
        or "GNEWS" in normalized
        or "GN NEWS" in normalized
    ):
        return "GLOBONEWS"

    if (
        "GLOBOPLAY NOVELAS" in normalized
        or "GLOBO PLAY NOVELAS" in normalized
        or "GLOBO NOVELAS" in normalized
        or normalized == "GLOBOPLAY"
        or normalized.startswith("GLOBOPLAY ")
    ):
        return "GLOBOPLAY NOVELAS"

    if (
        normalized.startswith(
            ("RBS ", "NSC ", "INTER TV ", "INTERTV ", "INTEGRACAO ", "ITEGRACAO ", "AMAZONICA ")
        )
        or "GAZETA SUL" in normalized
        or normalized == "GLOBO"
        or normalized.startswith("GLOBO ")
        or normalized.endswith(" GLOBO")
        or " GLOBO " in normalized
        or "REDE GLOBO" in normalized
        or "TV GLOBO" in normalized
        or any(tok in normalized for tok in _GLOBO_AFFILIATE_TOKENS)
    ):
        return "GLOBO SP"

    if any(tok in normalized for tok in _SBT_AFFILIATE_TOKENS):
        return "SBT"

    if "RECORD NEWS" in normalized or "RD NEWS" in normalized:
        return "RECORD NEWS"
    if (
        normalized.startswith("RD ")
        or normalized == "RD TV"
        or any(tok in normalized for tok in _RECORD_AFFILIATE_TOKENS)
    ):
        return "RECORD"

    if "BAND NEWS" in normalized or "BANDNEWS" in normalized or "BD NEWS" in normalized:
        return "BAND NEWS"
    if "BAND SPORTS" in normalized or "BANDSPORTS" in normalized or "BD SPORTS" in normalized:
        return "BAND SPORTS"
    if (
        normalized.startswith("BD ")
        or normalized == "BD TV"
        or any(tok in normalized for tok in _BAND_AFFILIATE_TOKENS)
    ):
        return "BAND"

    if "SPORTV 2" in normalized or "SPORTV2" in normalized:
        return "SPORTV 2"
    if "SPORTV 3" in normalized or "SPORTV3" in normalized:
        return "SPORTV 3"
    if "SPORTV" in normalized or "SPOR TV" in normalized:
        return "SPORTV"

    if "TELECINE" in normalized or normalized.startswith("TC "):
        for var in ("ACTION", "PIPOCA", "FUN", "TOUCH", "CULT", "PREMIUM"):
            if var in normalized:
                return f"TELECINE {var}"
        return "TELECINE PREMIUM"

    if "PREMIERE" in normalized or "PFC" in normalized:
        for num in ("2", "3", "4", "5", "6", "7", "8"):
            if f" {num}" in normalized or f"_{num}" in normalized or normalized.endswith(num):
                return f"PREMIERE {num}"
        return "PREMIERE CLUBES"

    if "ESPN" in normalized:
        for num in ("2", "3", "4", "5", "6"):
            if f" {num}" in normalized or f"_{num}" in normalized or normalized.endswith(num):
                return f"ESPN {num}"
        return "ESPN"

    if "HBO" in normalized:
        for var in ("2", "FAMILY", "POP", "MUNDI", "SIGNATURE", "XTREME", "PLUS"):
            if var in normalized:
                return f"HBO {var}" if var != "2" else "HBO2"
        return "HBO"

    if "DISCOVERY" in normalized or normalized.startswith("DISC "):
        for var in ("KIDS", "TURBO", "THEATER", "SCIENCE", "WORLD", "HOME HEALTH", "ID"):
            if var in normalized:
                return f"DISCOVERY {var}"
        return "DISCOVERY"

    return normalized
