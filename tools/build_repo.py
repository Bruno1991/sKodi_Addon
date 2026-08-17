from __future__ import annotations

import hashlib
import html
import os
import shutil
import stat
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS_DIR = ROOT / "addons"
SITE_DIR = ROOT / "docs"
EXCLUDED_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store", "Thumbs.db"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".log"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_NAMES or part.startswith(".") for part in path.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env"):
        return False
    return True


def zip_addon(addon_dir: Path, version: str, zips_dir: Path) -> Path:
    destination_dir = zips_dir / addon_dir.name
    destination_dir.mkdir(parents=True, exist_ok=True)
    zip_path = destination_dir / f"{addon_dir.name}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(addon_dir.rglob("*")):
            if source.is_file() and should_include(source.relative_to(addon_dir)):
                archive.write(source, Path(addon_dir.name) / source.relative_to(addon_dir))
    for asset_name in ("icon.png", "fanart.jpg", f"changelog-{version}.txt"):
        source = addon_dir / asset_name
        if source.is_file():
            shutil.copy2(source, destination_dir / asset_name)
    zip_path.with_suffix(zip_path.suffix + ".sha256").write_text(
        sha256(zip_path) + "\n", encoding="utf-8"
    )
    return zip_path


def build_addons_xml(addon_roots: list[ET.Element]) -> bytes:
    root = ET.Element("addons")
    for addon in addon_roots:
        root.append(addon)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_index(packages: list[tuple[str, str, Path]], site_dir: Path) -> str:
    repo_zip = None
    repo_version = None
    other_addons = []
    for addon_id, version, zip_path in packages:
        href = (zip_path.name if addon_id == "repository.srepo" else zip_path.relative_to(site_dir).as_posix())
        if addon_id == "repository.srepo":
            repo_zip = href
            repo_version = version
        else:
            other_addons.append((addon_id, version, href))
            
    cards_html = ""
    for addon_id, version, href in other_addons:
        cards_html += f'''
        <a href="{html.escape(href)}" class="card">
            <h3>{html.escape(addon_id)}</h3>
            <span class="version">v{html.escape(version)}</span>
        </a>'''

    hero_button = f'<a href="{html.escape(str(repo_zip))}" class="hero-btn">Download Repository v{html.escape(str(repo_version))}</a>' if repo_zip else ""
    
    # Generate hidden raw links for Kodi parsing
    kodi_links = []
    if repo_zip:
        kodi_links.append(f'<a href="{html.escape(str(repo_zip))}">{html.escape(str(repo_zip))}</a><br>')
    for _, _, href in other_addons:
        kodi_links.append(f'<a href="{html.escape(href)}">{html.escape(href.split("/")[-1])}</a><br>')
    kodi_links_html = "\n        ".join(kodi_links)

    template_path = ROOT / "tools" / "site_template" / "index.html"
    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")
        html_content = template_content.replace("{{HERO_BUTTON}}", hero_button).replace("{{ADDON_CARDS}}", cards_html).replace("{{KODI_LINKS}}", kodi_links_html)
        return html_content
    return ""


def _retry_remove(function, path: str, _excinfo: BaseException) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    function(path)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, onexc=_retry_remove)
    else:
        try:
            path.unlink()
        except PermissionError:
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
            path.unlink()


def publish_site(stage_dir: Path) -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    for child in SITE_DIR.iterdir():
        remove_path(child)
    for child in stage_dir.iterdir():
        shutil.move(str(child), str(SITE_DIR / child.name))


def build_site(site_dir: Path) -> list[tuple[str, str, Path]]:
    zips_dir = site_dir / "zips"
    zips_dir.mkdir(parents=True)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    # Copy site templates if they exist
    TEMPLATE_DIR = ROOT / "tools" / "site_template"
    if TEMPLATE_DIR.exists():
        shutil.copytree(TEMPLATE_DIR, site_dir, dirs_exist_ok=True)

    roots: list[ET.Element] = []
    packages: list[tuple[str, str, Path]] = []
    for addon_dir in sorted(path for path in ADDONS_DIR.iterdir() if path.is_dir()):
        root = ET.parse(addon_dir / "addon.xml").getroot()
        addon_id = root.attrib["id"]
        version = root.attrib["version"]
        zip_path = zip_addon(addon_dir, version, zips_dir)
        roots.append(root)
        packages.append((addon_id, version, zip_path))
        if addon_id == "repository.srepo":
            shutil.copy2(zip_path, site_dir / zip_path.name)

    addons_xml = build_addons_xml(roots)
    (site_dir / "addons.xml").write_bytes(addons_xml)
    (site_dir / "addons.xml.md5").write_text(
        hashlib.md5(addons_xml).hexdigest() + "\n", encoding="utf-8"
    )
    sums = [f"{sha256(path)}  {path.relative_to(site_dir).as_posix()}" for _, _, path in packages]
    (site_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (site_dir / "index.html").write_text(build_index(packages, site_dir), encoding="utf-8")
    return packages


def main() -> int:
    stage_dir = ROOT / f"docs-stage-{os.getpid()}"
    try:
        if stage_dir.exists():
            remove_path(stage_dir)
        stage_dir.mkdir(parents=True)
        packages = build_site(stage_dir)
        publish_site(stage_dir)
    finally:
        if stage_dir.exists():
            remove_path(stage_dir)
    print(f"Site gerado em {SITE_DIR} com {len(packages)} add-ons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
