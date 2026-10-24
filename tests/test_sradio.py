from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRADIO_LIB = ROOT / "addons" / "plugin.audio.sradio" / "resources" / "lib"
sys.path.insert(0, str(SRADIO_LIB))

from sradio.catalog import RadioCatalog, TuneInAPI, normalize_text
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

    def test_search_station_fallback(self) -> None:
        with patch.object(TuneInAPI, "search", return_value=[]):
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

    def test_resolve_station_stream_fallback(self) -> None:
        with patch.object(TuneInAPI, "resolve_stream", return_value=None):
            all_stations = self.catalog.get_all()
            first_id = all_stations[0]["guide_id"]
            stream = self.catalog.resolve_station_stream(first_id)
            self.assertIsNotNone(stream)
            self.assertIn("url", stream)
            self.assertTrue(stream["url"].startswith("http"))


class TuneInAPITests(unittest.TestCase):
    def test_build_url_adds_partner_and_json(self) -> None:
        url = TuneInAPI._build_url("Browse.ashx", {"c": "music"})
        self.assertIn("render=json", url)
        self.assertIn("partnerId=xwhZkVKi", url)
        self.assertIn("c=music", url)

    def test_build_url_preserves_existing_url(self) -> None:
        orig = "http://opml.radiotime.com/Browse.ashx?c=local"
        built = TuneInAPI._build_url(orig)
        self.assertIn("render=json", built)
        self.assertIn("partnerId=xwhZkVKi", built)
        self.assertIn("c=local", built)

    def test_build_url_relative_with_query(self) -> None:
        built = TuneInAPI._build_url("Browse.ashx?c=music")
        self.assertEqual(built.count("?"), 1)
        self.assertIn("c=music", built)
        self.assertIn("render=json", built)
        self.assertIn("partnerId=xwhZkVKi", built)

    def test_parse_outlines_station_and_folder(self) -> None:
        raw_outlines = [
            {
                "element": "outline",
                "type": "audio",
                "text": "Antena 1 FM",
                "guide_id": "s1234",
                "URL": "http://opml.radiotime.com/Tune.ashx?id=s1234",
                "image": "http://logo.png",
                "bitrate": "128",
            },
            {
                "element": "outline",
                "type": "link",
                "text": "São Paulo",
                "URL": "http://opml.radiotime.com/Browse.ashx?id=r101223",
            },
            {
                "element": "outline",
                "text": "Shows Populares",
                "children": [
                    {
                        "element": "outline",
                        "type": "audio",
                        "text": "Jovem Pan News",
                        "guide_id": "s7047",
                        "bitrate": "128",
                    }
                ],
            },
        ]

        parsed = TuneInAPI._parse_outlines(raw_outlines)
        self.assertEqual(len(parsed), 3)

        # Item 1: Estação
        self.assertFalse(parsed[0]["is_folder"])
        self.assertEqual(parsed[0]["guide_id"], "s1234")
        self.assertEqual(parsed[0]["name"], "Antena 1 FM")

        # Item 2: Pasta
        self.assertTrue(parsed[1]["is_folder"])
        self.assertEqual(parsed[1]["title"], "São Paulo")

        # Item 3: Filho descompactado
        self.assertFalse(parsed[2]["is_folder"])
        self.assertEqual(parsed[2]["guide_id"], "s7047")
        self.assertEqual(parsed[2]["name"], "Jovem Pan News")

    def test_resolve_stream_selection(self) -> None:
        mock_payload = {
            "head": {"status": "200"},
            "body": [
                {"url": "http://stream1.mp3", "bitrate": 64, "reliability": 80, "media_type": "mp3"},
                {"url": "http://stream2.mp3", "bitrate": 128, "reliability": 100, "media_type": "mp3"},
            ],
        }
        with patch.object(TuneInAPI, "_fetch_json", return_value=mock_payload):
            resolved = TuneInAPI.resolve_stream("s1234")
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["url"], "http://stream2.mp3")
            self.assertEqual(resolved["bitrate"], 128)


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

    def test_request_browse_url(self) -> None:
        req = Request.from_argv(["plugin://plugin.audio.sradio/", "2", "?action=browse&url=Browse.ashx%3Fc%3Dmusic"])
        self.assertEqual(req.action, "browse")
        self.assertEqual(req.params.get("url"), "Browse.ashx?c=music")


if __name__ == "__main__":
    unittest.main()
