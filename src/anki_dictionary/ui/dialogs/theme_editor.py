import json
import os

from aqt.qt import *
from aqt.utils import showInfo

from .themes import ThemeColors


class ThemeEditorDialog(QDialog):
    applied = pyqtSignal()

    def __init__(self, theme_manager, mw, path, dict_interface, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.dict_interface = dict_interface
        self.addonPath = path
        self.active_theme_file = os.path.join(self.addonPath, "user_files/themes", "active.json")
        self.themes_file = os.path.join(self.addonPath, "user_files/themes", "themes.json")
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Theme Editor")
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)

        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.themes.keys())
        self.theme_combo.currentTextChanged.connect(self.load_theme)
        theme_layout.addWidget(QLabel("Theme:"))
        theme_layout.addWidget(self.theme_combo)

        # Load active theme name and colors
        active_theme_name = self.load_active_theme_name()
        active_colors = self.load_active_theme_colors()

        scroll_layout.addLayout(theme_layout)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        self.color_editors = {}

        # Set combo box to active theme name and load colors
        self.theme_combo.setCurrentText(active_theme_name)
        # Manually load the active theme's colors into editors
        for color_name, (editor, _, preview) in self.color_editors.items():
            color_value = active_colors.get(color_name, "#ffffff")
            editor.setText(color_value)
            preview.setStyleSheet(f"background-color: {color_value}; border: 1px solid black;")

        row = 0
        fields = [
            "header_background", "selector", "header_text", "search_term", "border",
            "anki_button_background", "anki_button_text", "tab_hover",
            "current_tab_gradient_top", "current_tab_gradient_bottom",
            "example_highlight", "definition_background", "definition_text",
            "pitch_accent_color"
        ]

        for color_name in fields:
            # Use active_colors to initialize the color values
            color_value = active_colors.get(color_name, "#ffffff")
            label = QLabel(color_name.replace('_', ' ').title())
            color_edit = QLineEdit(color_value)
            color_button = QPushButton("Pick Color")
            color_preview = QLabel()
            color_preview.setFixedSize(30, 30)
            color_preview.setStyleSheet(f"background-color: {color_value}; border: 1px solid black;")
            self.color_editors[color_name] = (color_edit, color_button, color_preview)
            color_button.clicked.connect(lambda checked, name=color_name: self.pick_color(name))
            color_edit.textChanged.connect(lambda new_value, name=color_name: self.update_color_preview(name))
            grid_layout.addWidget(label, row, 0)
            grid_layout.addWidget(color_edit, row, 1)
            grid_layout.addWidget(color_button, row, 2)
            grid_layout.addWidget(color_preview, row, 3)
            row += 1

        scroll_layout.addLayout(grid_layout)

        button_layout = QHBoxLayout()
        save_and_apply_button = QPushButton("Save and Apply")
        save_as_button = QPushButton("Save As New")

        save_and_apply_button.clicked.connect(self.save_and_apply_theme)
        save_as_button.clicked.connect(self.save_as_theme)

        button_layout.addWidget(save_and_apply_button)
        button_layout.addWidget(save_as_button)

        main_layout.addWidget(scroll_area)
        main_layout.addLayout(button_layout)

    def save_theme(self):
        selected_theme_name = self.theme_combo.currentText()
        colors = ThemeColors(**self.get_current_colors())

        if selected_theme_name != "active":
            self.theme_manager.save_theme(selected_theme_name, colors)
        else:
            self._save_active_theme(colors)

        self.applied.emit()

    def save_and_apply_theme(self):
        selected_theme_name = self.theme_combo.currentText()
        colors = ThemeColors(**self.get_current_colors())

        if selected_theme_name != "active":
            self.theme_manager.save_theme(selected_theme_name, colors)
        else:
            self._save_active_theme(colors)

        self._save_active_theme(colors)
        self.refresh_application_theme()
        print(f"Applied theme: {selected_theme_name}")
        self.applied.emit()

    def pick_color(self, color_name):
        editor, _, _ = self.color_editors[color_name]  # Updated unpacking
        current_color = QColor(editor.text())
        color = QColorDialog.getColor(current_color, self)
        if color.isValid():
            editor.setText(color.name())

    def update_color_preview(self, color_name):
        editor, _, preview = self.color_editors[color_name]
        color_value = editor.text()
        try:
            preview.setStyleSheet(f"background-color: {color_value}; border: 1px solid black;")
            # editor.setStyleSheet(f"background-color: {color_value}; color: white;")
        except Exception as e:
            print(f"Error updating color preview: {e}")

    def load_theme(self, theme_name):
        theme = self.theme_manager.themes[theme_name]
        for color_name, (editor, _, preview) in self.color_editors.items():
            color_value = getattr(theme, color_name)
            editor.setText(color_value)
            preview.setStyleSheet(
                f"background-color: {color_value}; border: 1px solid black;")

    def get_current_colors(self):
        return {name: editor.text() for name, (editor, _, _) in self.color_editors.items()}

    def _save_active_theme(self, colors):
        try:
            theme_data = vars(colors)
            theme_data["active_theme_name"] = self.theme_combo.currentText()
            with open(self.active_theme_file, "w") as f:
                json.dump(theme_data, f, indent=2)
            print("Active theme saved.")
        except IOError as e:
            print(f"Error saving active theme: {e}")


    def save_as_theme(self):
        name_dialog = QDialog(self)
        layout = QVBoxLayout()
        name_edit = QLineEdit()
        save_button = QPushButton("Save")
        layout.addWidget(QLabel("Theme Name:"))
        layout.addWidget(name_edit)
        layout.addWidget(save_button)
        name_dialog.setLayout(layout)

        def save_new():
            name = name_edit.text()
            if name:
                colors = ThemeColors(**self.get_current_colors())
                self.theme_manager.save_theme(name, colors)
                self.theme_combo.addItem(name)
                self.theme_combo.setCurrentText(name)
                name_dialog.accept()

        save_button.clicked.connect(save_new)
        name_dialog.exec()

    def apply_theme(self):
        selected_theme_name = self.theme_combo.currentText()
        if selected_theme_name in self.theme_manager.themes:
            selected_theme_colors = self.theme_manager.themes[selected_theme_name]
            self._save_active_theme(selected_theme_colors)
            self.refresh_application_theme()
            print(f"Applied theme: {selected_theme_name}")
            self.applied.emit()
        else:
            print(f"Error: Selected theme '{selected_theme_name}' not found.")

    def refresh_application_theme(self):
        if self.dict_interface:
            self.dict_interface.refresh_application_theme()

    def load_active_theme_name(self):
        try:
            with open(self.active_theme_file, "r") as f:
                theme_data = json.load(f)
                return theme_data.get("active_theme_name", self.theme_manager.current_theme)
        except Exception as e:
            print(f"Error loading active theme name: {e}")
            return self.theme_manager.current_theme

    def load_active_theme_colors(self):
        """Load color values from active.json."""
        try:
            with open(self.active_theme_file, "r") as f:
                theme_data = json.load(f)
                return theme_data
        except Exception as e:
            print(f"Error loading active theme colors: {e}")
            return {}

    def load_theme_color(self, color_key):
        try:
            with open(self.active_theme_file, "r") as f:
                theme = json.load(f)
                if color_key in theme:
                    return QColor(theme[color_key])
        except Exception as e:
            print(f"Error loading active theme color: {e}")
        return QColor("#ffffff")
