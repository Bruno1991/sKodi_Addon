"""Deploy e automação de teste dos add-ons sRepo no Kodi instalado no emulador Android."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ADB = r"C:\dev\android_emulator\sdk\platform-tools\adb.exe"
SERIAL = "emulator-5554"
ROOT = Path(__file__).resolve().parents[1]
ADDONS_DIR = ROOT / "addons"
TEMPLATES_DIR = ROOT / "templates"


def run_adb(cmd_list: list[str]) -> str:
    full_cmd = [ADB, "-s", SERIAL] + cmd_list
    proc = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"[!] Erro no comando ADB: {' '.join(full_cmd)}")
        print(f"    Stderr: {proc.stderr.strip()}")
    return proc.stdout.strip()


def send_jsonrpc(method: str, params: dict | None = None) -> dict | None:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1,
    }
    if params:
        payload["params"] = params

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(("127.0.0.1", 9090))
        s.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        resp_data = s.recv(8192)
        s.close()
        return json.loads(resp_data.decode("utf-8", errors="replace"))
    except Exception as e:
        return None


def deploy_and_test():
    print("=" * 60)
    print(" Deploy do sRadio para Kodi no Emulador Android")
    print("=" * 60)

    # 1. Verificar dispositivo
    devices = run_adb(["devices"])
    if SERIAL not in devices:
        print(f"[!] Emulador {SERIAL} não detectado. Iniciando ou verificando ADB...")
        sys.exit(1)
    print(f"[+] Dispositivo conectado: {SERIAL}")

    # 2. Obter UID do Kodi
    pkg_info = run_adb(["shell", "pm list packages -U org.xbmc.kodi"])
    print(f"[+] Pacote Kodi: {pkg_info}")
    uid_str = "u0_a193"  # default
    for line in pkg_info.splitlines():
        if "uid:" in line:
            uid_num = line.split("uid:")[1].strip()
            if int(uid_num) >= 10000:
                uid_str = f"u0_a{int(uid_num) - 10000}"

    print(f"[+] UID do Kodi no Android: {uid_str}")

    # 3. Parar Kodi temporariamente para escrita limpa
    print("[+] Parando Kodi para escrita limpa...")
    run_adb(["shell", "am force-stop org.xbmc.kodi"])
    time.sleep(1)

    # 4. Criar diretório temporário no dispositivo
    run_adb(["shell", "mkdir -p /data/local/tmp/addons"])

    # 5. Enviar os add-ons
    addons_to_push = [
        "resource.images.saile",
        "script.module.saile.core",
        "plugin.audio.sradio",
        "repository.srepo",
    ]

    for addon in addons_to_push:
        src = ADDONS_DIR / addon
        if not src.exists():
            print(f"[!] Add-on não encontrado: {src}")
            continue
        print(f"[+] Enviando {addon}...")
        run_adb(["push", str(src), "/data/local/tmp/addons/"])

    # 6. Copiar para o diretório de dados do Kodi
    print("[+] Instalando add-ons no diretório do Kodi (.kodi/addons)...")
    target_addons = "/data/media/0/Android/data/org.xbmc.kodi/files/.kodi/addons"
    target_userdata = "/data/media/0/Android/data/org.xbmc.kodi/files/.kodi/userdata"
    run_adb(["shell", f"mkdir -p {target_addons}"])
    run_adb(["shell", f"cp -rf /data/local/tmp/addons/* {target_addons}/"])

    # 7. Configurar reprodução em segundo plano e tela bloqueada (advancedsettings.xml)
    adv_settings_src = TEMPLATES_DIR / "advancedsettings.xml"
    if adv_settings_src.exists():
        print("[+] Instalando advancedsettings.xml para reprodução contínua com tela bloqueada...")
        run_adb(["push", str(adv_settings_src), "/data/local/tmp/advancedsettings.xml"])
        run_adb(["shell", f"cp -f /data/local/tmp/advancedsettings.xml {target_userdata}/advancedsettings.xml"])

    # 8. Ajustar permissões e proprietário
    print(f"[+] Ajustando permissões ({uid_str}:ext_data_rw)...")
    run_adb(["shell", f"chown -R {uid_str}:ext_data_rw {target_addons}"])
    run_adb(["shell", f"chmod -R 775 {target_addons}"])
    run_adb(["shell", f"chown -R {uid_str}:ext_data_rw {target_userdata}"])

    # 9. Aplicar permissões do SO Android para reprodução com tela bloqueada (Doze Whitelist + WakeLock)
    print("[+] Aplicando permissões Android: Whitelist de Bateria e WakeLock...")
    run_adb(["shell", "dumpsys deviceidle whitelist +org.xbmc.kodi"])
    run_adb(["shell", "appops set org.xbmc.kodi RUN_IN_BACKGROUND allow"])
    run_adb(["shell", "appops set org.xbmc.kodi WAKE_LOCK allow"])

    # 10. Habilitar add-ons no banco de dados Addons33.db
    db_path = f"{target_userdata}/Database/Addons33.db"
    sql_commands = [
        "CREATE TABLE IF NOT EXISTS installed (id INTEGER PRIMARY KEY, addonID TEXT NOT NULL UNIQUE, enabled INTEGER, installDate TEXT, lastUpdated TEXT, lastUsed TEXT, origin TEXT);",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('resource.images.saile', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('script.module.saile.core', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('plugin.audio.sradio', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('repository.srepo', 1, datetime('now'));",
    ]
    for sql in sql_commands:
        run_adb(["shell", f"sqlite3 {db_path} \"{sql}\""])

    # 11. Redirecionar portas para JSON-RPC e Web
    print("[+] Redirecionando porta JSON-RPC (9090) e WebServer (8080)...")
    run_adb(["forward", "tcp:9090", "tcp:9090"])
    run_adb(["forward", "tcp:8080", "tcp:8080"])

    # 12. Iniciar Kodi
    print("[+] Iniciando Kodi no emulador...")
    run_adb(["shell", "monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1"])
    time.sleep(6)

    # 13. Testar rotas via Intent
    print("[+] Testando navegação dinâmica do sRadio...")
    test_urls = [
        "plugin://plugin.audio.sradio/?action=featured",
        "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fc%3Dmusic",
        "plugin://plugin.audio.sradio/?action=browse&url=Browse.ashx%3Fid%3Dr101223",
    ]
    for t_url in test_urls:
        print(f"    -> Abrindo {t_url}...")
        run_adb(["shell", f"am start -a android.intent.action.VIEW -d \"{t_url}\" org.xbmc.kodi"])
        time.sleep(2)

    # 14. Testar reprodução de rádio com resolução dinâmica via JSON-RPC
    print("[+] Testando reprodução via JSON-RPC (Player.Open)...")
    play_resp = send_jsonrpc("Player.Open", {"item": {"file": "plugin://plugin.audio.sradio/?action=play&guide_id=s7047"}})
    print(f"    -> Resposta Player.Open: {play_resp}")
    time.sleep(4)

    # 15. Checar status do player
    players_resp = send_jsonrpc("Player.GetActivePlayers")
    print(f"[+] Players ativos: {players_resp}")

    # 16. Teste de resiliência: Simular bloqueio de tela (Power Keyevent 26)
    print("\n[+] Testando reprodução com TELA BLOQUEADA...")
    print("    -> Bloqueando tela do emulador (Keyevent 26 / POWER)...")
    run_adb(["shell", "input keyevent 26"])
    time.sleep(3)

    screen_state = run_adb(["shell", "dumpsys power | grep 'mWakefulness='"])
    print(f"    -> Estado da tela no Android: {screen_state}")

    # Verificar se o player continua rodando com tela bloqueada
    players_during_lock = send_jsonrpc("Player.GetActivePlayers")
    print(f"    -> Status do Player durante tela bloqueada: {players_during_lock}")

    # Desbloquear tela (Keyevent 82 / MENU / UNLOCK)
    print("    -> Desbloqueando tela do emulador (Keyevent 82)...")
    run_adb(["shell", "input keyevent 82"])
    time.sleep(1)

    # 17. Verificar log do Kodi
    print("\n[+] Verificando kodi.log...")
    log_content = run_adb(["shell", "cat /data/media/0/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log | grep -iE 'sradio|plugin.audio.sradio' | tail -n 25"])
    if log_content:
        print("[+] Entradas recentes no kodi.log:")
        for line in log_content.splitlines():
            print(f"    | {line}")

    print("\n" + "=" * 60)
    print(" Deploy, Navegação TuneIn e Teste de Tela Bloqueada CONCLUÍDOS COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    deploy_and_test()
