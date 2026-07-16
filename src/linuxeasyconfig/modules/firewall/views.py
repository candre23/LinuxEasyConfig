from __future__ import annotations

import ipaddress
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
    QPushButton,
    QProgressBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import (
    PrivilegedRunner,
)
from linuxeasyconfig.core.privileged.task import (
    PrivilegedTask,
)

from .repository import FirewallRepository


class _TaskSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _TaskWorker(QRunnable):
    def __init__(
        self,
        task: PrivilegedTask,
    ) -> None:
        super().__init__()
        self._task = task
        self.signals = _TaskSignals()

    def run(self) -> None:
        try:
            result = PrivilegedRunner().run(
                self._task
            )
            self.signals.succeeded.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class FirewallView(QWidget):
    def __init__(
        self,
        repository: FirewallRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._active_worker: _TaskWorker | None = None
        self._busy = False

        heading = QLabel("Firewall")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Manage Ubuntu's built-in firewall using "
            "plain-language rules. Incoming connections are "
            "normally blocked unless a rule allows them."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview_tab(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_rules_tab(),
            "Inbound and Outbound Rules",
        )
        self._tabs.addTab(
            self._build_docker_rules_tab(),
            "Docker Rules",
        )
        self._tabs.addTab(
            self._build_log_tab(),
            "Blocked Activity",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

        self.reload()

    def _build_overview_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._setup_heading = QLabel()
        self._setup_heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        self._setup_description = QLabel()
        self._setup_description.setWordWrap(True)

        self._install_button = QPushButton(
            "Install Ubuntu Firewall"
        )
        self._install_button.clicked.connect(
            self._begin_install
        )

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)

        setup = QGroupBox("System Setup")
        setup_layout = QVBoxLayout(setup)
        setup_layout.addWidget(self._setup_heading)
        setup_layout.addWidget(
            self._setup_description
        )
        setup_layout.addWidget(self._install_button)
        setup_layout.addWidget(self._progress)

        self._installed = QLabel()
        self._active = QLabel()
        self._version = QLabel()
        self._logging_status = QLabel()
        self._incoming_status = QLabel()
        self._outgoing_status = QLabel()

        status = QGroupBox("Firewall Status")
        status_form = QFormLayout(status)
        status_form.addRow(
            "Installed:",
            self._installed,
        )
        status_form.addRow(
            "Protection enabled:",
            self._active,
        )
        status_form.addRow(
            "Version:",
            self._version,
        )
        status_form.addRow(
            "Logging:",
            self._logging_status,
        )
        status_form.addRow(
            "Default incoming:",
            self._incoming_status,
        )
        status_form.addRow(
            "Default outgoing:",
            self._outgoing_status,
        )

        self._enable_button = QPushButton()
        self._enable_button.clicked.connect(
            self._toggle_firewall
        )

        self._incoming_default = QComboBox()
        self._incoming_default.addItem(
            "Block unless allowed",
            "deny",
        )
        self._incoming_default.addItem(
            "Allow unless blocked",
            "allow",
        )
        self._incoming_default.addItem(
            "Reject unless allowed",
            "reject",
        )

        self._outgoing_default = QComboBox()
        self._outgoing_default.addItem(
            "Allow unless blocked",
            "allow",
        )
        self._outgoing_default.addItem(
            "Block unless allowed",
            "deny",
        )
        self._outgoing_default.addItem(
            "Reject unless allowed",
            "reject",
        )

        self._logging_level = QComboBox()
        self._logging_level.addItem(
            "Off",
            "off",
        )
        self._logging_level.addItem(
            "Low (recommended)",
            "low",
        )
        self._logging_level.addItem(
            "Medium",
            "medium",
        )
        self._logging_level.addItem(
            "High",
            "high",
        )
        self._logging_level.addItem(
            "Full",
            "full",
        )

        save_defaults = QPushButton(
            "Save Default Behavior"
        )
        save_defaults.clicked.connect(
            self._begin_save_defaults
        )
        save_logging = QPushButton(
            "Save Logging Level"
        )
        save_logging.clicked.connect(
            self._begin_save_logging
        )

        settings = QGroupBox(
            "Basic Protection Settings"
        )
        settings_form = QFormLayout(settings)
        settings_form.addRow(
            "Incoming connections:",
            self._incoming_default,
        )
        settings_form.addRow(
            "Outgoing connections:",
            self._outgoing_default,
        )
        settings_form.addRow("", save_defaults)
        settings_form.addRow(
            "Blocked activity logging:",
            self._logging_level,
        )
        settings_form.addRow("", save_logging)

        warning = QLabel(
            "Recommended home-server defaults: block incoming "
            "connections unless a rule allows them, and allow "
            "outgoing connections unless a rule blocks them."
        )
        warning.setWordWrap(True)

        refresh = QPushButton("Refresh Status")
        refresh.clicked.connect(
            self._begin_refresh_status
        )

        reset = QPushButton(
            "Reset All Firewall Rules"
        )
        reset.clicked.connect(
            self._begin_reset
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self._enable_button)
        buttons.addStretch()
        buttons.addWidget(refresh)
        buttons.addWidget(reset)

        layout.addWidget(setup)
        layout.addWidget(status)
        layout.addWidget(settings)
        layout.addWidget(warning)
        layout.addLayout(buttons)
        layout.addStretch()

        return container

    def _build_rules_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "Rules are evaluated in the order shown by UFW. "
            "Use local-network restrictions for administration "
            "services whenever practical."
        )
        note.setWordWrap(True)

        self._rules_table = QTableWidget(0, 4)
        self._rules_table.setHorizontalHeaderLabels(
            [
                "Number",
                "Destination / Port",
                "Action",
                "Source",
            ]
        )
        self._rules_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._rules_table.horizontalHeader().setStretchLastSection(
            True
        )
        self._rules_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._rules_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._rules_table.itemSelectionChanged.connect(
            self._update_delete_button
        )

        self._action = QComboBox()
        self._action.addItem(
            "Allow connection",
            "allow",
        )
        self._action.addItem(
            "Block silently",
            "deny",
        )
        self._action.addItem(
            "Reject connection",
            "reject",
        )
        self._action.addItem(
            "Limit repeated connections",
            "limit",
        )

        self._direction = QComboBox()
        self._direction.addItem(
            "Incoming to this computer",
            "incoming",
        )
        self._direction.addItem(
            "Outgoing from this computer",
            "outgoing",
        )

        self._source_scope = QComboBox()
        self._source_scope.addItem(
            "Anywhere",
            "anywhere",
        )
        self._source_scope.addItem(
            "Detected local network",
            "local",
        )
        self._source_scope.addItem(
            "Specific address or network",
            "specific",
        )
        self._source_scope.currentIndexChanged.connect(
            self._source_scope_changed
        )

        self._source = QLineEdit()
        self._source.setPlaceholderText(
            "Example: 192.168.1.0/24"
        )

        self._destination = QLineEdit()
        self._destination.setPlaceholderText(
            "Leave blank for this computer"
        )

        self._service_mode = QComboBox()
        self._service_mode.addItem(
            "Enter port manually",
            "port",
        )
        self._service_mode.addItem(
            "Use an installed application profile",
            "profile",
        )
        self._service_mode.currentIndexChanged.connect(
            self._service_mode_changed
        )

        self._profile = QComboBox()
        self._port = QLineEdit()
        self._port.setPlaceholderText(
            "Examples: 443, 8000:8010"
        )

        self._protocol = QComboBox()
        self._protocol.addItem("TCP", "tcp")
        self._protocol.addItem("UDP", "udp")
        self._protocol.addItem(
            "Both / any protocol",
            "any",
        )

        self._comment = QLineEdit()
        self._comment.setPlaceholderText(
            "Optional plain-language description"
        )

        self._local_network_note = QLabel()
        self._local_network_note.setWordWrap(True)
        self._local_networks: list[str] = []

        form_group = QGroupBox(
            "Add Firewall Rule"
        )
        form = QFormLayout(form_group)
        form.addRow("Action:", self._action)
        form.addRow("Direction:", self._direction)
        form.addRow(
            "Allowed or blocked source:",
            self._source_scope,
        )
        form.addRow(
            "Specific source:",
            self._source,
        )
        form.addRow(
            "Destination address:",
            self._destination,
        )
        form.addRow(
            "Service selection:",
            self._service_mode,
        )
        form.addRow(
            "Application profile:",
            self._profile,
        )
        form.addRow("Port or range:", self._port)
        form.addRow("Network protocol:", self._protocol)
        form.addRow(
            "Rule description:",
            self._comment,
        )
        form.addRow("", self._local_network_note)

        add = QPushButton("Add Rule")
        add.clicked.connect(self._begin_add_rule)

        self._delete_button = QPushButton(
            "Remove Selected Rule"
        )
        self._delete_button.clicked.connect(
            self._begin_delete_rule
        )

        actions = QHBoxLayout()
        actions.addWidget(add)
        actions.addStretch()
        actions.addWidget(self._delete_button)

        layout.addWidget(note)
        layout.addWidget(self._rules_table, 1)
        layout.addWidget(form_group)
        layout.addLayout(actions)

        self._source_scope_changed()
        self._service_mode_changed()
        self._update_delete_button()
        if hasattr(self, "_remove_docker_rule"):
            self._update_docker_rule_buttons()
        return container

    def _build_docker_rules_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        explanation = QLabel(
            "Docker-published ports can bypass ordinary UFW "
            "rules. These rules are applied in Docker's own "
            "forwarding path and are restored after restart."
        )
        explanation.setWordWrap(True)

        self._docker_backend = QLabel()
        self._docker_backend.setWordWrap(True)

        self._docker_rules_table = QTableWidget(0, 5)
        self._docker_rules_table.setHorizontalHeaderLabels(
            [
                "Container",
                "Published Port",
                "Container Port",
                "Protocol",
                "Access",
            ]
        )
        docker_header = (
            self._docker_rules_table.horizontalHeader()
        )
        docker_header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        docker_header.setStretchLastSection(True)
        self._docker_rules_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._docker_rules_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._docker_rules_table.setWordWrap(True)

        self._block_docker_rule = QPushButton(
            "Block Selected Docker Port"
        )
        self._block_docker_rule.clicked.connect(
            self._begin_block_docker_rule
        )

        self._unblock_docker_rule = QPushButton(
            "Unblock Selected Docker Port"
        )
        self._unblock_docker_rule.clicked.connect(
            self._begin_unblock_docker_rule
        )

        self._remove_docker_rule = QPushButton(
            "Stop Managing This Port"
        )
        self._remove_docker_rule.clicked.connect(
            self._begin_remove_docker_rule
        )
        self._docker_rules_table.itemSelectionChanged.connect(
            self._update_docker_rule_buttons
        )

        reapply = QPushButton(
            "Reapply Docker Rules"
        )
        reapply.clicked.connect(
            lambda: self._run_task(
                "firewall.reapply_docker_rules",
                {},
                "Docker Firewall Rules Reapplied",
            )
        )

        buttons = QHBoxLayout()
        buttons.addWidget(reapply)
        buttons.addStretch()
        buttons.addWidget(
            self._block_docker_rule
        )
        buttons.addWidget(
            self._unblock_docker_rule
        )
        buttons.addWidget(
            self._remove_docker_rule
        )

        layout.addWidget(explanation)
        layout.addWidget(self._docker_backend)
        layout.addWidget(
            self._docker_rules_table,
            1,
        )
        layout.addLayout(buttons)

        self._update_docker_rule_buttons()
        return container

    def _build_log_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "This view shows recent kernel log entries generated "
            "by UFW. Logging must be enabled before blocked "
            "connections will appear."
        )
        note.setWordWrap(True)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(
            QTextEdit.LineWrapMode.NoWrap
        )

        refresh = QPushButton(
            "Refresh Blocked Activity"
        )
        refresh.clicked.connect(
            self._refresh_logs
        )

        layout.addWidget(note)
        layout.addWidget(self._log_text, 1)
        layout.addWidget(refresh)
        return container

    def reload(self) -> None:
        try:
            status = self._repository.status()
        except Exception as exc:
            _show_scrollable_error(
                self,
                "Firewall Status Failed",
                str(exc),
            )
            return

        self._installed.setText(
            "Yes" if status.installed else "No"
        )
        self._active.setText(
            "Yes" if status.active else "No"
        )
        self._version.setText(status.version)
        self._logging_status.setText(status.logging)
        self._incoming_status.setText(
            status.default_incoming
        )
        self._outgoing_status.setText(
            status.default_outgoing
        )

        if status.installed:
            self._setup_heading.setText(
                "Ubuntu Firewall is installed"
            )
            self._setup_description.setText(
                "UFW is available and can be configured below."
            )
            self._install_button.setText(
                "Repair or Reinstall UFW"
            )
        else:
            self._setup_heading.setText(
                "Ubuntu Firewall is not installed"
            )
            self._setup_description.setText(
                "LEC can install Ubuntu's standard UFW firewall."
            )
            self._install_button.setText(
                "Install Ubuntu Firewall"
            )

        self._enable_button.setText(
            "Disable Firewall"
            if status.active
            else "Enable Firewall"
        )
        self._enable_button.setProperty(
            "firewall_active",
            status.active,
        )
        self._enable_button.setEnabled(
            status.installed
        )

        self._set_combo_data(
            self._incoming_default,
            status.default_incoming,
        )
        self._set_combo_data(
            self._outgoing_default,
            status.default_outgoing,
        )

        logging_value = (
            status.logging.split()[0].lower()
            if status.logging
            else "low"
        )
        self._set_combo_data(
            self._logging_level,
            logging_value,
        )

        self._refresh_local_networks()
        self._refresh_profiles()
        self._refresh_rules()
        self._refresh_docker_rules()
        self._refresh_logs()

        self._tabs.setEnabled(
            status.installed and not self._busy
        )

    def _refresh_local_networks(self) -> None:
        self._local_networks = (
            self._repository.local_networks()
        )

        if not self._local_networks:
            self._local_network_note.setText(
                "LEC could not detect the network connected to "
                "this computer. Select “Specific address or network” "
                "to enter one manually."
            )
            return

        descriptions = [
            self._describe_network(value)
            for value in self._local_networks
        ]

        if len(descriptions) == 1:
            self._local_network_note.setText(
                "Detected local network: "
                + descriptions[0]
                + ". Only devices on this network will match "
                "the rule."
            )
        else:
            self._local_network_note.setText(
                "Detected local networks: "
                + "; ".join(descriptions)
                + ". A rule will be created for each network."
            )

    @staticmethod
    def _describe_network(value: str) -> str:
        try:
            network = ipaddress.ip_network(
                value,
                strict=False,
            )
        except ValueError:
            return value

        if isinstance(network, ipaddress.IPv4Network):
            return (
                f"{network.network_address} through "
                f"{network.broadcast_address} ({value})"
            )

        return value

    def _refresh_profiles(self) -> None:
        current = self._profile.currentText()
        self._profile.clear()

        for profile in (
            self._repository.application_profiles()
        ):
            self._profile.addItem(profile)

        index = self._profile.findText(current)
        if index >= 0:
            self._profile.setCurrentIndex(index)

    def _refresh_rules(self) -> None:
        self._rules_table.setRowCount(0)

        for rule in self._repository.rules():
            row = self._rules_table.rowCount()
            self._rules_table.insertRow(row)

            values = [
                str(rule.number),
                rule.destination,
                rule.action.title(),
                rule.source,
            ]

            for column, value in enumerate(values):
                self._rules_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self._update_delete_button()

    def _refresh_docker_rules(self) -> None:
        self._docker_backend.setText(
            "Docker firewall backend: "
            + self._repository.docker_firewall_backend()
        )
        self._docker_rules_table.setRowCount(0)

        for rule in self._repository.docker_rules():
            row = self._docker_rules_table.rowCount()
            self._docker_rules_table.insertRow(row)

            values = [
                rule.container,
                str(rule.host_port),
                str(rule.container_port),
                rule.protocol.upper(),
                (
                    "Blocked"
                    if rule.blocked
                    else (
                        "Local network only: "
                        + ", ".join(rule.sources)
                    )
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self._docker_rules_table.setItem(
                    row,
                    column,
                    item,
                )

        self._docker_rules_table.resizeRowsToContents()
        self._update_docker_rule_buttons()

    def _begin_block_docker_rule(self) -> None:
        row = self._docker_rules_table.currentRow()

        if row < 0:
            return

        container = self._docker_rules_table.item(
            row,
            0,
        ).text()
        host_port = int(
            self._docker_rules_table.item(
                row,
                1,
            ).text()
        )
        protocol = (
            self._docker_rules_table.item(
                row,
                3,
            ).text().lower()
        )

        response = QMessageBox.question(
            self,
            "Block Docker Port",
            (
                f"Block all new connections to {container} "
                f"on port {host_port}/{protocol}?\n\n"
                "The container will continue running, but this "
                "published port will no longer be reachable."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.block_docker_service",
            {
                "container": container,
                "host_port": host_port,
                "protocol": protocol,
            },
            "Docker Port Blocked",
        )

    def _begin_unblock_docker_rule(self) -> None:
        row = self._docker_rules_table.currentRow()

        if row < 0:
            return

        container = self._docker_rules_table.item(
            row,
            0,
        ).text()
        host_port = int(
            self._docker_rules_table.item(
                row,
                1,
            ).text()
        )
        protocol = (
            self._docker_rules_table.item(
                row,
                3,
            ).text().lower()
        )

        response = QMessageBox.question(
            self,
            "Unblock Docker Port",
            (
                f"Allow new connections to {container} on "
                f"port {host_port}/{protocol} from the "
                "configured local networks?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.unblock_docker_service",
            {
                "container": container,
                "host_port": host_port,
                "protocol": protocol,
            },
            "Docker Port Unblocked",
        )

    def _begin_remove_docker_rule(self) -> None:
        row = self._docker_rules_table.currentRow()

        if row < 0:
            return

        container = self._docker_rules_table.item(
            row,
            0,
        ).text()
        host_port = int(
            self._docker_rules_table.item(
                row,
                1,
            ).text()
        )
        protocol = (
            self._docker_rules_table.item(
                row,
                3,
            ).text().lower()
        )

        response = QMessageBox.warning(
            self,
            "Stop Managing Docker Port",
            (
                f"Stop managing {container} on port "
                f"{host_port}/{protocol}?\n\n"
                "LEC's allow and block rules will both be removed. "
                "Docker will control access directly, and the service "
                "may become reachable from other computers."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.remove_docker_service",
            {
                "container": container,
                "host_port": host_port,
                "protocol": protocol,
            },
            "Docker Firewall Rule Removed",
        )

    def _update_docker_rule_buttons(self) -> None:
        row = self._docker_rules_table.currentRow()
        selected = row >= 0 and not self._busy
        blocked = False

        if selected:
            access_item = self._docker_rules_table.item(
                row,
                4,
            )
            blocked = (
                access_item is not None
                and access_item.text() == "Blocked"
            )

        self._block_docker_rule.setEnabled(
            selected and not blocked
        )
        self._unblock_docker_rule.setEnabled(
            selected and blocked
        )
        self._remove_docker_rule.setEnabled(selected)

    def _refresh_logs(self) -> None:
        lines = self._repository.recent_log_lines()
        self._log_text.setPlainText(
            "\n".join(lines)
            if lines
            else (
                "No recent UFW log entries were found."
            )
        )

    def _toggle_firewall(self) -> None:
        active = bool(
            self._enable_button.property(
                "firewall_active"
            )
        )
        enable = not active

        if enable:
            warning = (
                "Enable the firewall now?\n\n"
                "Before enabling it on a computer you access "
                "remotely, make sure an allow rule exists for "
                "that remote-access service."
            )
        else:
            warning = (
                "Disable firewall protection?\n\n"
                "Existing rules will remain saved but will not "
                "protect this computer until the firewall is "
                "enabled again."
            )

        response = QMessageBox.question(
            self,
            "Change Firewall State",
            warning,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.set_enabled",
            {"enabled": enable},
            "Firewall State Changed",
        )

    def _begin_install(self) -> None:
        self._run_task(
            "firewall.install",
            {},
            "Ubuntu Firewall Installed",
            installation=True,
        )

    def _begin_save_defaults(self) -> None:
        self._run_task(
            "firewall.set_defaults",
            {
                "incoming": (
                    self._incoming_default.currentData()
                ),
                "outgoing": (
                    self._outgoing_default.currentData()
                ),
            },
            "Default Behavior Saved",
        )

    def _begin_save_logging(self) -> None:
        self._run_task(
            "firewall.set_logging",
            {
                "level": (
                    self._logging_level.currentData()
                )
            },
            "Logging Level Saved",
        )

    def _begin_add_rule(self) -> None:
        source_mode = self._source_scope.currentData()

        if source_mode == "local":
            sources = list(self._local_networks)

            if not sources:
                QMessageBox.warning(
                    self,
                    "Local Network Not Detected",
                    (
                        "LEC could not determine the network connected "
                        "to this computer. Choose “Specific address or "
                        "network” and enter the desired network manually."
                    ),
                )
                return
        elif source_mode == "specific":
            sources = [self._source.text()]
        else:
            sources = ["anywhere"]

        profile = (
            self._profile.currentText()
            if self._service_mode.currentData()
            == "profile"
            else ""
        )
        port = (
            self._port.text()
            if self._service_mode.currentData()
            == "port"
            else ""
        )

        self._run_task(
            "firewall.add_rule",
            {
                "action": self._action.currentData(),
                "direction": self._direction.currentData(),
                "sources": sources,
                "destination": self._destination.text(),
                "port": port,
                "protocol": self._protocol.currentData(),
                "profile": profile,
                "comment": self._comment.text(),
            },
            "Firewall Rule Added",
        )

    def _begin_delete_rule(self) -> None:
        row = self._rules_table.currentRow()
        if row < 0:
            return

        number = int(
            self._rules_table.item(row, 0).text()
        )
        destination = self._rules_table.item(
            row,
            1,
        ).text()

        response = QMessageBox.question(
            self,
            "Remove Firewall Rule",
            (
                f"Remove firewall rule {number} "
                f"for {destination}?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.delete_rule",
            {"number": number},
            "Firewall Rule Removed",
        )

    def _begin_refresh_status(self) -> None:
        self._run_task(
            "firewall.refresh",
            {},
            "Firewall Status Refreshed",
        )

    def _begin_reset(self) -> None:
        response = QMessageBox.warning(
            self,
            "Reset Firewall",
            (
                "This removes every custom UFW rule and "
                "disables the firewall.\n\n"
                "This action cannot be undone through UFW. "
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "firewall.reset",
            {},
            "Firewall Reset",
        )

    def _source_scope_changed(self) -> None:
        self._source.setEnabled(
            self._source_scope.currentData()
            == "specific"
        )

    def _service_mode_changed(self) -> None:
        profile_mode = (
            self._service_mode.currentData()
            == "profile"
        )
        self._profile.setEnabled(profile_mode)
        self._port.setEnabled(not profile_mode)
        self._protocol.setEnabled(not profile_mode)

    def _update_delete_button(self) -> None:
        self._delete_button.setEnabled(
            self._rules_table.currentRow() >= 0
            and not self._busy
        )

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        *,
        installation: bool = False,
    ) -> None:
        self._run_task_sequence(
            [
                PrivilegedTask(
                    task_id=task_id,
                    arguments=arguments,
                )
            ],
            title,
            installation=installation,
        )

    def _run_task_sequence(
        self,
        tasks: list[PrivilegedTask],
        title: str,
        *,
        installation: bool = False,
    ) -> None:
        if self._busy or not tasks:
            return

        self._set_busy(True)

        if installation:
            self._progress.setVisible(True)

        self._pending_tasks = list(tasks)
        self._pending_title = title
        self._start_next_task()

    def _start_next_task(self) -> None:
        if not self._pending_tasks:
            QMessageBox.information(
                self,
                self._pending_title,
                "The operation completed successfully.",
            )
            self._task_finished()
            return

        worker = _TaskWorker(
            self._pending_tasks.pop(0)
        )
        worker.signals.failed.connect(
            self._task_failed
        )
        worker.signals.finished.connect(
            self._worker_finished
        )
        self._active_worker = worker
        self._thread_pool.start(worker)

    def _worker_finished(self) -> None:
        self._active_worker = None

        if getattr(
            self,
            "_sequence_failed",
            False,
        ):
            self._task_finished()
            return

        self._start_next_task()

    def _task_failed(self, message: str) -> None:
        self._sequence_failed = True
        self._pending_tasks.clear()
        _show_scrollable_error(
            self,
            "Firewall Operation Failed",
            message,
        )

    def _task_finished(self) -> None:
        self._sequence_failed = False
        self._active_worker = None
        self._progress.setVisible(False)
        self._set_busy(False)
        self.reload()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._tabs.setEnabled(not busy)
        self._install_button.setEnabled(not busy)
        self._update_delete_button()

    @staticmethod
    def _set_combo_data(
        combo: QComboBox,
        value: str,
    ) -> None:
        normalized = value.strip().lower()
        index = combo.findData(normalized)

        if index >= 0:
            combo.setCurrentIndex(index)


def _show_scrollable_error(
    parent: QWidget,
    title: str,
    message: str,
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(760, 520)
    dialog.setMinimumSize(520, 320)

    screen = dialog.screen()
    if screen is not None:
        available = screen.availableGeometry()
        dialog.setMaximumSize(
            int(available.width() * 0.9),
            int(available.height() * 0.85),
        )

    details = QTextEdit()
    details.setReadOnly(True)
    details.setPlainText(message)
    details.setLineWrapMode(
        QTextEdit.LineWrapMode.NoWrap
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Close
    )
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(
        QLabel(
            "The operation did not complete successfully."
        )
    )
    layout.addWidget(details, 1)
    layout.addWidget(buttons)
    dialog.exec()
