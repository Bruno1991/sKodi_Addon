from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for _lib in (
    ROOT / "addons" / "plugin.video.stv" / "resources" / "lib",
    ROOT / "addons" / "script.module.saile.core" / "lib",
    ROOT / "addons" / "script.module.saile.epg" / "lib",
):
    if str(_lib) not in sys.path:
        sys.path.insert(0, str(_lib))

from stv.bootstrap import _play_item, run
from stv.parental import get_parental_pin, is_restricted, set_parental_pin


class MockAddon:
    def __init__(self, pin: str = "", extra_settings: dict[str, str] | None = None) -> None:
        self.settings: dict[str, str] = {"parental_pin": pin, **(extra_settings or {})}

    def getSetting(self, key: str) -> str:
        return self.settings.get(key, "")

    def setSetting(self, key: str, value: str) -> None:
        self.settings[key] = value

    def getAddonInfo(self, key: str) -> str:
        return "fanart.jpg" if key == "fanart" else ""


class ParentalControlTests(unittest.TestCase):
    def test_restricted_keyword_detection(self) -> None:
        self.assertTrue(is_restricted(name="Canal XXX 4K"))
        self.assertTrue(is_restricted(category_name="Filmes Adultos"))
        self.assertTrue(is_restricted(name="Playboy TV HD"))
        self.assertTrue(is_restricted(name="Sessão +18 Noite"))
        self.assertTrue(is_restricted(plot="Conteúdo erótico para maiores de idade"))
        self.assertTrue(is_restricted(tmdb_adult=True))

        self.assertFalse(is_restricted(name="Globo SP HD"))
        self.assertFalse(is_restricted(name="Filmes de Ação 2024", category_name="VOD Lançamentos"))
        self.assertFalse(is_restricted(name="Turma da Mônica"))

    def test_pin_storage_and_retrieval(self) -> None:
        addon = MockAddon()
        self.assertEqual(get_parental_pin(addon), "")

        set_parental_pin(addon, "123456")
        self.assertEqual(get_parental_pin(addon), "123456")

        set_parental_pin(addon, "9876")
        self.assertEqual(get_parental_pin(addon), "9876")

    def test_category_route_enforces_parental_pin_via_category_name_param(self) -> None:
        fake_addon = MockAddon(
            pin="1234",
            extra_settings={
                "lan_sync_enabled": "false",
                "lan_sync_auto": "false",
                "epg_ttl_hours": "24",
            },
        )
        fake_xbmcaddon = SimpleNamespace(Addon=lambda *_args: fake_addon)
        fake_xbmcvfs = SimpleNamespace(translatePath=lambda p: p)
        captured_settings: dict[str, str] = {}

        class FakeApp:
            preferred_view_mode = 54

            def __init__(self, settings: dict[str, str]) -> None:
                captured_settings.update(settings)

        with (
            patch.dict(sys.modules, {"xbmcaddon": fake_xbmcaddon, "xbmcvfs": fake_xbmcvfs}),
            patch("stv.bootstrap.AppContainer", FakeApp),
            patch("stv.ui.directory.ensure_infowall_in_kodi_db"),
            patch("stv.ui.directory.init_directory"),
            patch("stv.ui.directory.finish_directory") as finish_dir,
            patch("stv.bootstrap.ensure_streams_loaded") as load_streams,
            patch("stv.bootstrap.verify_parental_pin", return_value=False) as verify_pin,
        ):
            run(
                [
                    "plugin://plugin.video.stv/",
                    "7",
                    "?action=category&section=vod&category_id=99&category_name=Filmes+Adultos",
                ]
            )

        verify_pin.assert_called_once()
        load_streams.assert_not_called()
        finish_dir.assert_called_once()
        self.assertEqual(captured_settings["lan_sync_enabled"], "false")
        self.assertEqual(captured_settings["lan_sync_auto"], "false")
        self.assertEqual(captured_settings["epg_ttl_hours"], "24")

    def test_play_item_resolves_false_when_parental_pin_is_rejected(self) -> None:
        from stv.routing import Request

        resolved_calls: list[tuple[int, bool]] = []
        fake_xbmcaddon = SimpleNamespace(Addon=lambda *_args: MockAddon(pin="1234"))
        fake_xbmcgui = SimpleNamespace(ListItem=lambda **_kwargs: object())
        fake_xbmcplugin = SimpleNamespace(
            setResolvedUrl=lambda handle, succeeded, _item: resolved_calls.append(
                (handle, succeeded)
            )
        )
        fake_player_mod = SimpleNamespace(play_video=lambda *_args, **_kwargs: None)

        with (
            patch.dict(
                sys.modules,
                {
                    "xbmcaddon": fake_xbmcaddon,
                    "xbmcgui": fake_xbmcgui,
                    "xbmcplugin": fake_xbmcplugin,
                    "stv.ui.player": fake_player_mod,
                },
            ),
            patch("stv.bootstrap.verify_parental_pin", return_value=False),
        ):
            req = Request("plugin://plugin.video.stv/", 5, {})
            _play_item(req, SimpleNamespace(), "vod", "77", "mp4", title="Filme +18")

        self.assertEqual(resolved_calls, [(5, False)])


if __name__ == "__main__":
    unittest.main()
