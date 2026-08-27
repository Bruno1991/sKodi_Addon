from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from stv.app.lan_sync import (
    ADDON_ID,
    PROTOCOL_VERSION,
    apply_import_payload,
    broadcast_lan_sync,
    build_export_payload,
)
from stv.app.services import AppContainer


class LanSyncTests(unittest.TestCase):
    def test_build_export_payload_sanitizes_secrets(self) -> None:
        app = AppContainer({
            "xtream_url": "http://secret-server.com:8080",
            "xtream_username": "my_secret_user",
            "xtream_password": "my_secret_password",
            "parental_pin": "1234",
            "profile_path": "",
        })
        mock_catalog = MagicMock()
        mock_catalog.get_favorite_ids.side_effect = lambda scope: ["101", "102"] if scope == "live" else ["201"] if scope == "vod" else ["301"]
        app._catalog_repo = mock_catalog

        payload = build_export_payload(app)

        self.assertEqual(payload["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(payload["addon_id"], ADDON_ID)
        self.assertTrue("device_id" in payload)
        self.assertEqual(len(payload["entities"]), 4)

        # Ensure no secret strings in dumped payload
        dumped = json.dumps(payload)
        self.assertNotIn("my_secret_user", dumped)
        self.assertNotIn("my_secret_password", dumped)
        self.assertNotIn("secret-server.com", dumped)
        self.assertNotIn("1234", dumped)

    def test_apply_import_payload_validates_and_applies(self) -> None:
        app = AppContainer({})
        mock_catalog = MagicMock()
        app._catalog_repo = mock_catalog

        valid_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "addon_id": ADDON_ID,
            "device_id": "other-device-uuid",
            "exported_at": "2026-08-27T12:00:00Z",
            "entities": [
                {"entity": "favorite", "scope": "live", "key": "555", "deleted": False},
                {"entity": "favorite", "scope": "vod", "key": "777", "deleted": False},
                {"entity": "favorite", "scope": "series", "key": "999", "deleted": False},
                {"entity": "favorite", "scope": "live", "key": "deleted-key", "deleted": True},
            ],
        }

        result = apply_import_payload(app, valid_payload)
        self.assertEqual(result["favorites_applied"], 3)
        mock_catalog.add_favorite.assert_any_call("live", "555")
        mock_catalog.add_favorite.assert_any_call("vod", "777")
        mock_catalog.add_favorite.assert_any_call("series", "999")

    def test_apply_import_payload_rejects_incompatible_version(self) -> None:
        app = AppContainer({})
        invalid_payload = {
            "protocol_version": 999,
            "addon_id": ADDON_ID,
            "entities": [],
        }
        with self.assertRaises(ValueError):
            apply_import_payload(app, invalid_payload)

    def test_apply_import_payload_rejects_incompatible_addon(self) -> None:
        app = AppContainer({})
        invalid_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "addon_id": "plugin.video.other",
            "entities": [],
        }
        with self.assertRaises(ValueError):
            apply_import_payload(app, invalid_payload)

    def test_broadcast_lan_sync_when_disabled(self) -> None:
        app = AppContainer({"lan_sync_enabled": "false"})
        res = broadcast_lan_sync(app)
        self.assertEqual(res["peers_found"], 0)
        self.assertEqual(res["favorites_synced"], 0)


if __name__ == "__main__":
    unittest.main()
