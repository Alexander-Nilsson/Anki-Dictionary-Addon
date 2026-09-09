#


import datetime

from aqt.qt import (
    QAbstractItemView,
    QAbstractTableModel,
    QHBoxLayout,
    QHeaderView,
    QKeySequence,
    QModelIndex,
    QPushButton,
    QShortcut,
    Qt,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from .common import miAsk


class HistoryModel(QAbstractTableModel):
    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self.dictInt = parent
        self.justTerms = [item[0] for item in history]

    def rowCount(self, index=QModelIndex()):  # noqa: B008  # ty:ignore[invalid-method-override]
        return len(self.history)

    def columnCount(self, index=QModelIndex()):  # noqa: B008  # ty:ignore[invalid-method-override]
        return 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if not 0 <= index.row() < len(self.history):
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            term = self.history[index.row()][0]
            date = self.history[index.row()][1]

            if index.column() == 0:
                return term
            elif index.column() == 1:
                return date
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        return None

    def insertRows(
        self,
        position=False,
        rows=1,
        index=QModelIndex(),  # noqa: B008
        term=False,
        date=False,
    ):  # ty:ignore[invalid-method-override]
        if not position:
            position = self.rowCount()
        self.beginInsertRows(QModelIndex(), position, position)
        for _row in range(rows):
            if term and date:
                if term in self.justTerms:
                    index = self.justTerms.index(term)
                    self.removeRows(index)
                    del self.justTerms[index]
                self.history.insert(0, [term, date])
                self.justTerms.insert(0, term)
        self.endInsertRows()
        self.dictInt.saveHistory()  # ty:ignore[unresolved-attribute]
        return True

    def removeRows(self, position, rows=1, index=QModelIndex()):  # noqa: B008  # ty:ignore[invalid-method-override]
        self.beginRemoveRows(QModelIndex(), position, position + rows - 1)
        del self.history[position : position + rows]
        self.endRemoveRows()
        self.dictInt.saveHistory()  # ty:ignore[unresolved-attribute]
        return True


class HistoryBrowser(QWidget):
    def __init__(self, historyModel, parent):
        super().__init__(parent, Qt.WindowType.Window)
        self.history_model = None
        self.setAutoFillBackground(True)
        self.resize(460, 360)
        self.setMinimumSize(320, 240)
        self.tableView = QTableView()
        self.model = historyModel
        self.dictInt = parent
        self.tableView.setModel(self.model)
        self.clearHistory = QPushButton("Clear History")
        self.clearHistory.clicked.connect(self.deleteHistory)
        self.tableView.doubleClicked.connect(self.searchAgain)
        self.setupTable()
        self.main_layout = self.getLayout()
        self.setLayout(self.main_layout)
        self.setColors()
        # These were previously self-assignments (no-ops) - kept as comments for reference
        pass
        self.setup_ui()  # Call the setup_ui method
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)

    def setup_ui(self):
        """
        Set up the user interface components for the history browser.
        """
        # Set the colors based on the active theme
        self.setColors()

    def setupTable(self):
        tableHeader = self.tableView.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # ty:ignore[unresolved-attribute]
        self.tableView.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.tableView.horizontalHeader().hide()  # ty:ignore[unresolved-attribute]

    def searchAgain(self):
        date = str(datetime.date.today())
        term = self.model.index(
            self.tableView.selectionModel().currentIndex().row(),  # ty:ignore[unresolved-attribute]
            0,
        ).data()
        self.model.insertRows(term=term, date=date)
        self.dictInt.initSearch(term)

    def setColors(self):
        """
        Theme the history browser to match the active dictionary theme.

        The browser is a separate top-level window, so it does not inherit the
        dictionary window's stylesheet. This builds a full Qt stylesheet from
        the active ``ThemeColors`` — window background, table, header, cells,
        selection and the footer button — mirroring ``theme_controller``'s
        design (rounded borders, the tab gradient for the button, etc.).
        """
        theme = self.dictInt.theme_manager.get_active_theme()

        # Brightness-aware hues for the hover/selection surfaces.
        from ..ui.theme_controller import hex_to_rgba

        border_soft = hex_to_rgba(theme.border, 0.6)

        sheet = f"""
        QWidget {{
            background-color: {theme.header_background};
            color: {theme.header_text};
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
        }}
        QTableView {{
            background-color: {theme.definition_background};
            color: {theme.definition_text};
            border: 1px solid {theme.border};
            border-radius: 8px;
            gridline-color: {theme.border};
            selection-background-color: {theme.search_term};
            selection-color: white;
            outline: none;
        }}
        QTableView::item {{
            padding: 6px 10px;
            border-bottom: 1px solid {border_soft};
        }}
        QTableView::item:hover {{
            background-color: {theme.tab_hover};
        }}
        QTableView::item:selected {{
            background-color: {theme.search_term};
            color: white;
            border-radius: 4px;
        }}
        QHeaderView {{
            background: transparent;
            border: none;
        }}
        QHeaderView::section {{
            background-color: {theme.selector};
            color: {theme.header_text};
            border-right: 1px solid {theme.border};
            border-bottom: 1px solid {theme.border};
            padding: 6px 10px;
            font-weight: 600;
        }}
        QPushButton {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {theme.current_tab_gradient_top},
                stop: 1 {theme.current_tab_gradient_bottom});
            color: {theme.anki_button_text};
            border: 1px solid {theme.border};
            border-radius: 6px;
            padding: 5px 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            border: 1.5px solid {theme.search_term};
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 {theme.current_tab_gradient_bottom},
                stop: 1 {theme.current_tab_gradient_top});
        }}
        QToolTip {{
            background-color: {theme.selector};
            color: {theme.header_text};
            border: 1px solid {theme.border};
            padding: 3px 6px;
        }}
        """
        self.setStyleSheet(sheet)
        self.update()  # Force the widget to repaint

    def deleteHistory(self):
        if miAsk(
            "Clearing your history cannot be undone. Would you like to proceed?", self
        ):
            self.model.removeRows(0, len(self.model.history))

    def getLayout(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.tableView)
        hbox = QHBoxLayout()
        self.clearHistory.setFixedSize(100, 30)
        hbox.addStretch()
        hbox.addWidget(self.clearHistory)
        vbox.addLayout(hbox)
        vbox.setContentsMargins(2, 2, 2, 2)
        return vbox
