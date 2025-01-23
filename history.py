# -*- coding: utf-8 -*-
# 

import json

from aqt.qt import *
from aqt.utils import askUser, showInfo
import datetime
from .miutils import miInfo, miAsk
from anki.utils import strip_html, is_win, is_mac, is_lin


class HistoryModel(QAbstractTableModel):

    def __init__(self, history, parent=None):
        super(HistoryModel, self).__init__(parent)
        self.history = history
        self.dictInt = parent
        self.justTerms = [item[0] for item in history]

    def rowCount(self, index=QModelIndex()):
        return len(self.history)

    def columnCount(self, index=QModelIndex()):
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

    def insertRows(self, position= False, rows=1, index=QModelIndex(), term = False, date = False):
        if not position:
            position = self.rowCount()
        self.beginInsertRows(QModelIndex(), position, position)
        for row in range(rows):
            if term and date:
                if term in self.justTerms:
                    index = self.justTerms.index(term)
                    self.removeRows(index)
                    del self.justTerms[index]
                self.history.insert(0, [term, date])
                self.justTerms.insert(0, term)
        self.endInsertRows()
        self.dictInt.saveHistory()
        return True

    def removeRows(self, position, rows=1, index=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), position, position + rows - 1)
        del self.history[position:position+rows]
        self.endRemoveRows()
        self.dictInt.saveHistory()
        return True


class HistoryBrowser(QWidget):
    def __init__(self, historyModel, parent):
        super(HistoryBrowser, self).__init__(parent, Qt.WindowType.Window)
        self.history_model = None
        self.setAutoFillBackground(True)
        self.resize(300, 200)
        self.tableView = QTableView()
        self.model = historyModel
        self.dictInt = parent
        self.tableView.setModel(self.model)
        self.clearHistory = QPushButton('Clear History')
        self.clearHistory.clicked.connect(self.deleteHistory)
        self.tableView.doubleClicked.connect(self.searchAgain)
        self.setupTable()
        self.layout = self.getLayout()
        self.setLayout(self.layout)
        self.setColors()
        self.history_model = self.history_model
        self.dictInt = self.dictInt
        self.setup_ui()  # Call the setup_ui method
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)

    def setup_ui(self):
        """
        Set up the user interface components for the history browser.
        """
        # Ensure the table view is properly set up
        self.setupTable()

        # Set up the layout
        self.layout = self.getLayout()
        self.setLayout(self.layout)

        # Set the colors based on the active theme
        self.setColors()

    def setupTable(self):
        tableHeader = self.tableView.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.horizontalHeader().hide()

    def searchAgain(self):
        date = str(datetime.date.today())
        term = self.model.index(self.tableView.selectionModel().currentIndex().row(), 0).data()
        self.model.insertRows(term=term, date=date)
        self.dictInt.initSearch(term)

    def setColors(self):
        """
        Set the colors for the history browser based on the active theme.
        """
        # Load the background color from the active theme
        background_color = self.dictInt.load_theme_color("background")
        print(f"Background color: {background_color}, Type: {type(background_color)}")  # Debug statement

        # Create a QPalette object and set the background color
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, background_color)

        # Apply the palette to the history browser
        self.setPalette(palette)
        self.setStyleSheet(self.dictInt.theme_manager.get_qt_styles(is_mac=is_mac))  # Reapply stylesheet
        self.update()  # Force the widget to repaint

        print("History browser colors updated.")  # Debug statement

    def deleteHistory(self):
        if miAsk('Clearing your history cannot be undone. Would you like to proceed?', self):
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