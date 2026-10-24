"""Teste dedicado de reprodução contínua com TELA BLOQUEADA no Kodi / sRadio (Android Emulator)."""
from __future__ import annotations

import json
import socket
import subprocess
import time
from typing import Any, Dict, Optional

ADB = r"C:\dev\android_emulator\sdk\platform-tools\adb.exe"
SERIAL = "emulator-5554"


def log(msg: str) -> None:
    print(msg, flush=True)


def run_adb(cmd_list: list[str]) -> str:
    full_cmd = [ADB, "-s", SERIAL] + cmd_list
    proc = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip()


def send_jsonrpc(method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
    payload = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params is not None:
        payload["params"] = params
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", 9090))
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")

        buf = bytearray()
        depth = 0
        in_string = False
        escape = False
        started = False

        while True:
            chunk = s.recv(8192)
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
        return json.loads(buf.decode("utf-8", errors="replace").strip())
    except Exception as e:
        log(f"    [!] Erro JSON-RPC ({method}): {e}")
        return None


def main():
    log("=" * 65)
    log(" Teste de Reprodução com Tela Bloqueada no sRadio (Android)")
    log("=" * 65)

    run_adb(["forward", "tcp:9090", "tcp:9090"])

    # 1. Verificar se Kodi está rodando
    pid = run_adb(["shell", "pidof org.xbmc.kodi"])
    if not pid:
        log("[+] Iniciando Kodi...")
        run_adb(["shell", "am", "start", "-n", "org.xbmc.kodi/.Splash"])
        time.sleep(5)

    # 2. Assegurar tela ligada antes do teste
    run_adb(["shell", "input keyevent 82"])
    time.sleep(1)

    # 3. Iniciar reprodução de uma rádio do sRadio via Playlist.Add e Player.Open
    log("\n[1] Iniciando reprodução da rádio (Antena 1)...")
    play_url = "plugin://plugin.audio.sradio/?action=play&guide_id=s7047&name=Antena+1"
    send_jsonrpc("Playlist.Clear", {"playlistid": 0})
    send_jsonrpc("Playlist.Add", {"playlistid": 0, "item": {"file": play_url}})
    play_resp = send_jsonrpc("Player.Open", {"item": {"playlistid": 0, "position": 0}})
    log(f"    -> Resposta Player.Open: {play_resp}")
    
    # Aguardar início da reprodução
    active_player_id = None
    for i in range(15):
        time.sleep(1)
        resp = send_jsonrpc("Player.GetActivePlayers")
        players = resp.get("result", []) if resp else []
        if players:
            active_player_id = players[0]["playerid"]
            player_type = players[0].get("type", "desconhecido")
            log(f"    -> Rádio conectada e tocando! Player ID: {active_player_id} (Tipo: {player_type})")
            break

    if active_player_id is None:
        log("[!] FALHA: O player não iniciou a tempo.")
        return 1

    # Obter propriedades iniciais
    props_before = send_jsonrpc("Player.GetProperties", {"playerid": active_player_id, "properties": ["time", "speed"]})
    log(f"    -> Propriedades antes do bloqueio: {props_before.get('result', {})}")

    # 4. Bloquear tela (Power Keyevent 26)
    log("\n[2] Bloqueando a tela do emulador (Keyevent 26 - POWER)...")
    run_adb(["shell", "input keyevent 26"])
    time.sleep(2)

    wakefulness = run_adb(["shell", "dumpsys power | grep 'mWakefulness='"])
    log(f"    -> Estado da tela após keyevent 26: {wakefulness.strip()}")

    # 5. Monitorar reprodução com tela bloqueada por 10 segundos
    log("\n[3] Monitorando reprodução durante 10 segundos com a tela bloqueada:")
    success = True
    for sec in [2, 5, 8, 10]:
        time.sleep(2)
        resp = send_jsonrpc("Player.GetActivePlayers")
        players = resp.get("result", []) if resp else []
        if not players:
            log(f"    [!] Segundo {sec}: Player PAROU com a tela bloqueada!")
            success = False
            break
        props = send_jsonrpc("Player.GetProperties", {"playerid": players[0]["playerid"], "properties": ["time", "speed"]})
        cur_time = props.get("result", {}).get("time", {}) if props else {}
        time_str = f"{cur_time.get('minutes', 0):02d}:{cur_time.get('seconds', 0):02d}"
        log(f"    [OK] Segundo {sec} bloqueado: Player ATIVO, tempo de áudio: {time_str}, velocidade: {props.get('result', {}).get('speed')}")

    # 6. Desbloquear a tela
    log("\n[4] Desbloqueando a tela do emulador...")
    run_adb(["shell", "input keyevent 82"])
    time.sleep(1)

    wake_after = run_adb(["shell", "dumpsys power | grep 'mWakefulness='"])
    log(f"    -> Estado da tela após desbloqueio: {wake_after.strip()}")

    # Verificar player após desbloquear
    resp_after = send_jsonrpc("Player.GetActivePlayers")
    players_after = resp_after.get("result", []) if resp_after else []
    log(f"    -> Players ativos após desbloqueio: {players_after}")

    # 7. Parar reprodução
    if players_after:
        send_jsonrpc("Player.Stop", {"playerid": players_after[0]["playerid"]})
        log("[+] Player parado com sucesso.")

    log("\n" + "=" * 65)
    if success and players_after:
        log(" RESULTADO: SUCESSO ABSOLUTO! A rádio continuou tocando com tela bloqueada!")
    else:
        log(" RESULTADO: FALHA! A reprodução foi interrompida com a tela bloqueada.")
    log("=" * 65)
    return 0 if (success and players_after) else 1


if __name__ == "__main__":
    raise SystemExit(main())
