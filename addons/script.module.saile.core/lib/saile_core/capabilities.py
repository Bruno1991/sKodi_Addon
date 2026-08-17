from __future__ import annotations

import platform
import sqlite3
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Capabilities:
    python: str
    operating_system: str
    machine: str
    sqlite: str
    sqlite_fts5: bool
    resource_images_saile: bool
    inputstream_adaptive: bool
    inputstream_ffmpegdirect: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _addon_available(addon_id: str) -> bool:
    try:
        import xbmcaddon

        xbmcaddon.Addon(addon_id)
        return True
    except Exception:
        return False


def _has_fts5() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE test_fts USING fts5(value)")
        return True
    except sqlite3.DatabaseError:
        return False
    finally:
        connection.close()


def detect_capabilities() -> Capabilities:
    return Capabilities(
        python=platform.python_version(),
        operating_system=platform.system(),
        machine=platform.machine(),
        sqlite=sqlite3.sqlite_version,
        sqlite_fts5=_has_fts5(),
        resource_images_saile=_addon_available("resource.images.saile"),
        inputstream_adaptive=_addon_available("inputstream.adaptive"),
        inputstream_ffmpegdirect=_addon_available("inputstream.ffmpegdirect"),
    )
