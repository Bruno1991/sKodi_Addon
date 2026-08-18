from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


def retry_remove(function: Callable[[str], object], path: str, _error: object) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    function(path)


def remove_directory(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT or ROOT not in resolved.parents:
        raise ValueError(f"Limpeza recusada fora do workspace: {resolved}")
    if resolved.exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(resolved, onexc=retry_remove)
        else:
            shutil.rmtree(
                resolved,
                onerror=lambda function, path, exc: retry_remove(function, path, exc[1]),
            )
        print(f"Removido: {resolved}")


for name in ("site", "dist", "build", ".pytest_cache", ".ruff_cache"):
    remove_directory(ROOT / name)
for path in ROOT.glob("docs-stage-*"):
    if path.is_dir():
        remove_directory(path)
for path in ROOT.rglob("__pycache__"):
    if path.is_dir():
        remove_directory(path)
