from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"


def dependencies(addon_id: str) -> set[str]:
    root = ET.parse(ADDONS / addon_id / "addon.xml").getroot()
    requires = root.find("requires")
    return {node.attrib["addon"] for node in requires.findall("import")} if requires is not None else set()


class DependencyGraphTests(unittest.TestCase):
    def test_plugins_use_shared_modules(self) -> None:
        expected = {
            "resource.images.saile",
            "script.module.saile.core",
            "script.module.saile.epg",
        }
        self.assertTrue(expected <= dependencies("plugin.video.stv"))

    def test_core_uses_shared_artwork(self) -> None:
        self.assertIn("resource.images.saile", dependencies("script.module.saile.core"))

    def test_epg_module_depends_on_core_but_not_stv(self) -> None:
        epg_dependencies = dependencies("script.module.saile.epg")
        self.assertIn("script.module.saile.core", epg_dependencies)
        self.assertNotIn("plugin.video.stv", epg_dependencies)


if __name__ == "__main__":
    unittest.main()
