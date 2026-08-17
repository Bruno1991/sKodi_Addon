"""Cliente HTTP seguro e leve para consumo de APIs remotas."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpClient:
    """Cliente HTTP síncrono para requisições JSON com timeout e User-Agent configuráveis."""

    def __init__(self, timeout: float = 15.0, user_agent: str = "sTv-Kodi/1.0") -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> object:
        """Executa uma requisição GET retornando a resposta decodificada como JSON."""
        request_headers = {"User-Agent": self.user_agent, **(headers or {})}
        request = Request(url, headers=request_headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
                return json.loads(payload)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(f"Falha ao consultar serviço remoto: {exc}") from exc
