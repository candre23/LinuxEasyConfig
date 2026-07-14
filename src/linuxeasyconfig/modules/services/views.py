from __future__ import annotations

import getpass
import os
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.config.systemd_unit import SystemdUnit
from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask
from linuxeasyconfig.widgets.data_table import DataTable

from .provider import ServicesTableProvider


_SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.@-]+$")


class _InstallSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _InstallWorker(QRunnable):
    """Install one generated service without blocking the Qt interface."""

    def __init__(
        self,
        *,
        staged_path: Path,
        service_name: str,
        enable_at_startup: bool,
        start_immediately: bool,
    ) -> None:
        super().__init__()

        self._staged_path = staged_path
        self._service_name = service_name
        self._enable_at_startup = enable_at_startup
        self._start_immediately = start_immediately
        self.signals = _InstallSignals()

    def run(self) -> None:
        try:
            task = PrivilegedTask(
                task_id="services.install",
                arguments={
                    "source": str(self._staged_path),
                    "service_name": self._service_name,
                    "enable_at_startup": self._enable_at_startup,
                    "start_immediately": self._start_immediately,
                },
            )

            message = PrivilegedRunner().run(task)
            self._safe_emit(self.signals.succeeded, message)
        except Exception as exc:
            self._safe_emit(self.signals.failed, str(exc))
        finally:
            self._staged_path.unlink(missing_ok=True)
            self._safe_emit(self.signals.finished)

    @staticmethod
    def _safe_emit(signal: Any, *arguments: Any) -> None:
        try:
            signal.emit(*arguments)
        except RuntimeError:
            pass


class _RemoveSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _RemoveWorker(QRunnable):
    """Remove one service without blocking the Qt interface."""

    def __init__(
        self,
        *,
        service_name: str,
        stop_service: bool,
        disable_at_startup: bool,
    ) -> None:
        super().__init__()

        self._service_name = service_name
        self._stop_service = stop_service
        self._disable_at_startup = disable_at_startup
        self.signals = _RemoveSignals()

    def run(self) -> None:
        try:
            task = PrivilegedTask(
                task_id="services.remove",
                arguments={
                    "service_name": self._service_name,
                    "stop_service": self._stop_service,
                    "disable_at_startup": self._disable_at_startup,
                },
            )

            message = PrivilegedRunner().run(task)
            self._safe_emit(self.signals.succeeded, message)
        except Exception as exc:
            self._safe_emit(self.signals.failed, str(exc))
        finally:
            self._safe_emit(self.signals.finished)

    @staticmethod
    def _safe_emit(signal: Any, *arguments: Any) -> None:
        try:
            signal.emit(*arguments)
        except RuntimeError:
            pass


class RemoveServiceDialog(QDialog):
    """Final removal options for one selected service."""

    def __init__(
        self,
        row: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Remove Background Service")
        self.setModal(True)
        self.resize(520, 300)

        service_name = str(row.get("name", "Unknown"))
        description = str(row.get("description", ""))
        status = str(row.get("status", "Unknown"))
        startup = str(row.get("startup", "Unknown"))
        unit_path = str(row.get("unit_file_path", ""))

        heading = QLabel(f"Remove {service_name}?")
        heading.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        details = QLabel(
            f"<b>Description:</b> {description}<br>"
            f"<b>Status:</b> {status}<br>"
            f"<b>Startup:</b> {startup}<br>"
            f"<b>Definition:</b> {unit_path}"
        )
        details.setWordWrap(True)
        details.setTextInteractionFlags(
            details.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        backup_notice = QLabel(
            "Before the service definition is deleted, LEC will create "
            "a verified, versioned backup and record the removal in the "
            "audit log."
        )
        backup_notice.setWordWrap(True)

        self._stop_service = QCheckBox(
            "Stop the service before removal"
        )
        self._stop_service.setChecked(
            str(row.get("active_state", "")) == "active"
        )

        self._disable_startup = QCheckBox(
            "Disable automatic startup before removal"
        )
        self._disable_startup.setChecked(
            str(row.get("startup_state", ""))
            in {"enabled", "enabled-runtime"}
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )
        remove_button = buttons.addButton(
            "Remove Service",
            QDialogButtonBox.ButtonRole.DestructiveRole,
        )
        remove_button.clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(heading)
        layout.addWidget(details)
        layout.addWidget(backup_notice)
        layout.addWidget(self._stop_service)
        layout.addWidget(self._disable_startup)
        layout.addStretch()
        layout.addWidget(buttons)

    @property
    def stop_service(self) -> bool:
        return self._stop_service.isChecked()

    @property
    def disable_at_startup(self) -> bool:
        return self._disable_startup.isChecked()


class ServicesView(QWidget):
    """Landing view for the Background Services module."""

    def __init__(
        self,
        provider: ServicesTableProvider,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._remove_in_progress = False
        self._active_remove_worker: _RemoveWorker | None = None
        self._remove_thread_pool = QThreadPool(self)
        self._remove_thread_pool.setMaxThreadCount(1)

        self._tabs = QTabWidget()

        services_tab, self._services_table = self._build_services_tab(
            provider
        )
        installer = InstallServiceView()
        installer.service_installed.connect(
            self._on_service_installed
        )

        self._tabs.addTab(services_tab, "Services")
        self._tabs.addTab(installer, "Install Service")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(self._tabs)

    def _build_services_tab(
        self,
        provider: ServicesTableProvider,
    ) -> tuple[QWidget, DataTable]:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = QLabel("Background Services")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "View and manage services installed on this computer."
        )
        description.setWordWrap(True)

        table = DataTable(
            provider=provider,
            selectable=True,
            sortable=True,
        )

        self._remove_button = QPushButton("Remove Selected Service")
        self._remove_button.setEnabled(False)
        self._remove_button.clicked.connect(
            self._begin_remove_selected_service
        )

        remove_row = QHBoxLayout()
        remove_row.addStretch()
        remove_row.addWidget(self._remove_button)

        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(
            self._update_remove_button
        )
        self._selection_timer.start(250)

        layout.addWidget(heading)
        # layout.addWidget(description)
        layout.addWidget(table, 1)
        layout.addLayout(remove_row)

        return container, table

    def _update_remove_button(self) -> None:
        row = self._services_table.selected_row_data()
        removable = bool(row and row.get("removable", False))
        self._remove_button.setEnabled(
            removable and not self._remove_in_progress
        )

        if row and not removable:
            self._remove_button.setToolTip(
                "Only regular service files stored directly under "
                "/etc/systemd/system can be removed here."
            )
        else:
            self._remove_button.setToolTip("")

    def _begin_remove_selected_service(self) -> None:
        if self._remove_in_progress:
            return

        row = self._services_table.selected_row_data()

        if not row or not row.get("removable", False):
            return

        warning = QMessageBox.warning(
            self,
            "Removing Services Can Damage the System",
            (
                "Removing the wrong background service can prevent "
                "applications or parts of Ubuntu from working correctly.\n\n"
                "LEC only enables removal for regular service files stored "
                "directly under /etc/systemd/system. Continue to the "
                "removal options for the selected service?"
            ),
            QMessageBox.StandardButton.Ok
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )

        if warning != QMessageBox.StandardButton.Ok:
            return

        dialog = RemoveServiceDialog(row, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        service_name = str(row.get("name", "")).strip()

        if not service_name:
            QMessageBox.critical(
                self,
                "Service Removal Failed",
                "The selected service name is invalid.",
            )
            return

        self._remove_in_progress = True
        self._remove_button.setEnabled(False)

        worker = _RemoveWorker(
            service_name=service_name,
            stop_service=dialog.stop_service,
            disable_at_startup=dialog.disable_at_startup,
        )
        worker.signals.succeeded.connect(
            self._remove_succeeded
        )
        worker.signals.failed.connect(
            self._remove_failed
        )
        worker.signals.finished.connect(
            self._remove_finished
        )

        self._active_remove_worker = worker
        self._remove_thread_pool.start(worker)

    def _remove_succeeded(self, message: str) -> None:
        QMessageBox.information(
            self,
            "Service Removed",
            message or "The service was removed successfully.",
        )
        self._services_table.reload()

    def _remove_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Service Removal Failed",
            message,
        )

    def _remove_finished(self) -> None:
        self._remove_in_progress = False
        self._active_remove_worker = None
        self._services_table.reload()
        self._update_remove_button()

    def _on_service_installed(self) -> None:
        self._tabs.setCurrentIndex(0)
        self._services_table.reload()


class InstallServiceView(QWidget):
    """Form for generating and installing a systemd service."""

    service_installed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._description_was_edited = False
        self._install_in_progress = False
        self._active_worker: _InstallWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        self._service_name = QLineEdit()
        self._service_name.setPlaceholderText("lec-test-daemon")
        self._service_name.textChanged.connect(
            self._update_default_description
        )
        self._service_name.textChanged.connect(
            self._invalidate_preview
        )

        self._description = QLineEdit()
        self._description.setPlaceholderText("LEC Test Daemon")
        self._description.textEdited.connect(
            self._mark_description_edited
        )
        self._description.textChanged.connect(
            self._invalidate_preview
        )

        self._launch_type = QComboBox()
        self._launch_type.addItem("Executable", "executable")
        self._launch_type.addItem("Python script", "python")
        self._launch_type.addItem("Shell script", "shell")
        self._launch_type.currentIndexChanged.connect(
            self._invalidate_preview
        )

        self._program_path = QLineEdit()
        self._program_path.textChanged.connect(
            self._invalidate_preview
        )
        self._program_button = QPushButton("Browse…")
        self._program_button.clicked.connect(
            self._select_program
        )

        program_row = QWidget()
        program_layout = QHBoxLayout(program_row)
        program_layout.setContentsMargins(0, 0, 0, 0)
        program_layout.addWidget(self._program_path, 1)
        program_layout.addWidget(self._program_button)

        self._arguments = QLineEdit()
        self._arguments.setPlaceholderText(
            "Optional command-line arguments"
        )
        self._arguments.textChanged.connect(
            self._invalidate_preview
        )

        self._working_directory = QLineEdit()
        self._working_directory.textChanged.connect(
            self._invalidate_preview
        )
        self._working_button = QPushButton("Browse…")
        self._working_button.clicked.connect(
            self._select_working_directory
        )

        working_row = QWidget()
        working_layout = QHBoxLayout(working_row)
        working_layout.setContentsMargins(0, 0, 0, 0)
        working_layout.addWidget(
            self._working_directory,
            1,
        )
        working_layout.addWidget(self._working_button)

        self._run_as_user = QLineEdit(getpass.getuser())
        self._run_as_user.textChanged.connect(
            self._invalidate_preview
        )

        self._start_at_boot = QCheckBox(
            "Start automatically when the computer starts"
        )
        self._start_at_boot.setChecked(True)
        self._start_at_boot.toggled.connect(
            self._invalidate_preview
        )

        self._start_immediately = QCheckBox(
            "Start immediately after installation"
        )
        self._start_immediately.setChecked(True)
        self._start_immediately.toggled.connect(
            self._invalidate_preview
        )

        self._restart_on_failure = QCheckBox(
            "Restart automatically if the program crashes"
        )
        self._restart_on_failure.setChecked(True)
        self._restart_on_failure.toggled.connect(
            self._invalidate_preview
        )

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.addRow("Service name:", self._service_name)
        form.addRow("Description:", self._description)
        form.addRow("Launch type:", self._launch_type)
        form.addRow("Program or script:", program_row)
        form.addRow("Arguments:", self._arguments)
        form.addRow("Working directory:", working_row)
        form.addRow("Run as user:", self._run_as_user)
        form.addRow("", self._start_at_boot)
        form.addRow("", self._start_immediately)
        form.addRow("", self._restart_on_failure)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(
            QTextEdit.LineWrapMode.NoWrap
        )
        self._preview.setPlaceholderText(
            "Complete the form and select Preview Service."
        )

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)

        self._preview_button = QPushButton("Preview Service")
        self._preview_button.clicked.connect(
            self._update_preview
        )

        self._install_button = QPushButton("Install Service")
        self._install_button.setEnabled(False)
        self._install_button.clicked.connect(
            self._install_service
        )

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._preview_button)
        button_layout.addWidget(self._install_button)

        heading = QLabel("Install a Background Service")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Choose a program or script that should run in the "
            "background. LEC will generate the required system "
            "configuration."
        )
        description.setWordWrap(True)

        preview_heading = QLabel("Configuration Preview")
        preview_heading.setStyleSheet("font-weight: bold;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addLayout(form)
        layout.addWidget(preview_heading)
        layout.addWidget(self._preview, 1)
        layout.addWidget(self._status_label)
        layout.addLayout(button_layout)

    def _select_program(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Program or Script",
            str(Path.home()),
        )

        if not path:
            return

        self._program_path.setText(path)

        if not self._working_directory.text().strip():
            self._working_directory.setText(
                str(Path(path).parent)
            )

        suffix = Path(path).suffix.lower()

        if suffix == ".py":
            self._launch_type.setCurrentIndex(
                self._launch_type.findData("python")
            )
        elif suffix in {".sh", ".bash"}:
            self._launch_type.setCurrentIndex(
                self._launch_type.findData("shell")
            )

    def _select_working_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Working Directory",
            self._working_directory.text().strip()
            or str(Path.home()),
        )

        if path:
            self._working_directory.setText(path)

    def _mark_description_edited(self) -> None:
        self._description_was_edited = True

    def _update_default_description(self, service_name: str) -> None:
        if self._description_was_edited:
            return

        cleaned = service_name.strip().removesuffix(".service")
        words = re.split(r"[-_.]+", cleaned)
        friendly = " ".join(
            word.upper() if word.lower() == "lec" else word.capitalize()
            for word in words
            if word
        )
        self._description.setText(friendly)

    def _invalidate_preview(self) -> None:
        if self._install_in_progress:
            return

        self._install_button.setEnabled(False)
        self._status_label.clear()

    def _update_preview(self) -> None:
        try:
            service_name = self._normalized_service_name()
            unit = self._build_unit()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Cannot Generate Service",
                str(exc),
            )
            return

        destination = Path(
            f"/etc/systemd/system/{service_name}.service"
        )

        existing_notice = ""
        if destination.exists():
            existing_notice = (
                "\nWarning\n"
                "    A service with this name already exists. "
                "Installing will replace it after creating a verified backup.\n"
            )

        self._preview.setPlainText(
            f"Service Name\n"
            f"    {service_name}\n\n"
            f"Destination\n"
            f"    {destination}\n"
            f"{existing_notice}\n"
            f"------------------------------------------------------------\n\n"
            f"{unit.preview()}"
        )

        self._status_label.clear()
        self._install_button.setEnabled(True)

    def _install_service(self) -> None:
        if self._install_in_progress:
            return

        try:
            service_name = self._normalized_service_name()
            unit = self._build_unit()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Cannot Install Service",
                str(exc),
            )
            return

        destination = Path(
            f"/etc/systemd/system/{service_name}.service"
        )

        if destination.exists():
            response = QMessageBox.question(
                self,
                "Replace Existing Service?",
                (
                    f"{destination.name} already exists.\n\n"
                    "LEC will create and verify a backup before replacing it. "
                    "Continue?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return

        staged_path = self._stage_unit(unit)

        self._install_in_progress = True
        self._set_form_enabled(False)
        self._status_label.setText(
            "Waiting for administrator authorization…"
        )

        worker = _InstallWorker(
            staged_path=staged_path,
            service_name=service_name,
            enable_at_startup=self._start_at_boot.isChecked(),
            start_immediately=self._start_immediately.isChecked(),
        )
        worker.signals.succeeded.connect(
            self._install_succeeded
        )
        worker.signals.failed.connect(
            self._install_failed
        )
        worker.signals.finished.connect(
            self._install_finished
        )

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _stage_unit(self, unit: SystemdUnit) -> Path:
        file_descriptor, filename = tempfile.mkstemp(
            prefix="lec-service-",
            suffix=".service",
        )
        path = Path(filename)

        try:
            os.fchmod(file_descriptor, 0o600)

            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
            ) as staged_file:
                staged_file.write(unit.render())
                staged_file.flush()
                os.fsync(staged_file.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise

        return path

    def _install_succeeded(self, message: str) -> None:
        self._status_label.setText(
            message or "Service installed successfully."
        )
        QMessageBox.information(
            self,
            "Service Installed",
            message or "The service was installed successfully.",
        )
        self.service_installed.emit()

    def _install_failed(self, message: str) -> None:
        self._status_label.setText(
            f"Installation failed: {message}"
        )
        QMessageBox.critical(
            self,
            "Service Installation Failed",
            message,
        )

    def _install_finished(self) -> None:
        self._install_in_progress = False
        self._active_worker = None
        self._set_form_enabled(True)

    def _set_form_enabled(self, enabled: bool) -> None:
        controls = (
            self._service_name,
            self._description,
            self._launch_type,
            self._program_path,
            self._program_button,
            self._arguments,
            self._working_directory,
            self._working_button,
            self._run_as_user,
            self._start_at_boot,
            self._start_immediately,
            self._restart_on_failure,
            self._preview_button,
        )

        for control in controls:
            control.setEnabled(enabled)

        self._install_button.setEnabled(
            enabled and bool(self._preview.toPlainText().strip())
        )

    def _build_unit(self) -> SystemdUnit:
        self._normalized_service_name()

        description = self._description.text().strip()
        program_path = Path(
            self._program_path.text().strip()
        )

        if not description:
            raise ValueError("Enter a service description.")

        if not program_path.is_file():
            raise ValueError(
                "Select an existing program or script."
            )

        working_directory_text = (
            self._working_directory.text().strip()
        )

        if not working_directory_text:
            working_directory = program_path.parent
            self._working_directory.setText(
                str(working_directory)
            )
        else:
            working_directory = Path(working_directory_text)

        if not working_directory.is_dir():
            raise ValueError(
                "Select an existing working directory."
            )

        run_as_user = self._run_as_user.text().strip()

        if not run_as_user:
            raise ValueError("Enter the user account to run as.")

        try:
            arguments = shlex.split(
                self._arguments.text().strip()
            )
        except ValueError as exc:
            raise ValueError(
                f"Arguments are invalid: {exc}"
            ) from exc

        launch_type = str(
            self._launch_type.currentData()
        )

        if launch_type == "python":
            executable = "/usr/bin/python3"
            command_arguments = [
                str(program_path),
                *arguments,
            ]
        elif launch_type == "shell":
            executable = "/bin/bash"
            command_arguments = [
                str(program_path),
                *arguments,
            ]
        else:
            executable = str(program_path)
            command_arguments = arguments

        unit = SystemdUnit()
        unit.add_comment(
            "Unit",
            "Created by Linux Easy Config",
        )
        unit.add_comment(
            "Unit",
            "Module: org.linuxeasyconfig.services",
        )
        unit.set("Unit", "Description", description)
        unit.set("Unit", "After", "network.target")

        unit.set(
            "Service",
            "ExecStart",
            SystemdUnit.command(
                executable,
                *command_arguments,
            ),
        )
        unit.set(
            "Service",
            "WorkingDirectory",
            str(working_directory),
        )
        unit.set("Service", "User", run_as_user)

        if self._restart_on_failure.isChecked():
            unit.set("Service", "Restart", "on-failure")
            unit.set("Service", "RestartSec", "3")
        else:
            unit.set("Service", "Restart", "no")

        if self._start_at_boot.isChecked():
            unit.set(
                "Install",
                "WantedBy",
                "multi-user.target",
            )

        return unit

    def _normalized_service_name(self) -> str:
        name = self._service_name.text().strip()

        if name.endswith(".service"):
            name = name.removesuffix(".service")

        if not name:
            raise ValueError("Enter a service name.")

        if not _SERVICE_NAME_PATTERN.fullmatch(name):
            raise ValueError(
                "Service names may contain only letters, numbers, "
                "periods, underscores, hyphens, and @."
            )

        return name
