from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


def main() -> int:
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("Linux Easy Config")
    window.resize(900, 600)

    label = QLabel("Linux Easy Config is running.")
    label.setStyleSheet("font-size: 20px; padding: 24px;")
    window.setCentralWidget(label)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
