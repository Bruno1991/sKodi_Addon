from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REQUIRED = {
    "README.md", "AGENTS.md", "Dockerfile", "contracts/error-envelope.schema.json", "contracts/log-event.schema.json",
    "native/cpp/CMakeLists.txt", "native/arduino/platformio.ini", "native/assembly-x86_64/secure_copy.S",
    "managed/dotnet/Corporate.Security/Corporate.Security.csproj", "managed/java/pom.xml", "managed/kotlin/pom.xml",
    "web-scripting/python/pyproject.toml", "web-scripting/python-kodi/addon.xml", "web-scripting/typescript/package.json",
    "web-scripting/php/composer.json", "web-scripting/web-vanilla/index.html", "systems/rust/Cargo.toml",
    "infrastructure/sql/ansi/001_core_schema.sql", "infrastructure/sql/mysql/001_core_schema.sql",
    "infrastructure/sql/postgresql/001_core_schema.sql", "infrastructure/sql/sqlite/001_core_schema.sql",
    "infrastructure/scripts/build-all.bash", "infrastructure/scripts/build-all.ps1", "infrastructure/scripts/build-all.sh"
}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]).resolve()
    files = sorted(path for path in root.rglob("*") if path.is_file() and ".build" not in path.parts and "manifest" not in path.relative_to(root).parts)
    relative = {path.relative_to(root).as_posix() for path in files}
    missing = sorted(REQUIRED - relative)
    errors: list[str] = [f"missing required file: {name}" for name in missing]
    for path in files:
        data = path.read_bytes()
        try: text = data.decode("utf-8")
        except UnicodeDecodeError: errors.append(f"non-UTF-8 text artifact: {path.relative_to(root)}"); continue
        if "\ufffd" in text: errors.append(f"replacement character: {path.relative_to(root)}")
        if re.search(r"(?m)^\s*\.{3}\s*$|<\.{3}>|\[\.{3}\]", text): errors.append(f"ellipsis placeholder is forbidden: {path.relative_to(root)}")
        if re.search(r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9+/=_-]{16,}", text): errors.append(f"possible embedded secret: {path.relative_to(root)}")
        if path.suffix == ".json":
            try: json.loads(text)
            except json.JSONDecodeError as error: errors.append(f"invalid JSON {path.relative_to(root)}: {error}")
        if path.suffix == ".xml":
            try: ET.fromstring(text)
            except ET.ParseError as error: errors.append(f"invalid XML/HTML {path.relative_to(root)}: {error}")
        if path.suffix == ".py":
            try: compile(text, str(path), "exec")
            except SyntaxError as error: errors.append(f"invalid Python {path.relative_to(root)}: {error}")
    if errors:
        print("PACKAGE VALIDATION FAILED")
        for error in errors: print(f"- {error}")
        return 1
    tree_lines = ["# Árvore real do projeto", "", "```text", root.name + "/"]
    for path in sorted(root.rglob("*")):
        if "manifest" in path.relative_to(root).parts or ".build" in path.parts: continue
        depth = len(path.relative_to(root).parts) - 1
        tree_lines.append("    " * depth + ("└── " if depth else "├── ") + path.name + ("/" if path.is_dir() else ""))
    tree_lines.extend(["```", ""])
    (root / "docs" / "PROJECT_TREE.md").write_text("\n".join(tree_lines), encoding="utf-8", newline="\n")
    files = sorted(path for path in root.rglob("*") if path.is_file() and "manifest" not in path.relative_to(root).parts)
    manifest_dir = root / "manifest"; manifest_dir.mkdir(exist_ok=True)
    checksums = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}" for path in files]
    (manifest_dir / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8", newline="\n")
    manifest = {"package": root.name, "version": "1.0.0", "content_files": len(files), "sha256_file": "manifest/SHA256SUMS.txt"}
    (manifest_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"PACKAGE VALIDATION PASSED: {len(files)} content files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
