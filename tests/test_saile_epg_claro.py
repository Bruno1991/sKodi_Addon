from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock, patch

from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
from saile_epg.providers.claro import ClaroEpgProvider, CLARO_OFFICIAL_CHANNELS


class ClaroEpgProviderTests(unittest.TestCase):
    def test_provider_initialization_defaults(self) -> None:
        provider = ClaroEpgProvider()
        self.assertEqual(provider.provider_id, "claro")
        self.assertGreater(len(CLARO_OFFICIAL_CHANNELS), 30)

    @patch("urllib.request.urlopen")
    def test_fetch_parses_live_channels_and_programs_with_logos(self, mock_urlopen: MagicMock) -> None:
        now = int(time.time())
        fake_api_response = {
            "status": 200,
            "response": {
                "liveChannels": [
                    {
                        "id": 1,
                        "name": "DISCOVERY KIDS HD",
                        "type": "INFANTIS",
                        "logo": "https://www.clarotvmais.com.br/img/channels/discovery_kids.png",
                        "channelNumber": 600,
                        "schedules": [
                            {
                                "title": "Peppa Pig",
                                "episodeName": "A Festa do Pijama",
                                "description": "Peppa e seus amigos vão dormir na casa da Zoe Zebra.",
                                "startTime": now - 600,
                                "endTime": now + 600,
                                "seasonNumber": 2,
                                "episodeNumber": 14,
                                "rating": {"code": "L"},
                            },
                            {
                                "title": "Show da Luna",
                                "episodeName": "Por que as estrelas brilham?",
                                "description": "Luna investiga o céu noturno.",
                                "startTime": now + 600,
                                "endTime": now + 1800,
                                "seasonNumber": 1,
                                "episodeNumber": 5,
                                "rating": {"code": "L"},
                            },
                        ],
                    }
                ]
            },
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_api_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        provider = ClaroEpgProvider(chunk_size=100)
        snapshot = provider.fetch(window_hours=12)

        self.assertIsInstance(snapshot, EpgSnapshot)
        self.assertEqual(snapshot.provider_id, "claro")
        self.assertGreater(len(snapshot.channels), 0)

        # Canal 1 verificado
        ch1 = next((ch for ch in snapshot.channels if ch.channel_key == "claro_1"), None)
        self.assertIsNotNone(ch1)
        self.assertEqual(ch1.display_name, "Discovery Kids")
        self.assertIn("discovery_kids.png", ch1.icon_url)

        # Programas verificados
        programs = [p for p in snapshot.programs if p.channel_key == "claro_1"]
        self.assertEqual(len(programs), 2)
        self.assertEqual(programs[0].title, "Peppa Pig")
        self.assertIn("Episódio: A Festa do Pijama", programs[0].description)
        self.assertEqual(programs[0].category, "INFANTIS")


if __name__ == "__main__":
    unittest.main()
