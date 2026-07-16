from __future__ import annotations

import pwd
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
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
        self._tabs.addTab(self._build_vnc(), "VNC")
        self._tabs.addTab(
            self._build_guacamole(),
            "Guacamole",
        )

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
        header = self._sessions.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        header.setStretchLastSection(True)
        self._sessions.verticalHeader().setVisible(False)

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


    def _build_vnc(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "TigerVNC creates a separate virtual Linux desktop. "
            "For security, expose its port only to your local "
            "network. A later Guacamole integration can provide "
            "browser access without exposing VNC directly."
        )
        note.setWordWrap(True)

        self._vnc_status = QLabel()
        self._vnc_status.setWordWrap(True)

        self._vnc_install = QPushButton(
            "Install TigerVNC"
        )
        self._vnc_install.clicked.connect(
            lambda: self._run_sequence(
                [
                    PrivilegedTask(
                        "remote_access.install_vnc",
                        {},
                    )
                ],
                "TigerVNC Installed",
                timeout=1000,
            )
        )

        self._vnc_toggle = QPushButton()
        self._vnc_toggle.clicked.connect(
            self._toggle_vnc
        )

        vnc_refresh = QPushButton(
            "Refresh VNC Status"
        )
        vnc_refresh.clicked.connect(
            lambda: self._run_sequence(
                [
                    PrivilegedTask(
                        "remote_access.refresh_vnc",
                        {},
                    )
                ],
                "VNC Status Refreshed",
            )
        )

        service = QGroupBox("TigerVNC Service")
        service_layout = QHBoxLayout(service)
        service_layout.addWidget(
            self._vnc_status,
            1,
        )
        service_layout.addWidget(
            self._vnc_install
        )
        service_layout.addWidget(
            self._vnc_toggle
        )
        service_layout.addWidget(vnc_refresh)

        self._vnc_user = QComboBox()
        for account in pwd.getpwall():
            if (
                account.pw_uid >= 1000
                and account.pw_dir
                and account.pw_shell
                not in {
                    "/usr/sbin/nologin",
                    "/bin/false",
                }
            ):
                self._vnc_user.addItem(
                    account.pw_name,
                    account.pw_name,
                )

        self._vnc_display = QSpinBox()
        self._vnc_display.setRange(1, 99)
        self._vnc_display.setValue(1)
        self._vnc_display.valueChanged.connect(
            self._update_vnc_port
        )

        self._vnc_port = QLabel("5901")

        self._vnc_geometry = QComboBox()
        self._vnc_geometry.setEditable(True)
        self._vnc_geometry.addItems(
            [
                "1920x1080",
                "1600x900",
                "1366x768",
                "1280x720",
                "1024x768",
            ]
        )

        self._vnc_depth = QComboBox()
        self._vnc_depth.addItem(
            "24-bit color (recommended)",
            24,
        )
        self._vnc_depth.addItem(
            "16-bit color",
            16,
        )
        self._vnc_depth.addItem(
            "32-bit color",
            32,
        )

        self._vnc_startup = QLineEdit()
        self._vnc_startup.setText(
            "dbus-run-session -- "
            "gnome-session --session=ubuntu"
        )

        self._vnc_password = QLineEdit()
        self._vnc_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self._vnc_password.setPlaceholderText(
            "Leave blank to retain the existing password"
        )

        self._vnc_password_confirm = QLineEdit()
        self._vnc_password_confirm.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self._vnc_enable = QCheckBox(
            "Enable and start the VNC session after saving"
        )
        self._vnc_enable.setChecked(True)

        self._vnc_firewall = QCheckBox(
            "Allow VNC through the Firewall module "
            "from detected local networks"
        )
        self._vnc_firewall_note = QLabel()
        self._vnc_firewall_note.setWordWrap(True)

        settings = QGroupBox(
            "Virtual Desktop Settings"
        )
        form = QFormLayout(settings)
        form.addRow(
            "Linux user:",
            self._vnc_user,
        )
        form.addRow(
            "Display number:",
            self._vnc_display,
        )
        form.addRow(
            "TCP port:",
            self._vnc_port,
        )
        form.addRow(
            "Resolution:",
            self._vnc_geometry,
        )
        form.addRow(
            "Color depth:",
            self._vnc_depth,
        )
        form.addRow(
            "Desktop startup command:",
            self._vnc_startup,
        )
        form.addRow(
            "VNC password:",
            self._vnc_password,
        )
        form.addRow(
            "Confirm password:",
            self._vnc_password_confirm,
        )
        form.addRow("", self._vnc_enable)
        form.addRow("", self._vnc_firewall)
        form.addRow(
            "",
            self._vnc_firewall_note,
        )

        save = QPushButton(
            "Save TigerVNC Configuration"
        )
        save.clicked.connect(
            self._save_vnc
        )

        layout.addWidget(note)
        layout.addWidget(service)
        layout.addWidget(settings)
        layout.addWidget(save)
        layout.addStretch()
        return container

    def _build_guacamole(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        heading = QLabel("Apache Guacamole")
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        note = QLabel(
            "Guacamole must be installed through the Docker module."
        )
        note.setWordWrap(True)

        future = QLabel(
            "After the Docker module installs Guacamole, this tab "
            "will configure its SSH, VNC, and RDP connections and "
            "offer secure publication through the Reverse Proxy module."
        )
        future.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(note)
        layout.addWidget(future)
        layout.addStretch()
        return container

    def _update_vnc_port(self) -> None:
        self._vnc_port.setText(
            str(5900 + self._vnc_display.value())
        )

    def _toggle_vnc(self) -> None:
        enable = not bool(
            self._vnc_toggle.property("active")
        )
        self._run_sequence(
            [
                PrivilegedTask(
                    "remote_access.set_vnc_service",
                    {"enabled": enable},
                )
            ],
            "TigerVNC Service Updated",
        )

    def _save_vnc(self) -> None:
        password = self._vnc_password.text()

        if (
            password
            != self._vnc_password_confirm.text()
        ):
            QMessageBox.warning(
                self,
                "Passwords Do Not Match",
                "Enter the same VNC password twice.",
            )
            return

        port = (
            5900
            + self._vnc_display.value()
        )

        tasks = [
            PrivilegedTask(
                "remote_access.save_vnc",
                {
                    "username": (
                        self._vnc_user.currentData()
                    ),
                    "display": (
                        self._vnc_display.value()
                    ),
                    "geometry": (
                        self._vnc_geometry.currentText()
                    ),
                    "depth": int(
                        self._vnc_depth.currentData()
                    ),
                    "startup_command": (
                        self._vnc_startup.text()
                    ),
                    "password": password,
                    "enabled": (
                        self._vnc_enable.isChecked()
                    ),
                },
            )
        ]

        if self._vnc_firewall.isChecked():
            capability = (
                self._context.capability_registry.get(
                    "firewall.allow_service"
                )
                if self._context is not None
                else None
            )
            networks = (
                self._repository.local_networks()
            )

            if (
                capability is not None
                and capability.privileged_task_id
                and networks
            ):
                tasks.append(
                    PrivilegedTask(
                        capability.privileged_task_id,
                        {
                            "action": "allow",
                            "direction": "incoming",
                            "sources": networks,
                            "destination": "",
                            "port": str(port),
                            "protocol": "tcp",
                            "profile": "",
                            "comment": (
                                "LEC Remote Access TigerVNC"
                            ),
                        },
                    )
                )

        self._run_sequence(
            tasks,
            "TigerVNC Configuration Saved",
        )

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

        self._reload_vnc()

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


    def _reload_vnc(self) -> None:
        snapshot = (
            self._repository.vnc_snapshot()
        )
        installed = bool(
            snapshot.get("installed", False)
        )
        configured = bool(
            snapshot.get("configured", False)
        )
        active = bool(
            snapshot.get("active", False)
        )

        if not installed:
            self._vnc_status.setText(
                "TigerVNC is not installed."
            )
        elif not configured:
            self._vnc_status.setText(
                "TigerVNC is installed but no "
                "virtual desktop is configured."
            )
        else:
            self._vnc_status.setText(
                "TigerVNC is configured and "
                + (
                    "running."
                    if active
                    else "stopped."
                )
            )

        self._vnc_install.setText(
            "Repair or Reinstall TigerVNC"
            if installed
            else "Install TigerVNC"
        )
        self._vnc_toggle.setText(
            "Stop and Disable VNC"
            if active
            else "Enable and Start VNC"
        )
        self._vnc_toggle.setProperty(
            "active",
            active,
        )
        self._vnc_toggle.setEnabled(
            installed
            and configured
            and not self._busy
        )

        configuration = snapshot.get(
            "configuration"
        )

        if isinstance(configuration, dict):
            user_index = self._vnc_user.findData(
                str(
                    configuration.get(
                        "username",
                        "",
                    )
                )
            )
            if user_index >= 0:
                self._vnc_user.setCurrentIndex(
                    user_index
                )

            self._vnc_display.setValue(
                int(
                    configuration.get(
                        "display",
                        1,
                    )
                )
            )
            self._vnc_geometry.setCurrentText(
                str(
                    configuration.get(
                        "geometry",
                        "1920x1080",
                    )
                )
            )
            depth_index = (
                self._vnc_depth.findData(
                    int(
                        configuration.get(
                            "depth",
                            24,
                        )
                    )
                )
            )
            if depth_index >= 0:
                self._vnc_depth.setCurrentIndex(
                    depth_index
                )
            self._vnc_startup.setText(
                str(
                    configuration.get(
                        "startup_command",
                        "",
                    )
                )
            )
            self._vnc_enable.setChecked(
                bool(
                    snapshot.get(
                        "enabled",
                        active,
                    )
                )
            )

        capability = (
            self._context.capability_registry.get(
                "firewall.allow_service"
            )
            if self._context is not None
            else None
        )
        networks = (
            self._repository.local_networks()
        )
        self._vnc_firewall.setEnabled(
            capability is not None
            and bool(networks)
        )

        if capability is None:
            self._vnc_firewall_note.setText(
                "Firewall integration is unavailable "
                "because the Firewall module is not loaded."
            )
        elif not networks:
            self._vnc_firewall_note.setText(
                "No local network could be detected."
            )
        else:
            self._vnc_firewall_note.setText(
                "Detected local network"
                + (
                    "s: "
                    if len(networks) != 1
                    else ": "
                )
                + ", ".join(networks)
            )

        self._update_vnc_port()

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
