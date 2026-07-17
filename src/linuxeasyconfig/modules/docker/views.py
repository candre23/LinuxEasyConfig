from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
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

from .presets import DockerPreset, default_values
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
        self._loaded_preset: DockerPreset | None = None
        self._preset_field_widgets: dict[str, QWidget] = {}

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
            self._build_presets(),
            "Presets",
        )
        self._create_tab = self._build_create()
        self._tabs.addTab(
            self._create_tab,
            "Container Builder",
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

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            [
                "Name",
                "Image",
                "State",
                "Status",
                "Published Ports",
                "Available from This Computer",
                "Available from Local Network",
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
        self._table.setColumnWidth(4, 240)
        self._table.setColumnWidth(5, 240)
        self._table.setColumnWidth(6, 240)
        self._table.setColumnWidth(7, 120)
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

    def _build_presets(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        explanation = QLabel(
            "Presets provide tested settings for Docker images "
            "and multi-container applications. Imported presets "
            "can create containers, networks, volumes, and files; "
            "only import presets from sources you trust."
        )
        explanation.setWordWrap(True)

        self._presets_table = QTableWidget(0, 4)
        self._presets_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Type",
                "Source",
                "Description",
            ]
        )
        preset_header = self._presets_table.horizontalHeader()
        preset_header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        preset_header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        self._presets_table.setColumnWidth(0, 180)
        self._presets_table.setColumnWidth(1, 140)
        self._presets_table.setColumnWidth(2, 150)
        self._presets_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._presets_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._presets_table.setWordWrap(True)
        self._presets_table.itemSelectionChanged.connect(
            self._update_preset_buttons
        )

        self._import_preset_button = QPushButton(
            "Import .lecdock Preset"
        )
        self._import_preset_button.clicked.connect(
            self._import_preset
        )

        refresh = QPushButton("Refresh Presets")
        refresh.clicked.connect(
            self._refresh_presets
        )

        self._send_preset_button = QPushButton(
            "Send to Container Builder"
        )
        self._send_preset_button.clicked.connect(
            self._send_selected_preset
        )

        buttons = QHBoxLayout()
        buttons.addWidget(
            self._import_preset_button
        )
        buttons.addWidget(refresh)
        buttons.addStretch()
        buttons.addWidget(
            self._send_preset_button
        )

        layout.addWidget(explanation)
        layout.addWidget(self._presets_table, 1)
        layout.addLayout(buttons)

        self._update_preset_buttons()
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

        self._preset_builder_group = QGroupBox(
            "Application Preset"
        )
        self._preset_builder_layout = QFormLayout(
            self._preset_builder_group
        )
        self._preset_builder_group.setVisible(False)

        clear_preset = QPushButton(
            "Clear Loaded Preset"
        )
        clear_preset.clicked.connect(
            self._clear_loaded_preset
        )
        self._preset_builder_layout.addRow(
            "",
            clear_preset,
        )

        group = QGroupBox("Container Settings")
        self._container_group = group
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

        self._create_button = QPushButton(
            "Pull Image and Create Container"
        )
        self._create_button.clicked.connect(
            self._create_container
        )

        layout.addWidget(note)
        layout.addWidget(
            self._preset_builder_group
        )
        layout.addWidget(group)
        layout.addWidget(self._create_button)
        layout.addStretch()
        self._access_scope_changed()
        return container

    def _refresh_presets(self) -> None:
        if not hasattr(self, "_presets_table"):
            return

        presets = self._repository.presets()
        self._presets_table.setRowCount(0)

        for preset in presets:
            row = self._presets_table.rowCount()
            self._presets_table.insertRow(row)

            values = (
                preset.name,
                (
                    "Application stack"
                    if preset.preset_type == "compose"
                    else "Single container"
                ),
                preset.source,
                preset.description,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    preset.preset_id,
                )
                self._presets_table.setItem(
                    row,
                    column,
                    item,
                )

        self._presets_table.resizeRowsToContents()
        self._update_preset_buttons()

    def _update_preset_buttons(self) -> None:
        selected = (
            hasattr(self, "_presets_table")
            and self._presets_table.currentRow() >= 0
        )

        if hasattr(self, "_send_preset_button"):
            self._send_preset_button.setEnabled(selected)

    def _selected_preset(self) -> DockerPreset | None:
        row = self._presets_table.currentRow()

        if row < 0:
            return None

        item = self._presets_table.item(row, 0)

        if item is None:
            return None

        preset_id = str(
            item.data(Qt.ItemDataRole.UserRole)
        )

        return next(
            (
                preset
                for preset in self._repository.presets()
                if preset.preset_id == preset_id
            ),
            None,
        )

    def _import_preset(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Docker Preset",
            str(Path.home()),
            "LEC Docker Presets (*.lecdock)",
        )

        if not filename:
            return

        try:
            destination = self._repository.import_preset(
                Path(filename)
            )
        except Exception as exc:
            _show_text(
                self,
                "Preset Import Failed",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Preset Imported",
            (
                "The Docker preset was imported to:\n"
                f"{destination}"
            ),
        )
        self._refresh_presets()

    def _send_selected_preset(self) -> None:
        preset = self._selected_preset()

        if preset is None:
            return

        if preset.preset_type == "container":
            self._apply_container_preset(preset)
        else:
            self._load_application_preset(preset)

        self._tabs.setCurrentWidget(
            self._create_tab
        )

    def _apply_container_preset(
        self,
        preset: DockerPreset,
    ) -> None:
        values = default_values(preset)
        container = preset.data["container"]

        def rendered(value: Any) -> str:
            result = str(value)

            for key, replacement in values.items():
                result = result.replace(
                    "{{" + key + "}}",
                    str(replacement),
                )

            return result

        self._clear_loaded_preset()
        self._name.setText(
            rendered(
                container.get(
                    "name",
                    values.get(
                        "container_name",
                        "",
                    ),
                )
            )
        )
        self._image.setText(
            rendered(container["image"])
        )
        self._host_port.setValue(
            int(
                values.get(
                    "host_port",
                    container.get(
                        "host_port",
                        0,
                    ),
                )
            )
        )
        self._container_port.setValue(
            int(
                container.get(
                    "container_port",
                    0,
                )
            )
        )
        self._host_path.setText(
            rendered(
                container.get(
                    "host_path",
                    "",
                )
            )
        )
        self._container_path.setText(
            rendered(
                container.get(
                    "container_path",
                    "",
                )
            )
        )
        self._environment.setPlainText(
            rendered(
                container.get(
                    "environment",
                    "",
                )
            )
        )

    def _load_application_preset(
        self,
        preset: DockerPreset,
    ) -> None:
        self._loaded_preset = preset
        self._preset_field_widgets.clear()

        while self._preset_builder_layout.rowCount() > 0:
            self._preset_builder_layout.removeRow(0)

        heading = QLabel(preset.description)
        heading.setWordWrap(True)
        self._preset_builder_layout.addRow(
            "",
            heading,
        )

        for field in preset.data["fields"]:
            field_id = str(field["id"])
            field_type = str(
                field.get("type", "text")
            )
            default = field.get("default", "")

            if field_type in {"integer", "port"}:
                widget = QSpinBox()
                widget.setRange(
                    1 if field_type == "port" else 0,
                    65535
                    if field_type == "port"
                    else 2147483647,
                )
                widget.setValue(int(default or 0))
            elif field_type == "boolean":
                widget = QCheckBox()
                widget.setChecked(bool(default))
            elif field_type == "choice":
                widget = QComboBox()

                for choice in field.get(
                    "choices",
                    [],
                ):
                    widget.addItem(
                        str(choice.get("label", "")),
                        str(choice.get("value", "")),
                    )

                index = widget.findData(str(default))
                widget.setCurrentIndex(
                    max(0, index)
                )
            else:
                widget = QLineEdit()

                if field_type == "password":
                    widget.setEchoMode(
                        QLineEdit.EchoMode.Password
                    )

                if field.get("generate") == "password":
                    default = secrets.token_urlsafe(24)

                widget.setText(str(default))

                placeholder = str(
                    field.get("placeholder", "")
                )

                if placeholder:
                    widget.setPlaceholderText(
                        placeholder
                    )

            help_text = str(
                field.get("help", "")
            )

            if help_text:
                widget.setToolTip(help_text)

            self._preset_field_widgets[
                field_id
            ] = widget
            self._preset_builder_layout.addRow(
                str(field["label"]) + ":",
                widget,
            )

            if (
                field_id == "application_name"
                and isinstance(widget, QLineEdit)
            ):
                widget.textChanged.connect(
                    self._update_preset_deploy_button
                )
            elif (
                field_id == "access_scope"
                and isinstance(widget, QComboBox)
            ):
                widget.currentIndexChanged.connect(
                    self._preset_access_scope_changed
                )
            elif (
                field_id == "allow_firewall"
                and isinstance(widget, QCheckBox)
            ):
                widget.toggled.connect(
                    self._preset_firewall_toggled
                )
            elif (
                field_id == "publish_reverse_proxy"
                and isinstance(widget, QCheckBox)
            ):
                widget.toggled.connect(
                    self._preset_proxy_toggled
                )

        clear_preset = QPushButton(
            "Clear Loaded Preset"
        )
        clear_preset.clicked.connect(
            self._clear_loaded_preset
        )
        self._preset_builder_layout.addRow(
            "",
            clear_preset,
        )

        self._preset_builder_group.setTitle(
            "Application Preset: "
            + preset.name
        )
        self._preset_builder_group.setVisible(True)
        self._container_group.setVisible(False)
        self._synchronize_preset_network_controls()
        self._update_preset_deploy_button()

    def _preset_access_scope_changed(self) -> None:
        self._synchronize_preset_network_controls()

    def _preset_firewall_toggled(
        self,
        checked: bool,
    ) -> None:
        if not checked:
            return

        scope = self._preset_field_widgets.get(
            "access_scope"
        )

        if isinstance(scope, QComboBox):
            index = scope.findData(
                "local_network"
            )

            if index >= 0:
                scope.setCurrentIndex(index)

        proxy = self._preset_field_widgets.get(
            "publish_reverse_proxy"
        )

        if isinstance(proxy, QCheckBox):
            proxy.setChecked(False)

        self._synchronize_preset_network_controls()

    def _preset_proxy_toggled(
        self,
        checked: bool,
    ) -> None:
        scope = self._preset_field_widgets.get(
            "access_scope"
        )
        firewall = self._preset_field_widgets.get(
            "allow_firewall"
        )

        if checked:
            if isinstance(scope, QComboBox):
                index = scope.findData(
                    "localhost"
                )

                if index >= 0:
                    scope.setCurrentIndex(index)

            if isinstance(firewall, QCheckBox):
                firewall.setChecked(False)

        self._synchronize_preset_network_controls()

    def _synchronize_preset_network_controls(
        self,
    ) -> None:
        scope = self._preset_field_widgets.get(
            "access_scope"
        )
        firewall = self._preset_field_widgets.get(
            "allow_firewall"
        )
        proxy = self._preset_field_widgets.get(
            "publish_reverse_proxy"
        )
        public_host = self._preset_field_widgets.get(
            "public_host"
        )
        proxy_login = self._preset_field_widgets.get(
            "proxy_login"
        )

        proxy_enabled = (
            isinstance(proxy, QCheckBox)
            and proxy.isChecked()
        )

        if isinstance(scope, QComboBox):
            if proxy_enabled:
                localhost_index = scope.findData(
                    "localhost"
                )

                if (
                    localhost_index >= 0
                    and scope.currentIndex()
                    != localhost_index
                ):
                    scope.setCurrentIndex(
                        localhost_index
                    )

                scope.setEnabled(False)
            else:
                scope.setEnabled(True)

        scope_value = (
            scope.currentData()
            if isinstance(scope, QComboBox)
            else "localhost"
        )

        if isinstance(firewall, QCheckBox):
            firewall_available = (
                scope_value == "local_network"
                and not proxy_enabled
                and self._context is not None
                and self._context.capability_registry.get(
                    "firewall.allow_docker_service"
                )
                is not None
            )

            if not firewall_available:
                firewall.setChecked(False)

            firewall.setEnabled(
                firewall_available
            )

        if isinstance(public_host, QLineEdit):
            public_host.setEnabled(
                proxy_enabled
            )

        if isinstance(proxy_login, QCheckBox):
            if not proxy_enabled:
                proxy_login.setChecked(False)

            proxy_login.setEnabled(
                proxy_enabled
            )

    def _update_preset_deploy_button(
        self,
        *_args: object,
    ) -> None:
        name_widget = self._preset_field_widgets.get(
            "application_name"
        )

        name = (
            name_widget.text().strip()
            if isinstance(name_widget, QLineEdit)
            else ""
        )

        if (
            name
            and self._repository.application_exists(
                name
            )
        ):
            self._create_button.setText(
                "Modify and Redeploy Preset Application"
            )
        else:
            self._create_button.setText(
                "Deploy Preset Application"
            )

    def _clear_loaded_preset(self) -> None:
        self._loaded_preset = None
        self._preset_field_widgets.clear()

        if hasattr(
            self,
            "_preset_builder_group",
        ):
            self._preset_builder_group.setVisible(False)
            self._container_group.setVisible(True)
            self._create_button.setText(
                "Pull Image and Create Container"
            )

    def _preset_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}

        for field_id, widget in (
            self._preset_field_widgets.items()
        ):
            if isinstance(widget, QLineEdit):
                values[field_id] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[field_id] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[field_id] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[field_id] = (
                    widget.currentData()
                )

        return values

    def _container_access_addresses(
        self,
        container_name: str,
        published_ports: str,
    ) -> tuple[str, str]:
        managed = next(
            (
                item
                for item in self._repository.managed_containers()
                if (
                    item.name == container_name
                    or container_name == f"{item.name}-web"
                )
            ),
            None,
        )

        if managed is None or managed.host_port <= 0:
            return "", ""

        scheme = (
            "https"
            if managed.service_protocol == "https"
            else "http"
            if managed.service_protocol == "http"
            else managed.service_protocol
        )
        port = managed.host_port

        if managed.access_scope == "localhost":
            local = f"{scheme}://127.0.0.1:{port}"
            return local, "Not directly available"

        if managed.access_scope == "local_network":
            address = managed.host_address.strip()

            if not address:
                address = (
                    self._repository.primary_local_address()
                )

            if not address:
                return "", ""

            url = f"{scheme}://{address}:{port}"
            return url, url

        if managed.access_scope == "all_networks":
            address = (
                self._repository.primary_local_address()
            )

            local = f"{scheme}://127.0.0.1:{port}"
            network = (
                f"{scheme}://{address}:{port}"
                if address
                else "Available on all interfaces"
            )
            return local, network

        return "", ""

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

            (
                local_address,
                network_address,
            ) = self._container_access_addresses(
                item.name,
                item.ports,
            )

            values = (
                item.name,
                item.image,
                item.state,
                item.status,
                item.ports,
                local_address,
                network_address,
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
        self._refresh_presets()

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
        if self._loaded_preset is not None:
            self._deploy_loaded_preset()
            return

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

    def _deploy_loaded_preset(self) -> None:
        preset = self._loaded_preset

        if preset is None:
            return

        values = self._preset_values()
        service = preset.data.get(
            "service",
            {},
        )

        if not isinstance(service, dict):
            service = {}

        application_name = str(
            values.get(
                "application_name",
                preset.preset_id.rsplit(".", 1)[-1],
            )
        )
        host_port = int(
            values.get("host_port", 0)
        )
        access_scope = str(
            values.get(
                "access_scope",
                "localhost",
            )
        )
        publish_proxy = bool(
            values.get(
                "publish_reverse_proxy",
                False,
            )
        )
        allow_firewall = bool(
            values.get(
                "allow_firewall",
                False,
            )
        )
        public_host = str(
            values.get("public_host", "")
        ).strip()

        if publish_proxy:
            access_scope = "localhost"
            values["access_scope"] = "localhost"

            if not public_host:
                QMessageBox.warning(
                    self,
                    "Public Hostname Required",
                    (
                        "Enter the public hostname that Caddy "
                        "should use for this application."
                    ),
                )
                return

        if access_scope == "all_networks":
            response = QMessageBox.warning(
                self,
                "All Networks Selected",
                (
                    "This application will publish its web port "
                    "on every network interface and may become "
                    "reachable from the internet.\n\n"
                    "Continue?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return

        existing_application = (
            self._repository.application_exists(
                application_name
            )
        )

        if existing_application:
            response = QMessageBox.question(
                self,
                "Modify and Redeploy Application",
                (
                    f"Update and redeploy {application_name}?\n\n"
                    "Existing Docker volumes and the stored "
                    "database password will be preserved."
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return

        tasks = [
            PrivilegedTask(
                "docker.deploy_preset",
                {
                    "preset": preset.data,
                    "values": values,
                },
            )
        ]

        if (
            access_scope == "local_network"
            and allow_firewall
        ):
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
                            "container": application_name,
                            "host_port": host_port,
                            "container_port": int(
                                service.get(
                                    "container_port",
                                    0,
                                )
                            ),
                            "protocol": str(
                                service.get(
                                    "transport_protocol",
                                    "tcp",
                                )
                            ),
                            "sources": (
                                self._repository.local_networks()
                            ),
                            "comment": (
                                "LEC Docker preset "
                                + application_name
                            ),
                        },
                    )
                )

        if publish_proxy:
            capability = (
                self._context.capability_registry.get(
                    "reverse_proxy.create_http_proxy"
                )
                if self._context is not None
                else None
            )

            if (
                capability is None
                or not capability.privileged_task_id
            ):
                QMessageBox.warning(
                    self,
                    "Reverse Proxy Unavailable",
                    (
                        "The Reverse Proxy module is not "
                        "available. Disable reverse proxy "
                        "publication or install that module first."
                    ),
                )
                return

            tasks.append(
                PrivilegedTask(
                    capability.privileged_task_id,
                    {
                        "original_name": "",
                        "data": {
                            "name": (
                                "Docker "
                                + application_name
                            ),
                            "public_host": public_host,
                            "route_type": "host",
                            "path": "",
                            "strip_path": True,
                            "credential_username": "",
                            "backend_host": "127.0.0.1",
                            "backend_port": host_port,
                            "backend_https": (
                                str(
                                    service.get(
                                        "protocol",
                                        "http",
                                    )
                                )
                                == "https"
                            ),
                            "require_login": bool(
                                values.get(
                                    "proxy_login",
                                    False,
                                )
                            ),
                            "enabled": True,
                        },
                    },
                )
            )

        self._run_sequence(
            tasks,
            preset.name + " Deployed",
            timeout=2000,
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
