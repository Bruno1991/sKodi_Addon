"""Padrão de referência; adaptar ao código real."""
from __future__ import annotations

import sys
from urllib.parse import parse_qs


def parse_params(raw: str) -> dict[str, str]:
    query = raw[1:] if raw.startswith("?") else raw
    return {key: values[0] for key, values in parse_qs(query).items() if values}


def dispatch(routes, default_handler):
    params = parse_params(sys.argv[2] if len(sys.argv) > 2 else "")
    action = params.pop("action", "home")
    handler = routes.get(action, default_handler)
    return handler(**params)
