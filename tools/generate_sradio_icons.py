"""Script para buscar icones oficiais do Google Fonts Material Symbols Outlined,
salvar SVG, HTML e PNG na pasta artwork/common e sincronizar no resource.images.saile.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTWORK_COMMON = ROOT / "artwork" / "common"
SVG_DIR = ARTWORK_COMMON / "svg"
HTML_DIR = ARTWORK_COMMON / "html"
PNG_DIR = ARTWORK_COMMON / "png"

# Gradiente oficial canonico do ecossistema SAILE
OFFICIAL_GRADIENT = "linear-gradient(45deg, #e012be, #4a2b9d)"

ICON_DEFS = [
    {
        "symbol": "my_location",
        "png": "local.png",
        "codepoint": "e55c",
        "description": "Esse icone sera utilizado para o menu de radios locais no sRadio",
    },
    {
        "symbol": "whatshot",
        "png": "alta.png",
        "codepoint": "e80e",
        "description": "Esse icone sera utilizado para o menu de melhores e radios em alta no sRadio",
    },
    {
        "symbol": "flag",
        "png": "brasil.png",
        "codepoint": "f0c6",
        "description": "Esse icone sera utilizado para o menu de radios do Brasil no sRadio",
    },
    {
        "symbol": "music_note",
        "png": "musica.png",
        "codepoint": "e405",
        "description": "Esse icone sera utilizado para o menu de generos musicais no sRadio",
    },
    {
        "symbol": "newspaper",
        "png": "noticias.png",
        "codepoint": "eb81",
        "description": "Esse icone sera utilizado para o menu de noticias e conversas no sRadio",
    },
    {
        "symbol": "sports_soccer",
        "png": "esportes.png",
        "codepoint": "ea2f",
        "description": "Esse icone sera utilizado para o menu de esportes ao vivo no sRadio",
    },
    {
        "symbol": "public",
        "png": "mundo.png",
        "codepoint": "e80b",
        "description": "Esse icone sera utilizado para o menu de localizacao global no sRadio",
    },
    {
        "symbol": "translate",
        "png": "idioma.png",
        "codepoint": "e8e2",
        "description": "Esse icone sera utilizado para o menu de idiomas no sRadio",
    },
    {
        "symbol": "podcasts",
        "png": "podcast.png",
        "codepoint": "f048",
        "description": "Esse icone sera utilizado para o menu de podcasts e programas no sRadio",
    },
    {
        "symbol": "radio",
        "png": "radio.png",
        "codepoint": "e03e",
        "description": "Esse icone sera utilizado para o menu de catalogo e estacoes de radio no sRadio",
    },
]


def fetch_svg_from_google(symbol_name: str) -> str:
    url = f"https://raw.githubusercontent.com/google/material-design-icons/master/symbols/web/{symbol_name}/materialsymbolsoutlined/{symbol_name}_48px.svg"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8").strip()

    # Formatar de maneira 100% compativel com o padrao de artwork/common/svg
    # Exemplo padrao: <svg xmlns="http://www.w3.org/2000/svg" height="48px" viewBox="0 -960 960 960" width="48px" fill="#FFFFFF"><path d="..."/></svg>
    content = content.replace('height="48"', 'height="48px"').replace('width="48"', 'width="48px"')
    if 'fill="' not in content:
        content = content.replace("<svg ", '<svg fill="#FFFFFF" ')

    return content


def generate_html_content(item: dict) -> str:
    symbol = item["symbol"]
    desc = item["description"]
    codepoint = item["codepoint"]

    return f"""<!-- {desc} -->

<!-- https://fonts.google.com/icons -->

<!-- Variable icon font -->
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&icon_names={symbol}" />
<style>
.material-symbols-outlined {{
  font-variation-settings:
  'FILL' 0,
  'wght' 400,
  'GRAD' 0,
  'opsz' 48
}}
</style>

<!-- Static icon font -->
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,400,0,0&icon_names={symbol}" />

<!-- Inserting the icon -->
<span class="material-symbols-outlined">
{symbol}
</span>

<!-- Code point {codepoint} -->

<!-- Icon name {symbol} -->
"""


async def render_icons(icons_to_render: list[dict], gradient: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 512, "height": 512})

        for item in icons_to_render:
            symbol = item["symbol"]
            png_name = item["png"]
            svg_file = SVG_DIR / f"{symbol}_256dp_FFFFFF_FILL0_wght400_GRAD0_opsz48.svg"
            png_file = PNG_DIR / png_name

            svg_content = svg_file.read_text(encoding="utf-8")
            encoded_svg = urllib.parse.quote(svg_content)

            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
        .mask-container {{
            width: 512px;
            height: 512px;
            background: {gradient};
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
</html>"""
            await page.set_content(html_content)
            await page.wait_for_timeout(50)
            await page.locator(".mask-container").screenshot(path=str(png_file), omit_background=True)
            print(f"[RENDER] {png_name} gerado a partir de {symbol}")

        await browser.close()


def main():
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Baixando e gerando {len(ICON_DEFS)} icones oficiais do Google Fonts...")

    for item in ICON_DEFS:
        symbol = item["symbol"]
        svg_filename = f"{symbol}_256dp_FFFFFF_FILL0_wght400_GRAD0_opsz48.svg"
        html_filename = f"{symbol}_256dp_FFFFFF_FILL0_wght400_GRAD0_opsz48.html"

        svg_path = SVG_DIR / svg_filename
        html_path = HTML_DIR / html_filename

        svg_content = fetch_svg_from_google(symbol)
        svg_path.write_text(svg_content, encoding="utf-8")
        print(f"[SVG] {svg_filename} salvo ({len(svg_content)} bytes)")

        html_content = generate_html_content(item)
        html_path.write_text(html_content, encoding="utf-8")
        print(f"[HTML] {html_filename} salvo")

    print(f"\nRenderizando PNGs 512x512 com Playwright e gradiente canonico...")
    asyncio.run(render_icons(ICON_DEFS, OFFICIAL_GRADIENT))

    print("\nProcesso concluido com sucesso!")


if __name__ == "__main__":
    main()
