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
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import DynamicDNSRepository


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
            value = PrivilegedRunner().run(
                self._task,
                timeout=self._timeout,
            )
            self.signals.succeeded.emit(str(value))
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class DynamicDNSView(QWidget):
    def __init__(
        self,
        repository: DynamicDNSRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._active_worker: _Worker | None = None
        self._busy = False
        self._editing_account_id = ""
        self._provider_fields: dict[str, QLineEdit] = {}

        heading = QLabel("Dynamic DNS")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        description = QLabel(
            "Manage provider accounts, dynamic hostnames, and "
            "automatic updates when your public IP address changes."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_providers(),
            "Providers",
        )
        self._tabs.addTab(
            self._build_hostnames(),
            "Hostnames",
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

        self._timer_status = QLabel()
        self._timer_status.setWordWrap(True)
        self._public_ipv4 = QLabel()
        self._public_ipv6 = QLabel()
        self._last_run = QLabel()
        self._last_success = QLabel()
        self._last_result = QLabel()
        self._last_result.setWordWrap(True)

        status = QGroupBox("DNS Updater Status")
        form = QFormLayout(status)
        form.addRow("DNS update service:", self._timer_status)
        form.addRow("Public IPv4:", self._public_ipv4)
        form.addRow("Public IPv6:", self._public_ipv6)
        form.addRow("Last checked:", self._last_run)
        form.addRow("Last successful update:", self._last_success)
        form.addRow("Last result:", self._last_result)

        install = QPushButton(
            "Install or Repair DNS Updater"
        )
        install.clicked.connect(
            lambda: self._run_task(
                "dynamic_dns.install_timer",
                {},
                "DNS Updater Installed",
            )
        )
        update = QPushButton("Sync DNS Now")
        update.clicked.connect(
            lambda: self._run_task(
                "dynamic_dns.update_now",
                {},
                "DNS Records Synchronized",
                timeout=240,
            )
        )
        refresh = QPushButton("Refresh Status")
        refresh.setToolTip(
            "Reload the latest DNS updater status. This is a "
            "read-only action and does not require administrator access."
        )
        refresh.clicked.connect(self.reload)

        buttons = QHBoxLayout()
        buttons.addWidget(install)
        buttons.addWidget(update)
        buttons.addWidget(refresh)
        buttons.addStretch()

        note = QLabel(
            "LEC checks your public address every five minutes. DNS "
            "providers are contacted when the address changes, when "
            "Sync DNS Now is selected, and at least once every seven "
            "days even if the address has not changed. Refresh Status "
            "only reloads the latest saved results, so it does not ask "
            "for an administrator password."
        )
        note.setWordWrap(True)

        layout.addWidget(status)
        layout.addLayout(buttons)
        layout.addWidget(note)
        layout.addStretch()
        return container

    def _build_providers(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._providers_table = QTableWidget(0, 4)
        self._providers_table.setHorizontalHeaderLabels(
            ["Name", "Provider", "Enabled", "ID"]
        )
        self._providers_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._providers_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._providers_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self._provider_type = QComboBox()
        for provider in self._repository.providers():
            self._provider_type.addItem(
                provider.name,
                provider.id,
            )
        self._provider_type.currentIndexChanged.connect(
            self._rebuild_provider_fields
        )

        self._provider_name = QLineEdit()
        self._provider_enabled = QCheckBox(
            "Provider account is enabled"
        )
        self._provider_enabled.setChecked(True)

        self._provider_form_group = QGroupBox(
            "Add Provider Account"
        )
        self._provider_form = QFormLayout(
            self._provider_form_group
        )
        self._provider_form.addRow(
            "Provider:",
            self._provider_type,
        )
        self._provider_form.addRow(
            "Account name:",
            self._provider_name,
        )
        self._provider_form.addRow(
            "",
            self._provider_enabled,
        )

        self._save_provider = QPushButton(
            "Test and Save Provider Account"
        )
        self._save_provider.clicked.connect(
            self._save_provider_account
        )
        delete = QPushButton(
            "Remove Selected Provider Account"
        )
        delete.clicked.connect(
            self._delete_selected_provider
        )
        cancel = QPushButton("Clear Form")
        cancel.clicked.connect(
            self._clear_provider_form
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self._save_provider)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(delete)

        warning = QLabel(
            "API tokens are stored root-only under "
            "/etc/linuxeasyconfig/dynamic_dns. Prefer tokens limited "
            "to DNS read and edit permissions for the intended zones."
        )
        warning.setWordWrap(True)

        layout.addWidget(warning)
        layout.addWidget(self._providers_table, 1)
        layout.addWidget(self._provider_form_group)
        layout.addLayout(buttons)

        self._rebuild_provider_fields()
        return container

    def _build_hostnames(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._hostnames_table = QTableWidget(0, 7)
        self._hostnames_table.setHorizontalHeaderLabels(
            [
                "Hostname",
                "Zone",
                "Provider Account",
                "IPv4",
                "IPv6",
                "Cloudflare Proxy",
                "ID",
            ]
        )
        header = self._hostnames_table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)
        self._hostnames_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._hostnames_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self._hostname_account = QComboBox()
        self._hostname_zone = QLineEdit()
        self._hostname_zone.setPlaceholderText(
            "example.com or example.dedyn.io"
        )
        self._hostname = QLineEdit()
        self._hostname.setPlaceholderText(
            "guac.example.com"
        )
        self._hostname_ipv4 = QCheckBox(
            "Manage IPv4 address"
        )
        self._hostname_ipv4.setChecked(True)
        self._hostname_ipv6 = QCheckBox(
            "Manage IPv6 address"
        )
        self._hostname_proxied = QCheckBox(
            "Use Cloudflare proxy when supported"
        )

        group = QGroupBox("Create Dynamic Hostname")
        form = QFormLayout(group)
        form.addRow(
            "Provider account:",
            self._hostname_account,
        )
        form.addRow("DNS zone:", self._hostname_zone)
        form.addRow(
            "Complete hostname:",
            self._hostname,
        )
        form.addRow("", self._hostname_ipv4)
        form.addRow("", self._hostname_ipv6)
        form.addRow("", self._hostname_proxied)

        create = QPushButton(
            "Create and Begin Managing Hostname"
        )
        create.clicked.connect(
            self._create_hostname
        )
        remove = QPushButton(
            "Stop Managing Selected Hostname"
        )
        remove.clicked.connect(
            self._delete_selected_hostname
        )

        buttons = QHBoxLayout()
        buttons.addWidget(create)
        buttons.addStretch()
        buttons.addWidget(remove)

        note = QLabel(
            "Creating a hostname immediately writes its current public "
            "IP to the provider, then the automatic update timer keeps "
            "it current."
        )
        note.setWordWrap(True)

        layout.addWidget(note)
        layout.addWidget(self._hostnames_table, 1)
        layout.addWidget(group)
        layout.addLayout(buttons)
        return container

    def reload(self) -> None:
        timer = self._repository.timer_status()
        status = self._repository.status()

        self._timer_status.setText(
            (
                "Installed, enabled, and running"
                if timer.active and timer.enabled
                else timer.detail
            )
        )
        self._public_ipv4.setText(
            str(status.get("public_ipv4", "")).strip()
            or "Not detected yet"
        )
        self._public_ipv6.setText(
            str(status.get("public_ipv6", "")).strip()
            or "Not available or not detected"
        )
        self._last_run.setText(
            str(status.get("last_run", "Never"))
        )
        self._last_success.setText(
            str(status.get("last_success", "Never"))
        )
        errors = status.get("errors", [])
        self._last_result.setText(
            "Successful"
            if status.get("success", False)
            else (
                "\n".join(str(value) for value in errors)
                if isinstance(errors, list) and errors
                else "No update has run yet."
            )
        )

        accounts = self._repository.accounts()
        account_names = {
            str(item.get("id", "")): str(
                item.get("name", "")
            )
            for item in accounts
        }

        self._providers_table.setRowCount(0)
        self._hostname_account.clear()

        for account in accounts:
            row = self._providers_table.rowCount()
            self._providers_table.insertRow(row)
            values = (
                str(account.get("name", "")),
                str(account.get("provider_id", "")),
                "Yes"
                if account.get("enabled", True)
                else "No",
                str(account.get("id", "")),
            )
            for column, value in enumerate(values):
                self._providers_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

            if account.get("enabled", True):
                self._hostname_account.addItem(
                    str(account.get("name", "")),
                    str(account.get("id", "")),
                )

        self._hostnames_table.setRowCount(0)

        for hostname in self._repository.hostnames():
            row = self._hostnames_table.rowCount()
            self._hostnames_table.insertRow(row)
            values = (
                str(hostname.get("hostname", "")),
                str(hostname.get("zone", "")),
                account_names.get(
                    str(
                        hostname.get(
                            "provider_account_id",
                            "",
                        )
                    ),
                    "Unknown",
                ),
                "Yes"
                if hostname.get("ipv4_enabled", True)
                else "No",
                "Yes"
                if hostname.get("ipv6_enabled", False)
                else "No",
                "Yes"
                if hostname.get("proxied", False)
                else "No",
                str(hostname.get("id", "")),
            )
            for column, value in enumerate(values):
                self._hostnames_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

    def _rebuild_provider_fields(self) -> None:
        while self._provider_form.rowCount() > 3:
            self._provider_form.removeRow(3)

        self._provider_fields.clear()
        provider_id = str(
            self._provider_type.currentData()
        )
        metadata = next(
            (
                item
                for item in self._repository.providers()
                if item.id == provider_id
            ),
            None,
        )

        if metadata is None:
            return

        for field in metadata.fields:
            widget = QLineEdit()

            if field.field_type == "password":
                widget.setEchoMode(
                    QLineEdit.EchoMode.Password
                )

            widget.setPlaceholderText(
                field.placeholder
            )
            widget.setToolTip(field.help)
            self._provider_fields[field.id] = widget
            self._provider_form.addRow(
                field.label + ":",
                widget,
            )

    def _save_provider_account(self) -> None:
        self._run_task(
            "dynamic_dns.provider_save",
            {
                "original_id": self._editing_account_id,
                "provider_id": str(
                    self._provider_type.currentData()
                ),
                "name": self._provider_name.text(),
                "credentials": {
                    key: widget.text()
                    for key, widget in (
                        self._provider_fields.items()
                    )
                },
                "enabled": (
                    self._provider_enabled.isChecked()
                ),
            },
            "Provider Account Saved",
            timeout=180,
        )

    def _delete_selected_provider(self) -> None:
        row = self._providers_table.currentRow()
        if row < 0:
            return
        account_id = self._providers_table.item(
            row,
            3,
        ).text()
        self._run_task(
            "dynamic_dns.provider_delete",
            {"account_id": account_id},
            "Provider Account Removed",
        )

    def _create_hostname(self) -> None:
        account_id = str(
            self._hostname_account.currentData()
        )

        if not account_id:
            QMessageBox.warning(
                self,
                "Provider Account Required",
                "Add and enable a provider account first.",
            )
            return

        self._run_task(
            "dynamic_dns.hostname_create",
            {
                "account_id": account_id,
                "zone": self._hostname_zone.text(),
                "hostname": self._hostname.text(),
                "ipv4_enabled": (
                    self._hostname_ipv4.isChecked()
                ),
                "ipv6_enabled": (
                    self._hostname_ipv6.isChecked()
                ),
                "proxied": (
                    self._hostname_proxied.isChecked()
                ),
                "owner_module_id": "",
                "owner_reference": "",
            },
            "Dynamic Hostname Created",
            timeout=300,
        )

    def _delete_selected_hostname(self) -> None:
        row = self._hostnames_table.currentRow()
        if row < 0:
            return

        hostname_id = self._hostnames_table.item(
            row,
            6,
        ).text()
        hostname = self._hostnames_table.item(
            row,
            0,
        ).text()

        dialog = QMessageBox(self)
        dialog.setWindowTitle(
            "Stop Managing Hostname"
        )
        dialog.setText(
            f"Stop managing {hostname}?"
        )
        dialog.setInformativeText(
            "Choose Yes to also delete the A and AAAA "
            "records from the provider. Choose No to leave "
            "the provider records in place but stop updating them."
        )
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel
        )
        response = dialog.exec()

        if response == QMessageBox.StandardButton.Cancel:
            return

        self._run_task(
            "dynamic_dns.hostname_delete",
            {
                "hostname_id": hostname_id,
                "delete_remote": (
                    response
                    == QMessageBox.StandardButton.Yes
                ),
            },
            "Dynamic Hostname Removed",
        )

    def _clear_provider_form(self) -> None:
        self._editing_account_id = ""
        self._provider_name.clear()
        self._provider_enabled.setChecked(True)
        for widget in self._provider_fields.values():
            widget.clear()

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        *,
        timeout: int = 180,
    ) -> None:
        if self._busy:
            return

        self._busy = True
        self._tabs.setEnabled(False)
        worker = _Worker(
            PrivilegedTask(
                task_id,
                arguments,
            ),
            timeout=timeout,
        )
        worker.signals.succeeded.connect(
            lambda message: QMessageBox.information(
                self,
                title,
                message,
            )
        )
        worker.signals.failed.connect(
            lambda message: _show_error(
                self,
                message,
            )
        )
        worker.signals.finished.connect(
            self._task_finished
        )
        self._active_worker = worker
        self._pool.start(worker)

    def _task_finished(self) -> None:
        self._active_worker = None
        self._busy = False
        self._tabs.setEnabled(True)
        self.reload()


def _show_error(
    parent: QWidget,
    message: str,
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(
        "Dynamic DNS Operation Failed"
    )
    dialog.resize(760, 500)
    details = QTextEdit()
    details.setReadOnly(True)
    details.setPlainText(message)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Close
    )
    buttons.rejected.connect(dialog.reject)
    layout = QVBoxLayout(dialog)
    layout.addWidget(details, 1)
    layout.addWidget(buttons)
    dialog.exec()
