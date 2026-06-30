from dataclasses import dataclass
from os.path import join

from aqt.qt import (
    QApplication,
    QIcon,
    QLabel,
    QProgressBar,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..utils.common import miInfo


@dataclass
class _MediaProgress:
    widget: QWidget
    bar: QProgressBar
    text_display: QLabel
    current_value: int = 0
    total: int = 0
    closed_because_finished_importing: bool = False


class BulkProcessor:
    def __init__(self, mw, dict_int, always_on_top):
        self._mw = mw
        self._dict_int = dict_int
        self._always_on_top = always_on_top
        self.text_importing = False
        self.media_export_progress_window: _MediaProgress | None = None

    def bulk_text_export(self, cards, add_text_card_fn):
        self.text_importing = True
        total = len(cards)
        importing_message = "Importing {} of " + str(total) + " cards."
        progress_widget, bar, text_display = self._get_progress_bar(
            "Anki Dictionary - Importing Text Cards",
            importing_message.format(0),
        )
        bar.setMaximum(total)
        for idx, card in enumerate(cards):
            if not self.text_importing:
                miInfo(
                    "Importing cards from the extension has been cancelled."
                    f"\n\n{idx} of {total} were added.",
                )
                return
            add_text_card_fn(card)
            bar.setValue(idx + 1)
            text_display.setText(importing_message.format(idx + 1))
            self._mw.app.processEvents()
        self.text_importing = False
        self._close_progress_bar(progress_widget)

    def bulk_media_export(self, card, add_media_card_fn):
        if self._mw.DictBulkMediaExportWasCancelled:
            return
        if self.media_export_progress_window is None:
            total = card["total"]
            importing_message = "Importing {} of " + str(total) + " cards."
            widget, bar, text_display = self._get_progress_bar(
                "Anki Dictionary - Importing Media Cards",
                importing_message.format(0),
            )
            self.media_export_progress_window = _MediaProgress(
                widget=widget,
                bar=bar,
                text_display=text_display,
                current_value=0,
                total=total,
            )
            bar.setMaximum(total)
        else:
            importing_message = (
                "Importing {} of "
                + str(self.media_export_progress_window.total)
                + " cards."
            )
        add_media_card_fn(card)
        state = self.media_export_progress_window
        try:
            if self._mw.DictBulkMediaExportWasCancelled:
                if state:
                    self._close_progress_bar(state.widget)
                return
            state.current_value += 1
            state.bar.setValue(state.current_value)
            state.text_display.setText(importing_message.format(state.current_value))
            self._mw.app.processEvents()
            if state.current_value == state.total:
                total = state.total
                if total == 1:
                    miInfo(f"{total} card has been imported.")
                else:
                    miInfo(f"{total} cards have been imported.")
                self._close_progress_bar(state.widget)
                self.media_export_progress_window = None
        except Exception:
            pass

    def cancel_media_export(self):
        state = self.media_export_progress_window
        if state:
            miInfo(
                "Importing cards from the extension has been cancelled from"
                f" within the browser.\n\n {state.current_value} cards were imported."
            )
            self._close_progress_bar(state.widget)
            self.media_export_progress_window = None
            self._mw.DictBulkMediaExportWasCancelled = False

    def _get_progress_bar(self, title, initial_text):
        progress_widget = QWidget()
        closed_because_finished_importing = False

        def _closed_progress_bar(event):
            if self.text_importing:
                self.text_importing = False
            event.accept()
            progress_widget.deleteLater()
            state = self.media_export_progress_window
            if state:
                current_value = state.current_value
                self.media_export_progress_window = None
                if not closed_because_finished_importing:
                    self._mw.DictBulkMediaExportWasCancelled = True
                    miInfo(
                        f"Importing cancelled.\n\n{current_value} cards were imported."
                    )

        text_display = QLabel()
        progress_widget.setWindowIcon(
            QIcon(
                join(
                    self._dict_int.addonPath,
                    "assets",
                    "icons",
                    "anki.svg",
                )
            )
        )
        progress_widget.setWindowTitle(title)
        text_display.setText(initial_text)

        bar = QProgressBar(progress_widget)
        layout = QVBoxLayout()
        layout.addWidget(text_display)
        layout.addWidget(bar)
        progress_widget.setLayout(layout)
        bar.move(10, 10)
        per = QLabel(bar)
        per.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_widget.setFixedSize(500, 100)
        progress_widget.setWindowModality(Qt.WindowModality.ApplicationModal)
        if self._always_on_top:
            progress_widget.setWindowFlags(
                progress_widget.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = int((screen_geometry.width() - progress_widget.width()) / 2)
            y = int((screen_geometry.height() - progress_widget.height()) / 2)
            progress_widget.move(x, y)
        progress_widget.show()
        progress_widget.setFocus()
        progress_widget.closeEvent = _closed_progress_bar  # ty: ignore[invalid-assignment]
        self._mw.app.processEvents()
        return progress_widget, bar, text_display

    @staticmethod
    def _close_progress_bar(widget: QWidget) -> None:
        if widget:
            widget.close()
            widget.deleteLater()
