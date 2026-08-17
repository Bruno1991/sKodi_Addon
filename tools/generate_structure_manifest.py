from __future__ import annotations

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "STRUCTURE_MANIFEST.json"
ARTWORK_MANIFEST = ROOT / "artwork" / "artwork-manifest.json"
EXCLUDED_PATHS = {"STRUCTURE_MANIFEST.json"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_paths(*args: str) -> set[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return {
        item.decode("utf-8").replace("\\", "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def package_paths() -> list[str]:
    paths = git_paths("ls-files", "-z")
    paths.update(git_paths("ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(path for path in paths if path not in EXCLUDED_PATHS and (ROOT / path).is_file())


def addon_ids() -> list[str]:
    ids: list[str] = []
    for xml_path in sorted((ROOT / "addons").glob("*/addon.xml")):
        ids.append(ET.parse(xml_path).getroot().attrib["id"])
    return ids


def skill_count() -> int:
    return sum(1 for _ in (ROOT / ".agents" / "skills").glob("*/*/SKILL.md"))


def fixed_shared_artwork_count() -> int:
    data = json.loads(ARTWORK_MANIFEST.read_text(encoding="utf-8"))
    return sum(1 for item in data["assets"] if item.get("role") == "shared_ui_asset")


def build_manifest() -> dict[str, object]:
    files = []
    for relative in package_paths():
        path = ROOT / relative
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return {
        "package": "SAILE sRepo architecture V2",
        "version": "2.0.0",
        "canonical_addon_ids": addon_ids(),
        "skill_count": skill_count(),
        "fixed_shared_artwork_count": fixed_shared_artwork_count(),
        "file_count_excluding_manifest": len(files),
        "files": files,
    }


def main() -> int:
    data = build_manifest()
    MANIFEST_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        "Manifesto estrutural gerado: "
        f"{data['file_count_excluding_manifest']} arquivos, "
        f"{data['fixed_shared_artwork_count']} artes compartilhadas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
