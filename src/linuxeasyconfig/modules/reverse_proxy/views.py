from __future__ import annotations

import json
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
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
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

from .repository import (
    ReverseProxyRepository,
    ReverseProxyStatus,
)
from .storage import ProxyRule


class _TaskSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _TaskWorker(QRunnable):
    def __init__(self, task: PrivilegedTask) -> None:
        super().__init__()
        self._task = task
        self.signals = _TaskSignals()

    def run(self) -> None:
        try:
            message = PrivilegedRunner().run(self._task)
            self.signals.succeeded.emit(message)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class ReverseProxyView(QWidget):
    def __init__(
        self,
        repository: ReverseProxyRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._status: ReverseProxyStatus | None = None
        self._busy = False
        self._active_worker: _TaskWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._editing_rule = ""
        self._editing_credential = ""

        heading = QLabel("Reverse Proxy Management")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        description = QLabel(
            "Install and manage Caddy reverse-proxy routes, "
            "login credentials, and Fail2Ban protection."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview_tab(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_rules_tab(),
            "Proxy Rules",
        )
        self._tabs.addTab(
            self._build_credentials_tab(),
            "Credentials",
        )
        self._tabs.addTab(
            self._build_intrusion_tab(),
            "Intrusion Protection",
        )
        self._tabs.addTab(
            self._build_logs_tab(),
            "Activity and Logs",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
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
            "Install Reverse Proxy System"
        )
        self._install_button.clicked.connect(
            self._begin_install
        )

        self._install_progress_label = QLabel(
            "Installation is not currently running."
        )
        self._install_progress_label.setWordWrap(True)
        self._install_progress = QProgressBar()
        self._install_progress.setRange(0, 0)
        self._install_progress.setVisible(False)

        setup_group = QGroupBox("System Setup")
        setup_layout = QVBoxLayout(setup_group)
        setup_layout.addWidget(self._setup_heading)
        setup_layout.addWidget(
            self._setup_description
        )
        setup_layout.addWidget(self._install_button)
        setup_layout.addWidget(
            self._install_progress_label
        )
        setup_layout.addWidget(
            self._install_progress
        )

        self._caddy_installed = QLabel()
        self._caddy_running = QLabel()
        self._caddy_version = QLabel()
        self._caddy_validation = QLabel()
        self._caddy_validation.setWordWrap(True)
        self._caddy_validation.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        caddy = QGroupBox("Caddy")
        caddy_form = QFormLayout(caddy)
        caddy_form.addRow(
            "Installed:",
            self._caddy_installed,
        )
        caddy_form.addRow(
            "Running:",
            self._caddy_running,
        )
        caddy_form.addRow(
            "Version:",
            self._caddy_version,
        )
        caddy_form.addRow(
            "Configuration:",
            self._caddy_validation,
        )

        self._fail2ban_installed = QLabel()
        self._fail2ban_running = QLabel()
        self._fail2ban_version = QLabel()
        self._fail2ban_validation = QLabel()
        self._fail2ban_validation.setWordWrap(True)
        self._fail2ban_validation.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        fail2ban = QGroupBox("Fail2Ban")
        fail2ban_form = QFormLayout(fail2ban)
        fail2ban_form.addRow(
            "Installed:",
            self._fail2ban_installed,
        )
        fail2ban_form.addRow(
            "Running:",
            self._fail2ban_running,
        )
        fail2ban_form.addRow(
            "Version:",
            self._fail2ban_version,
        )
        fail2ban_form.addRow(
            "Configuration:",
            self._fail2ban_validation,
        )

        services = QVBoxLayout()
        services.addWidget(caddy)
        services.addWidget(fail2ban)

        refresh = QPushButton("Refresh Status")
        refresh.clicked.connect(self.reload)
        self._reload_button = QPushButton(
            "Validate and Reload Both"
        )
        self._reload_button.clicked.connect(
            self._begin_reload
        )

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(refresh)
        buttons.addWidget(self._reload_button)

        layout.addWidget(setup_group)
        layout.addLayout(services)
        layout.addLayout(buttons)
        layout.addStretch()
        return container

    def _build_rules_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "Create simple hostname, URL-path, or "
            "credential-based routes. Caddy validates every "
            "change before it is activated."
        )
        note.setWordWrap(True)

        self._rules_table = QTableWidget(0, 6)
        self._rules_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Public address",
                "Routing",
                "Internal destination",
                "Login",
                "Enabled",
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
            self._update_rule_buttons
        )

        self._rule_name = QLineEdit()
        self._public_host = QLineEdit()
        self._route_type = QComboBox()
        self._route_type.addItem(
            "Entire public address",
            "host",
        )
        self._route_type.addItem(
            "URL path",
            "path",
        )
        self._route_type.addItem(
            "Authenticated username",
            "credential",
        )
        self._route_type.currentIndexChanged.connect(
            self._route_type_changed
        )

        self._rule_path = QLineEdit()
        self._rule_path.setPlaceholderText("/plex")
        self._strip_path = QCheckBox(
            "Remove this path before forwarding"
        )
        self._backend_host = QLineEdit("127.0.0.1")
        self._backend_port = QSpinBox()
        self._backend_port.setRange(1, 65535)
        self._backend_port.setValue(8080)
        self._backend_https = QCheckBox(
            "The internal service uses HTTPS"
        )
        self._require_login = QCheckBox(
            "Require a Caddy login"
        )
        self._rule_credential = QComboBox()
        self._rule_enabled = QCheckBox(
            "Rule is enabled"
        )
        self._rule_enabled.setChecked(True)

        form_group = QGroupBox("Add Proxy Rule")
        self._rule_form_group = form_group
        form = QFormLayout(form_group)
        form.addRow("Rule name:", self._rule_name)
        form.addRow(
            "Public hostname:",
            self._public_host,
        )
        form.addRow("Routing method:", self._route_type)
        form.addRow("Public URL path:", self._rule_path)
        form.addRow("", self._strip_path)
        form.addRow(
            "Authenticated user:",
            self._rule_credential,
        )
        form.addRow(
            "Internal server:",
            self._backend_host,
        )
        form.addRow(
            "Internal port:",
            self._backend_port,
        )
        form.addRow("", self._backend_https)
        form.addRow("", self._require_login)
        form.addRow("", self._rule_enabled)

        self._save_rule = QPushButton("Add Rule")
        self._save_rule.clicked.connect(
            self._begin_save_rule
        )
        self._cancel_rule = QPushButton("Cancel Modification")
        self._cancel_rule.clicked.connect(
            self._clear_rule_form
        )
        self._cancel_rule.setVisible(False)
        self._modify_rule = QPushButton("Modify Selected")
        self._modify_rule.clicked.connect(
            self._load_selected_rule
        )
        self._delete_rule = QPushButton("Remove Selected")
        self._delete_rule.clicked.connect(
            self._begin_delete_rule
        )

        actions = QHBoxLayout()
        actions.addWidget(self._save_rule)
        actions.addWidget(self._cancel_rule)
        actions.addStretch()
        actions.addWidget(self._modify_rule)
        actions.addWidget(self._delete_rule)

        layout.addWidget(note)
        layout.addWidget(self._rules_table, 1)
        layout.addWidget(form_group)
        layout.addLayout(actions)

        self._route_type_changed()
        self._update_rule_buttons()
        return container

    def _build_credentials_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "Passwords are hashed by Caddy and are never stored "
            "as readable text. Leave the password blank while "
            "modifying an account to keep its existing password."
        )
        note.setWordWrap(True)

        self._credentials_table = QTableWidget(0, 2)
        self._credentials_table.setHorizontalHeaderLabels(
            ["Username", "Used by rules"]
        )
        self._credentials_table.horizontalHeader().setStretchLastSection(
            True
        )
        self._credentials_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._credentials_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._credentials_table.itemSelectionChanged.connect(
            self._update_credential_buttons
        )

        self._credential_username = QLineEdit()
        self._credential_password = QLineEdit()
        self._credential_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self._credential_group = QGroupBox(
            "Add Credential"
        )
        form = QFormLayout(self._credential_group)
        form.addRow(
            "Username:",
            self._credential_username,
        )
        form.addRow(
            "Password:",
            self._credential_password,
        )

        self._save_credential = QPushButton(
            "Add Credential"
        )
        self._save_credential.clicked.connect(
            self._begin_save_credential
        )
        self._cancel_credential = QPushButton(
            "Cancel Modification"
        )
        self._cancel_credential.clicked.connect(
            self._clear_credential_form
        )
        self._cancel_credential.setVisible(False)
        self._modify_credential = QPushButton(
            "Modify Selected"
        )
        self._modify_credential.clicked.connect(
            self._load_selected_credential
        )
        self._delete_credential = QPushButton(
            "Remove Selected"
        )
        self._delete_credential.clicked.connect(
            self._begin_delete_credential
        )

        actions = QHBoxLayout()
        actions.addWidget(self._save_credential)
        actions.addWidget(self._cancel_credential)
        actions.addStretch()
        actions.addWidget(self._modify_credential)
        actions.addWidget(self._delete_credential)

        layout.addWidget(note)
        layout.addWidget(self._credentials_table, 1)
        layout.addWidget(self._credential_group)
        layout.addLayout(actions)

        self._update_credential_buttons()
        return container

    def _build_intrusion_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        explanation = QLabel(
            "Fail2Ban blocks addresses that repeatedly fail "
            "Caddy authentication. It does not replace security "
            "inside the proxied applications."
        )
        explanation.setWordWrap(True)

        self._protection_enabled = QCheckBox(
            "Enable Caddy login protection"
        )
        self._protection_preset = QComboBox()
        self._protection_preset.addItems(
            ["Balanced", "Strict", "Relaxed", "Custom"]
        )
        self._protection_preset.currentTextChanged.connect(
            self._preset_changed
        )
        self._max_attempts = QSpinBox()
        self._max_attempts.setRange(1, 100)
        self._find_minutes = QSpinBox()
        self._find_minutes.setRange(1, 10080)
        self._ban_minutes = QSpinBox()
        self._ban_minutes.setRange(1, 525600)

        self._permanent_ban = QCheckBox(
            "Block until manually unbanned"
        )
        self._permanent_ban.toggled.connect(
            self._permanent_ban_changed
        )

        self._incremental = QCheckBox(
            "Increase block time for repeat offenders"
        )
        self._never_block = QTextEdit()
        self._never_block.setMaximumHeight(90)
        self._never_block.setPlaceholderText(
            "One IP address or network per line"
        )

        settings = QGroupBox("Protection Settings")
        form = QFormLayout(settings)
        form.addRow("", self._protection_enabled)
        form.addRow("Preset:", self._protection_preset)
        form.addRow(
            "Failed attempts allowed:",
            self._max_attempts,
        )
        form.addRow(
            "Count failures within (minutes):",
            self._find_minutes,
        )
        form.addRow(
            "Block duration (minutes):",
            self._ban_minutes,
        )
        form.addRow(
            "Permanent block:",
            self._permanent_ban,
        )
        form.addRow("", self._incremental)
        form.addRow(
            "Addresses never blocked:",
            self._never_block,
        )

        save = QPushButton(
            "Save Protection Settings"
        )
        save.clicked.connect(
            self._begin_save_protection
        )

        self._jail_status = QLabel()
        self._banned_list = QListWidget()
        self._unban_button = QPushButton(
            "Unban Selected Address"
        )
        self._unban_button.clicked.connect(
            self._begin_unban
        )
        self._banned_list.itemSelectionChanged.connect(
            self._update_unban_button
        )
        refresh = QPushButton("Refresh Bans")
        refresh.clicked.connect(self._refresh_bans)

        ban_actions = QHBoxLayout()
        ban_actions.addStretch()
        ban_actions.addWidget(refresh)
        ban_actions.addWidget(self._unban_button)

        layout.addWidget(explanation)
        layout.addWidget(settings)
        layout.addWidget(save)
        layout.addWidget(self._jail_status)
        layout.addWidget(self._banned_list, 1)
        layout.addLayout(ban_actions)
        return container

    def _build_logs_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "This view shows the most recent LEC-managed Caddy "
            "access-log entries. Entries are structured JSON."
        )
        note.setWordWrap(True)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setLineWrapMode(
            QTextEdit.LineWrapMode.NoWrap
        )
        refresh = QPushButton("Refresh Activity")
        refresh.clicked.connect(self._refresh_logs)

        layout.addWidget(note)
        layout.addWidget(self._log_text, 1)
        layout.addWidget(refresh)
        return container

    def reload(self) -> None:
        try:
            self._status = self._repository.status()
        except Exception as exc:
            _show_scrollable_error(
                self,
                "Status Check Failed",
                str(exc),
            )
            return

        status = self._status
        self._caddy_installed.setText(
            _yes_no(status.caddy.installed)
        )
        self._caddy_running.setText(
            _yes_no(status.caddy.active)
        )
        self._caddy_version.setText(
            status.caddy.version
        )
        self._caddy_validation.setText(
            "Valid"
            if status.caddy_config_valid
            else status.caddy_config_detail
        )
        self._fail2ban_installed.setText(
            _yes_no(status.fail2ban.installed)
        )
        self._fail2ban_running.setText(
            _yes_no(status.fail2ban.active)
        )
        self._fail2ban_version.setText(
            status.fail2ban.version
        )
        self._fail2ban_validation.setText(
            "Valid"
            if status.fail2ban_config_valid
            else status.fail2ban_config_detail
        )

        if status.lec_setup_complete:
            self._setup_heading.setText(
                "Reverse proxy system is configured"
            )
            self._setup_description.setText(
                "Caddy and Fail2Ban are installed, running, "
                "and using valid configurations."
            )
            self._install_button.setText(
                "Repair or Complete Setup"
            )
        elif status.caddy.installed or status.fail2ban.installed:
            self._setup_heading.setText(
                "Setup is partially complete"
            )
            self._setup_description.setText(
                "Run setup again to repair or complete it."
            )
            self._install_button.setText(
                "Complete Setup"
            )
        else:
            self._setup_heading.setText(
                "Reverse proxy system is not installed"
            )
            self._setup_description.setText(
                "LEC can install and configure Caddy and "
                "Fail2Ban automatically."
            )
            self._install_button.setText(
                "Install Reverse Proxy System"
            )

        self._reload_button.setEnabled(
            status.lec_setup_complete
        )
        self._refresh_credentials()
        self._refresh_rules()
        self._refresh_protection()
        self._refresh_bans()
        self._refresh_logs()

    def _refresh_credentials(self) -> None:
        credentials = self._repository.credentials()
        rules = self._repository.rules()

        self._credentials_table.setRowCount(0)
        self._rule_credential.clear()

        for credential in credentials:
            used = [
                rule.name
                for rule in rules
                if rule.credential_username
                == credential.username
            ]
            row = self._credentials_table.rowCount()
            self._credentials_table.insertRow(row)
            self._credentials_table.setItem(
                row,
                0,
                QTableWidgetItem(credential.username),
            )
            self._credentials_table.setItem(
                row,
                1,
                QTableWidgetItem(", ".join(used)),
            )
            self._rule_credential.addItem(
                credential.username
            )

    def _refresh_rules(self) -> None:
        rules = self._repository.rules()
        self._rules_table.setRowCount(0)

        for rule in rules:
            route = {
                "host": "Entire address",
                "path": f"Path: {rule.path}",
                "credential": (
                    "User: "
                    + rule.credential_username
                ),
            }[rule.route_type]
            backend = (
                f"{'https' if rule.backend_https else 'http'}://"
                f"{rule.backend_host}:{rule.backend_port}"
            )
            row = self._rules_table.rowCount()
            self._rules_table.insertRow(row)
            values = [
                rule.name,
                rule.public_host,
                route,
                backend,
                "Required"
                if (
                    rule.require_login
                    or rule.route_type == "credential"
                )
                else "No",
                "Yes" if rule.enabled else "No",
            ]
            for column, value in enumerate(values):
                self._rules_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

    def _refresh_protection(self) -> None:
        settings = self._repository.protection_settings()
        self._protection_enabled.setChecked(
            settings.enabled
        )
        index = self._protection_preset.findText(
            settings.preset
        )
        self._protection_preset.setCurrentIndex(
            max(0, index)
        )
        self._max_attempts.setValue(
            settings.max_attempts
        )
        self._find_minutes.setValue(
            settings.find_minutes
        )
        self._ban_minutes.setValue(
            settings.ban_minutes
        )
        self._permanent_ban.setChecked(
            settings.permanent
        )
        self._incremental.setChecked(
            settings.incremental
        )
        self._permanent_ban_changed(
            settings.permanent
        )
        self._never_block.setPlainText(
            "\n".join(settings.never_block or [])
        )

    def _refresh_bans(self) -> None:
        self._banned_list.clear()
        addresses = self._repository.banned_addresses()
        for address in addresses:
            self._banned_list.addItem(address)
        self._jail_status.setText(
            f"{len(addresses)} currently banned address"
            f"{'es' if len(addresses) != 1 else ''}."
        )
        self._update_unban_button()

    def _refresh_logs(self) -> None:
        lines = self._repository.recent_activity()
        self._log_text.setPlainText(
            "\n".join(lines)
            if lines
            else "No LEC-managed Caddy activity has been logged yet."
        )

    def _route_type_changed(self) -> None:
        route_type = self._route_type.currentData()
        is_path = route_type == "path"
        is_credential = route_type == "credential"
        self._rule_path.setEnabled(is_path)
        self._strip_path.setEnabled(is_path)
        self._rule_credential.setEnabled(is_credential)
        self._require_login.setEnabled(
            not is_credential
        )
        if is_credential:
            self._require_login.setChecked(True)

    def _permanent_ban_changed(
        self,
        checked: bool,
    ) -> None:
        self._ban_minutes.setEnabled(
            not checked
        )
        self._incremental.setEnabled(
            not checked
        )

        if checked:
            self._incremental.setChecked(False)

    def _preset_changed(self, preset: str) -> None:
        values = {
            "Balanced": (5, 10, 60),
            "Strict": (3, 10, 1440),
            "Relaxed": (10, 15, 15),
        }.get(preset)
        if values:
            self._permanent_ban.setChecked(False)
            self._max_attempts.setValue(values[0])
            self._find_minutes.setValue(values[1])
            self._ban_minutes.setValue(values[2])

    def _begin_install(self) -> None:
        response = QMessageBox.question(
            self,
            "Install Reverse Proxy System",
            "LEC will install or repair Caddy and Fail2Ban. Continue?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if response == QMessageBox.StandardButton.Yes:
            self._run_task(
                "reverse_proxy.install",
                {},
                "Reverse Proxy System Installed",
                installation=True,
            )

    def _begin_reload(self) -> None:
        self._run_task(
            "reverse_proxy.reload",
            {},
            "Reverse Proxy System Reloaded",
        )

    def _begin_save_credential(self) -> None:
        self._run_task(
            "reverse_proxy.credential_save",
            {
                "original_username": self._editing_credential,
                "username": self._credential_username.text(),
                "password": self._credential_password.text(),
            },
            "Credential Saved",
        )

    def _begin_delete_credential(self) -> None:
        row = self._credentials_table.currentRow()
        if row < 0:
            return
        username = self._credentials_table.item(row, 0).text()
        self._run_task(
            "reverse_proxy.credential_delete",
            {"username": username},
            "Credential Removed",
        )

    def _begin_save_rule(self) -> None:
        self._run_task(
            "reverse_proxy.rule_save",
            {
                "original_name": self._editing_rule,
                "data": {
                    "name": self._rule_name.text(),
                    "public_host": self._public_host.text(),
                    "route_type": self._route_type.currentData(),
                    "path": self._rule_path.text(),
                    "strip_path": self._strip_path.isChecked(),
                    "credential_username": self._rule_credential.currentText(),
                    "backend_host": self._backend_host.text(),
                    "backend_port": self._backend_port.value(),
                    "backend_https": self._backend_https.isChecked(),
                    "require_login": self._require_login.isChecked(),
                    "enabled": self._rule_enabled.isChecked(),
                },
            },
            "Proxy Rule Saved",
        )

    def _begin_delete_rule(self) -> None:
        row = self._rules_table.currentRow()
        if row < 0:
            return
        name = self._rules_table.item(row, 0).text()
        self._run_task(
            "reverse_proxy.rule_delete",
            {"name": name},
            "Proxy Rule Removed",
        )

    def _begin_save_protection(self) -> None:
        self._run_task(
            "reverse_proxy.protection_save",
            {
                "data": {
                    "enabled": self._protection_enabled.isChecked(),
                    "preset": self._protection_preset.currentText(),
                    "max_attempts": self._max_attempts.value(),
                    "find_minutes": self._find_minutes.value(),
                    "ban_minutes": self._ban_minutes.value(),
                    "permanent": self._permanent_ban.isChecked(),
                    "incremental": self._incremental.isChecked(),
                    "never_block": self._never_block.toPlainText(),
                }
            },
            "Protection Settings Saved",
        )

    def _begin_unban(self) -> None:
        items = self._banned_list.selectedItems()
        if not items:
            return
        self._run_task(
            "reverse_proxy.unban",
            {"address": items[0].text()},
            "Address Unbanned",
        )

    def _load_selected_credential(self) -> None:
        row = self._credentials_table.currentRow()
        if row < 0:
            return
        username = self._credentials_table.item(row, 0).text()
        self._editing_credential = username
        self._credential_username.setText(username)
        self._credential_password.clear()
        self._credential_group.setTitle(
            "Modify Credential"
        )
        self._save_credential.setText(
            "Save Changes"
        )
        self._cancel_credential.setVisible(True)

    def _clear_credential_form(self) -> None:
        self._editing_credential = ""
        self._credential_username.clear()
        self._credential_password.clear()
        self._credential_group.setTitle(
            "Add Credential"
        )
        self._save_credential.setText(
            "Add Credential"
        )
        self._cancel_credential.setVisible(False)

    def _load_selected_rule(self) -> None:
        row = self._rules_table.currentRow()
        if row < 0:
            return
        name = self._rules_table.item(row, 0).text()
        rule = next(
            item
            for item in self._repository.rules()
            if item.name == name
        )
        self._editing_rule = rule.name
        self._rule_name.setText(rule.name)
        self._public_host.setText(rule.public_host)
        self._route_type.setCurrentIndex(
            self._route_type.findData(rule.route_type)
        )
        self._rule_path.setText(rule.path)
        self._strip_path.setChecked(rule.strip_path)
        self._backend_host.setText(rule.backend_host)
        self._backend_port.setValue(rule.backend_port)
        self._backend_https.setChecked(rule.backend_https)
        self._require_login.setChecked(rule.require_login)
        self._rule_enabled.setChecked(rule.enabled)
        index = self._rule_credential.findText(
            rule.credential_username
        )
        if index >= 0:
            self._rule_credential.setCurrentIndex(index)
        self._rule_form_group.setTitle(
            "Modify Proxy Rule"
        )
        self._save_rule.setText("Save Changes")
        self._cancel_rule.setVisible(True)

    def _clear_rule_form(self) -> None:
        self._editing_rule = ""
        self._rule_name.clear()
        self._public_host.clear()
        self._route_type.setCurrentIndex(0)
        self._rule_path.clear()
        self._strip_path.setChecked(True)
        self._backend_host.setText("127.0.0.1")
        self._backend_port.setValue(8080)
        self._backend_https.setChecked(False)
        self._require_login.setChecked(False)
        self._rule_enabled.setChecked(True)
        self._rule_form_group.setTitle("Add Proxy Rule")
        self._save_rule.setText("Add Rule")
        self._cancel_rule.setVisible(False)

    def _update_rule_buttons(self) -> None:
        selected = self._rules_table.currentRow() >= 0
        self._modify_rule.setEnabled(selected)
        self._delete_rule.setEnabled(selected)

    def _update_credential_buttons(self) -> None:
        selected = self._credentials_table.currentRow() >= 0
        self._modify_credential.setEnabled(selected)
        self._delete_credential.setEnabled(selected)

    def _update_unban_button(self) -> None:
        self._unban_button.setEnabled(
            bool(self._banned_list.selectedItems())
        )

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        *,
        installation: bool = False,
    ) -> None:
        if self._busy:
            return
        self._set_busy(True)

        if installation:
            self._install_progress.setVisible(True)
            self._install_progress_label.setText(
                "Installation is in progress. This may take "
                "several minutes; please be patient."
            )

        worker = _TaskWorker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )
        worker.signals.succeeded.connect(
            lambda message: QMessageBox.information(
                self,
                title,
                message,
            )
        )
        worker.signals.failed.connect(
            lambda message: _show_scrollable_error(
                self,
                "Reverse Proxy Operation Failed",
                message,
            )
        )
        worker.signals.finished.connect(
            self._task_finished
        )
        self._active_worker = worker
        self._thread_pool.start(worker)

    def _task_finished(self) -> None:
        self._active_worker = None
        self._install_progress.setVisible(False)
        self._install_progress_label.setText(
            "Installation is not currently running."
        )
        self._set_busy(False)
        self._clear_rule_form()
        self._clear_credential_form()
        self.reload()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._tabs.setEnabled(not busy)


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


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"
