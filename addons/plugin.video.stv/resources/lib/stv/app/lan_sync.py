"""Sincronização local em LAN (Zero-Config UDP Peer-to-Peer) entre dispositivos Kodi."""
from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stv.app.services import AppContainer

DEFAULT_LAN_PORT = 54242
PROTOCOL_VERSION = 1
ADDON_ID = "plugin.video.stv"

_listener_thread: threading.Thread | None = None
_listener_running: bool = False
_lan_sync_lock: threading.Lock = threading.Lock()
_lan_syncing: bool = False


def _get_device_id(profile_path: str = "") -> str:
    """Retorna ou cria um UUID único e persistente para identificar este dispositivo na LAN."""
    if profile_path and os.path.exists(profile_path):
        id_file = os.path.join(profile_path, "stv_device_id.txt")
        try:
            if os.path.exists(id_file):
                with open(id_file, "r", encoding="utf-8") as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
            new_id = str(uuid.uuid4())
            with open(id_file, "w", encoding="utf-8") as f:
                f.write(new_id)
            return new_id
        except Exception:
            pass
    try:
        return socket.gethostname() or str(uuid.uuid4())
    except Exception:
        return str(uuid.uuid4())


def build_export_payload(app: "AppContainer") -> dict[str, Any]:
    """Gera payload sanitizado de favoritos e estado de acordo com LAN_SYNC_CONTRACT.md."""
    profile_path = app.settings.get("profile_path", "")
    device_id = _get_device_id(profile_path)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    entities = []
    for scope in ("live", "vod", "series"):
        fav_ids = app.catalog.get_favorite_ids(scope)
        for fav_id in fav_ids:
            entities.append(
                {
                    "entity": "favorite",
                    "scope": scope,
                    "key": str(fav_id),
                    "updated_at": now_iso,
                    "deleted": False,
                    "payload": {},
                }
            )

    return {
        "protocol_version": PROTOCOL_VERSION,
        "addon_id": ADDON_ID,
        "device_id": device_id,
        "exported_at": now_iso,
        "entities": entities,
    }


def apply_import_payload(app: "AppContainer", payload: dict[str, Any]) -> dict[str, int]:
    """Aplica e mescla os dados sanitizados recebidos de outro dispositivo via LAN."""
    if not isinstance(payload, dict):
        raise ValueError("Payload de sincronização inválido")

    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError(f"Versão de protocolo incompatível: {payload.get('protocol_version')}")

    if payload.get("addon_id") != ADDON_ID:
        raise ValueError(f"Addon incompatível: {payload.get('addon_id')}")

    entities = payload.get("entities", [])
    if not isinstance(entities, list):
        return {"favorites_applied": 0}

    applied_count = 0
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_type = entity.get("entity")
        scope = entity.get("scope")
        key = entity.get("key")
        deleted = bool(entity.get("deleted", False))

        if entity_type == "favorite" and scope in {"live", "vod", "series"} and key and not deleted:
            try:
                app.catalog.add_favorite(scope, str(key))
                applied_count += 1
            except Exception:
                pass

    return {"favorites_applied": applied_count}


def start_lan_listener_if_needed(app: "AppContainer", port: int = DEFAULT_LAN_PORT) -> None:
    """Inicia socket listener UDP em background daemon thread para responder a outros dispositivos sTv."""
    global _listener_thread, _listener_running

    if app.settings.get("lan_sync_enabled", "true").lower() == "false":
        return

    if _listener_running and _listener_thread and _listener_thread.is_alive():
        return

    _listener_running = True

    def _listen() -> None:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
            except Exception:
                sock.bind(("0.0.0.0", port))
            sock.settimeout(2.0)

            while _listener_running:
                try:
                    data, addr = sock.recvfrom(65535)
                    msg = json.loads(data.decode("utf-8"))
                    profile_path = app.settings.get("profile_path", "")
                    my_device_id = _get_device_id(profile_path)

                    if msg.get("addon_id") != ADDON_ID:
                        continue
                    if msg.get("device_id") == my_device_id:
                        continue

                    msg_type = msg.get("type")
                    if msg_type == "DISCOVER":
                        # Responde enviando nosso payload para o endereço que chamou
                        export_data = build_export_payload(app)
                        response = {
                            "type": "SYNC_DATA",
                            "protocol_version": PROTOCOL_VERSION,
                            "addon_id": ADDON_ID,
                            "device_id": my_device_id,
                            "data": export_data,
                        }
                        resp_bytes = json.dumps(response).encode("utf-8")
                        sock.sendto(resp_bytes, addr)

                    elif msg_type == "SYNC_DATA":
                        # Mescla dados recebidos
                        if "data" in msg:
                            apply_import_payload(app, msg["data"])

                except (socket.timeout, BlockingIOError):
                    continue
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    _listener_thread = threading.Thread(target=_listen, daemon=True, name="sTv-LanListener")
    _listener_thread.start()


def broadcast_lan_sync(app: "AppContainer", port: int = DEFAULT_LAN_PORT, timeout: float = 1.5) -> dict[str, int]:
    """Envia broadcast na LAN, troca dados com outros dispositivos sTv e mescla favoritos."""
    if app.settings.get("lan_sync_enabled", "true").lower() == "false":
        return {"peers_found": 0, "favorites_synced": 0}

    # Garante que o listener local também esteja ativo
    start_lan_listener_if_needed(app, port)

    profile_path = app.settings.get("profile_path", "")
    my_device_id = _get_device_id(profile_path)
    export_data = build_export_payload(app)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    peers_found = set()
    total_applied = 0

    try:
        # Envia broadcast com nossos dados
        broadcast_msg = {
            "type": "SYNC_DATA",
            "protocol_version": PROTOCOL_VERSION,
            "addon_id": ADDON_ID,
            "device_id": my_device_id,
            "data": export_data,
        }
        raw_msg = json.dumps(broadcast_msg).encode("utf-8")
        sock.sendto(raw_msg, ("255.255.255.255", port))

        # Também envia pacote de DISCOVER para forçar resposta de nós silenciosos
        discover_msg = {
            "type": "DISCOVER",
            "protocol_version": PROTOCOL_VERSION,
            "addon_id": ADDON_ID,
            "device_id": my_device_id,
        }
        sock.sendto(json.dumps(discover_msg).encode("utf-8"), ("255.255.255.255", port))

        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                data, addr = sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8"))
                peer_id = msg.get("device_id")
                if not peer_id or peer_id == my_device_id or msg.get("addon_id") != ADDON_ID:
                    continue

                peers_found.add(peer_id)
                if msg.get("type") == "SYNC_DATA" and "data" in msg:
                    res = apply_import_payload(app, msg["data"])
                    total_applied += res.get("favorites_applied", 0)
            except (socket.timeout, BlockingIOError):
                break
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try:
            sock.close()
        except Exception:
            pass

    return {
        "peers_found": len(peers_found),
        "favorites_synced": total_applied,
    }


def trigger_background_lan_sync(app: "AppContainer") -> bool:
    """Dispara a sincronização LAN silenciosamente em background thread."""
    global _lan_syncing

    if app.settings.get("lan_sync_enabled", "true").lower() == "false":
        return False
    if app.settings.get("lan_sync_auto", "true").lower() == "false":
        return False

    with _lan_sync_lock:
        if _lan_syncing:
            return False
        _lan_syncing = True

    def _worker() -> None:
        global _lan_syncing
        try:
            broadcast_lan_sync(app)
        except Exception:
            pass
        finally:
            with _lan_sync_lock:
                _lan_syncing = False

    thread = threading.Thread(target=_worker, daemon=True, name="sTv-LanAutoSync")
    thread.start()
    return True
