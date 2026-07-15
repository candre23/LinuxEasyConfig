from __future__ import annotations

import grp
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
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask
from linuxeasyconfig.core.table_actions import TableAction
from linuxeasyconfig.widgets.data_table import DataTable

from .local_folder import (
    LocalFolderPreview,
    build_local_folder_preview,
    suggested_mountpoint as suggested_local_mountpoint,
)
from .network_share import (
    NetworkSharePreview,
    build_nfs_preview,
    build_smb_preview,
    dependency_status,
    suggested_mountpoint,
)
from .provider import MountsTableProvider


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


class MountsView(QWidget):
    """Landing view for mounted and configurable storage."""

    def __init__(
        self,
        provider: MountsTableProvider,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._provider = provider
        self._active_worker: _TaskWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        self._tabs = QTabWidget()

        mounted_tab, self._mounted_table = (
            self._build_mounted_storage_tab(provider)
        )

        self._network_share = NetworkShareView()
        self._network_share.share_saved.connect(
            self._on_mount_saved
        )

        self._local_folder = LocalFolderMountView()
        self._local_folder.mount_saved.connect(
            self._on_mount_saved
        )

        self._tabs.addTab(
            mounted_tab,
            "Mounted Storage",
        )
        self._tabs.addTab(
            self._network_share,
            "Add/Modify Network Share",
        )
        self._tabs.addTab(
            self._local_folder,
            "Add Local Folder Mount",
        )

        heading = QLabel("Mount Management")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "View mounted storage and connect network shares."
        )
        description.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

    def _build_mounted_storage_tab(
        self,
        provider: MountsTableProvider,
    ) -> tuple[QWidget, DataTable]:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 0, 0)

        explanation = QLabel(
            "This list includes active mounts and persistent entries "
            "from /etc/fstab."
        )
        explanation.setWordWrap(True)

        table = DataTable(
            provider=provider,
            selectable=True,
            sortable=True,
            action_handler=self._handle_table_action,
        )

        layout.addWidget(explanation)
        layout.addWidget(table, 1)
        return container, table

    def _handle_table_action(
        self,
        action: TableAction,
        row: dict[str, Any],
    ) -> bool:
        if action.id == "modify":
            if bool(row.get("mounted", False)):
                QMessageBox.information(
                    self,
                    "Unmount Before Modifying",
                    (
                        f"{row['mountpoint']} is currently mounted.\n\n"
                        "Unmount the share before changing its "
                        "configuration."
                    ),
                )
                return True

            if bool(row.get("bind_mount", False)):
                self._local_folder.load_existing(row)
                self._tabs.setCurrentIndex(2)
            else:
                self._network_share.load_existing(row)
                self._tabs.setCurrentIndex(1)

            return True

        if action.id == "mount":
            self._run_row_task(
                "mounts.mount",
                {"mountpoint": row["mountpoint"]},
                "Mount Filesystem",
                (
                    f"Mount {row['source']} at "
                    f"{row['mountpoint']}?"
                ),
            )
            return True

        if action.id == "unmount":
            self._run_row_task(
                "mounts.unmount",
                {"mountpoint": row["mountpoint"]},
                "Unmount Filesystem",
                (
                    f"Unmount {row['mountpoint']}?\n\n"
                    "Applications using files on this mount may stop "
                    "working until it is mounted again."
                ),
            )
            return True

        if action.id == "remove":
            self._run_row_task(
                "mounts.remove_entry",
                {
                    "source": row["source"],
                    "mountpoint": row["mountpoint"],
                    "credential_path": row.get(
                        "credential_path",
                        "",
                    ),
                    "unmount_first": bool(
                        row.get("mounted", False)
                    ),
                },
                "Remove Persistent Mount",
                (
                    f"Remove {row['source']} from /etc/fstab?\n\n"
                    "LEC will create a verified backup first. "
                    "The share will also be unmounted if necessary."
                ),
            )
            return True

        return False

    def _run_row_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        message: str,
    ) -> None:
        response = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        worker = _TaskWorker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )
        worker.signals.succeeded.connect(
            self._row_task_succeeded
        )
        worker.signals.failed.connect(
            self._row_task_failed
        )
        worker.signals.finished.connect(
            self._row_task_finished
        )

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _row_task_succeeded(self, message: str) -> None:
        QMessageBox.information(
            self,
            "Mount Management",
            message,
        )

    def _row_task_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Mount Action Failed",
            message,
        )

    def _row_task_finished(self) -> None:
        self._active_worker = None
        self._mounted_table.reload()

    def _on_mount_saved(self) -> None:
        self._tabs.setCurrentIndex(0)
        self._mounted_table.reload()


class LocalFolderMountView(QWidget):
    """Create or modify a persistent bind mount."""

    mount_saved = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._editing = False
        self._original_source = ""
        self._original_mountpoint = ""
        self._mountpoint_was_edited = False
        self._save_in_progress = False
        self._active_worker: _TaskWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        self._heading = QLabel("Add a Local Folder Mount")
        self._heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        explanation = QLabel(
            "Make an existing local folder appear at another path. "
            "Linux calls this a bind mount."
        )
        explanation.setWordWrap(True)

        self._source = QLineEdit()
        self._source.setPlaceholderText(
            "/home/user/folder"
        )
        self._source.textChanged.connect(
            self._update_mountpoint_suggestion
        )

        browse_source = QPushButton("Browse…")
        browse_source.clicked.connect(
            self._browse_source
        )

        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self._source, 1)
        source_layout.addWidget(browse_source)

        self._mountpoint = QLineEdit()
        self._mountpoint.setPlaceholderText(
            "/mnt/folder"
        )
        self._mountpoint.textEdited.connect(
            self._mark_mountpoint_edited
        )

        browse_mountpoint = QPushButton("Browse…")
        browse_mountpoint.clicked.connect(
            self._browse_mountpoint
        )

        mountpoint_row = QWidget()
        mountpoint_layout = QHBoxLayout(mountpoint_row)
        mountpoint_layout.setContentsMargins(0, 0, 0, 0)
        mountpoint_layout.addWidget(
            self._mountpoint,
            1,
        )
        mountpoint_layout.addWidget(
            browse_mountpoint
        )

        self._startup_mode = QComboBox()
        self._startup_mode.addItem(
            "Mount during startup",
            "startup",
        )
        self._startup_mode.addItem(
            "Mount when first accessed",
            "on-demand",
        )
        self._startup_mode.addItem(
            "Manual only",
            "manual",
        )

        self._read_only = QCheckBox(
            "Mount read-only"
        )

        self._mount_now = QCheckBox(
            "Mount the folder immediately after saving"
        )
        self._mount_now.setChecked(True)

        form = QFormLayout()
        form.addRow("Source folder:", source_row)
        form.addRow("Mount point:", mountpoint_row)
        form.addRow(
            "Startup behavior:",
            self._startup_mode,
        )
        form.addRow("", self._read_only)
        form.addRow("", self._mount_now)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMinimumHeight(120)
        self._preview.setPlaceholderText(
            "Select Preview Configuration to generate the entry."
        )

        preview_button = QPushButton(
            "Preview Configuration"
        )
        preview_button.clicked.connect(
            self._preview_configuration
        )

        self._save_button = QPushButton(
            "Save Local Folder Mount"
        )
        self._save_button.clicked.connect(
            self._save_configuration
        )

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(
            self._clear_form
        )

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(clear_button)
        buttons.addWidget(preview_button)
        buttons.addWidget(self._save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._heading)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(
            QLabel("Configuration preview:")
        )
        layout.addWidget(self._preview)
        layout.addLayout(buttons)
        layout.addStretch()

    def load_existing(
        self,
        row: dict[str, Any],
    ) -> None:
        self._clear_form()
        self._editing = True
        self._original_source = str(row["source"])
        self._original_mountpoint = str(
            row["mountpoint"]
        )
        self._source.setText(
            self._original_source
        )
        self._mountpoint_was_edited = True
        self._mountpoint.setText(
            self._original_mountpoint
        )

        options = tuple(row.get("option_list", ()))

        if "noauto" in options:
            mode = "manual"
        elif "x-systemd.automount" in options:
            mode = "on-demand"
        else:
            mode = "startup"

        index = self._startup_mode.findData(mode)
        if index >= 0:
            self._startup_mode.setCurrentIndex(index)

        self._read_only.setChecked(
            "ro" in options
        )
        self._mount_now.setChecked(False)
        self._heading.setText(
            "Modify Local Folder Mount"
        )
        self._save_button.setText(
            "Save Changes"
        )

    def _browse_source(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Source Folder",
            self._source.text().strip()
            or str(Path.home()),
        )
        if path:
            self._source.setText(path)

    def _browse_mountpoint(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Existing Mount Point",
            self._mountpoint.text().strip()
            or "/mnt",
        )
        if path:
            self._mountpoint_was_edited = True
            self._mountpoint.setText(path)

    def _mark_mountpoint_edited(self) -> None:
        self._mountpoint_was_edited = True

    def _update_mountpoint_suggestion(self) -> None:
        if self._mountpoint_was_edited:
            return

        source = self._source.text().strip()

        if not source:
            self._mountpoint.clear()
            return

        self._mountpoint.setText(
            suggested_local_mountpoint(source)
        )

    def _preview_configuration(self) -> None:
        try:
            preview = self._build_preview()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Configuration Is Incomplete",
                str(exc),
            )
            return

        self._preview.setPlainText(
            "# Entry to be written to /etc/fstab\n"
            f"{preview.fstab_line}\n"
        )

    def _save_configuration(self) -> None:
        if self._save_in_progress:
            return

        try:
            preview = self._build_preview()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Configuration Is Incomplete",
                str(exc),
            )
            return

        task_id = (
            "mounts.update_local_folder"
            if self._editing
            else "mounts.install_local_folder"
        )

        arguments: dict[str, Any] = {
            "source": preview.source,
            "mountpoint": preview.mountpoint,
            "fstab_line": preview.fstab_line,
            "mount_now": self._mount_now.isChecked(),
        }

        if self._editing:
            arguments.update(
                {
                    "original_source": self._original_source,
                    "original_mountpoint": (
                        self._original_mountpoint
                    ),
                }
            )

        response = QMessageBox.question(
            self,
            "Save Local Folder Mount",
            (
                f"Make {preview.source} available at "
                f"{preview.mountpoint}?\n\n"
                "LEC will create a verified backup before "
                "changing /etc/fstab."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._save_in_progress = True
        self._save_button.setEnabled(False)

        worker = _TaskWorker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )
        worker.signals.succeeded.connect(
            self._save_succeeded
        )
        worker.signals.failed.connect(
            self._save_failed
        )
        worker.signals.finished.connect(
            self._save_finished
        )
        self._active_worker = worker
        self._thread_pool.start(worker)

    def _save_succeeded(self, message: str) -> None:
        QMessageBox.information(
            self,
            "Local Folder Mount Saved",
            message,
        )
        self._clear_form()
        self.mount_saved.emit()

    def _save_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Local Folder Mount Could Not Be Saved",
            message,
        )

    def _save_finished(self) -> None:
        self._active_worker = None
        self._save_in_progress = False
        self._save_button.setEnabled(True)

    def _build_preview(self) -> LocalFolderPreview:
        return build_local_folder_preview(
            source=self._source.text(),
            mountpoint=self._mountpoint.text(),
            read_only=self._read_only.isChecked(),
            startup_mode=str(
                self._startup_mode.currentData()
            ),
        )

    def _clear_form(self) -> None:
        self._editing = False
        self._original_source = ""
        self._original_mountpoint = ""
        self._source.clear()
        self._mountpoint_was_edited = False
        self._mountpoint.clear()
        self._startup_mode.setCurrentIndex(0)
        self._read_only.setChecked(False)
        self._mount_now.setChecked(True)
        self._preview.clear()
        self._heading.setText(
            "Add a Local Folder Mount"
        )
        self._save_button.setText(
            "Save Local Folder Mount"
        )


class NetworkShareView(QWidget):
    """SMB and NFS network-share configuration form."""

    share_saved = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._mountpoint_was_edited = False
        self._save_in_progress = False
        self._active_worker: _TaskWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        self._editing = False
        self._original_source = ""
        self._original_mountpoint = ""
        self._existing_credential_path = ""

        self._heading = QLabel("Add a Network Share")
        self._heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        explanation = QLabel(
            "Configure a Windows/SMB share or an NFS export. "
            "LEC will back up /etc/fstab before saving."
        )
        explanation.setWordWrap(True)

        self._protocol = QComboBox()
        self._protocol.addItem(
            "Windows / SMB share",
            "smb",
        )
        self._protocol.addItem(
            "NFS share",
            "nfs",
        )
        self._protocol.currentIndexChanged.connect(
            self._protocol_changed
        )

        self._dependency = QLabel()
        self._dependency.setWordWrap(True)
        self._dependency.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        protocol_form = QFormLayout()
        protocol_form.addRow("Share type:", self._protocol)
        protocol_form.addRow(
            "Required software:",
            self._dependency,
        )

        self._forms = QStackedWidget()
        self._forms.addWidget(self._build_smb_form())
        self._forms.addWidget(self._build_nfs_form())

        self._mountpoint = QLineEdit()
        self._mountpoint.setPlaceholderText(
            "/mnt/server-share"
        )
        self._mountpoint.textEdited.connect(
            self._mark_mountpoint_edited
        )

        self._startup_mode = QComboBox()
        self._startup_mode.addItem(
            "Mount when first accessed (recommended)",
            "on-demand",
        )
        self._startup_mode.addItem(
            "Mount during startup",
            "startup",
        )
        self._startup_mode.addItem(
            "Manual only",
            "manual",
        )

        self._read_only = QCheckBox("Mount read-only")
        self._read_only.toggled.connect(
            self._update_smb_group_controls
        )
        self._mount_now = QCheckBox(
            "Mount the share immediately after saving"
        )
        self._mount_now.setChecked(True)

        behavior_group = QGroupBox(
            "Local Mount Behavior"
        )
        behavior_form = QFormLayout(behavior_group)
        behavior_form.addRow(
            "Local mount point:",
            self._mountpoint,
        )
        behavior_form.addRow(
            "Startup behavior:",
            self._startup_mode,
        )
        behavior_form.addRow("", self._read_only)
        behavior_form.addRow("", self._mount_now)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMinimumHeight(120)

        self._preview_button = QPushButton(
            "Preview Configuration"
        )
        self._preview_button.clicked.connect(
            self._preview_configuration
        )

        self._save_button = QPushButton(
            "Save Network Share"
        )
        self._save_button.clicked.connect(
            self._save_configuration
        )

        self._clear_button = QPushButton("Clear")
        self._clear_button.clicked.connect(
            self._clear_form
        )

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._clear_button)
        button_layout.addWidget(self._preview_button)
        button_layout.addWidget(self._save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._heading)
        layout.addWidget(explanation)
        layout.addLayout(protocol_form)
        layout.addWidget(self._forms)
        layout.addWidget(behavior_group)
        layout.addWidget(
            QLabel("Configuration preview:")
        )
        layout.addWidget(self._preview)
        layout.addLayout(button_layout)
        layout.addStretch()

        self._connect_suggestion_signals()
        self._refresh_smb_groups()
        self._protocol_changed()

    def _build_smb_form(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        form.setContentsMargins(0, 0, 0, 0)

        self._smb_server = QLineEdit()
        self._smb_share = QLineEdit()

        self._smb_guest = QCheckBox(
            "Connect without a username or password"
        )
        self._smb_guest.toggled.connect(
            self._update_smb_credentials_enabled
        )

        self._smb_username = QLineEdit()
        self._smb_password = QLineEdit()
        self._smb_password.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        self._smb_domain = QLineEdit()

        self._smb_credential_help = QLabel(
            "When modifying an existing share, leave the username, "
            "password, and domain fields blank to keep the saved "
            "credentials. Enter new credentials only when you want "
            "to replace them."
        )
        self._smb_credential_help.setWordWrap(True)
        self._smb_credential_help.setMinimumHeight(48)
        self._smb_credential_help.setTextFormat(
            Qt.TextFormat.PlainText
        )
        self._smb_credential_help.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._smb_local_group = QComboBox()
        self._smb_local_group.currentIndexChanged.connect(
            self._update_smb_group_controls
        )

        self._refresh_groups_button = QPushButton("Refresh Groups")
        self._refresh_groups_button.clicked.connect(
            self._refresh_smb_groups
        )

        group_row = QWidget()
        group_row_layout = QHBoxLayout(group_row)
        group_row_layout.setContentsMargins(0, 0, 0, 0)
        group_row_layout.addWidget(self._smb_local_group, 1)
        group_row_layout.addWidget(self._refresh_groups_button)

        self._smb_group_access = QComboBox()
        self._smb_group_access.addItem(
            "Group members can read only",
            "read",
        )
        self._smb_group_access.addItem(
            "Group members can read and write",
            "write",
        )

        self._smb_group_help = QLabel(
            "Optional: restrict local access to members of one "
            "Linux group. This does not change permissions on "
            "the NAS itself."
        )
        self._smb_group_help.setWordWrap(True)
        self._smb_group_help.setMinimumHeight(42)
        self._smb_group_help.setTextFormat(
            Qt.TextFormat.PlainText
        )
        self._smb_group_help.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._smb_group_status = QLabel()
        self._smb_group_status.setWordWrap(True)
        self._smb_group_status.setMinimumHeight(34)
        self._smb_group_status.setTextFormat(
            Qt.TextFormat.PlainText
        )
        self._smb_group_status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        form.addRow("Server:", self._smb_server)
        form.addRow("Share name:", self._smb_share)
        form.addRow("", self._smb_guest)
        form.addRow("Username:", self._smb_username)
        form.addRow("Password:", self._smb_password)
        form.addRow("Domain:", self._smb_domain)
        form.addRow("", self._smb_credential_help)
        form.addRow("Local access group:", group_row)
        form.addRow("Group permissions:", self._smb_group_access)
        form.addRow("", self._smb_group_status)
        form.addRow("", self._smb_group_help)

        return container

    def _build_nfs_form(self) -> QWidget:
        container = QWidget()
        form = QFormLayout(container)
        form.setContentsMargins(0, 0, 0, 0)

        self._nfs_server = QLineEdit()
        self._nfs_export = QLineEdit()

        self._nfs_version = QComboBox()
        self._nfs_version.addItems(
            ["Automatic", "4.2", "4.1", "4", "3"]
        )

        form.addRow("Server:", self._nfs_server)
        form.addRow(
            "Exported path:",
            self._nfs_export,
        )
        form.addRow(
            "NFS version:",
            self._nfs_version,
        )
        return container

    def load_existing(
        self,
        row: dict[str, Any],
    ) -> None:
        self._clear_form()

        self._editing = True
        self._original_source = str(row["source"])
        self._original_mountpoint = str(
            row["mountpoint"]
        )
        self._existing_credential_path = str(
            row.get("credential_path", "")
        )

        filesystem = str(row["filesystem"]).lower()
        options = tuple(row.get("option_list", ()))

        if filesystem in {"cifs", "smb3"}:
            self._protocol.setCurrentIndex(0)
            server, share = _split_smb_source(
                self._original_source,
                options,
            )
            self._smb_server.setText(server)
            self._smb_share.setText(share)
            self._smb_guest.setChecked(
                "guest" in options
            )

            self._refresh_smb_groups()
            group_name = _group_name_from_options(
                options
            )
            group_index = (
                self._smb_local_group.findData(
                    group_name
                )
            )
            if group_index >= 0:
                self._smb_local_group.setCurrentIndex(
                    group_index
                )

            file_mode = _option_value(
                options,
                "file_mode",
            )
            group_access = (
                "write"
                if file_mode in {"0660", "660"}
                else "read"
            )
            access_index = (
                self._smb_group_access.findData(
                    group_access
                )
            )
            if access_index >= 0:
                self._smb_group_access.setCurrentIndex(
                    access_index
                )
        else:
            self._protocol.setCurrentIndex(1)
            server, export = _split_nfs_source(
                self._original_source
            )
            self._nfs_server.setText(server)
            self._nfs_export.setText(export)
            version = _option_value(
                options,
                "nfsvers",
            )
            if version:
                index = self._nfs_version.findText(
                    version
                )
                if index >= 0:
                    self._nfs_version.setCurrentIndex(
                        index
                    )

        self._mountpoint_was_edited = True
        self._mountpoint.setText(
            self._original_mountpoint
        )
        self._read_only.setChecked(
            "ro" in options
        )
        self._mount_now.setChecked(
            bool(row.get("mounted", False))
        )

        if "noauto" in options:
            mode = "manual"
        elif "x-systemd.automount" in options:
            mode = "on-demand"
        else:
            mode = "startup"

        index = self._startup_mode.findData(mode)
        if index >= 0:
            self._startup_mode.setCurrentIndex(index)

        self._heading.setText(
            "Modify Network Share"
        )
        self._save_button.setText(
            "Save Changes"
        )
        self._preview.clear()

    def _connect_suggestion_signals(self) -> None:
        for field in (
            self._smb_server,
            self._smb_share,
            self._nfs_server,
            self._nfs_export,
        ):
            field.textChanged.connect(
                self._update_mountpoint_suggestion
            )

    def _protocol_changed(self) -> None:
        protocol = self._current_protocol()
        self._forms.setCurrentIndex(
            0 if protocol == "smb" else 1
        )

        status = dependency_status(protocol)

        if status.available:
            self._dependency.setText(
                f"Installed ({status.helper})"
            )
            self._save_button.setEnabled(True)
        else:
            self._dependency.setText(
                f"Not installed. Run: {status.install_command}"
            )
            self._save_button.setEnabled(False)

        if not self._editing:
            self._mountpoint_was_edited = False
            self._update_mountpoint_suggestion()

        self._update_smb_group_controls()
        self._preview.clear()

    def _update_smb_credentials_enabled(
        self,
        guest: bool,
    ) -> None:
        self._smb_username.setEnabled(not guest)
        self._smb_password.setEnabled(not guest)
        self._smb_domain.setEnabled(not guest)

    def _refresh_smb_groups(self) -> None:
        selected = str(
            self._smb_local_group.currentData() or ""
        )

        self._smb_local_group.blockSignals(True)
        self._smb_local_group.clear()
        self._smb_local_group.addItem(
            "No local group restriction",
            "",
        )

        for group in sorted(
            grp.getgrall(),
            key=lambda item: item.gr_name.casefold(),
        ):
            self._smb_local_group.addItem(
                group.gr_name,
                group.gr_name,
            )

        index = self._smb_local_group.findData(selected)
        self._smb_local_group.setCurrentIndex(
            index if index >= 0 else 0
        )
        self._smb_local_group.blockSignals(False)
        self._update_smb_group_controls()

    def _update_smb_group_controls(self) -> None:
        group_selected = bool(
            self._smb_local_group.currentData()
        )
        smb_selected = self._current_protocol() == "smb"
        whole_mount_read_only = self._read_only.isChecked()

        enabled = (
            smb_selected
            and group_selected
            and not whole_mount_read_only
        )
        self._smb_group_access.setEnabled(enabled)
        self._refresh_groups_button.setEnabled(smb_selected)

        if not smb_selected:
            self._smb_group_status.setText(
                "Local group controls apply only to Windows/SMB shares."
            )
            return

        if not group_selected:
            self._smb_group_status.setText(
                "Choose a local group to enable group permission choices."
            )
            return

        if whole_mount_read_only:
            index = self._smb_group_access.findData("read")
            if index >= 0:
                self._smb_group_access.setCurrentIndex(index)
            self._smb_group_status.setText(
                "The entire mount is set to read-only, so group members "
                "can only be given read-only access. Uncheck ‘Mount "
                "read-only’ to enable the read/write option."
            )
            return

        self._smb_group_status.setText(
            "Choose whether members of the selected group may only read "
            "the share or may also create, change, and delete files."
        )

    def _mark_mountpoint_edited(self) -> None:
        self._mountpoint_was_edited = True

    def _update_mountpoint_suggestion(self) -> None:
        if self._mountpoint_was_edited:
            return

        if self._current_protocol() == "smb":
            server = self._smb_server.text()
            remote = self._smb_share.text()
        else:
            server = self._nfs_server.text()
            remote = self._nfs_export.text()

        if not server.strip() and not remote.strip():
            self._mountpoint.clear()
            return

        self._mountpoint.setText(
            suggested_mountpoint(
                protocol=self._current_protocol(),
                server=server,
                remote_name=remote,
            )
        )

    def _preview_configuration(self) -> None:
        try:
            preview = self._build_preview()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Configuration Is Incomplete",
                str(exc),
            )
            return

        self._preview.setPlainText(
            self._render_preview(preview)
        )

    def _save_configuration(self) -> None:
        if self._save_in_progress:
            return

        try:
            preview = self._build_preview()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Configuration Is Incomplete",
                str(exc),
            )
            return

        task_id = (
            "mounts.update_network_share"
            if self._editing
            else "mounts.install_network_share"
        )

        arguments = {
            "protocol": preview.protocol,
            "source": preview.source,
            "mountpoint": preview.mountpoint,
            "filesystem": preview.filesystem,
            "fstab_line": preview.fstab_line,
            "credential_path": (
                preview.credential_path or ""
            ),
            "credential_text": (
                preview.credential_text or ""
            ),
            "mount_now": self._mount_now.isChecked(),
        }

        if self._editing:
            arguments.update(
                {
                    "original_source": self._original_source,
                    "original_mountpoint": (
                        self._original_mountpoint
                    ),
                }
            )

        response = QMessageBox.question(
            self,
            "Save Network Share",
            (
                f"Save {preview.source} at "
                f"{preview.mountpoint}?\n\n"
                "LEC will create a verified backup first."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)

        worker = _TaskWorker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )
        worker.signals.succeeded.connect(
            self._save_succeeded
        )
        worker.signals.failed.connect(
            self._save_failed
        )
        worker.signals.finished.connect(
            self._save_finished
        )

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _save_succeeded(self, message: str) -> None:
        QMessageBox.information(
            self,
            "Network Share Saved",
            message,
        )
        self._clear_form()
        self.share_saved.emit()

    def _save_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Network Share Could Not Be Saved",
            message,
        )

    def _save_finished(self) -> None:
        self._active_worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self._save_in_progress = busy
        for widget in (
            self._protocol,
            self._forms,
            self._mountpoint,
            self._startup_mode,
            self._read_only,
            self._mount_now,
            self._clear_button,
            self._preview_button,
        ):
            widget.setEnabled(not busy)

        status = dependency_status(
            self._current_protocol()
        )
        self._save_button.setEnabled(
            not busy and status.available
        )

    def _build_preview(self) -> NetworkSharePreview:
        startup_mode = str(
            self._startup_mode.currentData()
        )

        if self._current_protocol() == "smb":
            return build_smb_preview(
                server=self._smb_server.text(),
                share=self._smb_share.text(),
                mountpoint=self._mountpoint.text(),
                username=self._smb_username.text(),
                password=self._smb_password.text(),
                domain=self._smb_domain.text(),
                guest=self._smb_guest.isChecked(),
                read_only=self._read_only.isChecked(),
                startup_mode=startup_mode,
                existing_credential_path=(
                    self._existing_credential_path
                ),
                local_group=str(
                    self._smb_local_group.currentData()
                    or ""
                ),
                group_access=str(
                    self._smb_group_access.currentData()
                ),
            )

        return build_nfs_preview(
            server=self._nfs_server.text(),
            export_path=self._nfs_export.text(),
            mountpoint=self._mountpoint.text(),
            nfs_version=self._nfs_version.currentText(),
            read_only=self._read_only.isChecked(),
            startup_mode=startup_mode,
        )

    @staticmethod
    def _render_preview(
        preview: NetworkSharePreview,
    ) -> str:
        lines = [
            "# Entry to be written to /etc/fstab",
            preview.fstab_line,
        ]

        if preview.credential_path:
            lines.extend(
                [
                    "",
                    "# Credential file",
                    preview.credential_path,
                ]
            )

            if preview.credential_text:
                lines.extend(
                    [
                        "",
                        preview.credential_text,
                    ]
                )
            else:
                lines.append(
                    "# Existing credential file will be retained."
                )

        return "\n".join(lines).rstrip() + "\n"

    def _clear_form(self) -> None:
        self._editing = False
        self._original_source = ""
        self._original_mountpoint = ""
        self._existing_credential_path = ""

        for field in (
            self._smb_server,
            self._smb_share,
            self._smb_username,
            self._smb_password,
            self._smb_domain,
            self._nfs_server,
            self._nfs_export,
        ):
            field.clear()

        self._smb_guest.setChecked(False)
        self._smb_local_group.setCurrentIndex(0)
        self._smb_group_access.setCurrentIndex(0)
        self._nfs_version.setCurrentIndex(0)
        self._startup_mode.setCurrentIndex(0)
        self._read_only.setChecked(False)
        self._mount_now.setChecked(True)
        self._mountpoint_was_edited = False
        self._mountpoint.clear()
        self._preview.clear()
        self._heading.setText(
            "Add a Network Share"
        )
        self._save_button.setText(
            "Save Network Share"
        )

    def _current_protocol(self) -> str:
        return str(self._protocol.currentData())


def _split_smb_source(
    source: str,
    options: tuple[str, ...],
) -> tuple[str, str]:
    cleaned = source.removeprefix("//")
    server, _, share = cleaned.partition("/")
    prefix = _option_value(options, "prefixpath")

    if prefix:
        share = f"{share}/{prefix}"

    return server, share


def _group_name_from_options(
    options: tuple[str, ...],
) -> str:
    value = _option_value(options, "gid")

    if not value:
        return ""

    try:
        return grp.getgrgid(int(value)).gr_name
    except (ValueError, KeyError):
        try:
            return grp.getgrnam(value).gr_name
        except KeyError:
            return ""


def _split_nfs_source(source: str) -> tuple[str, str]:
    server, _, export = source.partition(":")
    return server, export


def _option_value(
    options: tuple[str, ...],
    name: str,
) -> str:
    prefix = f"{name}="

    for option in options:
        if option.startswith(prefix):
            return option.partition("=")[2]

    return ""
