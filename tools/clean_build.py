from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ("site", "dist", "build"):
    path = ROOT / name
    if path.exists():
        shutil.rmtree(path)
        print(f"Removido: {path}")
