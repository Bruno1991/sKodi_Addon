from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"
EXPECTED = {
    "repository.srepo",
    "resource.images.saile",
    "script.module.saile.core",
    "script.module.saile.epg",
    "plugin.video.stv",
}
LOCAL_DEPENDENCIES = EXPECTED - {"repository.srepo"}
REQUIRED_SHARED_ART = {
    "common/search.png",
    "common/erro.png",
    "common/check.png",
    "common/sync.png",
    "common/folder.png",
    "stv/live.png",
    "stv/vod.png",
    "stv/series.png",
    "stv/favoritos.png",
}


def validate_addon(addon_dir: Path, actual: set[str]) -> list[str]:
    errors: list[str] = []
    xml_path = addon_dir / "addon.xml"
    if not xml_path.is_file():
        return [f"{addon_dir.name}: addon.xml ausente"]
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        return [f"{addon_dir.name}: XML inválido: {exc}"]
    if root.tag != "addon":
        errors.append(f"{addon_dir.name}: raiz XML deve ser <addon>")
    if root.attrib.get("id") != addon_dir.name:
        errors.append(f"{addon_dir.name}: id do addon.xml não coincide com a pasta")
    for attr in ("id", "name", "version", "provider-name"):
        if not root.attrib.get(attr):
            errors.append(f"{addon_dir.name}: atributo obrigatório ausente: {attr}")
    for asset in ("icon.png", "fanart.jpg"):
        path = addon_dir / asset
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{addon_dir.name}: {asset} ausente ou vazio")
    for extension in root.findall("extension"):
        library = extension.attrib.get("library")
        if library and not (addon_dir / library).exists():
            errors.append(f"{addon_dir.name}: library/entrypoint ausente: {library}")
    requires = root.find("requires")
    if requires is not None:
        for dependency in requires.findall("import"):
            dependency_id = dependency.attrib.get("addon", "")
            if dependency_id in LOCAL_DEPENDENCIES and dependency_id not in actual:
                errors.append(f"{addon_dir.name}: dependência local ausente: {dependency_id}")
    settings = addon_dir / "resources" / "settings.xml"
    if settings.is_file():
        try:
            settings_root = ET.parse(settings).getroot()
            if settings_root.tag != "settings":
                errors.append(f"{addon_dir.name}: resources/settings.xml inválido")
        except ET.ParseError as exc:
            errors.append(f"{addon_dir.name}: settings.xml inválido: {exc}")
    return errors


def validate_shared_art() -> list[str]:
    media = ADDONS / "resource.images.saile" / "resources" / "media"
    return [
        f"resource.images.saile: asset compartilhado ausente: {relative}"
        for relative in sorted(REQUIRED_SHARED_ART)
        if not (media / relative).is_file() or (media / relative).stat().st_size == 0
    ]


def main() -> int:
    actual = {path.name for path in ADDONS.iterdir() if path.is_dir()}
    errors = [f"Add-on obrigatório ausente: {addon_id}" for addon_id in sorted(EXPECTED - actual)]
    for addon_id in sorted(EXPECTED & actual):
        errors.extend(validate_addon(ADDONS / addon_id, actual))
    errors.extend(validate_shared_art())
    if errors:
        print("Validação falhou:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Add-ons válidos: " + ", ".join(sorted(EXPECTED)))
    print(f"Artwork compartilhado válido: {len(REQUIRED_SHARED_ART)} arquivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
