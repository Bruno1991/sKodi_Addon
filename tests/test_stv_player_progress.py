from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

LIB_DIR = Path(__file__).resolve().parents[1] / "addons" / "plugin.video.stv" / "resources" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

_FAKE_KODI = {name: SimpleNamespace() for name in ("xbmc", "xbmcgui", "xbmcplugin")}
with patch.dict(sys.modules, _FAKE_KODI):
    from stv.ui.player import resume_progress_to_save, track_playback_progress

URL = "http://iptv.example/movie/u/p/42.mp4"


def tearDownModule() -> None:
    # stv.ui.player ficou ligado aos dublês do Kodi; outro teste deve reimportá-lo do zero.
    sys.modules.pop("stv.ui.player", None)


class FakePlayer:
    """Toca `ticks` leituras de posição e depois para, como o xbmc.Player."""

    def __init__(
        self, positions: list[float], total: float, playing_file: str = URL, start_after: int = 0
    ):
        self.positions = list(positions)
        self.total = total
        self.playing_file = playing_file
        self.start_after = start_after
        self.current = 0.0

    def isPlayingVideo(self) -> bool:
        if self.start_after > 0:
            self.start_after -= 1
            return False
        return bool(self.positions)

    def getPlayingFile(self) -> str:
        return self.playing_file

    def getTime(self) -> float:
        self.current = self.positions.pop(0)
        return self.current

    def getTotalTime(self) -> float:
        return self.total


class FakeMonitor:
    def abortRequested(self) -> bool:
        return False

    def waitForAbort(self, _timeout: float) -> bool:
        return False


class FakeCatalog:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str, float, float]] = []

    def update_playback_progress(
        self, media_type: str, item_id: str, position: float, total: float
    ) -> None:
        self.saved.append((media_type, item_id, position, total))


class PlaybackProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = SimpleNamespace(catalog=FakeCatalog())

    def test_resume_progress_to_save(self) -> None:
        self.assertEqual(resume_progress_to_save(600, 6000), (600, 6000))
        self.assertEqual(resume_progress_to_save(5800, 6000), (0.0, 0.0))  # assistido: limpa
        self.assertIsNone(resume_progress_to_save(0, 6000))
        self.assertIsNone(resume_progress_to_save(10, 0))

    def test_saves_last_position_read_while_playing(self) -> None:
        player = FakePlayer([10.0, 11.0, 1200.0], total=6000.0, start_after=2)
        track_playback_progress(self.app, "vod", "42", URL, player, FakeMonitor())
        self.assertEqual(self.app.catalog.saved, [("vod", "42", 1200.0, 6000.0)])

    def test_clears_resume_when_watched_to_the_end(self) -> None:
        player = FakePlayer([5990.0], total=6000.0)
        track_playback_progress(self.app, "series", "7", URL, player, FakeMonitor())
        self.assertEqual(self.app.catalog.saved, [("series", "7", 0.0, 0.0)])

    def test_ignores_progress_of_another_item(self) -> None:
        player = FakePlayer([300.0], total=6000.0, playing_file="http://outro/item.mp4")
        track_playback_progress(self.app, "vod", "42", URL, player, FakeMonitor())
        self.assertEqual(self.app.catalog.saved, [])

    def test_gives_up_when_playback_never_starts(self) -> None:
        player = FakePlayer([], total=0.0)
        track_playback_progress(
            self.app, "vod", "42", URL, player, FakeMonitor(), start_timeout_s=2
        )
        self.assertEqual(self.app.catalog.saved, [])


if __name__ == "__main__":
    unittest.main()
