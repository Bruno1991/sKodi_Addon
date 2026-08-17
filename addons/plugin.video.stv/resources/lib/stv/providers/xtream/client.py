"""Cliente para integração com a API Xtream Codes (player_api.php)."""
from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit
from typing import Any

from stv.infrastructure.http import HttpClient


class XtreamClient:
    """Consome endpoints do provedor Xtream e gera URLs diretas de streaming."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        http: HttpClient | None = None,
    ) -> None:
        self.host = self._normalize_host(host)
        self.username = username.strip()
        self.password = password
        self.http = http or HttpClient()

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Normaliza e valida o host informado pelo usuário."""
        value = host.strip().rstrip("/")
        if not value:
            raise ValueError("Servidor Xtream não configurado nas opções do add-on")
        if not value.startswith(("http://", "https://")):
            value = "http://" + value
        parts = urlsplit(value)
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

    def request(self, action: str, **params: object) -> Any:
        """Executa uma chamada autenticada à API player_api.php."""
        query = {
            "username": self.username,
            "password": self.password,
            "action": action,
            **{key: value for key, value in params.items() if value is not None},
        }
        return self.http.get_json(f"{self.host}/player_api.php?{urlencode(query)}")

    def stream_url(self, media_type: str, stream_id: str, extension: str = "") -> str:
        """Gera a URL de streaming final no momento da reprodução."""
        roots = {"live": "live", "vod": "movie", "series": "series"}
        root = roots.get(media_type, "live")
        ext = extension.lstrip(".") or ("ts" if media_type == "live" else "mp4")
        return f"{self.host}/{root}/{self.username}/{self.password}/{stream_id}.{ext}"
