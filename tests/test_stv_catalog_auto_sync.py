from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
for _lib in (
    ROOT / "addons" / "plugin.video.stv" / "resources" / "lib",
    ROOT / "addons" / "script.module.saile.epg" / "lib",
):
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))

from stv.app.services import AppContainer


class CatalogAutoSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        AppContainer._catalog_syncing.clear()

    def test_trigger_background_catalog_sync_when_not_configured(self) -> None:
        app = AppContainer({})
        # Xtream not configured
        self.assertFalse(app.trigger_background_catalog_sync_if_expired("live"))

    def test_trigger_background_catalog_sync_when_cache_valid(self) -> None:
        app = AppContainer(
            {"xtream_url": "http://server.com", "xtream_username": "u", "xtream_password": "p"}
        )
        mock_catalog = MagicMock()
        mock_catalog.get_categories.return_value = ["Cat1"]
        mock_catalog.is_cache_valid.return_value = True
        app._catalog_repo = mock_catalog

        self.assertFalse(app.trigger_background_catalog_sync_if_expired("live"))

    def test_trigger_background_catalog_sync_when_cache_stale(self) -> None:
        app = AppContainer(
            {
                "xtream_url": "http://server.com",
                "xtream_username": "u",
                "xtream_password": "p",
                "cache_ttl_hours": "12",
            }
        )
        mock_catalog = MagicMock()
        mock_catalog.get_categories.return_value = []
        mock_catalog.is_cache_valid.return_value = False
        app._catalog_repo = mock_catalog

        with patch("stv.app.sync.sync_section_catalog") as mock_sync:
            triggered = app.trigger_background_catalog_sync_if_expired("live")
            self.assertTrue(triggered)
            time.sleep(0.1)
            mock_sync.assert_called_once_with(app, "live")

    def test_trigger_background_catalog_sync_all_sections_from_home(self) -> None:
        app = AppContainer(
            {"xtream_url": "http://server.com", "xtream_username": "u", "xtream_password": "p"}
        )
        mock_catalog = MagicMock()
        mock_catalog.get_categories.return_value = []
        mock_catalog.is_cache_valid.return_value = False
        app._catalog_repo = mock_catalog

        with patch("stv.app.sync.sync_section_catalog") as mock_sync:
            triggered = app.trigger_background_catalog_sync_if_expired()
            self.assertTrue(triggered)
            time.sleep(0.15)
            self.assertEqual(mock_sync.call_count, 3)


if __name__ == "__main__":
    unittest.main()
