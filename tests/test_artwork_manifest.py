from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArtworkManifestTests(unittest.TestCase):
    def test_shared_fixed_assets_exist(self) -> None:
        data = json.loads((ROOT / "artwork" / "artwork-manifest.json").read_text(encoding="utf-8"))
        shared = [item for item in data["assets"] if item.get("role") == "shared_ui_asset"]
        self.assertEqual(len(shared), 9)
        for item in shared:
            self.assertTrue((ROOT / item["source"]).is_file(), item["source"])
            self.assertTrue((ROOT / item["destination"]).is_file(), item["destination"])


if __name__ == "__main__":
    unittest.main()
