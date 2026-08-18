from __future__ import annotations

import base64
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

EPG_LIB = Path(__file__).resolve().parents[1] / "addons" / "script.module.saile.epg" / "lib"
if str(EPG_LIB) not in sys.path:
    sys.path.insert(0, str(EPG_LIB))

from saile_epg.providers.xtream import XtreamEpgProvider


def encoded(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


class XtreamEpgProviderTests(unittest.TestCase):
    def test_short_epg_builds_snapshot_and_deduplicates_quality_variants(self) -> None:
        now = int(datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc).timestamp())
        streams = [
            {
                "stream_id": "1",
                "name": "BR | GLOBO RJ FHD",
                "epg_channel_id": "globo.rj.br",
                "stream_icon": "https://img.example/globo.png",
            },
            {
                "stream_id": "2",
                "name": "GLOBO RJ HD",
                "epg_channel_id": "globo.rj.br",
            },
        ]

        def request(action: str, **_params: object) -> object:
            self.assertEqual(action, "get_short_epg")
            return {
                "epg_listings": [
                    {
                        "title": encoded("Jornal Local"),
                        "description": encoded("Notícias do Rio."),
                        "start_timestamp": now - 600,
                        "stop_timestamp": now + 1800,
                    }
                ]
            }

        with patch("saile_epg.providers.xtream.time.time", return_value=now):
            snapshot = XtreamEpgProvider(request, streams).fetch()

        self.assertEqual(len(snapshot.channels), 1)
        self.assertEqual(snapshot.channels[0].display_name, "Globo RJ")
        self.assertEqual(snapshot.channels[0].epg_id, "globo.rj.br")
        self.assertEqual(snapshot.programs[0].title, "Jornal Local")
        self.assertEqual(snapshot.programs[0].description, "Notícias do Rio.")

    def test_failure_of_first_channel_does_not_abort_other_channels(self) -> None:
        now = int(datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc).timestamp())
        streams = [
            {"stream_id": "1", "name": "Canal indisponível", "epg_channel_id": "off"},
            {"stream_id": "2", "name": "Globo HD", "epg_channel_id": "globo"},
        ]

        def request(_action: str, **params: object) -> object:
            if params["stream_id"] == "1":
                raise TimeoutError("canal sem resposta")
            return {
                "epg_listings": [
                    {
                        "title": encoded("Jornal"),
                        "start_timestamp": now - 60,
                        "stop_timestamp": now + 600,
                    }
                ]
            }

        with patch("saile_epg.providers.xtream.time.time", return_value=now):
            snapshot = XtreamEpgProvider(request, streams).fetch()

        self.assertEqual([channel.epg_id for channel in snapshot.channels], ["globo", "off"])
        self.assertEqual(snapshot.programs[0].title, "Jornal")

    def test_all_epg_ids_are_preserved_even_without_programs(self) -> None:
        streams = [
            {
                "stream_id": str(index),
                "name": f"Canal {index} HD",
                "epg_channel_id": f"canal-{index}",
            }
            for index in range(1, 502)
        ]

        snapshot = XtreamEpgProvider(
            lambda _action, **_params: {"epg_listings": []},
            streams,
        ).fetch()

        self.assertEqual(len(snapshot.channels), 501)
        self.assertEqual(snapshot.programs, ())


if __name__ == "__main__":
    unittest.main()
