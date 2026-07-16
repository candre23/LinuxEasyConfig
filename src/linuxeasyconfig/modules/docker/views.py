from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.module_api import ModuleContext
from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import DockerRepository


class _Signals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(
        self,
        task: PrivilegedTask,
        timeout: int = 180,
    ) -> None:
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


class DockerView(QWidget):
    def __init__(
        self,
        repository: DockerRepository,
        context: ModuleContext | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._context = context
        self._busy = False
        self._active_worker: _Worker | None = None
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

        heading = QLabel("Docker")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Install Docker and manage common container "
            "operations without editing command lines or "
            "configuration files."
        )
        description.setWordWrap(True)

        self._operation_label = QLabel()
        self._operation_label.setWordWrap(True)
        self._operation_label.setVisible(False)

        self._operation_progress = QProgressBar()
        self._operation_progress.setRange(0, 0)
        self._operation_progress.setVisible(False)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_containers(),
            "Containers",
        )
        self._tabs.addTab(
            self._build_create(),
            "Create Container",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._operation_label)
        layout.addWidget(self._operation_progress)
        layout.addWidget(self._tabs, 1)

        self.reload()

    def _build_overview(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._setup = QLabel()
        self._setup.setWordWrap(True)

        self._caddy_warning = QLabel()
        self._caddy_warning.setWordWrap(True)
        self._caddy_warning.setStyleSheet(
            "font-weight: bold;"
        )

        self._install = QPushButton(
            "Install Docker Engine"
        )
        self._install.clicked.connect(
            lambda: self._run_task(
                "docker.install",
                {},
                "Docker Installed",
                timeout=1400,
                long_operation=True,
            )
        )

        self._installed = QLabel()
        self._running = QLabel()
        self._enabled = QLabel()
        self._version = QLabel()
        self._compose = QLabel()

        status = QGroupBox("Docker Status")
        form = QFormLayout(status)
        form.addRow("Installed:", self._installed)
        form.addRow("Running:", self._running)
        form.addRow(
            "Starts automatically:",
            self._enabled,
        )
        form.addRow(
            "Docker version:",
            self._version,
        )
        form.addRow(
            "Compose version:",
            self._compose,
        )

        start = QPushButton("Start")
        start.clicked.connect(
            lambda: self._service_action("start")
        )
        stop = QPushButton("Stop")
        stop.clicked.connect(
            lambda: self._service_action("stop")
        )
        restart = QPushButton("Restart")
        restart.clicked.connect(
            lambda: self._service_action("restart")
        )
        enable = QPushButton("Enable at Startup")
        enable.clicked.connect(
            lambda: self._service_action("enable")
        )
        disable = QPushButton("Disable at Startup")
        disable.clicked.connect(
            lambda: self._service_action("disable")
        )
        refresh = QPushButton("Refresh Status")
        refresh.clicked.connect(
            lambda: self._run_task(
                "docker.refresh",
                {},
                "Docker Status Refreshed",
            )
        )

        buttons = QHBoxLayout()
        for button in (
            start,
            stop,
            restart,
            enable,
            disable,
            refresh,
        ):
            buttons.addWidget(button)

        layout.addWidget(self._setup)
        layout.addWidget(self._caddy_warning)
        layout.addWidget(self._install)
        layout.addWidget(status)
        layout.addLayout(buttons)
        layout.addStretch()
        return container

    def _build_containers(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                "Name",
                "Image",
                "State",
                "Status",
                "Published Ports",
                "ID",
            ]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)
        self._table.setWordWrap(True)
        self._table.setTextElideMode(
            Qt.TextElideMode.ElideNone
        )
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(1, 170)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 180)
        self._table.setColumnWidth(4, 260)
        self._table.setColumnWidth(5, 120)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        start = QPushButton("Start")
        start.clicked.connect(
            lambda: self._selected_action("start")
        )
        stop = QPushButton("Stop")
        stop.clicked.connect(
            lambda: self._selected_action("stop")
        )
        restart = QPushButton("Restart")
        restart.clicked.connect(
            lambda: self._selected_action("restart")
        )
        logs = QPushButton("View Logs")
        logs.clicked.connect(self._view_logs)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_selected)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(
            lambda: self._run_task(
                "docker.refresh",
                {},
                "Container List Refreshed",
            )
        )

        buttons = QHBoxLayout()
        for button in (
            start,
            stop,
            restart,
            logs,
            remove,
            refresh,
        ):
            buttons.addWidget(button)

        layout.addWidget(self._table, 1)
        layout.addLayout(buttons)
        return container

    def _build_create(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "This form intentionally includes only common "
            "home-server settings. Application-specific LEC "
            "modules can provide more guided setup."
        )
        note.setWordWrap(True)

        self._name = QLineEdit()
        self._image = QLineEdit()
        self._image.setPlaceholderText(
            "Example: nginx:latest"
        )

        self._host_port = QSpinBox()
        self._host_port.setRange(0, 65535)
        self._container_port = QSpinBox()
        self._container_port.setRange(0, 65535)

        self._protocol = QComboBox()
        self._protocol.addItem("TCP", "tcp")
        self._protocol.addItem("UDP", "udp")

        self._access_scope = QComboBox()
        self._access_scope.addItem(
            "Local or reverse proxy only (recommended)",
            "localhost",
        )
        self._access_scope.addItem(
            "Local network",
            "local_network",
        )
        self._access_scope.addItem(
            "All networks (not recommended)",
            "all_networks",
        )
        self._access_scope.currentIndexChanged.connect(
            self._access_scope_changed
        )

        self._service_protocol = QComboBox()
        self._service_protocol.addItem(
            "HTTP web service",
            "http",
        )
        self._service_protocol.addItem(
            "HTTPS web service",
            "https",
        )
        self._service_protocol.addItem(
            "Other TCP service",
            "tcp",
        )
        self._service_protocol.addItem(
            "Other UDP service",
            "udp",
        )

        self._host_path = QLineEdit()
        self._host_path.setPlaceholderText(
            "/srv/application-data"
        )
        self._container_path = QLineEdit()
        self._container_path.setPlaceholderText(
            "/data"
        )

        self._environment = QTextEdit()
        self._environment.setMaximumHeight(110)
        self._environment.setPlaceholderText(
            "One NAME=value entry per line"
        )

        self._restart = QComboBox()
        self._restart.addItem(
            "Unless manually stopped",
            "unless-stopped",
        )
        self._restart.addItem(
            "Always",
            "always",
        )
        self._restart.addItem(
            "Only after failure",
            "on-failure",
        )
        self._restart.addItem(
            "Do not restart automatically",
            "no",
        )

        self._firewall = QCheckBox(
            "Allow the published port through Firewall "
            "from detected local networks"
        )
        self._proxy = QCheckBox(
            "Create a Reverse Proxy rule for this web service"
        )
        self._proxy.toggled.connect(
            self._proxy_toggled
        )
        self._public_host = QLineEdit()
        self._public_host.setPlaceholderText(
            "app.example.com"
        )
        self._proxy_login = QCheckBox(
            "Require Caddy login"
        )

        group = QGroupBox("Container Settings")
        form = QFormLayout(group)
        form.addRow("Container name:", self._name)
        form.addRow("Image:", self._image)
        form.addRow(
            "Host port:",
            self._host_port,
        )
        form.addRow(
            "Container port:",
            self._container_port,
        )
        form.addRow("Transport protocol:", self._protocol)
        form.addRow(
            "Network access:",
            self._access_scope,
        )
        form.addRow(
            "Service type:",
            self._service_protocol,
        )
        form.addRow(
            "Host data folder:",
            self._host_path,
        )
        form.addRow(
            "Container data folder:",
            self._container_path,
        )
        form.addRow(
            "Environment variables:",
            self._environment,
        )
        form.addRow(
            "Restart behavior:",
            self._restart,
        )
        form.addRow("", self._firewall)
        form.addRow("", self._proxy)
        form.addRow(
            "Public hostname:",
            self._public_host,
        )
        form.addRow("", self._proxy_login)

        create = QPushButton(
            "Pull Image and Create Container"
        )
        create.clicked.connect(self._create_container)

        layout.addWidget(note)
        layout.addWidget(group)
        layout.addWidget(create)
        layout.addStretch()
        self._access_scope_changed()
        return container

    def reload(self) -> None:
        status = self._repository.status()
        self._installed.setText(
            "Yes" if status.installed else "No"
        )
        self._running.setText(
            "Yes" if status.active else "No"
        )
        self._enabled.setText(
            "Yes" if status.enabled else "No"
        )
        self._version.setText(status.version)
        self._compose.setText(
            status.compose_version
        )

        self._setup.setText(
            (
                "Docker Engine is installed and "
                + (
                    "running."
                    if status.active
                    else "not currently running."
                )
            )
            if status.installed
            else (
                "Docker Engine is not installed. LEC can "
                "install Docker Engine and the Docker Compose "
                "plugin from Docker's official repository."
            )
        )
        self._install.setText(
            "Repair or Update Docker"
            if status.installed
            else "Install Docker Engine"
        )

        if self._repository.caddy_installed():
            self._caddy_warning.setText(
                "Reverse proxy system detected."
            )
        else:
            self._caddy_warning.setText(
                "Reverse proxy system is not installed. "
                "It is strongly recommended that any "
                "application exposed to the internet do so "
                "through a reverse proxy."
            )

        self._table.setRowCount(0)

        for item in self._repository.containers():
            row = self._table.rowCount()
            self._table.insertRow(row)

            values = (
                item.name,
                item.image,
                item.state,
                item.status,
                item.ports,
                item.container_id,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._table.setItem(
                    row,
                    column,
                    item,
                )

        self._table.resizeRowsToContents()

        firewall_capability = (
            self._context.capability_registry.get(
                "firewall.allow_docker_service"
            )
            if self._context is not None
            else None
        )
        proxy_capability = (
            self._context.capability_registry.get(
                "reverse_proxy.create_http_proxy"
            )
            if self._context is not None
            else None
        )

        self._firewall.setEnabled(
            firewall_capability is not None
        )
        self._proxy.setEnabled(
            proxy_capability is not None
        )
        self._public_host.setEnabled(
            proxy_capability is not None
        )
        self._proxy_login.setEnabled(
            proxy_capability is not None
        )

    def _access_scope_changed(self) -> None:
        scope = self._access_scope.currentData()

        if scope == "all_networks":
            QMessageBox.warning(
                self,
                "All Networks Selected",
                (
                    "This publishes the container port on every "
                    "network interface. It may be reachable from "
                    "the internet depending on your router and "
                    "network configuration.\n\n"
                    "Use Local or reverse proxy only whenever "
                    "practical."
                ),
            )

        self._firewall.setEnabled(
            scope == "local_network"
            and self._context is not None
            and self._context.capability_registry.get(
                "firewall.allow_docker_service"
            )
            is not None
        )

    def _proxy_toggled(self, checked: bool) -> None:
        if checked:
            self._access_scope.setCurrentIndex(
                self._access_scope.findData(
                    "localhost"
                )
            )
            self._access_scope.setEnabled(False)
            self._firewall.setChecked(False)
            self._firewall.setEnabled(False)
        else:
            self._access_scope.setEnabled(True)
            self._access_scope_changed()

    def _service_action(self, action: str) -> None:
        self._run_task(
            "docker.service_action",
            {"action": action},
            "Docker Service Updated",
        )

    def _selected_name(self) -> str | None:
        row = self._table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                "No Container Selected",
                "Select a container first.",
            )
            return None

        return self._table.item(row, 0).text()

    def _selected_action(self, action: str) -> None:
        name = self._selected_name()

        if name is None:
            return

        self._run_task(
            "docker.container_action",
            {
                "container": name,
                "action": action,
            },
            "Container Updated",
        )

    def _remove_selected(self) -> None:
        name = self._selected_name()

        if name is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Remove Container")
        dialog.resize(560, 280)

        explanation = QLabel(
            f"Remove container {name}?\n\n"
            "The container itself will be deleted. "
            "Choose whether to also remove its image "
            "and attached data."
        )
        explanation.setWordWrap(True)

        remove_image = QCheckBox(
            "Also delete the container image"
        )
        remove_data = QCheckBox(
            "Also permanently delete attached data"
        )

        data_warning = QLabel(
            "Deleting data removes attached Docker volumes "
            "and bind-mounted host files or folders. "
            "This cannot be undone."
        )
        data_warning.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText("Remove")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addWidget(explanation)
        layout.addWidget(remove_image)
        layout.addWidget(remove_data)
        layout.addWidget(data_warning)
        layout.addStretch()
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if remove_data.isChecked():
            confirmation = QMessageBox.warning(
                self,
                "Permanently Delete Data",
                (
                    "Permanently delete the container's "
                    "attached data?\n\n"
                    "This action cannot be undone."
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if confirmation != QMessageBox.StandardButton.Yes:
                return

        self._run_task(
            "docker.remove_container",
            {
                "container": name,
                "force": True,
                "remove_volumes": True,
                "remove_image": (
                    remove_image.isChecked()
                ),
                "remove_data": (
                    remove_data.isChecked()
                ),
            },
            "Container Removed",
        )

    def _view_logs(self) -> None:
        name = self._selected_name()

        if name is None:
            return

        task = PrivilegedTask(
            "docker.container_logs",
            {
                "container": name,
                "lines": 300,
            },
        )

        self._run_task(
            task.task_id,
            task.arguments,
            "Container Logs",
            show_result=True,
        )

    def _create_container(self) -> None:
        tasks = [
            PrivilegedTask(
                "docker.create_container",
                {
                    "name": self._name.text(),
                    "image": self._image.text(),
                    "host_port": self._host_port.value(),
                    "container_port": (
                        self._container_port.value()
                    ),
                    "protocol": (
                        self._protocol.currentData()
                    ),
                    "host_path": (
                        self._host_path.text()
                    ),
                    "container_path": (
                        self._container_path.text()
                    ),
                    "environment_lines": (
                        self._environment.toPlainText()
                    ),
                    "restart_policy": (
                        self._restart.currentData()
                    ),
                    "access_scope": (
                        self._access_scope.currentData()
                    ),
                    "bind_address": (
                        self._repository.primary_local_address()
                        if self._access_scope.currentData()
                        == "local_network"
                        else ""
                    ),
                    "service_protocol": (
                        self._service_protocol.currentData()
                    ),
                    "reverse_proxy_compatible": (
                        self._proxy.isChecked()
                    ),
                    "public_host": (
                        self._public_host.text()
                    ),
                },
            )
        ]

        if self._firewall.isChecked():
            capability = (
                self._context.capability_registry.get(
                    "firewall.allow_docker_service"
                )
                if self._context is not None
                else None
            )

            if (
                capability is not None
                and capability.privileged_task_id
            ):
                tasks.append(
                    PrivilegedTask(
                        capability.privileged_task_id,
                        {
                            "container": self._name.text(),
                            "host_port": self._host_port.value(),
                            "container_port": (
                                self._container_port.value()
                            ),
                            "protocol": (
                                self._protocol.currentData()
                            ),
                            "sources": (
                                self._repository.local_networks()
                            ),
                            "comment": (
                                "LEC Docker "
                                + self._name.text()
                            ),
                        },
                    )
                )

        if self._proxy.isChecked():
            capability = (
                self._context.capability_registry.get(
                    "reverse_proxy.create_http_proxy"
                )
                if self._context is not None
                else None
            )

            if (
                capability is not None
                and capability.privileged_task_id
            ):
                tasks.append(
                    PrivilegedTask(
                        capability.privileged_task_id,
                        {
                            "original_name": "",
                            "data": {
                                "name": (
                                    "Docker "
                                    + self._name.text()
                                ),
                                "public_host": (
                                    self._public_host.text()
                                ),
                                "route_type": "host",
                                "path": "",
                                "strip_path": True,
                                "credential_username": "",
                                "backend_host": "127.0.0.1",
                                "backend_port": (
                                    self._host_port.value()
                                ),
                                "backend_https": False,
                                "require_login": (
                                    self._proxy_login.isChecked()
                                ),
                                "enabled": True,
                            },
                        },
                    )
                )

        self._run_sequence(
            tasks,
            "Container Created",
            timeout=1400,
            long_operation=True,
        )

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        *,
        timeout: int = 180,
        show_result: bool = False,
        long_operation: bool = False,
    ) -> None:
        self._show_result = show_result
        self._run_sequence(
            [
                PrivilegedTask(
                    task_id,
                    arguments,
                )
            ],
            title,
            timeout=timeout,
            long_operation=long_operation,
        )

    def _run_sequence(
        self,
        tasks: list[PrivilegedTask],
        title: str,
        *,
        timeout: int = 180,
        long_operation: bool = False,
    ) -> None:
        if self._busy:
            return

        self._busy = True
        self._long_operation = long_operation
        self._pending = list(tasks)

        if long_operation:
            self._operation_label.setText(
                "Installation or download is in progress. "
                "Please be patient; this may take several minutes."
            )
            self._operation_label.setVisible(True)
            self._operation_progress.setVisible(True)
        self._title = title
        self._timeout = timeout
        self._tabs.setEnabled(False)
        self._start_next()

    def _start_next(self) -> None:
        if not self._pending:
            self._finish()
            return

        worker = _Worker(
            self._pending.pop(0),
            timeout=self._timeout,
        )
        worker.signals.succeeded.connect(
            self._succeeded
        )
        worker.signals.failed.connect(
            self._failed
        )
        worker.signals.finished.connect(
            self._worker_finished
        )
        self._active_worker = worker
        self._pool.start(worker)

    def _succeeded(self, message: str) -> None:
        if getattr(
            self,
            "_show_result",
            False,
        ):
            _show_text(
                self,
                self._title,
                message,
            )
            self._show_result = False

    def _failed(self, message: str) -> None:
        self._pending.clear()
        self._failed_flag = True
        _show_text(
            self,
            "Docker Operation Failed",
            message,
        )

    def _worker_finished(self) -> None:
        self._active_worker = None

        if getattr(
            self,
            "_failed_flag",
            False,
        ):
            self._finish()
        else:
            self._start_next()

    def _finish(self) -> None:
        self._failed_flag = False
        self._busy = False
        self._tabs.setEnabled(True)
        self._operation_label.setVisible(False)
        self._operation_progress.setVisible(False)
        self.reload()


def _show_text(
    parent: QWidget,
    title: str,
    message: str,
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(800, 540)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(message)
    text.setLineWrapMode(
        QTextEdit.LineWrapMode.NoWrap
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Close
    )
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(text, 1)
    layout.addWidget(buttons)
    dialog.exec()
