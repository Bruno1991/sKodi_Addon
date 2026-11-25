from __future__ import annotations

import re

from saile_core.artwork import common_art

_URL_RE = re.compile(r"(?i)\b(?:https?|ftp)://[^\s'\"),;]+")
_FILE_URI_RE = re.compile(r"(?i)\bfile://[^\s'\"),;]+")
_SECRET_KV_RE = re.compile(
    r"(?i)\b(username|user|password|pass|passwd|token|api_key|apikey|secret)\s*([=:])\s*[^\s&'\"),;]+"
)
_LOCAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\|/(?:Users|home|data|storage|sdcard|var|tmp|private)/)[^\s'\"),;]+"
)


def sanitize_error_message(exc: object, fallback: str = "Erro inesperado") -> str:
    """Remove URLs, credenciais e caminhos locais antes de exibir erros na interface."""
    raw = str(exc or "").strip()
    if not raw:
        return fallback
    cleaned = _SECRET_KV_RE.sub(r"\1\2[REDACTED]", raw)
    cleaned = _URL_RE.sub("[URL]", cleaned)
    cleaned = _FILE_URI_RE.sub("[CAMINHO]", cleaned)
    cleaned = _LOCAL_PATH_RE.sub("[CAMINHO]", cleaned)
    cleaned = " ".join(cleaned.split()).strip(" :;-")
    if not cleaned:
        return fallback
    return f"{cleaned[:157]}..." if len(cleaned) > 160 else cleaned


def notify_error(title: str, message: str, duration_ms: int = 5000) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("erro.png"), duration_ms, True)


def notify_success(title: str, message: str, duration_ms: int = 3500) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("check.png"), duration_ms, False)


def notify_info(title: str, message: str, duration_ms: int = 4500) -> None:
    import xbmcgui

    xbmcgui.Dialog().notification(title, message, common_art("sync.png"), duration_ms, False)
