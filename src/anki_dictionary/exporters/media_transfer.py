"""Media handling for the card exporter.

Since the exporter's UI moved to the Svelte page, this class no longer owns
any widgets: the image thumbnail and audio label are rendered by the web UI
from the paths ``CardExporter`` holds. What is left is the collection-side
work — copying the picked media into Anki's media folder and playing audio.
"""

from ..utils import media_manager


class MediaTransfer:
    def __init__(self, mw, audio_player):
        self._mw = mw
        self._audio_player = audio_player

    def move_image_to_media_folder(self, img_path, img_name):
        if img_path and img_name:
            media_manager.copy_to_media(
                img_path,
                img_name,
                self._mw.col.media.dir(),
            )

    def move_audio_to_media_folder(self, audio_path, audio_name):
        if audio_path and audio_name:
            media_manager.copy_to_media(
                audio_path,
                audio_name,
                self._mw.col.media.dir(),
            )

    def play_audio(self, audio_path):
        if audio_path:
            self._audio_player.play(audio_path)
