from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.database import EpgDatabase
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.repository import EpgRepository


class EpgPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = EpgDatabase(Path(self.temp_dir.name) / "epg.db")
        database.initialize()
        self.repository = EpgRepository(database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _snapshot(self) -> EpgSnapshot:
        return EpgSnapshot(
            provider_id="xtream",
            fetched_at_utc=1_000,
            channels=(
                EpgChannel("xtream", "globo.sp.br", "globo.sp.br", "Globo SP", "GLOBO SP"),
            ),
            programs=(
                EpgProgram("xtream", "globo.sp.br", "Jornal", 900, 1_100, "Notícias"),
                EpgProgram("xtream", "globo.sp.br", "Novela", 1_100, 1_300),
            ),
        )

    def test_exact_epg_id_resolves_now_and_next(self) -> None:
        self.repository.replace_snapshot(self._snapshot())
        current, next_program = self.repository.get_now_next(
            "xtream", "globo.sp.br", "Nome diferente", at_utc=1_000
        )
        self.assertIsNotNone(current)
        self.assertIsNotNone(next_program)
        self.assertEqual(current.title, "Jornal")
        self.assertEqual(next_program.title, "Novela")

    def test_normalized_name_is_safe_fallback(self) -> None:
        self.repository.replace_snapshot(self._snapshot())
        current, _next = self.repository.get_now_next(
            "xtream", "", "BR | GLOBO SP FHD", at_utc=1_000
        )
        self.assertIsNotNone(current)
        self.assertEqual(current.title, "Jornal")

        channels = self.repository.list_channels("xtream")
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].display_name, "Globo SP")
        resolved = self.repository.resolve_channel("xtream", "", "BR | GLOBO SP FHD")
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved.channel_key, "globo.sp.br")

    def test_empty_snapshot_preserves_previous_cache(self) -> None:
        self.repository.replace_snapshot(self._snapshot())
        with self.assertRaises(ValueError):
            self.repository.replace_snapshot(EpgSnapshot("xtream", (), (), 2_000))
        status = self.repository.sync_status("xtream")
        self.assertIsNotNone(status)
        self.assertEqual(status["program_count"], 2)


if __name__ == "__main__":
    unittest.main()
