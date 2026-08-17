import asyncio
import os
import sys
import urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SVG_DIR = ROOT / "artwork" / "common" / "svg"
PNG_DIR = ROOT / "artwork" / "common" / "png"

COMMON_MAP = {
    "search_256dp": "search.png",
    "error_256dp": "erro.png",
    "check_circle_256dp": "check.png",
    "sync_256dp": "sync.png",
    "folder_256dp": "folder.png",
    "cinematic_blur_256dp": "series.png",
    "favorite_256dp": "favoritos.png",
    "live_tv_256dp": "live.png",
    "movie_256dp": "vod.png"
}

async def render_svg_to_png(svg_content: str, background_style: str, output_path: Path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        encoded_svg = urllib.parse.quote(svg_content)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
                .mask-container {{
                    width: 512px;
                    height: 512px;
                    background: {background_style};
                    -webkit-mask-image: url('data:image/svg+xml;utf8,{encoded_svg}');
                    -webkit-mask-size: contain;
                    -webkit-mask-position: center;
                    -webkit-mask-repeat: no-repeat;
                    mask-image: url('data:image/svg+xml;utf8,{encoded_svg}');
                    mask-size: contain;
                    mask-position: center;
                    mask-repeat: no-repeat;
                }}
            </style>
        </head>
        <body>
            <div class="mask-container"></div>
        </body>
        </html>
        """
        
        await page.set_viewport_size({"width": 512, "height": 512})
        await page.set_content(html_content)
        await page.wait_for_timeout(100)
        
        await page.locator(".mask-container").screenshot(path=str(output_path), omit_background=True)
        await browser.close()

async def main():
    if len(sys.argv) < 2:
        print("Uso: python colorize_common_svgs.py <background_style>")
        sys.exit(1)
        
    background_style = sys.argv[1]
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Applying color variation: '{background_style}'")
    for svg_file in SVG_DIR.iterdir():
        if svg_file.is_file() and svg_file.name.endswith(".svg"):
            dest_name = None
            for key, val in COMMON_MAP.items():
                if key in svg_file.name:
                    dest_name = val
                    break
            
            if dest_name:
                svg_content = svg_file.read_text(encoding="utf-8")
                dest_path = PNG_DIR / dest_name
                print(f"Generating {dest_name}...")
                await render_svg_to_png(svg_content, background_style, dest_path)
    
    print("All common SVGs colorized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
