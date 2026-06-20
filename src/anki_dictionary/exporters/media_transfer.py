from aqt.qt import QPixmap, Qt

from ..utils import media_manager


class MediaTransfer:
    def __init__(
        self, mw, image_map_label, audio_map_label, audio_play_button, audio_player
    ):
        self._mw = mw
        self._image_map_label = image_map_label
        self._audio_map_label = audio_map_label
        self._audio_play_button = audio_play_button
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

    def export_image(self, path, name):
        self._image_map_label.setText("")
        screenshot = QPixmap(path)
        screenshot = screenshot.scaled(
            200,
            200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_map_label.setPixmap(screenshot)

    def export_audio(self, path, tag, name):
        self._audio_map_label.setText(tag)
        self._audio_play_button.show()
