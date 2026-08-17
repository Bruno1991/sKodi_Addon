from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", "site", "__pycache__", ".pytest_cache"}


def walk(path: Path, prefix: str = "", lines: list[str] | None = None) -> list[str]:
    if lines is None:
        lines = []
    entries = [
        item
        for item in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if item.name not in EXCLUDE
    ]
    for index, item in enumerate(entries):
        last = index == len(entries) - 1
        branch = "└── " if last else "├── "
        lines.append(prefix + branch + item.name + ("/" if item.is_dir() else ""))
        if item.is_dir():
            walk(item, prefix + ("    " if last else "│   "), lines)
    return lines


def main() -> int:
    lines = [ROOT.name + "/"]
    walk(ROOT, lines=lines)
    output_file = ROOT / "TREE_FINAL.txt"
    output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Árvore gerada em {output_file} ({len(lines)} entradas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
