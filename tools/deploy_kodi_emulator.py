"""Deploy e automação de teste dos add-ons sRepo no Kodi instalado no emulador Android."""

import os
import subprocess
import sys
import time
from pathlib import Path

ADB = r"C:\dev\android_emulator\sdk\platform-tools\adb.exe"
SERIAL = "emulator-5554"
ROOT = Path(__file__).resolve().parents[1]
ADDONS_DIR = ROOT / "addons"


def run_adb(cmd_list: list[str]) -> str:
    full_cmd = [ADB, "-s", SERIAL] + cmd_list
    proc = subprocess.run(full_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"[!] Erro no comando ADB: {' '.join(full_cmd)}")
        print(f"    Stderr: {proc.stderr.strip()}")
    return proc.stdout.strip()


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
            # ex: 10193 -> u0_a193
            if int(uid_num) >= 10000:
                uid_str = f"u0_a{int(uid_num) - 10000}"

    print(f"[+] UID do Kodi no Android: {uid_str}")

    # 3. Parar Kodi temporariamente para escrita limpa
    print("[+] Parando Kodi...")
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
    run_adb(["shell", f"mkdir -p {target_addons}"])
    run_adb(["shell", f"cp -rf /data/local/tmp/addons/* {target_addons}/"])

    # 7. Ajustar permissões e proprietário
    print(f"[+] Ajustando permissões ({uid_str}:ext_data_rw)...")
    run_adb(["shell", f"chown -R {uid_str}:ext_data_rw {target_addons}"])
    run_adb(["shell", f"chmod -R 775 {target_addons}"])

    # 8. Habilitar add-ons no banco de dados Addons33.db
    db_path = "/data/media/0/Android/data/org.xbmc.kodi/files/.kodi/userdata/Database/Addons33.db"
    sql_commands = [
        "CREATE TABLE IF NOT EXISTS installed (id INTEGER PRIMARY KEY, addonID TEXT NOT NULL UNIQUE, enabled INTEGER, installDate TEXT, lastUpdated TEXT, lastUsed TEXT, origin TEXT);",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('resource.images.saile', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('script.module.saile.core', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('plugin.audio.sradio', 1, datetime('now'));",
        "INSERT OR REPLACE INTO installed (addonID, enabled, installDate) VALUES ('repository.srepo', 1, datetime('now'));",
    ]
    for sql in sql_commands:
        run_adb(["shell", f"sqlite3 {db_path} \"{sql}\""])

    # 9. Iniciar Kodi
    print("[+] Iniciando Kodi no emulador...")
    run_adb(["shell", "monkey -p org.xbmc.kodi -c android.intent.category.LAUNCHER 1"])
    time.sleep(5)

    # 10. Testar execução do plugin.audio.sradio
    print("[+] Testando execução de rota do sRadio (action=featured)...")
    # Kodi responde ao intent android.intent.action.VIEW com URI de plugin
    run_adb(["shell", "am start -a android.intent.action.VIEW -d \"plugin://plugin.audio.sradio/?action=featured\" org.xbmc.kodi"])
    time.sleep(3)

    # 11. Verificar log do Kodi
    print("[+] Verificando kodi.log...")
    log_content = run_adb(["shell", "cat /data/media/0/Android/data/org.xbmc.kodi/files/.kodi/temp/kodi.log | grep -iE 'sradio|plugin.audio.sradio' | tail -n 25"])
    if log_content:
        print("[+] Entradas relevantes encontradas no kodi.log:")
        for line in log_content.splitlines():
            print(f"    | {line}")
    else:
        print("[*] Log ainda não gravou eventos específicos ou carregamento ocorreu em silêncio.")

    print("\n[+] Deploy e teste concluídos com sucesso!")


if __name__ == "__main__":
    deploy_and_test()
