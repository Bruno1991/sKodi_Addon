from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
import time

from saile_epg.database import EpgDatabase
from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.normalizer import (
    clean_channel_title,
    get_canonical_channel_name,
    normalize_channel_name,
)
from saile_epg.repository import EpgRepository


class EpgAliasesAndResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_epg.db"
        self.db = EpgDatabase(db_path)
        self.db.initialize()
        self.repo = EpgRepository(self.db)

        # Snapshot com canais oficiais da Claro
        channels = (
            EpgChannel("claro", "claro_124", "124", "Globo SP", "GLOBO SP", "http://logo/globo.png"),
            EpgChannel("claro", "claro_78", "78", "GloboNews", "GLOBONEWS", "http://logo/globonews.png"),
            EpgChannel("claro", "claro_184", "184", "SBT", "SBT", "http://logo/sbt.png"),
            EpgChannel("claro", "claro_317", "317", "Record", "RECORD", "http://logo/record.png"),
            EpgChannel("claro", "claro_174", "174", "Band", "BAND", "http://logo/band.png"),
            EpgChannel("claro", "claro_185", "185", "Rede TV!", "REDE TV", "http://logo/redetv.png"),
            EpgChannel("claro", "claro_30", "30", "SporTV", "SPORTV", "http://logo/sportv.png"),
            EpgChannel("claro", "claro_31", "31", "SporTV 2", "SPORTV 2", "http://logo/sportv2.png"),
            EpgChannel("claro", "claro_72", "72", "Telecine Pipoca", "TELECINE PIPOCA", "http://logo/pipoca.png"),
            EpgChannel("claro", "claro_68", "68", "Telecine Premium", "TELECINE PREMIUM", "http://logo/premium.png"),
            EpgChannel("claro", "claro_107", "107", "Premiere Clubes", "PREMIERE CLUBES", "http://logo/pfc1.png"),
            EpgChannel("claro", "claro_108", "108", "Premiere 2", "PREMIERE 2", "http://logo/pfc2.png"),
            EpgChannel("claro", "claro_2", "2", "Cartoon", "CARTOON", "http://logo/cartoon.png"),
            EpgChannel("claro", "claro_83", "83", "Warner Channel", "WARNER CHANNEL", "http://logo/warner.png"),
            EpgChannel("claro", "claro_82", "82", "Sony Channel", "SONY CHANNEL", "http://logo/sony.png"),
            EpgChannel("claro", "claro_1", "1", "Discovery Kids", "DISCOVERY KIDS", "http://logo/dkids.png"),
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
        self.assertEqual(get_canonical_channel_name("BR: GLOBOPLAY NOVELAS HD"), "GLOBOPLAY NOVELAS")
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

    def test_resolve_channel_with_various_iptv_names(self) -> None:
        # 1. Globo RJ / Minas -> matches Claro Globo SP
        ch_globo_rj = self.repo.resolve_channel("claro", "", "BR | GLOBO RJ HD")
        self.assertIsNotNone(ch_globo_rj)
        self.assertEqual(ch_globo_rj.channel_key, "claro_124")

        # 2. GloboNews -> matches Claro GloboNews (claro_78), not Globo SP (claro_124)
        ch_globonews = self.repo.resolve_channel("claro", "", "BR | GLOBO NEWS HD")
        self.assertIsNotNone(ch_globonews)
        self.assertEqual(ch_globonews.channel_key, "claro_78")

        ch_gnews = self.repo.resolve_channel("claro", "", "BR: GLOBONEWS FHD")
        self.assertIsNotNone(ch_gnews)
        self.assertEqual(ch_gnews.channel_key, "claro_78")

        # 3. TC Pipoca -> matches Telecine Pipoca
        ch_pipoca = self.repo.resolve_channel("claro", "", "BR: TC PIPOCA FHD")
        self.assertIsNotNone(ch_pipoca)
        self.assertEqual(ch_pipoca.channel_key, "claro_72")

        # 4. PFC 1 -> matches Premiere Clubes
        ch_pfc = self.repo.resolve_channel("claro", "", "BR: PFC 1 FHD")
        self.assertIsNotNone(ch_pfc)
        self.assertEqual(ch_pfc.channel_key, "claro_107")

        # 5. Cartoon Network -> matches Cartoon
        ch_cartoon = self.repo.resolve_channel("claro", "", "BR: CARTOON NETWORK")
        self.assertIsNotNone(ch_cartoon)
        self.assertEqual(ch_cartoon.channel_key, "claro_2")

        # 6. Warner -> matches Warner Channel
        ch_warner = self.repo.resolve_channel("claro", "", "BR: WARNER HD")
        self.assertIsNotNone(ch_warner)
        self.assertEqual(ch_warner.channel_key, "claro_83")

    def test_get_now_next_with_aliased_channel_names(self) -> None:
        now_prog, next_prog = self.repo.get_now_next("claro", "", "BR | GLOBO RJ FHD")
        self.assertIsNotNone(now_prog)
        self.assertEqual(now_prog.title, "Jornal Nacional")

        now_prog_news, _ = self.repo.get_now_next("claro", "", "BR | GLOBO NEWS HD")
        self.assertIsNotNone(now_prog_news)
        self.assertEqual(now_prog_news.title, "Estúdio i")

        now_prog_tc, _ = self.repo.get_now_next("claro", "", "BR: TC PIPOCA HD")
        self.assertIsNotNone(now_prog_tc)
        self.assertEqual(now_prog_tc.title, "Filme Incrível")


if __name__ == "__main__":
    unittest.main()
