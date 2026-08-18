from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
CORE_LIB = ROOT / "addons" / "script.module.saile.core" / "resources" / "lib"
if str(STV_LIB) not in sys.path:
    sys.path.insert(0, str(STV_LIB))
if str(CORE_LIB) not in sys.path:
    sys.path.insert(0, str(CORE_LIB))

from stv.app.sync import _parse_streams
from stv.bootstrap import _item_icon


class UIStandardizationTests(unittest.TestCase):
    def test_parse_streams_live_logos_and_icons(self) -> None:
        data = [
            {"stream_id": 1, "name": "Canal 1", "stream_icon": "http://img.com/1.png"},
            {"stream_id": 2, "name": "Canal 2", "logo": "http://img.com/2.png"},
            {"stream_id": 3, "name": "Canal 3", "icon": "http://img.com/3.png"},
            {"stream_id": 4, "name": "Canal 4"},  # No icon
        ]
        parsed = _parse_streams("live", 100, data, default_category_id="10")
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0].icon, "http://img.com/1.png")
        self.assertEqual(parsed[1].icon, "http://img.com/2.png")
        self.assertEqual(parsed[2].icon, "http://img.com/3.png")
        self.assertEqual(parsed[3].icon, "")

    def test_parse_streams_vod_and_series_arts(self) -> None:
        vod_data = [
            {"stream_id": 10, "name": "Filme 1", "cover": "http://img.com/c1.jpg", "backdrop_path": "http://img.com/b1.jpg"},
        ]
        vod_parsed = _parse_streams("vod", 100, vod_data)
        self.assertEqual(vod_parsed[0].icon, "http://img.com/c1.jpg")
        self.assertEqual(vod_parsed[0].fanart, "http://img.com/b1.jpg")

        series_data = [
            {"series_id": 20, "name": "Serie 1", "cover": "http://img.com/s1.jpg", "backdrop_path": ["http://img.com/sb1.jpg"]},
        ]
        series_parsed = _parse_streams("series", 100, series_data)
        self.assertEqual(series_parsed[0].icon, "http://img.com/s1.jpg")
        self.assertEqual(series_parsed[0].fanart, "http://img.com/sb1.jpg")

    def test_item_icon_fallback_by_section(self) -> None:
        # Valid URLs should be returned as-is
        self.assertEqual(_item_icon("live", "http://example.com/logo.png"), "http://example.com/logo.png")
        self.assertEqual(_item_icon("vod", "https://example.com/poster.jpg"), "https://example.com/poster.jpg")
        self.assertEqual(_item_icon("series", "special://home/art.png"), "special://home/art.png")

        # Empty/invalid URLs must fallback to official section icon
        live_fallback = _item_icon("live", "")
        self.assertTrue(live_fallback.endswith("live.png"), live_fallback)

        vod_fallback = _item_icon("vod", "")
        self.assertTrue(vod_fallback.endswith("vod.png"), vod_fallback)

        series_fallback = _item_icon("series", "")
        self.assertTrue(series_fallback.endswith("series.png"), series_fallback)

        other_fallback = _item_icon("other", "")
        self.assertTrue(other_fallback.endswith("folder.png"), other_fallback)

    def test_format_live_channel_metadata_with_epg(self) -> None:
        import tempfile
        from stv.app.services import AppContainer
        from stv.bootstrap import _format_live_channel_metadata
        from stv.domain.models import EpgProgram

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = {
                "profile_path": tmp_dir,
                "epg_enabled": "true",
                "epg_cache_hours": "4",
            }
            app = AppContainer(settings)
            
            # 1. Sem EPG: deve retornar título limpo e plot default
            title, plot = _format_live_channel_metadata(app, "BR | GLOBO SP FHD", default_plot="Canal de TV")
            self.assertEqual(title, "Globo SP")
            self.assertEqual(plot, "Canal de TV")

            # 2. Com EPG populado: deve formatar 🔴 NO AR e ⏭️ A SEGUIR
            programs = [
                EpgProgram(
                    channel_key="GLOBO",
                    title="Jornal Nacional",
                    start_time="2020-01-01 20:30",
                    end_time="2099-01-01 21:20",
                    synopsis="Notícias do dia no Brasil.",
                ),
                EpgProgram(
                    channel_key="GLOBO",
                    title="Novela das Nove",
                    start_time="2099-01-01 21:20",
                    end_time="2099-01-01 22:25",
                    synopsis="Capítulo de hoje.",
                ),
            ]
            app.catalog.upsert_epg_programs(programs)

            title_epg, plot_epg = _format_live_channel_metadata(app, "BR | GLOBO SP FHD")
            self.assertEqual(title_epg, "Globo SP")
            self.assertIn("🔴 NO AR: Jornal Nacional", plot_epg)
            self.assertIn("Notícias do dia no Brasil.", plot_epg)
            self.assertIn("⏭️ A SEGUIR: Novela das Nove", plot_epg)


if __name__ == "__main__":
    unittest.main()

