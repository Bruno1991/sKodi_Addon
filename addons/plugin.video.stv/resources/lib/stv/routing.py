from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode


@dataclass(frozen=True)
class Request:
    base_url: str
    handle: int
    params: dict[str, str]

    @property
    def action(self) -> str:
        return self.params.get("action", "home")

    @classmethod
    def from_argv(cls, argv: list[str]) -> "Request":
        base_url = argv[0] if argv else "plugin://plugin.video.stv/"
        handle = int(argv[1]) if len(argv) > 1 and argv[1] else -1
        query = argv[2][1:] if len(argv) > 2 and argv[2].startswith("?") else ""
        return cls(base_url=base_url, handle=handle, params=dict(parse_qsl(query)))

    def url(self, **params: object) -> str:
        clean = {key: str(value) for key, value in params.items() if value is not None}
        return f"{self.base_url}?{urlencode(clean)}"
