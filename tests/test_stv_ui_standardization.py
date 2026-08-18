from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
STV_LIB = ROOT / "addons" / "plugin.video.stv" / "resources" / "lib"
CORE_LIB = ROOT / "addons" / "script.module.saile.core" / "lib"
EPG_LIB = ROOT / "addons" / "script.module.saile.epg" / "lib"
for path in (STV_LIB, CORE_LIB, EPG_LIB):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from stv.app.sync import _parse_streams
from stv.bootstrap import (
    _episode_thumbnail,
    _format_live_channel_metadata,
    _item_icon,
    _show_section,
)
from stv.domain.live_channels import build_live_catalog
from stv.domain.models import Category, MediaItem
from stv.routing import Request
from stv.ui.directory import INFOWALL_VIEW_MODE, finish_directory


class UIStandardizationTests(unittest.TestCase):
    def test_live_root_promotes_epg_groups_and_hides_absorbed_category(self) -> None:
        from saile_epg.models import EpgChannel

        matched = MediaItem(
            "live", "1", "Globo", "10", epg_id="globo", normalized_name="GLOBO"
        )
        unmatched = MediaItem(
            "live", "2", "Canal Local", "20", normalized_name="CANAL LOCAL"
        )
        live_catalog = build_live_catalog(
            (EpgChannel("xtream", "globo", "globo", "Globo", "GLOBO"),),
            (matched, unmatched),
        )
        app = SimpleNamespace(
            get_live_catalog=lambda: live_catalog,
            catalog=SimpleNamespace(
                is_catalog_complete=lambda _section: True,
                get_categories=lambda _section: [
                    Category("10", "Abertos", media_type="live"),
                    Category("20", "Locais", media_type="live"),
                    Category("30", "Ainda não carregada", media_type="live"),
                ]
            ),
        )
        added_labels: list[str] = []
        request = Request("plugin://plugin.video.stv/", 7, {})
        with (
            patch("stv.bootstrap.ensure_categories_loaded"),
            patch("stv.bootstrap._add_promoted_live_channel") as promoted,
            patch("stv.ui.directory.init_directory"),
            patch("stv.ui.directory.finish_directory"),
            patch(
                "stv.ui.directory.add_folder",
                side_effect=lambda _handle, label, *_args, **_kwargs: added_labels.append(label),
            ),
            patch("stv.bootstrap._icon", return_value="icon.png"),
        ):
            _show_section(request, app, "live", "fanart.jpg")

        promoted.assert_called_once()
        self.assertNotIn("Abertos", added_labels)
        self.assertIn("Locais", added_labels)
        self.assertNotIn("Ainda não carregada", added_labels)

    def test_parse_streams_live_logos_and_epg_id(self) -> None:
        data = [
            {
                "stream_id": 1,
                "name": "BR | GLOBO SP FHD [VIP]",
                "stream_icon": "http://img.com/1.png",
                "epg_channel_id": "canal-1.br",
            },
            {"stream_id": 2, "name": "Canal 2", "logo": "http://img.com/2.png"},
            {"stream_id": 3, "name": "Canal 3", "icon": "http://img.com/3.png"},
            {"stream_id": 4, "name": "Canal 4"},
        ]
        parsed = _parse_streams("live", 100, data, default_category_id="10")
        self.assertEqual(len(parsed), 4)
        self.assertEqual(parsed[0].icon, "http://img.com/1.png")
        self.assertEqual(parsed[0].epg_id, "canal-1.br")
        self.assertEqual(parsed[0].name, "Globo SP")
        self.assertEqual(parsed[0].source_name, "BR | GLOBO SP FHD [VIP]")
        self.assertEqual(parsed[0].normalized_name, "GLOBO SP")
        self.assertEqual(parsed[1].icon, "http://img.com/2.png")
        self.assertEqual(parsed[2].icon, "http://img.com/3.png")
        self.assertEqual(parsed[3].icon, "")

    def test_parse_streams_vod_and_series_arts(self) -> None:
        vod_data = [
            {
                "stream_id": 10,
                "name": "Filme 1",
                "cover": "http://img.com/c1.jpg",
                "backdrop_path": "http://img.com/b1.jpg",
            },
        ]
        vod_parsed = _parse_streams("vod", 100, vod_data)
        self.assertEqual(vod_parsed[0].icon, "http://img.com/c1.jpg")
        self.assertEqual(vod_parsed[0].fanart, "http://img.com/b1.jpg")
        self.assertEqual(vod_parsed[0].name, "Filme 1")
        self.assertEqual(vod_parsed[0].normalized_name, "")

        series_data = [
            {
                "series_id": 20,
                "name": "Serie 1",
                "cover": "http://img.com/s1.jpg",
                "backdrop_path": ["http://img.com/sb1.jpg"],
            },
        ]
        series_parsed = _parse_streams("series", 100, series_data)
        self.assertEqual(series_parsed[0].icon, "http://img.com/s1.jpg")
        self.assertEqual(series_parsed[0].fanart, "http://img.com/sb1.jpg")

    def test_item_icon_fallback_by_section(self) -> None:
        self.assertEqual(_item_icon("live", "http://example.com/logo.png"), "http://example.com/logo.png")
        self.assertEqual(_item_icon("vod", "https://example.com/poster.jpg"), "https://example.com/poster.jpg")
        self.assertEqual(_item_icon("series", "special://home/art.png"), "special://home/art.png")
        self.assertTrue(_item_icon("live", "").endswith("live.png"))
        self.assertTrue(_item_icon("vod", "").endswith("vod.png"))
        self.assertTrue(_item_icon("series", "").endswith("series.png"))
        self.assertTrue(_item_icon("other", "").endswith("folder.png"))

    def test_episode_frame_has_priority_over_series_cover(self) -> None:
        episode = {"info": {"movie_image": "https://img.example/episode-frame.jpg"}}
        self.assertEqual(
            _episode_thumbnail(episode, "https://img.example/series-cover.jpg"),
            "https://img.example/episode-frame.jpg",
        )
        self.assertEqual(
            _episode_thumbnail({}, "https://img.example/series-cover.jpg"),
            "https://img.example/series-cover.jpg",
        )

    def test_format_live_channel_metadata_uses_module_cache(self) -> None:
        from saile_epg.models import EpgChannel, EpgProgram, EpgSnapshot
        from stv.app.services import AppContainer

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = {
                "profile_path": str(Path(tmp_dir) / "stv"),
                "epg_profile_path": str(Path(tmp_dir) / "epg"),
                "epg_enabled": "true",
            }
            app = AppContainer(settings)
            title, plot = _format_live_channel_metadata(
                app,
                "BR | GLOBO SP FHD",
                default_plot="Canal de TV",
                epg_id="globo.sp.br",
            )
            self.assertEqual(title, "Globo SP")
            self.assertEqual(plot, "Canal de TV")

            now = int(time.time())
            snapshot = EpgSnapshot(
                provider_id="xtream",
                fetched_at_utc=now,
                channels=(
                    EpgChannel(
                        "xtream", "globo.sp.br", "globo.sp.br", "Globo SP", "GLOBO SP"
                    ),
                ),
                programs=(
                    EpgProgram(
                        "xtream",
                        "globo.sp.br",
                        "Jornal Nacional",
                        now - 600,
                        now + 600,
                        "Notícias do dia no Brasil.",
                    ),
                    EpgProgram(
                        "xtream",
                        "globo.sp.br",
                        "Novela das Nove",
                        now + 600,
                        now + 1_800,
                    ),
                ),
            )
            app.epg.repository.replace_snapshot(snapshot)

            title_epg, plot_epg = _format_live_channel_metadata(
                app,
                "BR | GLOBO SP FHD",
                epg_id="globo.sp.br",
            )
            self.assertEqual(title_epg, "Globo SP")
            self.assertIn("[B]NO AR[/B]", plot_epg)
            self.assertIn("Jornal Nacional", plot_epg)
            self.assertIn("Notícias do dia no Brasil.", plot_epg)
            self.assertIn("[B]A SEGUIR[/B]", plot_epg)
            self.assertIn("Novela das Nove", plot_epg)

    def test_finish_directory_enforces_infowall_before_and_after_completion(self) -> None:
        calls: list[str] = []
        fake_xbmc = SimpleNamespace(executebuiltin=lambda command: calls.append(command))
        fake_xbmcplugin = SimpleNamespace(
            SORT_METHOD_UNSORTED=0,
            SORT_METHOD_LABEL_IGNORE_THE=1,
            SORT_METHOD_VIDEO_TITLE=2,
            SORT_METHOD_GENRE=3,
            setContent=lambda *_args: calls.append("setContent"),
            addSortMethod=lambda *_args: None,
            endOfDirectory=lambda *_args, **_kwargs: calls.append("endOfDirectory"),
        )
        with patch.dict(sys.modules, {"xbmc": fake_xbmc, "xbmcplugin": fake_xbmcplugin}):
            finish_directory(7, content="episodes")

        view_call = f"Container.SetViewMode({INFOWALL_VIEW_MODE})"
        self.assertEqual(INFOWALL_VIEW_MODE, 54)
        self.assertEqual(calls.count(view_call), 2)
        self.assertLess(calls.index(view_call), calls.index("endOfDirectory"))
        self.assertEqual(calls[-1], view_call)


if __name__ == "__main__":
    unittest.main()
