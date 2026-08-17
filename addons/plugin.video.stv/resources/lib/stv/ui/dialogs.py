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


def show_sync_dialog(app: "AppContainer") -> None:
    """Exibe o menu modal de sincronização e gerenciamento de dados do sTv."""
    import xbmc
    import xbmcgui
    from saile_core.notifications import notify_error, notify_info, notify_success
    from stv.app.sync import sync_full_catalog

    options = [
        "🔄 Sincronizar Catálogo Completo (Xtream)",
        "📤 Exportar Favoritos e Progresso (Backup)",
        "📥 Importar Favoritos e Progresso (Restaurar)",
        "📡 Sincronização LAN (Status da Rede)",
        "🗑️ Limpar Catálogo e Cache Local",
    ]

    dialog = xbmcgui.Dialog()
    choice = dialog.select("sTv — Sincronizar Dados", options)

    if choice == 0:
        # Sincronizar Catálogo
        if sync_full_catalog(app):
            xbmc.executebuiltin("Container.Refresh")

    elif choice == 1:
        # Exportar Favoritos e Progresso
        profile_path = app.settings.get("profile_path", "")
        if not profile_path:
            notify_error("sTv", "Caminho do perfil não localizado")
            return

        export_data = {
            "version": 1,
            "addon": "plugin.video.stv",
            "favorites": {
                "live": [item.item_id for item in app.catalog.get_favorites("live")],
                "vod": [item.item_id for item in app.catalog.get_favorites("vod")],
                "series": [item.item_id for item in app.catalog.get_favorites("series")],
            },
        }
        export_file = os.path.join(profile_path, "stv_backup.json")
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            notify_success("sTv", f"Backup salvo em stv_backup.json")
        except Exception as exc:
            notify_error("sTv", f"Erro ao exportar: {exc}")

    elif choice == 2:
        # Importar Favoritos e Progresso
        profile_path = app.settings.get("profile_path", "")
        export_file = os.path.join(profile_path, "stv_backup.json")
        if not os.path.exists(export_file):
            dialog.ok("sTv — Importar Dados", "Nenhum arquivo stv_backup.json encontrado na pasta de perfil.")
            return

        try:
            with open(export_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            favs = data.get("favorites", {})
            count = 0
            for media_type, item_ids in favs.items():
                for item_id in item_ids:
                    app.catalog.toggle_favorite(media_type, item_id)
                    count += 1
            notify_success("sTv", f"{count} registros restaurados!")
            xbmc.executebuiltin("Container.Refresh")
        except Exception as exc:
            notify_error("sTv", f"Erro ao importar: {exc}")

    elif choice == 3:
        # Status da LAN
        local_ip = _get_local_ip()
        msg = (
            f"Endereço IP Local: {local_ip}\n\n"
            "A sincronização LAN do ecossistema SAILE é estritamente manual e local-first.\n\n"
            "Para sincronizar com outro dispositivo na mesma rede:\n"
            "1. Exporte o backup neste dispositivo.\n"
            "2. Copie o arquivo stv_backup.json para o segundo dispositivo.\n"
            "3. Use a opção 'Importar Favoritos' no segundo Kodi."
        )
        dialog.ok("sTv — Sincronização LAN", msg)

    elif choice == 4:
        # Limpar Cache
        confirm = dialog.yesno("sTv — Limpar Cache", "Deseja apagar todo o catálogo local e forçar novo download?")
        if confirm:
            try:
                with app.database.connect() as conn:
                    conn.execute("DELETE FROM categories")
                    conn.execute("DELETE FROM media_items")
                notify_success("sTv", "Catálogo local limpo com sucesso!")
                xbmc.executebuiltin("Container.Refresh")
            except Exception as exc:
                notify_error("sTv", f"Erro ao limpar banco: {exc}")
