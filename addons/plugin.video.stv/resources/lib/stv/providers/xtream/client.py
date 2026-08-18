"""Cliente para integração robusta com a API Xtream Codes (player_api.php)."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

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
        self.raw_host = host
        self.host = self._normalize_host(host) if host.strip() else ""
        self.username = username.strip()
        self.password = password.strip()
        self.http = http or HttpClient()

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Normaliza e valida o host informado pelo usuário."""
        value = host.strip().rstrip("/")
        if not value:
            return ""
        if not value.startswith(("http://", "https://")):
            value = "http://" + value
        parts = urlsplit(value)
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

    @property
    def is_configured(self) -> bool:
        """Verifica se as credenciais mínimas foram preenchidas."""
        return bool(self.host and self.username and self.password)

    def request(
        self,
        action: str,
        request_timeout: float | None = None,
        **params: object,
    ) -> Any:
        """Executa uma chamada autenticada à API player_api.php."""
        if not self.is_configured:
            raise ValueError("Servidor Xtream não configurado nas configurações do add-on")

        query = {
            "username": self.username,
            "password": self.password,
            "action": action,
            **{key: str(value) for key, value in params.items() if value is not None},
        }
        return self.http.get_json(
            f"{self.host}/player_api.php?{urlencode(query)}",
            timeout=request_timeout,
        )

    def get_series_info(self, series_id: str) -> dict[str, Any]:
        """Obtém detalhes de temporadas e episódios de uma série."""
        data = self.request("get_series_info", series_id=series_id)
        return data if isinstance(data, dict) else {}

    def xmltv_url(self) -> str:
        """Gera a URL XMLTV autorizada do provedor sem realizar a requisição."""
        if not self.is_configured:
            raise ValueError("Servidor Xtream não configurado")
        query = urlencode({"username": self.username, "password": self.password})
        return f"{self.host}/xmltv.php?{query}"

    def stream_url(self, media_type: str, stream_id: str, extension: str = "") -> str:
        """Gera a URL de streaming final no momento da reprodução."""
        if not self.is_configured:
            raise ValueError("Servidor Xtream não configurado")
        roots = {"live": "live", "vod": "movie", "series": "series"}
        root = roots.get(media_type, "live")
        ext = extension.lstrip(".") or ("ts" if media_type == "live" else "mp4")
        return f"{self.host}/{root}/{self.username}/{self.password}/{stream_id}.{ext}"

    def probe_stream(self, media_type: str, stream_id: str, extension: str = "") -> float | None:
        """Sonda somente a variante solicitada e nunca expõe sua URL autenticada."""
        return self.http.probe_stream(self.stream_url(media_type, stream_id, extension))
