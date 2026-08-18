from __future__ import annotations

import gzip
import sys
import unittest
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.errors import EpgSyncError
from saile_epg.providers.xmltv import XmltvProvider, parse_xmltv_timestamp


XMLTV = b"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="globo.sp.br"><display-name>Globo SP</display-name></channel>
  <programme start="20260818100000 -0300" stop="20260818120000 -0300" channel="globo.sp.br">
    <title>Encontro</title>
  </programme>
</tv>"""
FETCHED_AT = int(datetime(2026, 8, 18, 13, 30, tzinfo=timezone.utc).timestamp())


class FakeHttpResponse:
    def __init__(self, data: bytes, content_encoding: str = "") -> None:
        self._stream = BytesIO(data)
        self.headers = {"Content-Encoding": content_encoding}
        # Reproduz respostas observadas em runtimes Kodi nas quais o objeto HTTP
        # não pode ser usado diretamente como fileobj pelo gzip.GzipFile.
        self.tell = None

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class XmltvProviderTests(unittest.TestCase):
    def test_timestamp_is_normalized_to_utc(self) -> None:
        actual = parse_xmltv_timestamp("20260818100000 -0300")
        expected = int(datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(actual, expected)

    def test_parse_channels_and_programs_in_window(self) -> None:
        xmltv = XMLTV.replace(
            b"</title>",
            b"</title><desc>Programa de variedades.</desc><category>Variedades</category>",
        )
        snapshot = XmltvProvider("https://example/xmltv.php").parse(
            BytesIO(xmltv),
            fetched_at_utc=FETCHED_AT,
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

    def test_fetch_buffers_plain_http_response_before_parsing(self) -> None:
        response = FakeHttpResponse(XMLTV)
        with (
            patch("saile_epg.providers.xmltv.urlopen", return_value=response),
            patch("saile_epg.providers.xmltv.time.time", return_value=FETCHED_AT),
        ):
            snapshot = XmltvProvider("https://example/xmltv.php").fetch()

        self.assertEqual(len(snapshot.channels), 1)
        self.assertEqual(len(snapshot.programs), 1)

    def test_fetch_buffers_gzip_response_without_calling_response_tell(self) -> None:
        response = FakeHttpResponse(gzip.compress(XMLTV), content_encoding="gzip")
        with (
            patch("saile_epg.providers.xmltv.urlopen", return_value=response),
            patch("saile_epg.providers.xmltv.time.time", return_value=FETCHED_AT),
        ):
            snapshot = XmltvProvider("https://example/xmltv.php").fetch()

        self.assertEqual(snapshot.programs[0].title, "Encontro")

    def test_fetch_detects_gzip_by_magic_bytes(self) -> None:
        response = FakeHttpResponse(gzip.compress(XMLTV))
        with (
            patch("saile_epg.providers.xmltv.urlopen", return_value=response),
            patch("saile_epg.providers.xmltv.time.time", return_value=FETCHED_AT),
        ):
            snapshot = XmltvProvider("https://example/xmltv.php").fetch()

        self.assertEqual(snapshot.channels[0].display_name, "Globo SP")

    def test_incompatible_http_response_has_safe_error_code(self) -> None:
        response = FakeHttpResponse(XMLTV)
        response.read = None
        with patch("saile_epg.providers.xmltv.urlopen", return_value=response):
            with self.assertRaises(EpgSyncError) as raised:
                XmltvProvider("https://example/xmltv.php").fetch()

        self.assertEqual(raised.exception.code, "EPG-HTTP-READ")
        self.assertNotIn("example", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
