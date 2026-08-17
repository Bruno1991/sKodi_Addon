from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.providers.xtream.client import XtreamClient


class XtreamClientTests(unittest.TestCase):
    def test_host_normalization(self) -> None:
        client = XtreamClient(host="http://server.com:8080/", username="user", password="pwd")
        self.assertEqual(client.host, "http://server.com:8080")

        client2 = XtreamClient(host="server.com:8080", username="user", password="pwd")
        self.assertEqual(client2.host, "http://server.com:8080")

        with self.assertRaises(ValueError):
            XtreamClient(host="", username="user", password="pwd")

    def test_stream_url_generation(self) -> None:
        client = XtreamClient(host="http://iptv.example:8080", username="alice", password="secretpassword")

        # Live stream URL default ts
        live_url = client.stream_url("live", "101")
        self.assertEqual(live_url, "http://iptv.example:8080/live/alice/secretpassword/101.ts")

        # VOD stream URL with custom extension
        vod_url = client.stream_url("vod", "202", extension="mkv")
        self.assertEqual(vod_url, "http://iptv.example:8080/movie/alice/secretpassword/202.mkv")

        # Series stream URL default mp4
        series_url = client.stream_url("series", "303")
        self.assertEqual(series_url, "http://iptv.example:8080/series/alice/secretpassword/303.mp4")


if __name__ == "__main__":
    unittest.main()
