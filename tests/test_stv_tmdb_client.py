from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.providers.tmdb.client import TmdbClient


class TmdbClientTests(unittest.TestCase):
    def test_client_initialization_with_default_key(self) -> None:
        client = TmdbClient()
        self.assertEqual(client.api_key, TmdbClient.DEFAULT_API_KEY)
        self.assertEqual(client.language, "pt-BR")

    def test_image_url_formatting(self) -> None:
        url = TmdbClient.format_fanart_url("/backdrop123.jpg", None)
        self.assertEqual(url, "https://image.tmdb.org/t/p/w1280/backdrop123.jpg")

        url_poster = TmdbClient.format_fanart_url(None, "/poster123.jpg")
        self.assertEqual(url_poster, "https://image.tmdb.org/t/p/w500/poster123.jpg")

        url_none = TmdbClient.format_fanart_url(None, None)
        self.assertEqual(url_none, "")


if __name__ == "__main__":
    unittest.main()
