from __future__ import annotations

import json
import sys
from pathlib import Path

from platformdirs import user_config_dir

from PySide6.QtCore import QSize, Qt
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

from linuxeasyconfig.core.module_loader import (
    USER_MODULES_DIRECTORY,
)
from linuxeasyconfig.core.module_manager import ModuleManager
from linuxeasyconfig.core.registries import (
    CapabilityRegistry,
    FeatureRegistry,
    LocalServiceRegistry,
    ViewRegistry,
)
from linuxeasyconfig.core.view_renderer import ViewRenderError, ViewRenderer
from linuxeasyconfig.core.theme import apply_appearance


STARTUP_FEATURE_ID = "lec_settings.main"


class MainWindow(QMainWindow):
    def __init__(
        self,
        feature_registry: FeatureRegistry,
        view_registry: ViewRegistry,
        feature_module_paths: dict[str, Path],
    ) -> None:
        super().__init__()

        self._feature_registry = feature_registry
        self._view_registry = view_registry
        self._feature_module_paths = feature_module_paths
        self._renderer = ViewRenderer()
        self._view_indexes: dict[str, int] = {}
        self._navigation_icon_size = _saved_icon_size()

        self.setWindowTitle("Linux Easy Config")
        self.resize(1180, 760)

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
        self.apply_navigation_icon_size(
            self._navigation_icon_size
        )
        self._feature_list.currentItemChanged.connect(
            self._on_feature_selected
        )
        self._select_startup_feature()

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

            icon = self._resolve_feature_icon(
                feature.id,
                feature.icon,
            )
            if not icon.isNull():
                item.setIcon(icon)
                item.setData(
                    Qt.ItemDataRole.UserRole + 1,
                    icon,
                )

            self._feature_list.addItem(item)

    def apply_navigation_icon_size(
        self,
        value: str,
    ) -> None:
        normalized = str(value).strip().lower()

        if normalized not in {"none", "small", "large"}:
            normalized = "small"

        self._navigation_icon_size = normalized

        if normalized == "large":
            icon_size = QSize(32, 32)
            feature_height = 40
            category_height = 24
        elif normalized == "none":
            icon_size = QSize(1, 1)
            feature_height = 26
            category_height = 22
        else:
            icon_size = QSize(20, 20)
            feature_height = 28
            category_height = 22

        self._feature_list.setIconSize(icon_size)

        for row in range(self._feature_list.count()):
            item = self._feature_list.item(row)
            feature_id = item.data(
                Qt.ItemDataRole.UserRole
            )

            if feature_id:
                stored_icon = item.data(
                    Qt.ItemDataRole.UserRole + 1
                )

                if normalized == "none":
                    item.setIcon(QIcon())
                elif isinstance(stored_icon, QIcon):
                    item.setIcon(stored_icon)

                item.setSizeHint(
                    QSize(0, feature_height)
                )
            else:
                item.setSizeHint(
                    QSize(0, category_height)
                )

    def _select_startup_feature(self) -> None:
        for row in range(self._feature_list.count()):
            item = self._feature_list.item(row)

            if (
                item.data(Qt.ItemDataRole.UserRole)
                == STARTUP_FEATURE_ID
            ):
                self._feature_list.setCurrentItem(item)
                return

    def _resolve_feature_icon(
        self,
        feature_id: str,
        theme_icon_name: str,
    ) -> QIcon:
        module_path = self._feature_module_paths.get(feature_id)

        if module_path is not None:
            for filename in (
                "icon.svg",
                "icon.png",
                "icon.webp",
                "icon.jpg",
                "icon.jpeg",
            ):
                icon_path = module_path / filename
                if icon_path.is_file():
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        return icon

        if theme_icon_name:
            themed = QIcon.fromTheme(theme_icon_name)
            if not themed.isNull():
                return themed

        return QIcon.fromTheme("applications-system")

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




def _saved_icon_size() -> str:
    settings_path = (
        Path(user_config_dir("linuxeasyconfig"))
        / "settings.json"
    )

    try:
        settings = json.loads(
            settings_path.read_text(encoding="utf-8")
        )
        value = str(
            settings.get("icon_size", "small")
        ).strip().lower()
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        value = "small"

    if value not in {"none", "small", "large"}:
        return "small"

    return value


def _apply_saved_appearance(
    application: QApplication,
) -> None:
    settings_path = (
        Path(user_config_dir("linuxeasyconfig"))
        / "settings.json"
    )

    try:
        settings = json.loads(
            settings_path.read_text(encoding="utf-8")
        )
        appearance = str(
            settings.get("appearance", "system")
        ).strip().lower()
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        appearance = "system"

    apply_appearance(application, appearance)


def main() -> int:
    app = QApplication(sys.argv)
    _apply_saved_appearance(app)

    feature_registry = FeatureRegistry()
    view_registry = ViewRegistry()
    capability_registry = CapabilityRegistry()
    service_registry = LocalServiceRegistry()

    module_manager = ModuleManager(
        feature_registry,
        view_registry,
        capability_registry,
        service_registry,
    )

    modules_directory = (
        Path(__file__).resolve().parent / "modules"
    )
    result = module_manager.load_from_directory(
        modules_directory,
        USER_MODULES_DIRECTORY,
    )

    window = MainWindow(
        feature_registry,
        view_registry,
        module_manager.feature_module_paths(),
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
