"""Padrão de montagem; nunca registrar a URL final com credenciais."""
from __future__ import annotations

from urllib.parse import urlencode


def player_api_url(host: str, username: str, password: str, action: str | None = None) -> str:
    base = host.rstrip("/") + "/player_api.php"
    params = {"username": username, "password": password}
    if action:
        params["action"] = action
    return f"{base}?{urlencode(params)}"
