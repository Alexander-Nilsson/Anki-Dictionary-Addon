from __future__ import annotations

from typing import Any

from aqt.qt import QColor, QFrame, QPushButton

from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


_FALLBACK_THEME: dict[str, str] = {
    "header_background": "#51576d",
    "selector": "#949cbb",
    "header_text": "#babbf1",
    "search_term": "#f4b8e4",
    "border": "#babbf1",
    "anki_button_background": "#99d1db",
    "anki_button_text": "#c6d0f5",
    "tab_hover": "#f4b8e4",
    "current_tab_gradient_top": "#737994",
    "current_tab_gradient_bottom": "#414559",
    "example_highlight": "#414559",
    "definition_background": "#51576d",
    "definition_text": "#c6d0f5",
    "pitch_accent_color": "#eebebe",
}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def load_color(theme_manager: Any, color_key: str) -> QColor:
    try:
        active_theme = theme_manager.get_active_theme()
        color_value = getattr(active_theme, color_key, "#ffffff")
        return QColor(color_value)
    except Exception as e:
        logger.error(f"Error loading theme color '{color_key}': {e}")
    return QColor("#ffffff")


def generate_qt_stylesheet(theme_dict: dict[str, str]) -> str:
    return f"""
        QWidget {{
            background-color: {theme_dict["header_background"]};
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        QPushButton {{
            color: {theme_dict["header_text"]};
            border: 1.5px solid {theme_dict["border"]};
            border-radius: 6px;
            padding: 8px;
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {theme_dict["current_tab_gradient_top"]},
                stop: 1 {theme_dict["current_tab_gradient_bottom"]});
        }}
        QPushButton:hover {{
            border: 2px solid {theme_dict["search_term"]};
            background: {theme_dict["tab_hover"]};
        }}
        QLineEdit, QComboBox {{
            background-color: {theme_dict["header_background"]};
            color: {theme_dict["header_text"]};
            border: 1.5px solid {theme_dict["border"]};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QLineEdit:focus {{
            border: 2px solid {theme_dict["search_term"]};
        }}
        QLabel {{
            color: {theme_dict["header_text"]};
            font-weight: bold;
        }}
        QComboBox QAbstractItemView {{
            background-color: {theme_dict["header_background"]};
            color: {theme_dict["header_text"]};
            border: 1px solid {theme_dict["border"]};
            selection-background-color: {theme_dict["search_term"]};
        }}
    """


def generate_html_css(theme_dict: dict[str, str]) -> str:
    return f"""
        <style id="customThemeCss">
            :root {{
                --background: {theme_dict["header_background"]};
                --selector: {theme_dict["selector"]};
                --background-secondary: {theme_dict["selector"]};
                --text: {theme_dict["header_text"]};
                --header_text: {theme_dict["header_text"]};
                --text-secondary: {theme_dict["search_term"]};
                --search_term: {theme_dict["search_term"]};
                --border: {theme_dict["border"]};
                --button-bg: {theme_dict["anki_button_background"]};
                --button-text: {theme_dict["anki_button_text"]};
                --button-bg-hover: {theme_dict["tab_hover"]};
                --tab_hover: {theme_dict["tab_hover"]};
                --definition_background: {theme_dict["definition_background"]};
                --definition_text: {theme_dict["definition_text"]};
            }}
            body {{
                background-color: {theme_dict["header_background"]};
                color: {theme_dict["header_text"]};
            }}
            .header {{
                background-color: {theme_dict["header_background"]};
                color: {theme_dict["header_text"]};
                border-bottom: 2px solid {theme_dict["border"]};
            }}
            .targetTerm {{
                color: {theme_dict["search_term"]} !important;
            }}
            .exampleSentence {{
                background-color: {hex_to_rgba(theme_dict["example_highlight"], 0.2)};
                border-radius: 3px;
                padding: 1px 4px;
                margin: 0 2px;
            }}
            .definitionBlock {{
                background-color: {theme_dict["definition_background"]};
                color: {theme_dict["definition_text"]};
                border: 1px solid {theme_dict["border"]};
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            .altterm {{
                color: {theme_dict["pitch_accent_color"]};
            }}
            .ankiExportButton {{
                border: 1.5px solid {theme_dict["border"]};
                border-radius: 6px;
                padding: 6px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {theme_dict["current_tab_gradient_top"]},
                    stop: 1 {theme_dict["current_tab_gradient_bottom"]});
                transition: all 0.2s;
            }}
            .ankiExportButton:hover {{
                border-color: {theme_dict["search_term"]};
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .ankiExportButton img {{
                height: 28px !important;
                width: 28px !important;
            }}
            .tablinks {{
                border: 1px solid {theme_dict["border"]};
                border-radius: 6px 6px 0 0;
                margin-right: 2px;
            }}
            .tablinks.active {{
                background-image: linear-gradient(
                    {theme_dict["current_tab_gradient_top"]},
                    {theme_dict["current_tab_gradient_bottom"]}
                );
                border-bottom: 2px solid {theme_dict["search_term"]};
            }}
            .tablinks:hover {{
                background-color: {theme_dict["tab_hover"]};
            }}
            .overwriteSelect, .fieldSelect {{
                background-color: {theme_dict["selector"]};
                border: 1px solid {theme_dict["border"]};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: inherit;
                cursor: pointer;
            }}
            .fieldSelectCont {{
                position: relative;
                min-width: 200px;
                display: inline-block;
            }}
            .fieldCheckboxes, .overwriteCheckboxes {{
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background-color: {theme_dict["header_background"]};
                border: 1px solid {theme_dict["border"]};
                border-radius: 0 0 6px 6px;
                display: none;
                z-index: 1000;
                min-width: 250px;
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
                overflow: hidden;
                flex-direction: column;
            }}
            .fieldCheckboxes.open, .overwriteCheckboxes.open {{
                display: flex;
            }}
            .fieldSearchInput {{
                width: 100%;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {theme_dict["border"]};
                background-color: {theme_dict["selector"]};
                color: {theme_dict["header_text"]};
                box-sizing: border-box;
                font-size: inherit;
                outline: none;
                flex-shrink: 0;
            }}
            .fieldSearchInput::placeholder {{
                color: {theme_dict["header_text"]};
                opacity: 0.6;
            }}
            .fieldOptionsContainer {{
                max-height: 250px;
                overflow-y: auto;
                padding: 5px 0;
                flex: 1;
                min-height: 0;
            }}
            .fieldCheckboxLabel {{
                display: flex;
                align-items: center;
                padding: 8px 10px;
                cursor: pointer;
                color: {theme_dict["header_text"]};
                white-space: nowrap;
                user-select: none;
            }}
            .fieldCheckboxLabel:hover {{
                background-color: {theme_dict["tab_hover"]};
            }}
            .fieldCheckboxLabel input[type="checkbox"] {{
                margin-right: 8px;
                cursor: pointer;
            }}
            .fieldCheckboxLabel span {{
                flex: 1;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
    </style>
    """


def get_theme_dict(theme_manager: Any) -> dict[str, str]:
    try:
        active_theme = theme_manager.get_active_theme()
        return vars(active_theme)
    except Exception as e:
        logger.error(f"Error loading active theme: {e}")
        return dict(_FALLBACK_THEME)


def get_window_icon_name(theme_manager: Any) -> str:
    return "nightanki.svg" if theme_manager.is_dark else "anki.svg"


def apply_child_widget_styles(dict_int: Any, theme_manager: Any) -> None:
    theme_dict = get_theme_dict(theme_manager)
    combo_style = theme_manager.get_combo_style()

    dict_int.dictGroups.setStyleSheet(combo_style)
    dict_int.sType.setStyleSheet(combo_style)

    search_style = f"""
        QLineEdit {{
            color: {theme_dict["header_text"]};
            background: {theme_dict["header_background"]};
            border: 1.5px solid {theme_dict["border"]};
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: 500;
        }}
        QLineEdit:focus {{
            border: 2px solid {theme_dict["search_term"]};
        }}
    """
    dict_int.search.setStyleSheet(search_style)

    for button in dict_int.findChildren(QPushButton):
        if not hasattr(button, "svgWidget"):
            button.setStyleSheet(theme_manager.get_qt_styles())

    for frame in dict_int.findChildren(QFrame):
        if frame.frameShape() in (QFrame.Shape.VLine, QFrame.Shape.HLine):
            border_color = load_color(theme_manager, "border")
            c = border_color
            frame.setStyleSheet(
                f"background-color: rgba({c.red()}, {c.green()}, {c.blue()}, 50);"
            )
