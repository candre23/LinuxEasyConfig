from __future__ import annotations

import pwd
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.module_api import ModuleContext
from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import RemoteAccessRepository


class _Signals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(self, task: PrivilegedTask, timeout: int = 180) -> None:
        super().__init__()
        self._task = task
        self._timeout = timeout
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = PrivilegedRunner().run(
                self._task,
                timeout=self._timeout,
            )
            self.signals.succeeded.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class RemoteAccessView(QWidget):
    def __init__(
        self,
        repository: RemoteAccessRepository,
        context: ModuleContext | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._context = context
        self._busy = False
        self._pending: list[PrivilegedTask] = []
        self._active_worker: _Worker | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

        heading = QLabel("Remote Access")
        heading.setStyleSheet("font-size: 24px; font-weight: bold;")
        description = QLabel(
            "Manage OpenSSH remote terminal access. "
            "Changes are validated before the SSH service is restarted."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_overview(), "OpenSSH")
        self._tabs.addTab(self._build_keys(), "Authorized Keys")
        self._tabs.addTab(self._build_sessions(), "Active Sessions")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

        self.reload()

    def _build_overview(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._install = QPushButton("Install OpenSSH Server")
        self._install.clicked.connect(
            lambda: self._run_sequence(
                [PrivilegedTask("remote_access.install", {})],
                "OpenSSH Installed",
                timeout=1000,
            )
        )
        self._toggle = QPushButton()
        self._toggle.clicked.connect(self._toggle_service)
        refresh = QPushButton("Refresh Status")
        refresh.clicked.connect(
            lambda: self._run_sequence(
                [PrivilegedTask("remote_access.refresh", {})],
                "Status Refreshed",
            )
        )

        setup = QGroupBox("Service")
        setup_layout = QHBoxLayout(setup)
        setup_layout.addWidget(self._status, 1)
        setup_layout.addWidget(self._install)
        setup_layout.addWidget(self._toggle)
        setup_layout.addWidget(refresh)

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._password = QCheckBox("Allow password authentication")
        self._keys = QCheckBox("Allow public-key authentication")
        self._root = QComboBox()
        self._root.addItem("Do not allow root login", "no")
        self._root.addItem(
            "Allow root only with a key",
            "prohibit-password",
        )
        self._root.addItem("Allow root login", "yes")

        self._firewall = QCheckBox(
            "Allow SSH through the Firewall module "
            "from detected local networks"
        )
        self._firewall_note = QLabel()
        self._firewall_note.setWordWrap(True)

        form_group = QGroupBox("SSH Settings")
        form = QFormLayout(form_group)
        form.addRow("Listening port:", self._port)
        form.addRow("", self._password)
        form.addRow("", self._keys)
        form.addRow("Root login:", self._root)
        form.addRow("", self._firewall)
        form.addRow("", self._firewall_note)

        save = QPushButton("Save SSH Settings")
        save.clicked.connect(self._save_settings)

        layout.addWidget(setup)
        layout.addWidget(form_group)
        layout.addWidget(save)
        layout.addStretch()
        return container

    def _build_keys(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        note = QLabel(
            "Add an OpenSSH public key to a local user's "
            "authorized_keys file."
        )
        note.setWordWrap(True)

        self._key_user = QComboBox()
        for account in pwd.getpwall():
            if account.pw_uid >= 1000 and account.pw_dir:
                self._key_user.addItem(
                    account.pw_name,
                    account.pw_name,
                )

        self._key_text = QPlainTextEdit()
        self._key_text.setPlaceholderText(
            "ssh-ed25519 AAAA… comment"
        )
        add = QPushButton("Add Authorized Key")
        add.clicked.connect(self._add_key)

        form = QFormLayout()
        form.addRow("Local user:", self._key_user)
        form.addRow("Public key:", self._key_text)

        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(add)
        layout.addStretch()
        return container

    def _build_sessions(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self._sessions = QTableWidget(0, 4)
        self._sessions.setHorizontalHeaderLabels(
            ["User", "Terminal", "Login Time", "Remote Address"]
        )
        refresh = QPushButton("Refresh Sessions")
        refresh.clicked.connect(
            lambda: self._run_sequence(
                [PrivilegedTask("remote_access.refresh", {})],
                "Sessions Refreshed",
            )
        )
        layout.addWidget(self._sessions)
        layout.addWidget(refresh)
        return container

    def reload(self) -> None:
        snapshot = self._repository.snapshot()
        installed = bool(snapshot.get("installed", False))
        active = bool(snapshot.get("active", False))

        self._status.setText(
            (
                f"OpenSSH is installed and "
                f"{'running' if active else 'stopped'}."
            )
            if installed
            else "OpenSSH Server is not installed."
        )
        self._install.setText(
            "Repair or Reinstall OpenSSH"
            if installed
            else "Install OpenSSH Server"
        )
        self._toggle.setText(
            "Stop and Disable SSH"
            if active
            else "Enable and Start SSH"
        )
        self._toggle.setProperty("active", active)
        self._toggle.setEnabled(installed and not self._busy)

        self._port.setValue(int(snapshot.get("port", 22)))
        self._password.setChecked(
            bool(snapshot.get("password_authentication", False))
        )
        self._keys.setChecked(
            bool(snapshot.get("public_key_authentication", True))
        )
        index = self._root.findData(
            str(snapshot.get("permit_root_login", "no"))
        )
        if index >= 0:
            self._root.setCurrentIndex(index)

        capability = (
            self._context.capability_registry.get(
                "firewall.allow_service"
            )
            if self._context is not None
            else None
        )
        networks = self._repository.local_networks()
        self._firewall.setEnabled(
            capability is not None and bool(networks)
        )
        if capability is None:
            self._firewall_note.setText(
                "Firewall integration is unavailable because "
                "the Firewall module is not loaded."
            )
        elif not networks:
            self._firewall_note.setText(
                "No local network could be detected."
            )
        else:
            self._firewall_note.setText(
                "Detected local network"
                + ("s: " if len(networks) != 1 else ": ")
                + ", ".join(networks)
            )

        self._sessions.setRowCount(0)
        for session in snapshot.get("sessions", []):
            if not isinstance(session, dict):
                continue
            row = self._sessions.rowCount()
            self._sessions.insertRow(row)
            for column, key in enumerate(
                ("user", "terminal", "login", "address")
            ):
                self._sessions.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(session.get(key, ""))),
                )

    def _toggle_service(self) -> None:
        enable = not bool(self._toggle.property("active"))
        self._run_sequence(
            [
                PrivilegedTask(
                    "remote_access.set_service",
                    {"enabled": enable},
                )
            ],
            "SSH Service Updated",
        )

    def _save_settings(self) -> None:
        tasks = [
            PrivilegedTask(
                "remote_access.save_settings",
                {
                    "port": self._port.value(),
                    "password_authentication": self._password.isChecked(),
                    "public_key_authentication": self._keys.isChecked(),
                    "permit_root_login": self._root.currentData(),
                },
            )
        ]

        if self._firewall.isChecked():
            capability = (
                self._context.capability_registry.get(
                    "firewall.allow_service"
                )
                if self._context is not None
                else None
            )
            networks = self._repository.local_networks()
            if capability is not None and capability.privileged_task_id:
                tasks.append(
                    PrivilegedTask(
                        capability.privileged_task_id,
                        {
                            "action": "allow",
                            "direction": "incoming",
                            "sources": networks,
                            "destination": "",
                            "port": str(self._port.value()),
                            "protocol": "tcp",
                            "profile": "",
                            "comment": "LEC Remote Access SSH",
                        },
                    )
                )

        self._run_sequence(tasks, "SSH Settings Saved")

    def _add_key(self) -> None:
        self._run_sequence(
            [
                PrivilegedTask(
                    "remote_access.add_authorized_key",
                    {
                        "username": self._key_user.currentData(),
                        "key": self._key_text.toPlainText(),
                    },
                )
            ],
            "Authorized Key Added",
        )

    def _run_sequence(
        self,
        tasks: list[PrivilegedTask],
        title: str,
        *,
        timeout: int = 180,
    ) -> None:
        if self._busy:
            return
        self._busy = True
        self._pending = list(tasks)
        self._title = title
        self._timeout = timeout
        self._tabs.setEnabled(False)
        self._start_next()

    def _start_next(self) -> None:
        if not self._pending:
            QMessageBox.information(
                self,
                self._title,
                "The operation completed successfully.",
            )
            self._finish()
            return

        worker = _Worker(
            self._pending.pop(0),
            timeout=self._timeout,
        )
        worker.signals.failed.connect(self._failed)
        worker.signals.finished.connect(self._worker_finished)
        self._active_worker = worker
        self._pool.start(worker)

    def _failed(self, message: str) -> None:
        self._pending.clear()
        self._failed_flag = True
        QMessageBox.critical(
            self,
            "Remote Access Operation Failed",
            message,
        )

    def _worker_finished(self) -> None:
        self._active_worker = None
        if getattr(self, "_failed_flag", False):
            self._finish()
        else:
            self._start_next()

    def _finish(self) -> None:
        self._failed_flag = False
        self._busy = False
        self._tabs.setEnabled(True)
        self.reload()
