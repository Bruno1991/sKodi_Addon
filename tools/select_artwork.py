import json
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTWORK_DIR = ROOT / "artwork"
MANIFEST = ARTWORK_DIR / "artwork-manifest.json"

ADDONS = [
    "repository.srepo",
    "plugin.video.stv",
    "resource.images.saile",
    "script.module.saile.core",
    "script.module.saile.epg"
]

COMMON_MAP = {
    "search.png": ("common", "common/search.png"),
    "erro.png": ("common", "common/erro.png"),
    "check.png": ("common", "common/check.png"),
    "sync.png": ("common", "common/sync.png"),
    "folder.png": ("common", "common/folder.png"),
    "live.png": ("stv", "stv/live.png"),
    "vod.png": ("stv", "stv/vod.png"),
    "series.png": ("stv", "stv/series.png"),
    "favoritos.png": ("stv", "stv/favoritos.png"),
}

def get_available_styles(category: str) -> list[str]:
    path = ARTWORK_DIR / "addons" / category
    if not path.is_dir():
        return []
    return [d.name for d in path.iterdir() if d.is_dir()]

def generate_manifest(icon_style: str, fanart_style: str) -> dict:
    assets = []
    
    # Addon Icons
    for addon in ADDONS:
        icon_src = ARTWORK_DIR / "addons" / "icons" / icon_style / addon / "icon.png"
        if icon_src.exists():
            assets.append({
                "source": f"artwork/addons/icons/{icon_style}/{addon}/icon.png",
                "addon_id": addon,
                "role": "addon_icon",
                "destination": f"addons/{addon}/icon.png",
                "temporary": False
            })
        
    # Addon Fanarts
    for addon in ADDONS:
        fanart_src = ARTWORK_DIR / "addons" / "fanarts" / fanart_style / addon / "fanart.jpg"
        if fanart_src.exists():
            assets.append({
                "source": f"artwork/addons/fanarts/{fanart_style}/{addon}/fanart.jpg",
                "addon_id": addon,
                "role": "addon_fanart",
                "destination": f"addons/{addon}/fanart.jpg",
                "temporary": False
            })
            
    # Common assets
    for filename, (scope, dest_suffix) in COMMON_MAP.items():
        assets.append({
            "source": f"artwork/common/png/{filename}",
            "addon_id": "resource.images.saile",
            "role": "shared_ui_asset",
            "scope": scope,
            "destination": f"addons/resource.images.saile/resources/media/{dest_suffix}",
            "temporary": False
        })

    manifest = {
        "version": "2.0.0",
        "status": "dynamic-artwork",
        "shared_resource_addon": "resource.images.saile",
        "fixed_shared_asset_count": len(COMMON_MAP),
        "replacement_rule": "Replace files keeping the canonical filename and compatible dimensions.",
        "icon_style": icon_style,
        "fanart_style": fanart_style,
        "assets": assets
    }
    return manifest

def main():
    parser = argparse.ArgumentParser(description="Select and apply artwork styles.")
    
    icon_styles = get_available_styles("icons")
    fanart_styles = get_available_styles("fanarts")
    
    parser.add_argument("--icon-style", choices=icon_styles, 
                        default=icon_styles[0] if icon_styles else None,
                        help="Select the icon style")
    parser.add_argument("--fanart-style", choices=fanart_styles, 
                        default=fanart_styles[0] if fanart_styles else None,
                        help="Select the fanart style")
    parser.add_argument("--common-color", type=str, default=None,
                        help="CSS background style for common icons (e.g. 'red', 'linear-gradient(...)')")
    parser.add_argument("--list", action="store_true", help="List available styles")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available Icon Styles:")
        for s in icon_styles:
            print(f"  - {s}")
        print("\nAvailable Fanart Styles:")
        for s in fanart_styles:
            print(f"  - {s}")
        return 0

    if not args.icon_style or not args.fanart_style:
        print("Error: No styles found in artwork/addons/")
        return 1

    if args.common_color:
        import subprocess
        print(f"Applying common color: '{args.common_color}'...")
        color_script = ROOT / "tools" / "colorize_common_svgs.py"
        subprocess.run([sys.executable, str(color_script), args.common_color], check=True)

    print(f"Generating manifest for Icon Style: '{args.icon_style}', Fanart Style: '{args.fanart_style}'...")
    
    manifest_data = generate_manifest(args.icon_style, args.fanart_style)
    
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        
    print("Manifest updated successfully.")
    print("Run `python tools/bootstrap_artwork.py` to apply the changes to the addons.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
