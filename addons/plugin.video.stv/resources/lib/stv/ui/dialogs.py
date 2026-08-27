"""Diálogos e menus interativos de sincronização LAN e gerenciamento de estado."""
from __future__ import annotations

import json
import os
import socket
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stv.app.services import AppContainer


def _get_local_ip() -> str:
    """Detecta o IP local do dispositivo na rede interna."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _exception_fingerprint(exc: Exception) -> str:
    """Gera rastreio útil sem mensagem, URL, credencial ou caminho pessoal."""
    frames: list[str] = []
    traceback = exc.__traceback__
    while traceback is not None:
        filename = os.path.basename(traceback.tb_frame.f_code.co_filename)
        frames.append(f"{filename}:{traceback.tb_lineno}")
        traceback = traceback.tb_next
    return " > ".join(frames[-8:]) or "sem-rastreio"


def show_sync_dialog(app: "AppContainer") -> None:
    """Exibe o menu modal de sincronização e gerenciamento de dados do sTv."""
    import xbmc
    import xbmcgui
    from saile_core.notifications import notify_error, notify_info, notify_success
    from stv.app.sync import sync_full_catalog
    from stv.app.lan_sync import broadcast_lan_sync, build_export_payload, apply_import_payload

    options = [
        "Sincronizar Tudo (Catálogo + EPG)",
        "Sincronizar Catálogo Completo (Xtream)",
        "Sincronizar Guia de Programação (EPG)",
        "Sincronização LAN (Buscar Dispositivos na Rede)",
        "Exportar Backup (Salvar Arquivo)",
        "Importar Backup (Restaurar Arquivo)",
        "Limpar Catálogo e Cache Local",
    ]

    dialog = xbmcgui.Dialog()
    choice = dialog.select("sTv — Sincronizar Dados", options)

    if choice == 0:
        # Sincronizar Tudo (Catálogo + EPG)
        if not app.xtream.is_configured:
            notify_error("sTv", "Configure os dados do Xtream nas configurações")
            return
        progress = xbmcgui.DialogProgress()
        progress.create("sTv", "Sincronizando Catálogo e EPG...")
        try:
            progress.update(20, "Baixando catálogo Xtream...")
            sync_full_catalog(app)
            progress.update(70, "Baixando guia de programação (EPG)...")
            result = app.sync_epg(refresh_live_catalog=True)
            progress.update(100, "Sincronização concluída!")
            notify_success("sTv", f"Tudo atualizado! {result.get('program_count', 0)} programas no guia.")
            xbmc.executebuiltin("Container.Refresh")
        except Exception as exc:
            notify_error("sTv", f"Falha na sincronização: {exc}")
        finally:
            progress.close()

    elif choice == 1:
        # Sincronizar Catálogo
        if sync_full_catalog(app):
            xbmc.executebuiltin("Container.Refresh")

    elif choice == 2:
        if not app.xtream.is_configured:
            notify_error("sTv", "Configure os dados do Xtream antes de sincronizar o EPG")
            return
        progress = xbmcgui.DialogProgress()
        progress.create("sTv", "Sincronizando guia oficial Claro TV+...")
        try:
            progress.update(10, "Atualizando grade e horários...")
            result = app.sync_epg(refresh_live_catalog=True)
            progress.update(100, "EPG atualizado")
            message = (
                f"EPG ({result.get('source', 'local')}): "
                f"{result['channel_count']} canais e {result['program_count']} programas"
            )
            if result.get("program_count"):
                notify_success("sTv", message)
            else:
                notify_info("sTv", f"{message}. O provedor não enviou horários.")
            xbmc.executebuiltin("Container.Refresh")
        except Exception as exc:
            from saile_epg import EpgSyncError

            error_code = getattr(exc, "code", "EPG-UNEXPECTED")
            xbmc.log(
                f"[sTv][EPG] {type(exc).__name__} {error_code} "
                f"({_exception_fingerprint(exc)})",
                xbmc.LOGERROR,
            )
            if isinstance(exc, EpgSyncError):
                message = str(exc)
            else:
                message = f"Falha interna ao processar o guia [{error_code}]"
            notify_error("sTv", message)
        finally:
            progress.close()

    elif choice == 3:
        # Sincronização em LAN
        progress = xbmcgui.DialogProgress()
        progress.create("sTv", "Buscando outros aparelhos Kodi na rede local...")
        try:
            progress.update(30, "Enviando broadcast UDP na LAN...")
            res = broadcast_lan_sync(app, timeout=2.0)
            progress.update(100, "Sincronização LAN concluída!")
            peers = res.get("peers_found", 0)
            favs = res.get("favorites_synced", 0)
            if peers > 0:
                notify_success("sTv", f"LAN: {peers} dispositivo(s) encontrado(s), {favs} favoritos mesclados!")
                xbmc.executebuiltin("Container.Refresh")
            else:
                local_ip = _get_local_ip()
                dialog.ok(
                    "sTv — Sincronização LAN",
                    f"Nenhum outro aparelho sTv foi detectado nesta busca.\n\n"
                    f"Seu IP Local: {local_ip}\n"
                    f"Certifique-se de que o outro dispositivo Kodi esteja ligado na mesma rede Wi-Fi/LAN com o sTv aberto."
                )
        except Exception as exc:
            notify_error("sTv", f"Erro na sincronização LAN: {exc}")
        finally:
            progress.close()

    elif choice == 4:
        # Exportar backup
        profile_path = app.settings.get("profile_path", "")
        if not profile_path:
            notify_error("sTv", "Caminho do perfil não localizado")
            return

        export_data = build_export_payload(app)
        export_file = os.path.join(profile_path, "stv_backup.json")
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            notify_success("sTv", "Backup salvo em stv_backup.json")
        except Exception as exc:
            notify_error("sTv", f"Erro ao exportar: {exc}")

    elif choice == 5:
        # Importar backup
        profile_path = app.settings.get("profile_path", "")
        export_file = os.path.join(profile_path, "stv_backup.json")
        if not os.path.exists(export_file):
            dialog.ok("sTv — Importar Dados", "Nenhum arquivo stv_backup.json encontrado na pasta de perfil.")
            return

        try:
            with open(export_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            res = apply_import_payload(app, data)
            count = res.get("favorites_applied", 0)
            notify_success("sTv", f"{count} favoritos restaurados com sucesso!")
            xbmc.executebuiltin("Container.Refresh")
        except Exception as exc:
            notify_error("sTv", f"Erro ao importar: {exc}")

    elif choice == 6:
        # Limpar Cache
        confirm = dialog.yesno("sTv — Limpar Cache", "Deseja apagar todo o catálogo local e forçar novo download?")
        if confirm:
            try:
                with app.database.connect() as conn:
                    conn.execute("DELETE FROM categories")
                    conn.execute("DELETE FROM media_items")
                    conn.execute("DELETE FROM catalog_sync_state")
                app.epg.clear()
                notify_success("sTv", "Catálogo local limpo com sucesso!")
                xbmc.executebuiltin("Container.Refresh")
            except Exception as exc:
                notify_error("sTv", f"Erro ao limpar banco: {exc}")
