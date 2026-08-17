from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"))

from stv.app.services import AppContainer
from stv.routing import Request as StvRequest


class RoutingTests(unittest.TestCase):
    def test_stv_request_parsing(self) -> None:
        request = StvRequest.from_argv(["plugin://plugin.video.stv/", "7", "?action=live&category_id=2"])
        self.assertEqual(request.handle, 7)
        self.assertEqual(request.action, "live")
        self.assertEqual(request.params.get("category_id"), "2")

    def test_stv_request_url_generation(self) -> None:
        request = StvRequest.from_argv(["plugin://plugin.video.stv/", "7", ""])
        generated = request.url(action="category", section="vod", category_id="10")
        self.assertIn("action=category", generated)
        self.assertIn("section=vod", generated)
        self.assertIn("category_id=10", generated)

    def test_stv_container_uses_xtream_url_setting(self) -> None:
        app = AppContainer(
            {
                "xtream_url": "https://example.com:8080",
                "xtream_username": "testuser",
                "xtream_password": "testpassword",
                "profile_path": ".",
            }
        )
        self.assertEqual(app.xtream.host, "https://example.com:8080")
        self.assertEqual(app.xtream.username, "testuser")


if __name__ == "__main__":
    unittest.main()
