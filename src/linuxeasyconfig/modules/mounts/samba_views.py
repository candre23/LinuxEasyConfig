from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    Signal,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import (
    PrivilegedRunner,
)
from linuxeasyconfig.core.privileged.task import (
    PrivilegedTask,
)

from .samba_share import (
    HostedShare,
    detected_local_networks,
    load_hosted_shares,
    local_groups,
    local_users,
    samba_status,
    split_names,
    validate_share_values,
)


class _Signals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(
        self,
        task: PrivilegedTask,
    ) -> None:
        super().__init__()
        self._task = task
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = PrivilegedRunner().run(
                self._task,
                timeout=900,
            )
            self.signals.succeeded.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class HostedSharesView(QWidget):
    shares_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._editing_name = ""
        self._busy = False
        self._active_worker: _Worker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        self._status = QLabel()
        self._status.setWordWrap(True)

        self._install_button = QPushButton(
            "Install Samba Server"
        )
        self._install_button.clicked.connect(
            self._install_samba
        )

        self._configure_firewall = QCheckBox(
            "Allow Samba through UFW only from "
            "the detected local network"
        )
        self._configure_firewall.setChecked(True)

        setup = QGroupBox("Samba Server")
        setup_layout = QVBoxLayout(setup)
        setup_layout.addWidget(self._status)
        setup_layout.addWidget(
            self._configure_firewall
        )
        setup_layout.addWidget(
            self._install_button
        )

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            [
                "Share Name",
                "Folder",
                "Access",
                "Permissions",
                "Network Scope",
                "Enabled",
            ]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(
            True
        )
        self._table.itemSelectionChanged.connect(
            self._selection_changed
        )

        self._name = QLineEdit()
        self._name.setPlaceholderText(
            "Example: Family Photos"
        )

        self._path = QLineEdit()
        self._path.setPlaceholderText(
            "/srv/samba/photos"
        )

        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_folder)

        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self._path, 1)
        path_layout.addWidget(browse)

        self._comment = QLineEdit()
        self._comment.setPlaceholderText(
            "Optional description shown to network clients"
        )

        self._read_only = QCheckBox(
            "Share is read-only"
        )
        self._read_only.setChecked(True)

        self._guest = QCheckBox(
            "Allow access without a username or password "
            "(may be blocked by newer versions of Windows)"
        )
        self._guest.toggled.connect(
            self._guest_changed
        )

        self._users = QLineEdit()
        self._users.setPlaceholderText(
            "Comma-separated local usernames"
        )

        self._groups = QLineEdit()
        self._groups.setPlaceholderText(
            "Comma-separated local group names"
        )

        account_help = QLabel(
            "Authenticated users must be ordinary local "
            "Linux users and must also have a Samba password. "
            "Use the password section below to enable one."
        )
        account_help.setWordWrap(True)

        self._local_only = QCheckBox(
            "Allow connections only from the "
            "detected local network"
        )
        self._local_only.setChecked(True)

        networks = detected_local_networks()
        self._network_note = QLabel(
            (
                "Detected local network"
                + ("s" if len(networks) != 1 else "")
                + ": "
                + ", ".join(networks)
            )
            if networks
            else (
                "No local IPv4 network was detected. "
                "Local-network restriction cannot be saved "
                "until a network is available."
            )
        )
        self._network_note.setWordWrap(True)

        self._enabled = QCheckBox(
            "Share is enabled"
        )
        self._enabled.setChecked(True)

        form_group = QGroupBox(
            "Create or Edit a Shared Folder"
        )
        form = QFormLayout(form_group)
        form.addRow("Share name:", self._name)
        form.addRow("Folder:", path_row)
        form.addRow("Description:", self._comment)
        form.addRow("", self._read_only)
        form.addRow("", self._guest)
        form.addRow("Allowed users:", self._users)
        form.addRow("Allowed groups:", self._groups)
        form.addRow("", account_help)
        form.addRow("", self._local_only)
        form.addRow("", self._network_note)
        form.addRow("", self._enabled)

        self._save = QPushButton(
            "Create Share"
        )
        self._save.clicked.connect(
            self._save_share
        )

        self._clear = QPushButton("Clear")
        self._clear.clicked.connect(
            self._clear_form
        )

        self._edit = QPushButton(
            "Edit Selected"
        )
        self._edit.clicked.connect(
            self._edit_selected
        )

        self._remove = QPushButton(
            "Remove Selected"
        )
        self._remove.clicked.connect(
            self._remove_selected
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self._clear)
        buttons.addWidget(self._save)
        buttons.addStretch()
        buttons.addWidget(self._edit)
        buttons.addWidget(self._remove)

        self._password_user = QComboBox()
        self._password = QLineEdit()
        self._password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self._password_confirm = QLineEdit()
        self._password_confirm.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        set_password = QPushButton(
            "Set or Change Samba Password"
        )
        set_password.clicked.connect(
            self._set_password
        )

        password_group = QGroupBox(
            "Authenticated Samba Users"
        )
        password_form = QFormLayout(
            password_group
        )
        password_form.addRow(
            "Local user:",
            self._password_user,
        )
        password_form.addRow(
            "Samba password:",
            self._password,
        )
        password_form.addRow(
            "Confirm password:",
            self._password_confirm,
        )
        password_form.addRow("", set_password)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(setup)
        layout.addWidget(self._table)
        layout.addWidget(form_group)
        layout.addLayout(buttons)
        layout.addWidget(password_group)
        layout.addStretch()

        self.reload()

    def reload(self) -> None:
        status = samba_status()

        if status.installed:
            state = (
                "running"
                if status.service_active
                else "not running"
            )
            self._status.setText(
                f"{status.version}; service {state}; "
                f"{status.configured_shares} "
                "LEC-managed share(s)."
            )
            self._install_button.setText(
                "Repair or Reinstall Samba"
            )
        else:
            self._status.setText(
                "Samba server is not installed. "
                "Install it before creating hosted shares."
            )
            self._install_button.setText(
                "Install Samba Server"
            )

        self._table.setRowCount(0)

        for share in load_hosted_shares():
            row = self._table.rowCount()
            self._table.insertRow(row)

            access = (
                "Guest"
                if share.guest_access
                else (
                    "Restricted"
                    if (
                        share.allowed_users
                        or share.allowed_groups
                    )
                    else "Authenticated users"
                )
            )
            permissions = (
                "Read only"
                if share.read_only
                else "Read and write"
            )
            scope = (
                "Local network"
                if share.local_network_only
                else "Any reachable network"
            )

            values = [
                share.name,
                share.path,
                access,
                permissions,
                scope,
                "Yes" if share.enabled else "No",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(256, share)
                self._table.setItem(
                    row,
                    column,
                    item,
                )

        current_user = (
            self._password_user.currentText()
        )
        self._password_user.clear()
        self._password_user.addItems(
            local_users()
        )
        index = self._password_user.findText(
            current_user
        )
        if index >= 0:
            self._password_user.setCurrentIndex(
                index
            )

        self._selection_changed()
        self._set_installed_controls(
            status.installed
        )

    def _set_installed_controls(
        self,
        installed: bool,
    ) -> None:
        for widget in (
            self._table,
            self._name,
            self._path,
            self._comment,
            self._read_only,
            self._guest,
            self._users,
            self._groups,
            self._local_only,
            self._enabled,
            self._save,
            self._clear,
            self._edit,
            self._remove,
            self._password_user,
            self._password,
            self._password_confirm,
        ):
            widget.setEnabled(
                installed and not self._busy
            )

        self._install_button.setEnabled(
            not self._busy
        )
        self._guest_changed(
            self._guest.isChecked()
        )
        self._selection_changed()

    def _selection_changed(self) -> None:
        selected = (
            self._table.currentRow() >= 0
        )
        self._edit.setEnabled(
            selected and not self._busy
        )
        self._remove.setEnabled(
            selected and not self._busy
        )

    def _guest_changed(
        self,
        guest: bool,
    ) -> None:
        enabled = not guest and not self._busy
        self._users.setEnabled(enabled)
        self._groups.setEnabled(enabled)

        if guest:
            self._users.clear()
            self._groups.clear()

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Share",
            self._path.text().strip() or "/srv",
        )

        if path:
            self._path.setText(path)

    def _install_samba(self) -> None:
        self._run_task(
            "mounts.install_samba_server",
            {
                "configure_firewall": (
                    self._configure_firewall.isChecked()
                )
            },
            "Samba Installed",
        )

    def _save_share(self) -> None:
        users = split_names(
            self._users.text()
        )
        groups = split_names(
            self._groups.text()
        )

        try:
            validate_share_values(
                name=self._name.text(),
                path=self._path.text(),
                comment=self._comment.text(),
                guest_access=(
                    self._guest.isChecked()
                ),
                allowed_users=users,
                allowed_groups=groups,
            )
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Share Is Incomplete",
                str(exc),
            )
            return

        task_id = "mounts.save_hosted_share"
        self._run_task(
            task_id,
            {
                "original_name": (
                    self._editing_name
                ),
                "name": self._name.text(),
                "path": self._path.text(),
                "comment": self._comment.text(),
                "read_only": (
                    self._read_only.isChecked()
                ),
                "guest_access": (
                    self._guest.isChecked()
                ),
                "allowed_users": users,
                "allowed_groups": groups,
                "local_network_only": (
                    self._local_only.isChecked()
                ),
                "enabled": (
                    self._enabled.isChecked()
                ),
            },
            "Samba Share Saved",
        )

    def _selected_share(
        self,
    ) -> HostedShare | None:
        row = self._table.currentRow()
        if row < 0:
            return None

        item = self._table.item(row, 0)
        value = item.data(256)

        return (
            value
            if isinstance(value, HostedShare)
            else None
        )

    def _edit_selected(self) -> None:
        share = self._selected_share()
        if share is None:
            return

        self._editing_name = share.name
        self._name.setText(share.name)
        self._path.setText(share.path)
        self._comment.setText(share.comment)
        self._read_only.setChecked(
            share.read_only
        )
        self._guest.setChecked(
            share.guest_access
        )
        self._users.setText(
            ", ".join(share.allowed_users)
        )
        self._groups.setText(
            ", ".join(share.allowed_groups)
        )
        self._local_only.setChecked(
            share.local_network_only
        )
        self._enabled.setChecked(
            share.enabled
        )
        self._save.setText("Save Changes")

    def _remove_selected(self) -> None:
        share = self._selected_share()
        if share is None:
            return

        response = QMessageBox.question(
            self,
            "Remove Shared Folder",
            (
                f"Remove network share "
                f"{share.name!r}?\n\n"
                "The folder and its files will not "
                "be deleted."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "mounts.remove_hosted_share",
            {"name": share.name},
            "Samba Share Removed",
        )

    def _set_password(self) -> None:
        password = self._password.text()

        if password != self._password_confirm.text():
            QMessageBox.warning(
                self,
                "Passwords Do Not Match",
                "Enter the same password twice.",
            )
            return

        self._run_task(
            "mounts.set_samba_password",
            {
                "username": (
                    self._password_user.currentText()
                ),
                "password": password,
            },
            "Samba Password Saved",
        )

    def _clear_form(self) -> None:
        self._editing_name = ""
        self._name.clear()
        self._path.clear()
        self._comment.clear()
        self._read_only.setChecked(True)
        self._guest.setChecked(False)
        self._users.clear()
        self._groups.clear()
        self._local_only.setChecked(True)
        self._enabled.setChecked(True)
        self._save.setText("Create Share")

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
    ) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_installed_controls(
            samba_status().installed
        )

        worker = _Worker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )
        worker.signals.succeeded.connect(
            lambda message: self._succeeded(
                title,
                message,
            )
        )
        worker.signals.failed.connect(
            self._failed
        )
        worker.signals.finished.connect(
            self._finished
        )
        self._active_worker = worker
        self._thread_pool.start(worker)

    def _succeeded(
        self,
        title: str,
        message: str,
    ) -> None:
        QMessageBox.information(
            self,
            title,
            message,
        )
        self._clear_form()
        self._password.clear()
        self._password_confirm.clear()
        self.shares_changed.emit()

    def _failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Samba Operation Failed",
            message,
        )

    def _finished(self) -> None:
        self._active_worker = None
        self._busy = False
        self.reload()
