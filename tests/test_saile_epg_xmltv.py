from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.providers.xmltv import XmltvProvider, parse_xmltv_timestamp


class XmltvProviderTests(unittest.TestCase):
    def test_timestamp_is_normalized_to_utc(self) -> None:
        actual = parse_xmltv_timestamp("20260818100000 -0300")
        expected = int(datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(actual, expected)

    def test_parse_channels_and_programs_in_window(self) -> None:
        xmltv = b"""<?xml version="1.0" encoding="UTF-8"?>
        <tv>
          <channel id="globo.sp.br">
            <display-name>Globo SP</display-name>
            <icon src="https://img.example/globo.png" />
          </channel>
          <programme start="20260818100000 -0300" stop="20260818120000 -0300" channel="globo.sp.br">
            <title>Encontro</title>
            <desc>Programa de variedades.</desc>
            <category>Variedades</category>
          </programme>
        </tv>"""
        fetched_at = int(datetime(2026, 8, 18, 13, 30, tzinfo=timezone.utc).timestamp())
        snapshot = XmltvProvider("https://example/xmltv.php").parse(
            BytesIO(xmltv),
            fetched_at_utc=fetched_at,
        )

        self.assertEqual(snapshot.provider_id, "xtream")
        self.assertEqual(len(snapshot.channels), 1)
        self.assertEqual(snapshot.channels[0].epg_id, "globo.sp.br")
        self.assertEqual(snapshot.channels[0].normalized_name, "GLOBO SP")
        self.assertEqual(len(snapshot.programs), 1)
        self.assertEqual(snapshot.programs[0].title, "Encontro")
        self.assertEqual(snapshot.programs[0].category, "Variedades")

    def test_invalid_or_empty_xmltv_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            XmltvProvider("https://example/xmltv.php").parse(BytesIO(b"<tv />"))


if __name__ == "__main__":
    unittest.main()
