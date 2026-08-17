from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.infrastructure.http import HttpClient


class HttpClientTests(unittest.TestCase):
    def test_http_client_initialization(self) -> None:
        client = HttpClient(timeout=20.0)
        self.assertEqual(client.timeout, 20.0)
        self.assertIn("IPTVSmartersPro", client.user_agent)
        self.assertIsNotNone(client._ssl_context)


if __name__ == "__main__":
    unittest.main()
