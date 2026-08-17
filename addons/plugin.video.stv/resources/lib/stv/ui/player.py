import xbmc
import xbmcgui

from stv.app.services import AppContainer


class SailePlayer(xbmc.Player):
    def __init__(self, app: AppContainer, media_type: str, item_id: str):
        super().__init__()
        self.app = app
        self.media_type = media_type
        self.item_id = item_id

    def onPlayBackStopped(self) -> None:
        try:
            position = self.getTime()
            total = self.getTotalTime()
            if total > 0 and position > 0:
                self.app.catalog.update_playback_progress(self.media_type, self.item_id, position, total)
        except Exception:
            pass

    def onPlayBackEnded(self) -> None:
        try:
            self.app.catalog.update_playback_progress(self.media_type, self.item_id, 0, 0)
        except Exception:
            pass


def play_video(app: AppContainer, media_type: str, item_id: str, url: str) -> None:
    listitem = xbmcgui.ListItem(path=url)
    
    resume = app.catalog.get_playback_progress(media_type, item_id)
    if resume and resume.get("position", 0) > 0 and resume.get("total", 0) > 0:
        if (resume["position"] / resume["total"]) < 0.95:
            listitem.setProperty('StartOffset', str(resume["position"]))

    player = SailePlayer(app, media_type, item_id)
    player.play(url, listitem)
    
    while player.isPlaying():
        xbmc.sleep(100)
