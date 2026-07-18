from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


DARK_STYLESHEET = """
QMainWindow,
QWidget {
    background-color: #1b1b21;
    color: #f4f4f6;
}

QTabWidget::pane {
    border: 1px solid #34343d;
    background-color: #18181d;
    top: -1px;
}

QTabBar::tab {
    background-color: #24242b;
    color: #e8e8ec;
    border: 1px solid #3a3a45;
    border-bottom: none;
    padding: 7px 14px;
    margin-right: 2px;
}

QTabBar::tab:hover {
    background-color: #303039;
}

QTabBar::tab:selected {
    background-color: #4f46b8;
    color: #ffffff;
    border-color: #766ee0;
}

QGroupBox {
    border: 1px solid #34343d;
    border-radius: 3px;
    margin-top: 8px;
    padding-top: 8px;
    background-color: #1f1f25;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QTableWidget,
QTableView,
QTreeWidget,
QListWidget,
QPlainTextEdit,
QTextEdit,
QLineEdit,
QComboBox {
    background-color: #101014;
    color: #f4f4f6;
    border: 1px solid #363640;
    selection-background-color: #4f46b8;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #26262d;
    color: #f4f4f6;
    border: 1px solid #3a3a45;
    padding: 4px;
}

QPushButton {
    background-color: #292931;
    color: #f4f4f6;
    border: 1px solid #444450;
    border-radius: 3px;
    padding: 5px 10px;
}

QPushButton:hover {
    background-color: #35353f;
}

QPushButton:pressed {
    background-color: #4f46b8;
}

QComboBox QAbstractItemView {
    background-color: #101014;
    color: #f4f4f6;
    selection-background-color: #4f46b8;
}

QScrollBar:vertical,
QScrollBar:horizontal {
    background: #18181d;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #3a3a45;
    min-height: 20px;
    min-width: 20px;
}
"""


def apply_appearance(
    application: QApplication | None,
    appearance: str,
) -> None:
    if application is None:
        return

    normalized = appearance.strip().lower()

    if normalized == "dark":
        application.setStyle("Fusion")

        palette = QPalette()
        palette.setColor(
            QPalette.ColorRole.Window,
            QColor("#1b1b21"),
        )
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor("#f4f4f6"),
        )
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor("#101014"),
        )
        palette.setColor(
            QPalette.ColorRole.AlternateBase,
            QColor("#1f1f25"),
        )
        palette.setColor(
            QPalette.ColorRole.Text,
            QColor("#f4f4f6"),
        )
        palette.setColor(
            QPalette.ColorRole.Button,
            QColor("#292931"),
        )
        palette.setColor(
            QPalette.ColorRole.ButtonText,
            QColor("#f4f4f6"),
        )
        palette.setColor(
            QPalette.ColorRole.Highlight,
            QColor("#4f46b8"),
        )
        palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor("#ffffff"),
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipBase,
            QColor("#1f1f25"),
        )
        palette.setColor(
            QPalette.ColorRole.ToolTipText,
            QColor("#ffffff"),
        )

        application.setPalette(palette)
        application.setStyleSheet(DARK_STYLESHEET)
        return

    application.setStyleSheet("")

    if normalized == "light":
        application.setStyle("Fusion")
        application.setPalette(
            application.style().standardPalette()
        )
        return

    application.setPalette(QPalette())
