from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artwork" / "artwork-manifest.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    copied = 0
    for asset in data["assets"]:
        source = ROOT / asset["source"]
        destination = ROOT / asset["destination"]
        if not source.is_file():
            raise FileNotFoundError(f"Artwork ausente: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    print(f"Artwork copiado: {copied} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
