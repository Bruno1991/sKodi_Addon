from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"))

from stv.navigation_contract import HOME_ENTRIES as STV_HOME, SECTION_FIXED_ENTRIES, VALID_SECTIONS


class NavigationContractTests(unittest.TestCase):
    def test_stv_home_order(self) -> None:
        self.assertEqual([item[0] for item in STV_HOME], ["TV ao Vivo", "VOD", "Séries", "Sincronizar Dados"])

    def test_stv_section_fixed_order(self) -> None:
        self.assertEqual([item[0] for item in SECTION_FIXED_ENTRIES], ["Buscar", "Favoritos"])

    def test_stv_valid_sections(self) -> None:
        self.assertEqual(VALID_SECTIONS, frozenset({"live", "vod", "series"}))


if __name__ == "__main__":
    unittest.main()
