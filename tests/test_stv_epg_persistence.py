from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.domain.models import EpgProgram
from stv.persistence.database import Database
from stv.persistence.repository import CatalogRepository


class EpgPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.db")
        self.db.initialize()
        self.repo = CatalogRepository(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_epg_upsert_and_now_next_retrieval(self) -> None:
        ref_time = datetime(2026, 8, 18, 20, 45)
        
        programs = [
            EpgProgram(
                channel_key="GLOBO",
                title="Jornal Nacional",
                start_time="2026-08-18 20:30",
                end_time="2026-08-18 21:20",
                synopsis="Notícias do dia",
                duration_minutes=50,
            ),
            EpgProgram(
                channel_key="GLOBO",
                title="Novela das Nove",
                start_time="2026-08-18 21:20",
                end_time="2026-08-18 22:25",
                synopsis="Capítulo emocionante",
                duration_minutes=65,
            ),
        ]
        self.repo.upsert_epg_programs(programs)

        now_prog, next_prog = self.repo.get_current_and_next_program("GLOBO", ref_time=ref_time)
        
        self.assertIsNotNone(now_prog)
        assert now_prog is not None
        self.assertEqual(now_prog.title, "Jornal Nacional")
        self.assertEqual(now_prog.start_time, "2026-08-18 20:30")
        self.assertEqual(now_prog.end_time, "2026-08-18 21:20")

        self.assertIsNotNone(next_prog)
        assert next_prog is not None
        self.assertEqual(next_prog.title, "Novela das Nove")
        self.assertEqual(next_prog.start_time, "2026-08-18 21:20")

    def test_epg_cache_validity_ttl(self) -> None:
        self.assertFalse(self.repo.is_epg_cache_valid("SPORTV", ttl_hours=4))

        program = EpgProgram(
            channel_key="SPORTV",
            title="Tá na Área",
            start_time="2026-08-18 17:00",
            end_time="2026-08-18 19:00",
        )
        self.repo.upsert_epg_programs([program])

        self.assertTrue(self.repo.is_epg_cache_valid("SPORTV", ttl_hours=4))

        # Simula expiração alterando updated_at no banco
        with self.db.connect() as conn:
            conn.execute("UPDATE epg_programs SET updated_at = datetime('now', '-5 hours') WHERE channel_key = 'SPORTV'")

        self.assertFalse(self.repo.is_epg_cache_valid("SPORTV", ttl_hours=4))
        self.assertTrue(self.repo.is_epg_cache_valid("SPORTV", ttl_hours=6))

    def test_clean_expired_epg(self) -> None:
        old_prog = EpgProgram(
            channel_key="BAND",
            title="Programa Antigo",
            start_time="2026-08-10 10:00",
            end_time="2026-08-10 11:00",
        )
        future_prog = EpgProgram(
            channel_key="BAND",
            title="Programa Futuro",
            start_time="2026-08-25 10:00",
            end_time="2026-08-25 11:00",
        )
        self.repo.upsert_epg_programs([old_prog, future_prog])

        deleted = self.repo.clean_expired_epg(before_iso="2026-08-15 00:00")
        self.assertEqual(deleted, 1)

        with self.db.connect() as conn:
            remaining = conn.execute("SELECT COUNT(*) as total FROM epg_programs WHERE channel_key = 'BAND'").fetchone()
            self.assertEqual(remaining["total"], 1)


if __name__ == "__main__":
    unittest.main()
