from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
)

from linuxeasyconfig.core.module_manager import ModuleManager
from linuxeasyconfig.core.registries import FeatureRegistry, ViewRegistry
from linuxeasyconfig.core.view_renderer import ViewRenderError, ViewRenderer


class MainWindow(QMainWindow):
    def __init__(
        self,
        feature_registry: FeatureRegistry,
        view_registry: ViewRegistry,
    ) -> None:
        super().__init__()

        self._feature_registry = feature_registry
        self._view_registry = view_registry
        self._renderer = ViewRenderer()
        self._view_indexes: dict[str, int] = {}

        self.setWindowTitle("Linux Easy Config")
        self.resize(1000, 650)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._feature_list = QListWidget()
        self._feature_list.setMinimumWidth(240)
        self._feature_list.setMaximumWidth(360)

        self._view_stack = QStackedWidget()

        welcome = QLabel("Select a feature from the list to begin.")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("font-size: 16px;")
        self._view_stack.addWidget(welcome)

        splitter.addWidget(self._feature_list)
        splitter.addWidget(self._view_stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self._populate_features()
        self._feature_list.currentItemChanged.connect(
            self._on_feature_selected
        )

    def _populate_features(self) -> None:
        features = sorted(
            self._feature_registry.all(),
            key=lambda feature: (
                feature.category.lower(),
                feature.title.lower(),
            ),
        )

        current_category: str | None = None

        for feature in features:
            if feature.category != current_category:
                category_item = QListWidgetItem(feature.category)
                category_item.setFlags(Qt.ItemFlag.NoItemFlags)
                category_item.setData(
                    Qt.ItemDataRole.UserRole,
                    None,
                )

                font = category_item.font()
                font.setBold(True)
                category_item.setFont(font)

                self._feature_list.addItem(category_item)
                current_category = feature.category

            item = QListWidgetItem(feature.title)
            item.setData(
                Qt.ItemDataRole.UserRole,
                feature.id,
            )
            item.setToolTip(feature.description)

            if feature.icon:
                item.setIcon(QIcon.fromTheme(feature.icon))

            self._feature_list.addItem(item)

    def _on_feature_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous

        if current is None:
            return

        feature_id = current.data(Qt.ItemDataRole.UserRole)

        if not feature_id:
            return

        feature = self._feature_registry.get(str(feature_id))

        if feature is None:
            return

        if feature.target_type != "view":
            QMessageBox.information(
                self,
                "Feature Not Available",
                (
                    "LEC does not yet support feature target type "
                    f"{feature.target_type!r}."
                ),
            )
            return

        view = self._view_registry.get(feature.target_id)

        if view is None:
            QMessageBox.warning(
                self,
                "View Not Found",
                (
                    f"The feature {feature.title!r} refers to a view "
                    "that is not registered."
                ),
            )
            return

        if view.id not in self._view_indexes:
            try:
                widget = self._renderer.render(view)
            except ViewRenderError as exc:
                QMessageBox.critical(
                    self,
                    "View Could Not Be Displayed",
                    str(exc),
                )
                return

            index = self._view_stack.addWidget(widget)
            self._view_indexes[view.id] = index

        self._view_stack.setCurrentIndex(
            self._view_indexes[view.id]
        )


def main() -> int:
    app = QApplication(sys.argv)

    feature_registry = FeatureRegistry()
    view_registry = ViewRegistry()
    module_manager = ModuleManager(
        feature_registry,
        view_registry,
    )

    modules_directory = (
        Path(__file__).resolve().parent / "modules"
    )
    result = module_manager.load_from_directory(
        modules_directory
    )

    window = MainWindow(
        feature_registry,
        view_registry,
    )
    window.show()

    if result.load_errors or result.registration_errors:
        messages: list[str] = []

        for error in result.load_errors:
            messages.append(
                f"{error.module_path.name}: {error.message}"
            )

        for error in result.registration_errors:
            messages.append(
                f"{error.module_id}: {error.message}"
            )

        QMessageBox.warning(
            window,
            "Some Modules Could Not Be Loaded",
            "\n\n".join(messages),
        )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
