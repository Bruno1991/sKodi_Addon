from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRADIO_LIB = ROOT / "addons" / "plugin.audio.sradio" / "resources" / "lib"
sys.path.insert(0, str(SRADIO_LIB))

from sradio.catalog import RadioCatalog, normalize_text
from sradio.favorites import FavoritesManager
from sradio.routing import Request


class SRadioCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = RadioCatalog()

    def test_catalog_loads_stations(self) -> None:
        self.assertGreater(self.catalog.total_count, 1000)

    def test_normalize_text(self) -> None:
        self.assertEqual(normalize_text("Rádio São Paulo - 100.1 FM!"), "radio sao paulo - 100.1 fm!")

    def test_get_station_by_id(self) -> None:
        all_stations = self.catalog.get_all()
        self.assertTrue(len(all_stations) > 0)
        first_id = all_stations[0]["guide_id"]
        station = self.catalog.get_station(first_id)
        self.assertIsNotNone(station)
        self.assertEqual(station["guide_id"], first_id)
        self.assertTrue("direct_stream_url" in station)

    def test_search_station(self) -> None:
        results = self.catalog.search("FM")
        self.assertGreater(len(results), 0)

    def test_brazil_groups(self) -> None:
        groups = self.catalog.get_brazil_groups()
        self.assertIn("São Paulo", groups)
        self.assertGreater(len(groups["São Paulo"]), 0)

    def test_genre_groups(self) -> None:
        genres = self.catalog.get_genre_groups()
        self.assertIn("Rock", genres)
        self.assertGreater(len(genres["Rock"]), 0)

    def test_featured_stations(self) -> None:
        featured = self.catalog.get_featured()
        self.assertGreater(len(featured), 0)


class SRadioFavoritesTests(unittest.TestCase):
    def test_favorites_toggle(self) -> None:
        tmp_fav = ROOT / "scratch" / "test_fav.json"
        if tmp_fav.exists():
            tmp_fav.unlink()

        fav_mgr = FavoritesManager(file_path=tmp_fav)
        self.assertEqual(len(fav_mgr.get_all()), 0)

        mock_station = {"guide_id": "s9999", "name": "Rádio Teste FM", "direct_stream_url": "http://stream.mp3"}
        added = fav_mgr.toggle(mock_station)
        self.assertTrue(added)
        self.assertTrue(fav_mgr.is_favorite("s9999"))
        self.assertEqual(len(fav_mgr.get_all()), 1)

        removed = fav_mgr.toggle(mock_station)
        self.assertFalse(removed)
        self.assertFalse(fav_mgr.is_favorite("s9999"))
        self.assertEqual(len(fav_mgr.get_all()), 0)

        if tmp_fav.exists():
            tmp_fav.unlink()


class SRadioRoutingTests(unittest.TestCase):
    def test_request_from_argv(self) -> None:
        argv = ["plugin://plugin.audio.sradio/", "5", "?action=list_city&city=Campinas"]
        req = Request.from_argv(argv)
        self.assertEqual(req.base_url, "plugin://plugin.audio.sradio/")
        self.assertEqual(req.handle, 5)
        self.assertEqual(req.action, "list_city")
        self.assertEqual(req.params.get("city"), "Campinas")

    def test_request_url_builder(self) -> None:
        req = Request.from_argv(["plugin://plugin.audio.sradio/", "1", ""])
        url = req.url(action="play", guide_id="s123")
        self.assertIn("action=play", url)
        self.assertIn("guide_id=s123", url)


if __name__ == "__main__":
    unittest.main()
