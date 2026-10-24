"""Bateria completa de testes automatizados para todos os menus do sRadio no Kodi (Emulador Android).

Executa navegação em 100% dos menus raiz e submenus, testa busca, favoritos, reprodução
dinâmica e analisa o arquivo kodi.log linha por linha em busca de erros, exceções ou alertas.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ADB = r"C:\dev\android_emulator\sdk\platform-tools\adb.exe"
SERIAL = "emulator-5554"
ROOT = Path(__file__).resolve().parents[1]
ADDONS_DIR = ROOT / "addons"


def log(msg: str) -> None:
    print(msg, flush=True)


def run_adb(cmd_list: list[str]) -> str:
    full_cmd = [ADB, "-s", SERIAL] + cmd_list
    proc = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        log(f"[!] Erro no comando ADB: {' '.join(full_cmd)}")
        log(f"    Stderr: {proc.stderr.strip()}")
    return proc.stdout.strip()


def send_jsonrpc(method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 12) -> Optional[Dict[str, Any]]:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1,
    }
    if params is not None:
        payload["params"] = params

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", 9090))
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")

        # Leitor de stream JSON com rastreamento de profundidade de chaves
        buf = bytearray()
        depth = 0
        in_string = False
        escape = False
        started = False

        while True:
            chunk = s.recv(16384)
            if not chunk:
                break
            buf.extend(chunk)

            for byte in chunk:
                char = chr(byte)
                if escape:
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == "{":
                        depth += 1
                        started = True
                    elif char == "}":
                        depth -= 1
                        if started and depth == 0:
                            break
            if started and depth == 0:
                break

        s.close()
        raw_resp = buf.decode("utf-8", errors="replace").strip()
        if not raw_resp:
            return None
        return json.loads(raw_resp)
    except Exception as e:
        log(f"    [!] Erro na chamada JSON-RPC ({method}): {e}")
        return None


def get_directory(url: str, timeout: int = 12) -> Tuple[bool, List[Dict[str, Any]], str]:
    resp = send_jsonrpc("Files.GetDirectory", {"directory": url, "media": "files"}, timeout=timeout)
    if not resp or "error" in resp:
        err = resp.get("error", {}).get("message", "Sem resposta do Kodi") if resp else "Timeout ou erro de conexão"
        return False, [], str(err)

    files = resp.get("result", {}).get("files", [])
    return True, files, ""


def sync_code_to_emulator() -> None:
    log("[+] Sincronizando código atualizado do sRadio com o emulador...")
    target_addons = "/data/media/0/Android/data/org.xbmc.kodi/files/.kodi/addons/plugin.audio.sradio"
    local_sradio = ADDONS_DIR / "plugin.audio.sradio"

    run_adb(["push", str(local_sradio), "/data/local/tmp/"])
    run_adb(["shell", f"cp -rf /data/local/tmp/plugin.audio.sradio/* {target_addons}/"])
    run_adb(["shell", f"chown -R u0_a193:ext_data_rw {target_addons}"])
    run_adb(["shell", f"chmod -R 775 {target_addons}"])
    log("[+] Add-on atualizado no emulador.")


def get_log_offset() -> int:
    out = run_adb(["shell", "wc -c /data/media/0/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log"])
    try:
        return int(out.split()[0])
    except Exception:
        return 0


def read_log_since(offset: int) -> List[str]:
    out = run_adb(["shell", f"tail -c +{offset + 1} /data/media/0/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log"])
    return out.splitlines()


def run_battery() -> Dict[str, Any]:
    log("=" * 70)
    log(" Bateria Completa de Testes de Todos os Menus do sRadio")
    log("=" * 70)

    # 1. Atualizar código no emulador
    sync_code_to_emulator()

    # 2. Registrar offset inicial do log
    log_offset_start = get_log_offset()
    log(f"[+] Offset inicial de kodi.log: {log_offset_start} bytes")

    # Definição dos menus e rotas para teste sistemático
    test_suite = [
        ("T01_ROOT", "Menu Raiz / Home", "plugin://plugin.audio.sradio/", 10),
        ("T02_LOCAL", "Rádios Locais (Browse c=local)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dlocal", 1),
        ("T03_BEST", "Melhores & Em Alta (Browse c=best)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dbest", 3),
        ("T04_BRAZIL", "Brasil Cidades & Estados (Browse id=r101223)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fid%3Dr101223", 5),
        ("T05_BRAZIL_SUB", "Submenu Brasil - Cidades de SP (id=r101223 subfolder)", "plugin://plugin.audio.sradio/?action=browse&url=http%3A%2F%2Fopml.radiotime.com%2FBrowse.ashx%3Fid%3Dr101223%26partnerId%3DxwhZkVKi", 5),
        ("T06_MUSIC", "Música por Gênero (Browse c=music)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dmusic", 5),
        ("T07_MUSIC_ROCK", "Submenu Música - Gênero Rock (id=c57951)", "plugin://plugin.audio.sradio/?action=browse&url=http%3A%2F%2Fopml.radiotime.com%2FBrowse.ashx%3Fid%3Dc57951%26partnerId%3DxwhZkVKi", 3),
        ("T08_TALK", "Notícias & Conversas (Browse c=talk)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dtalk", 3),
        ("T09_SPORTS", "Esportes ao Vivo (Browse c=sports)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dsports", 2),
        ("T10_LOCATION", "Por Localização / Mundo (Browse id=r0)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fid%3Dr0", 5),
        ("T11_LOCATION_SA", "Submenu Localização - América do Sul (id=r101219)", "plugin://plugin.audio.sradio/?action=browse&url=http%3A%2F%2Fopml.radiotime.com%2FBrowse.ashx%3Fid%3Dr101219%26partnerId%3DxwhZkVKi", 5),
        ("T12_LANG", "Por Idioma (Browse c=lang)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dlang", 5),
        ("T13_PODCAST", "Podcasts & Programas (Browse c=podcast)", "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dpodcast", 3),
        ("T14_OFFLINE_CACHE", "Catálogo em Cache Offline (action=all_stations)", "plugin://plugin.audio.sradio/?action=all_stations", 1000),
        ("T15_SEARCH_NAME", "Busca em Tempo Real por Nome (query=Jovem Pan)", "plugin://plugin.audio.sradio/?action=search&query=Jovem+Pan", 1),
        ("T16_SEARCH_FREQ", "Busca em Tempo Real por Frequência (query=100.1)", "plugin://plugin.audio.sradio/?action=search&query=100.1", 1),
        ("T17_FAVORITES", "Menu de Favoritos (action=favorites)", "plugin://plugin.audio.sradio/?action=favorites", 0),
    ]

    results: Dict[str, Any] = {
        "total": len(test_suite) + 2,
        "passed": 0,
        "failed": 0,
        "tests": [],
    }

    # Executar testes de diretório
    for tid, tname, turl, min_items in test_suite:
        log(f"\n[*] Executando [{tid}] {tname}...")
        t0 = time.time()
        ok, items, err = get_directory(turl)
        elapsed = round(time.time() - t0, 2)

        if ok and len(items) >= min_items:
            log(f"    [OK] Retornou {len(items)} itens em {elapsed}s")
            for it in items[:3]:
                log(f"         - {it.get('label')}")
            results["passed"] += 1
            results["tests"].append({"id": tid, "name": tname, "status": "PASS", "items": len(items), "elapsed": elapsed})
        else:
            log(f"    [FALHA] Retornou {len(items)} itens (esperava >= {min_items}). Erro: {err}")
            results["failed"] += 1
            results["tests"].append({"id": tid, "name": tname, "status": "FAIL", "items": len(items), "error": err, "elapsed": elapsed})

    # Teste 18: Toggle de Favoritos
    log("\n[*] Executando [T18_FAV_TOGGLE] Adicionar e Remover dos Favoritos...")
    t0 = time.time()
    test_id = "s_test_battery_999"
    fav_toggle_url = f"plugin://plugin.audio.sradio/?action=toggle_fav&guide_id={test_id}&name=Estacao+Teste+Bateria&cat=Teste"

    # 1. Adicionar via toggle
    get_directory(fav_toggle_url)
    time.sleep(1)
    ok_fav, fav_items, _ = get_directory("plugin://plugin.audio.sradio/?action=favorites")
    is_in_fav = any(test_id in it.get("file", "") or "Estacao Teste Bateria" in it.get("label", "") for it in fav_items)

    # 2. Remover via toggle para limpar
    get_directory(fav_toggle_url)
    time.sleep(1)
    ok_fav2, fav_items2, _ = get_directory("plugin://plugin.audio.sradio/?action=favorites")
    is_removed = not any(test_id in it.get("file", "") or "Estacao Teste Bateria" in it.get("label", "") for it in fav_items2)

    elapsed = round(time.time() - t0, 2)
    if is_in_fav and is_removed:
        log(f"    [OK] Favorito adicionado e removido com sucesso via toggle em {elapsed}s")
        results["passed"] += 1
        results["tests"].append({"id": "T18_FAV_TOGGLE", "name": "Toggle de Favoritos", "status": "PASS", "elapsed": elapsed})
    else:
        log(f"    [FALHA] Falha no ciclo toggle de favoritos (adicionado={is_in_fav}, removido={is_removed}).")
        results["failed"] += 1
        results["tests"].append({"id": "T18_FAV_TOGGLE", "name": "Toggle de Favoritos", "status": "FAIL", "elapsed": elapsed})

    # Teste 19: Reprodução ao Vivo e Verificação do Player
    log("\n[*] Executando [T19_PLAYBACK] Reprodução de Rádio e Player OSD...")
    t0 = time.time()
    play_resp = send_jsonrpc("Player.Open", {"item": {"file": "plugin://plugin.audio.sradio/?action=play&guide_id=s7047"}})
    time.sleep(4)

    players_resp = send_jsonrpc("Player.GetActivePlayers")
    active_players = players_resp.get("result", []) if players_resp else []
    log(f"    -> Players ativos: {active_players}")

    # Parar reprodução para liberar recursos
    if active_players:
        for p in active_players:
            send_jsonrpc("Player.Stop", {"playerid": p.get("playerid", 0)})

    elapsed = round(time.time() - t0, 2)
    if play_resp and "result" in play_resp:
        log(f"    [OK] Resolução de stream e comando do player aceitos em {elapsed}s")
        results["passed"] += 1
        results["tests"].append({"id": "T19_PLAYBACK", "name": "Reprodução de Rádio ao Vivo", "status": "PASS", "elapsed": elapsed})
    else:
        log(f"    [FALHA] Falha ao enviar Player.Open: {play_resp}")
        results["failed"] += 1
        results["tests"].append({"id": "T19_PLAYBACK", "name": "Reprodução de Rádio ao Vivo", "status": "FAIL", "elapsed": elapsed})

    # 3. Análise Detalhada dos Logs do Kodi
    log("\n" + "=" * 70)
    log(" Análise Detalhada do Arquivo kodi.log")
    log("=" * 70)

    log_lines = read_log_since(log_offset_start)
    log(f"[+] Total de linhas registradas no log durante a bateria: {len(log_lines)}")

    errors: List[str] = []
    warnings: List[str] = []
    sradio_events: List[str] = []

    for line in log_lines:
        line_strip = line.strip()
        line_lower = line_strip.lower()

        if "error <general>" in line_lower or "traceback (most recent call last)" in line_lower or "exception" in line_lower:
            if not any(ign in line_lower for ign in ["failed to update input device", "zeroconf"]):
                errors.append(line_strip)
        elif "warning <general>" in line_lower:
            warnings.append(line_strip)

        if "sradio" in line_lower or "plugin.audio.sradio" in line_lower:
            sradio_events.append(line_strip)

    log(f"[+] Linhas relacionadas ao sRadio: {len(sradio_events)}")
    log(f"[+] Total de Advertências (Warnings): {len(warnings)}")
    log(f"[+] Total de Erros Críticos (Errors): {len(errors)}")

    if errors:
        log("\n[!] Erros detectados no log:")
        for err_line in errors:
            log(f"    | {err_line}")
    else:
        log("\n[V] NENHUM ERRO OU EXCEÇÃO PYTHON DETECTADO NO KODI.LOG!")

    results["log_analysis"] = {
        "total_lines": len(log_lines),
        "sradio_events_count": len(sradio_events),
        "warning_count": len(warnings),
        "error_count": len(errors),
        "errors": errors,
        "sample_warnings": warnings[:5],
    }

    # Resumo Final
    log("\n" + "=" * 70)
    log(f" RESUMO DA BATERIA: {results['passed']}/{results['total']} TESTES APROVADOS ({results['passed'] / results['total'] * 100:.1f}%)")
    log("=" * 70)

    return results


if __name__ == "__main__":
    res = run_battery()
    if res["failed"] > 0 or res["log_analysis"]["error_count"] > 0:
        sys.exit(1)
    sys.exit(0)
