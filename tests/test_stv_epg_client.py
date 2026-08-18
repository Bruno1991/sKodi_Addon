from __future__ import annotations

import sys
import unittest
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from stv.domain.models import EpgProgram
from stv.providers.epg.claro import ClaroEpgClient


class ClaroEpgClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ClaroEpgClient()

    def test_normalize_datetime_formats(self) -> None:
        self.assertEqual(self.client._normalize_datetime("2026-08-18 10:30:00"), "2026-08-18 10:30")
        self.assertEqual(self.client._normalize_datetime("2026-08-18 14:00"), "2026-08-18 14:00")
        self.assertEqual(self.client._normalize_datetime("2026-08-18T20:45:00Z"), "2026-08-18 20:45")
        self.assertEqual(self.client._normalize_datetime(""), "")

    def test_parse_programs_dict_payload(self) -> None:
        payload = {
            "exibicoes": [
                {
                    "titulo": "Jornal Nacional",
                    "sinopse": "Principais notícias do Brasil e do mundo.",
                    "dhInicio": "2026-08-18 20:30:00",
                    "dhFim": "2026-08-18 21:20:00",
                    "duracao": 50,
                    "nomeCanal": "GLOBO SP",
                },
                {
                    "titulo": "Novela das Nove",
                    "sinopse": "Capítulo inédito da trama.",
                    "dhInicio": "2026-08-18 21:20:00",
                    "dhFim": "2026-08-18 22:25:00",
                    "duracao": 65,
                    "nomeCanal": "GLOBO SP",
                },
            ]
        }
        programs = self.client._parse_programs(payload, default_channel_key="GLOBO")
        self.assertEqual(len(programs), 2)
        
        p1 = programs[0]
        self.assertEqual(p1.channel_key, "GLOBO")
        self.assertEqual(p1.title, "Jornal Nacional")
        self.assertEqual(p1.start_time, "2026-08-18 20:30")
        self.assertEqual(p1.end_time, "2026-08-18 21:20")
        self.assertEqual(p1.synopsis, "Principais notícias do Brasil e do mundo.")
        self.assertEqual(p1.duration_minutes, 50)

        p2 = programs[1]
        self.assertEqual(p2.channel_key, "GLOBO")
        self.assertEqual(p2.title, "Novela das Nove")
        self.assertEqual(p2.start_time, "2026-08-18 21:20")

    def test_parse_programs_list_payload(self) -> None:
        payload = [
            {
                "nomePrograma": "Globo Esporte",
                "descricao": "Destaques esportivos da rodada.",
                "dataInicio": "2026-08-18 13:00",
                "dataFim": "2026-08-18 13:25",
            }
        ]
        programs = self.client._parse_programs(payload, default_channel_key="GLOBO")
        self.assertEqual(len(programs), 1)
        self.assertEqual(programs[0].title, "Globo Esporte")
        self.assertEqual(programs[0].synopsis, "Destaques esportivos da rodada.")

    def test_fetch_channel_empty_on_invalid_channel(self) -> None:
        res = self.client.fetch_channel_programs("")
        self.assertEqual(res, [])


if __name__ == "__main__":
    unittest.main()
