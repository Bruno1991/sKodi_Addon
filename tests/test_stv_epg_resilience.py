from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from saile_epg.models import EpgChannel, EpgProgram
from stv.app.services import AppContainer
from stv.domain.models import MediaItem


class EpgResilienceTests(unittest.TestCase):
    def setUp(self) -> None:
        AppContainer._epg_syncing = False

    def test_is_epg_cache_valid_when_empty_or_stale(self) -> None:
        app = AppContainer({"epg_enabled": "true", "epg_ttl_hours": "6"})
        mock_epg = SimpleNamespace(status=lambda _provider: None)
        app._epg_service = mock_epg

        self.assertFalse(app.is_epg_cache_valid())

        # Test stale sync (e.g. 7 hours ago with 6h TTL)
        now = int(time.time())
        mock_epg.status = lambda _provider: {"synced_at_utc": now - (7 * 3600)}
        self.assertFalse(app.is_epg_cache_valid())

        # Test fresh sync (e.g. 2 hours ago with 6h TTL)
        mock_epg.status = lambda _provider: {"synced_at_utc": now - (2 * 3600)}
        self.assertTrue(app.is_epg_cache_valid())

    def test_trigger_background_epg_sync_respects_settings_and_lock(self) -> None:
        # Disabled EPG
        app_disabled = AppContainer({"epg_enabled": "false"})
        self.assertFalse(app_disabled.trigger_background_epg_sync_if_expired())

        # Valid cache does not trigger
        app = AppContainer({"epg_enabled": "true", "epg_ttl_hours": "6"})
        app.is_epg_cache_valid = lambda ttl_hours=None: True
        self.assertFalse(app.trigger_background_epg_sync_if_expired())

        # Expired cache triggers thread
        app.is_epg_cache_valid = lambda ttl_hours=None: False
        with patch.object(app, "sync_epg") as mock_sync:
            triggered = app.trigger_background_epg_sync_if_expired()
            self.assertTrue(triggered)
            # Give thread moment to run
            time.sleep(0.1)
            mock_sync.assert_called_once_with(refresh_live_catalog=False)

    def test_get_items_epg_schedule_batch_resolution(self) -> None:
        app = AppContainer({"epg_enabled": "true"})
        mock_epg = MagicMock()
        mock_epg.resolve_channel.side_effect = lambda epg_id, name: (
            EpgChannel("claro", "globo-sp", "globo_sp", "Globo SP", "GLOBO SP")
            if "GLOBO" in name.upper()
            else (
                EpgChannel("claro", "sbt-sp", "sbt_sp", "SBT SP", "SBT SP")
                if "SBT" in name.upper()
                else None
            )
        )

        now_prog = EpgProgram("globo-sp", "globo", "Jornal", "", 100, 200)
        next_prog = EpgProgram("globo-sp", "globo", "Novela", "", 200, 300)

        mock_epg.get_now_next_many.return_value = {
            "globo-sp": (now_prog, next_prog),
            "sbt-sp": (None, None),
        }
        app._epg_service = mock_epg

        items = [
            MediaItem("live", "101", "Globo SP HD", "1", epg_id="globo"),
            MediaItem("live", "102", "SBT HD", "1", epg_id="sbt"),
            MediaItem("live", "103", "Canal Desconhecido", "1", epg_id=""),
        ]

        schedule = app.get_items_epg_schedule(items)

        mock_epg.get_now_next_many.assert_called_once()
        self.assertEqual(schedule["101"], (now_prog, next_prog))
        self.assertEqual(schedule["102"], (None, None))
        self.assertNotIn("103", schedule)


if __name__ == "__main__":
    unittest.main()
