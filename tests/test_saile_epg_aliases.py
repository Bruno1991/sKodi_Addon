from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.database import EpgDatabase
from saile_epg.errors import EpgSyncError
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import get_canonical_channel_name, normalize_channel_name
from saile_epg.providers.claro import CLARO_OFFICIAL_CHANNELS
from saile_epg.repository import EpgRepository
from saile_epg.service import EpgService


class EpgAliasesAndResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_epg.db"
        self.db = EpgDatabase(db_path)
        self.db.initialize()
        self.repo = EpgRepository(self.db)

        channels = tuple(
            EpgChannel(
                "claro",
                f"claro_{ch['id']}",
                str(ch["id"]),
                ch["name"],
                normalize_channel_name(ch["name"]),
                ch.get("logo", ""),
            )
            for ch in CLARO_OFFICIAL_CHANNELS
        )
        now = int(time.time())
        programs = (
            EpgProgram("claro", "claro_124", "Jornal Nacional", now - 300, now + 1800, "Notícias"),
            EpgProgram("claro", "claro_78", "Estúdio i", now - 300, now + 1800, "Notícias"),
            EpgProgram("claro", "claro_72", "Filme Incrível", now - 600, now + 3600, "Filme"),
            EpgProgram("claro", "claro_107", "Jogo Ao Vivo", now - 100, now + 5000, "Futebol"),
        )
        self.repo.replace_snapshot(EpgSnapshot("claro", channels, programs, now))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_canonical_channel_aliases(self) -> None:
        self.assertEqual(get_canonical_channel_name("BR | GLOBO RJ FHD"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("BR: GLOBO MINAS"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("BR | GLOBO NEWS HD"), "GLOBONEWS")
        self.assertEqual(get_canonical_channel_name("BR: GLOBONEWS FHD"), "GLOBONEWS")
        self.assertEqual(
            get_canonical_channel_name("BR: GLOBOPLAY NOVELAS HD"), "GLOBOPLAY NOVELAS"
        )
        self.assertEqual(get_canonical_channel_name("BR: TC PIPOCA 4K"), "TELECINE PIPOCA")
        self.assertEqual(get_canonical_channel_name("BR: TC PREMIUM HD"), "TELECINE PREMIUM")
        self.assertEqual(get_canonical_channel_name("BR: PFC CLUBES"), "PREMIERE CLUBES")
        self.assertEqual(get_canonical_channel_name("BR: PFC 1 HD"), "PREMIERE CLUBES")
        self.assertEqual(get_canonical_channel_name("BR: PFC 2 HD"), "PREMIERE 2")
        self.assertEqual(get_canonical_channel_name("BR: CARTOON NETWORK HD"), "CARTOON")
        self.assertEqual(get_canonical_channel_name("BR: WARNER"), "WARNER CHANNEL")
        self.assertEqual(get_canonical_channel_name("BR: SONY"), "SONY CHANNEL")
        self.assertEqual(get_canonical_channel_name("BR: REDETV SP"), "REDE TV")
        self.assertEqual(get_canonical_channel_name("RPC Curitiba"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("EPTV Campinas"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("RBS Caxias Do Sul"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("NSC Florianopolis"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("Tv Bahia"), "GLOBO SP")
        self.assertEqual(get_canonical_channel_name("SBT MG Tv Alterosa"), "SBT")
        self.assertEqual(get_canonical_channel_name("Rd Bahia Hd¹"), "RECORD")
        self.assertEqual(get_canonical_channel_name("Bd SP Hd¹"), "BAND")
        self.assertEqual(get_canonical_channel_name("SporTV 4k¹"), "SPORTV")
        self.assertEqual(get_canonical_channel_name("Ge-fast"), "GE TV")
        self.assertEqual(get_canonical_channel_name("Receitas Fast"), "SABOR ARTE")

    def test_resolve_channel_with_various_iptv_names_and_hd_targets(self) -> None:
        expected_matches = (
            ("BR | GLOBO RJ HD", "claro_124"),
            ("BR | GLOBO NEWS HD", "claro_78"),
            ("BR: GLOBONEWS FHD", "claro_78"),
            ("BR: TC PIPOCA FHD", "claro_72"),
            ("BR: PFC 1 FHD", "claro_107"),
            ("BR: CARTOON NETWORK", "claro_2"),
            ("BR: WARNER HD", "claro_83"),
            ("BR: CNN MONEY FHD", "claro_349"),
            ("BR: BMC NEWS HD", "claro_321"),
            ("BR: DAZN", "claro_329"),
            ("BR: UNIVERSAL PREMIER FHD", "claro_323"),
            ("BR: SBT NEWS", "claro_469"),
            ("BR: CANAL GOV", "claro_471"),
            ("BR: ADULT SWIM", "claro_322"),
            ("BR: DOG TV", "claro_268"),
        )
        for raw_name, expected_key in expected_matches:
            with self.subTest(raw_name=raw_name):
                resolved = self.repo.resolve_channel("claro", "", raw_name)
                self.assertIsNotNone(resolved)
                assert resolved is not None
                self.assertEqual(resolved.channel_key, expected_key)

    def test_get_now_next_with_aliased_channel_names(self) -> None:
        now_prog, _ = self.repo.get_now_next("claro", "", "BR | GLOBO RJ FHD")
        self.assertIsNotNone(now_prog)
        assert now_prog is not None
        self.assertEqual(now_prog.title, "Jornal Nacional")

        now_prog_news, _ = self.repo.get_now_next("claro", "", "BR | GLOBO NEWS HD")
        self.assertIsNotNone(now_prog_news)
        assert now_prog_news is not None
        self.assertEqual(now_prog_news.title, "Estúdio i")

        now_prog_tc, _ = self.repo.get_now_next("claro", "", "BR: TC PIPOCA HD")
        self.assertIsNotNone(now_prog_tc)
        assert now_prog_tc is not None
        self.assertEqual(now_prog_tc.title, "Filme Incrível")

    def test_sync_claro_network_failure_preserves_existing_cache(self) -> None:
        service = EpgService(Path(self.temp_dir.name) / "resilient_epg.db")
        now = int(time.time())
        service.repository.replace_snapshot(
            EpgSnapshot(
                "claro",
                (EpgChannel("claro", "claro_124", "124", "Globo SP", "GLOBO SP"),),
                (EpgProgram("claro", "claro_124", "Jornal", now - 60, now + 600),),
                now,
            )
        )
        with (
            patch(
                "saile_epg.service.ClaroEpgProvider.fetch",
                side_effect=EpgSyncError("EPG-CLARO-EMPTY", "Falha simulada de rede"),
            ),
            self.assertRaises(EpgSyncError),
        ):
            service.sync_claro(wipe_legacy=True)

        self.assertEqual(len(service.list_channels("claro")), 1)
        status = service.status("claro")
        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual(status["program_count"], 1)


if __name__ == "__main__":
    unittest.main()
