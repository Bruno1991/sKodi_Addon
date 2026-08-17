"""Padrão de resolução; não persiste a URL temporária."""
from __future__ import annotations

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def resolve_audio(webpage_url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(webpage_url, download=False)
    except DownloadError as exc:
        raise RuntimeError("Não foi possível resolver a faixa") from exc
    if not info or not info.get("url"):
        raise RuntimeError("A fonte não retornou um formato reproduzível")
    return {
        "url": info["url"],
        "title": info.get("title") or "",
        "artist": info.get("artist") or info.get("uploader") or "",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
    }
