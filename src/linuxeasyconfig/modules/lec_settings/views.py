from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask
from linuxeasyconfig.core.theme import apply_appearance

from .module_management import ModuleManagementRepository
from .overview_repository import OverviewRepository
from .repository import RecoveryRepository, RecoveryRevision
from .settings import LECSettings, load_settings, save_settings


class _RestoreSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _RestoreWorker(QRunnable):
    def __init__(
        self,
        revision: RecoveryRevision,
    ) -> None:
        super().__init__()
        self._revision = revision
        self.signals = _RestoreSignals()

    def run(self) -> None:
        try:
            task = PrivilegedTask(
                task_id="lec_settings.restore",
                arguments={
                    "module_id": self._revision.module_id,
                    "revision": self._revision.revision,
                    "destination": str(
                        self._revision.destination
                    ),
                    "backup_path": (
                        str(self._revision.backup_path)
                        if self._revision.backup_path
                        else ""
                    ),
                    "restore_mode": (
                        self._revision.restore_mode
                    ),
                },
            )
            message = PrivilegedRunner().run(task)
            self.signals.succeeded.emit(message)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class LECSettingsView(QWidget):
    def __init__(
        self,
        overview_repository: OverviewRepository,
        recovery_repository: RecoveryRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._overview_repository = overview_repository
        self._recovery_repository = recovery_repository
        self._module_management = ModuleManagementRepository()
        self._settings = load_settings()

        heading = QLabel("LEC Settings")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "View Linux Easy Config information, change application "
            "preferences, and recover previous configuration revisions."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview_tab(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_settings_tab(),
            "Settings",
        )
        self._recovery_tab = RecoveryTab(
            recovery_repository
        )
        self._tabs.addTab(
            self._recovery_tab,
            "Recovery",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

    def _build_overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(14)

        information = self._overview_repository.information()

        application = QGroupBox("Application")
        form = QFormLayout(application)
        form.addRow(
            "LEC version:",
            QLabel(information.lec_version),
        )
        form.addRow(
            "Python version:",
            QLabel(information.python_version),
        )
        form.addRow(
            "Operating system:",
            QLabel(information.operating_system),
        )
        install_path = QLabel(
            information.installation_path
        )
        install_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow(
            "Installation path:",
            install_path,
        )
        form.addRow(
            "Installed modules:",
            QLabel(str(information.loaded_module_count)),
        )

        module_group = QGroupBox("Installed Modules")
        module_layout = QVBoxLayout(module_group)

        table = QTableWidget(
            len(information.modules),
            6,
        )
        table.setHorizontalHeaderLabels(
            [
                "Module",
                "Version",
                "Module ID",
                "Source",
                "Status",
                "Path",
            ]
        )
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.Stretch,
        )

        for row, module in enumerate(
            information.modules
        ):
            values = (
                module.name,
                module.version,
                module.module_id,
                module.source_type,
                module.status,
                module.path,
            )

            for column, value in enumerate(values):
                table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        module_layout.addWidget(table)

        layout.addWidget(application)
        layout.addWidget(module_group, 1)
        return page

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(14)

        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(
            appearance_group
        )

        self._appearance = QComboBox()
        self._appearance.addItem(
            "Use system appearance",
            "system",
        )
        self._appearance.addItem(
            "Light mode",
            "light",
        )
        self._appearance.addItem(
            "Dark mode",
            "dark",
        )
        current_index = self._appearance.findData(
            self._settings.appearance
        )
        self._appearance.setCurrentIndex(
            max(current_index, 0)
        )
        appearance_form.addRow(
            "Color mode:",
            self._appearance,
        )

        self._icon_size = QComboBox()
        self._icon_size.addItem(
            "No module icons",
            "none",
        )
        self._icon_size.addItem(
            "Small",
            "small",
        )
        self._icon_size.addItem(
            "Large",
            "large",
        )
        icon_size_index = self._icon_size.findData(
            self._settings.icon_size
        )
        self._icon_size.setCurrentIndex(
            max(icon_size_index, 1)
        )
        appearance_form.addRow(
            "Module icon size:",
            self._icon_size,
        )

        behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(
            behavior_group
        )

        self._confirm_destructive = QCheckBox(
            "Confirm destructive operations"
        )
        self._confirm_destructive.setChecked(
            self._settings.confirm_destructive_actions
        )

        self._show_advanced = QCheckBox(
            "Show advanced options when modules support them"
        )
        self._show_advanced.setChecked(
            self._settings.show_advanced_options
        )

        behavior_layout.addWidget(
            self._confirm_destructive
        )
        behavior_layout.addWidget(
            self._show_advanced
        )

        note = QLabel(
            "LEC always opens to this module's Overview tab. "
            "Additional application-wide settings can be added here "
            "as they are defined."
        )
        note.setWordWrap(True)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(
            self._save_settings
        )

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(save_button)

        module_group = QGroupBox("Modules")
        module_layout = QVBoxLayout(module_group)

        module_note = QLabel(
            "Install optional .lec modules or remove modules "
            "previously installed by the current user. Bundled "
            "modules cannot be removed. A custom module may "
            "override a bundled module with the same module ID."
        )
        module_note.setWordWrap(True)

        add_module_button = QPushButton("Add .lec Module")
        add_module_button.clicked.connect(self._add_module)

        remove_module_button = QPushButton("Remove Custom Module")
        remove_module_button.clicked.connect(self._remove_module)

        module_buttons = QHBoxLayout()
        module_buttons.addWidget(add_module_button)
        module_buttons.addWidget(remove_module_button)
        module_buttons.addStretch(1)

        module_layout.addWidget(module_note)
        module_layout.addLayout(module_buttons)

        layout.addWidget(appearance_group)
        layout.addWidget(behavior_group)
        layout.addWidget(module_group)
        layout.addWidget(note)
        layout.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _add_module(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Add LEC Module",
            str(Path.home()),
            "LEC Modules (*.lec)",
        )

        if not filename:
            return

        try:
            candidate = self._module_management.inspect_import(
                Path(filename)
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Invalid LEC Module",
                str(exc),
            )
            return

        warnings: list[str] = []
        if candidate.overrides_builtin:
            warnings.append(
                "This module has the same module ID as a bundled "
                "LEC module. Installing it will override the bundled "
                "module after LEC restarts. The bundled copy remains "
                "installed and becomes active again if this custom "
                "override is removed."
            )
        if candidate.replaces_custom:
            warnings.append(
                "A custom module with this module ID is already "
                "installed and will be replaced."
            )

        if warnings:
            response = QMessageBox.warning(
                self,
                "Confirm Module Replacement",
                (
                    f"Module: {candidate.name}\n"
                    f"Version: {candidate.version}\n"
                    f"Module ID: {candidate.module_id}\n\n"
                    + "\n\n".join(warnings)
                    + "\n\nAn incompatible module can prevent LEC "
                    "or related modules from loading. Continue?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return

        try:
            destination = self._module_management.install(candidate)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Module Installation Failed",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Module Installed",
            (
                f"{candidate.name} was installed to:\n"
                f"{destination}\n\n"
                "Restart Linux Easy Config to load the module."
            ),
        )

    def _remove_module(self) -> None:
        modules = self._module_management.custom_modules()

        if not modules:
            QMessageBox.information(
                self,
                "No Custom Modules",
                "There are no custom modules to remove.",
            )
            return

        labels = [module.display_name for module in modules]
        selection, accepted = QInputDialog.getItem(
            self,
            "Remove Custom Module",
            "Select a custom module:",
            labels,
            0,
            False,
        )

        if not accepted:
            return

        try:
            module = modules[labels.index(selection)]
        except ValueError:
            return

        detail = f"Remove {module.name} ({module.version})?\n\n"
        if module.overrides_builtin:
            detail += (
                "The bundled module it overrides will become active "
                "again after LEC restarts."
            )
        else:
            detail += (
                "The module will no longer be available after LEC "
                "restarts."
            )

        response = QMessageBox.question(
            self,
            "Confirm Module Removal",
            detail,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            self._module_management.remove(module)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Module Removal Failed",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Module Removed",
            (
                f"{module.name} was removed.\n\n"
                "Restart Linux Easy Config to apply the change."
            ),
        )

    def _save_settings(self) -> None:
        self._settings = LECSettings(
            appearance=str(
                self._appearance.currentData()
            ),
            icon_size=str(
                self._icon_size.currentData()
            ),
            confirm_destructive_actions=(
                self._confirm_destructive.isChecked()
            ),
            show_advanced_options=(
                self._show_advanced.isChecked()
            ),
        )
        save_settings(self._settings)
        application = QApplication.instance()
        apply_appearance(
            application,
            self._settings.appearance,
        )

        if application is not None:
            for window in application.topLevelWidgets():
                apply_method = getattr(
                    window,
                    "apply_navigation_icon_size",
                    None,
                )

                if callable(apply_method):
                    apply_method(
                        self._settings.icon_size
                    )

        QMessageBox.information(
            self,
            "Settings Saved",
            "LEC settings were saved.",
        )


class RecoveryTab(QWidget):
    def __init__(
        self,
        repository: RecoveryRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._revisions: list[RecoveryRevision] = []
        self._selected: RecoveryRevision | None = None
        self._active_worker: _RestoreWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        description = QLabel(
            "Review files changed by Linux Easy Config and restore "
            "an earlier snapshot. Restoring a snapshot creates a new "
            "backup of the current state first."
        )
        description.setWordWrap(True)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            [
                "Time",
                "Module",
                "Operation",
                "Destination",
                "Revision",
            ]
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.itemSelectionChanged.connect(
            self._selection_changed
        )

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._preview.setPlaceholderText(
            "Select a revision to inspect its backup."
        )

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._table)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 330])

        self._status = QLabel()
        self._status.setWordWrap(True)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.reload)

        self._protected_preview_button = QPushButton(
            "Load Protected Preview"
        )
        self._protected_preview_button.setEnabled(False)
        self._protected_preview_button.clicked.connect(
            self._load_protected_preview
        )

        self._restore_button = QPushButton(
            "Revert To Selected Snapshot"
        )
        self._restore_button.setEnabled(False)
        self._restore_button.clicked.connect(
            self._begin_restore
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self._status, 1)
        buttons.addWidget(refresh_button)
        buttons.addWidget(
            self._protected_preview_button
        )
        buttons.addWidget(self._restore_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(description)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

        self.reload()

    def reload(self) -> None:
        self._selected = None
        self._restore_button.setEnabled(False)
        self._protected_preview_button.setEnabled(False)
        self._preview.clear()
        self._revisions = self._repository.revisions()

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._revisions))

        for row_number, revision in enumerate(
            self._revisions
        ):
            values = (
                revision.display_timestamp,
                _friendly_module_name(
                    revision.module_id
                ),
                revision.operation,
                str(revision.destination),
                str(revision.revision),
            )

            for column_number, value in enumerate(
                values
            ):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    revision.key,
                )
                self._table.setItem(
                    row_number,
                    column_number,
                    item,
                )

        self._table.setSortingEnabled(True)
        self._status.setText(
            f"{len(self._revisions)} revisions available."
        )

    def _selection_changed(self) -> None:
        selected_rows = (
            self._table.selectionModel().selectedRows()
        )

        if not selected_rows:
            self._selected = None
            self._restore_button.setEnabled(False)
            self._protected_preview_button.setEnabled(False)
            self._preview.clear()
            return

        key_item = self._table.item(
            selected_rows[0].row(),
            0,
        )

        if key_item is None:
            return

        key = key_item.data(Qt.ItemDataRole.UserRole)
        self._selected = next(
            (
                revision
                for revision in self._revisions
                if revision.key == key
            ),
            None,
        )

        if self._selected is None:
            return

        self._preview.setPlainText(
            self._repository.preview_text(
                self._selected
            )
        )
        self._protected_preview_button.setEnabled(
            self._selected.restore_mode == "file"
            and self._selected.backup_available
        )
        self._restore_button.setEnabled(
            self._selected.restore_mode
            in {"file", "delete"}
            and (
                self._selected.restore_mode == "delete"
                or self._selected.backup_available
            )
        )

    def _load_protected_preview(self) -> None:
        revision = self._selected

        if (
            revision is None
            or revision.backup_path is None
            or revision.restore_mode != "file"
        ):
            return

        try:
            preview = PrivilegedRunner().run(
                PrivilegedTask(
                    task_id="lec_settings.preview",
                    arguments={
                        "module_id": revision.module_id,
                        "revision": revision.revision,
                        "destination": str(
                            revision.destination
                        ),
                        "backup_path": str(
                            revision.backup_path
                        ),
                    },
                ),
                timeout=90,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Backup Preview Failed",
                str(exc),
            )
            return

        self._preview.setPlainText(str(preview))

    def _begin_restore(self) -> None:
        revision = self._selected

        if revision is None:
            return

        later = self._repository.later_revisions_for_file(
            revision
        )
        warning = (
            f"Restore revision {revision.revision} for:\n\n"
            f"{revision.destination}\n\n"
        )

        if later:
            warning += (
                f"This will supersede {len(later)} later "
                "revision(s) for this file.\n\n"
            )

        warning += (
            "LEC will back up the current state before restoring."
        )

        answer = QMessageBox.question(
            self,
            "Confirm Recovery",
            warning,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)
        worker = _RestoreWorker(revision)
        self._active_worker = worker
        worker.signals.succeeded.connect(
            self._restore_succeeded
        )
        worker.signals.failed.connect(
            self._restore_failed
        )
        worker.signals.finished.connect(
            self._restore_finished
        )
        self._thread_pool.start(worker)

    def _set_busy(self, busy: bool) -> None:
        self._table.setEnabled(not busy)
        self._restore_button.setEnabled(not busy)
        self._protected_preview_button.setEnabled(
            not busy
        )
        self._status.setText(
            "Restoring configuration..."
            if busy
            else ""
        )

    def _restore_succeeded(self, message: str) -> None:
        QMessageBox.information(
            self,
            "Recovery Complete",
            message,
        )
        self.reload()

    def _restore_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Recovery Failed",
            message,
        )

    def _restore_finished(self) -> None:
        self._active_worker = None
        self._set_busy(False)



def _friendly_module_name(module_id: str) -> str:
    value = module_id.rsplit(".", 1)[-1]
    return value.replace("_", " ").title()
