from __future__ import annotations

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
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import (
    LocalGroup,
    UserAccount,
    UserPermissionsRepository,
)


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
            message = PrivilegedRunner().run(
                self._task
            )
            self.signals.succeeded.emit(message)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class UserPermissionsView(QWidget):
    """Create service users and manage their access."""

    def __init__(
        self,
        repository: UserPermissionsRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._accounts: list[UserAccount] = []
        self._groups: list[LocalGroup] = []
        self._active_worker: _TaskWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._busy = False

        heading = QLabel("User Permissions")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Create dedicated service accounts, manage group "
            "memberships, and grant specific folder access without "
            "giving applications full administrator privileges."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_accounts_tab(),
            "Accounts and Groups",
        )
        self._tabs.addTab(
            self._build_groups_tab(),
            "Local Groups",
        )
        self._tabs.addTab(
            self._build_folder_access_tab(),
            "Folder Access",
        )
        self._tabs.addTab(
            self._build_create_account_tab(),
            "Create Service Account",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

        self.reload()

    def _build_accounts_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 0, 0)

        filter_row = QHBoxLayout()

        self._account_filter = QComboBox()
        self._account_filter.addItem(
            "Service accounts",
            "Service",
        )
        self._account_filter.addItem(
            "Human users",
            "Human",
        )
        self._account_filter.addItem(
            "All accounts",
            "All",
        )
        self._account_filter.currentIndexChanged.connect(
            self._populate_account_table
        )

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.reload)

        filter_row.addWidget(QLabel("Show:"))
        filter_row.addWidget(self._account_filter)
        filter_row.addStretch()
        filter_row.addWidget(refresh_button)

        self._account_table = QTableWidget()
        self._account_table.setColumnCount(6)
        self._account_table.setHorizontalHeaderLabels(
            [
                "User",
                "Type",
                "UID",
                "Primary Group",
                "Login",
                "Home",
            ]
        )
        self._account_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._account_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._account_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._account_table.verticalHeader().setVisible(False)
        self._account_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._account_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._account_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._account_table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._account_table.horizontalHeader().setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._account_table.horizontalHeader().setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.Stretch,
        )
        self._account_table.itemSelectionChanged.connect(
            self._account_selected
        )

        details = QWidget()
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(12, 0, 0, 0)

        self._account_heading = QLabel(
            "Select an account"
        )
        self._account_heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        self._account_details = QLabel()
        self._account_details.setWordWrap(True)
        self._account_details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        group_help = QLabel(
            "Checked groups are supplementary memberships. "
            "The account's primary group is managed separately "
            "by Linux and is not shown as a checked item here."
        )
        group_help.setWordWrap(True)

        self._group_filter = QLineEdit()
        self._group_filter.setPlaceholderText(
            "Filter groups…"
        )
        self._group_filter.textChanged.connect(
            self._filter_group_list
        )

        self._group_list = QListWidget()
        self._group_list.setEnabled(False)

        self._save_groups_button = QPushButton(
            "Save Group Memberships"
        )
        self._save_groups_button.setEnabled(False)
        self._save_groups_button.clicked.connect(
            self._save_group_memberships
        )

        details_layout.addWidget(self._account_heading)
        details_layout.addWidget(self._account_details)
        details_layout.addWidget(group_help)
        details_layout.addWidget(self._group_filter)
        details_layout.addWidget(self._group_list, 1)
        details_layout.addWidget(
            self._save_groups_button
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )
        splitter.addWidget(self._account_table)
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([700, 450])

        layout.addLayout(filter_row)
        layout.addWidget(splitter, 1)
        return container

    def _build_groups_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 0, 0)

        explanation = QLabel(
            "Create local groups for shared service access. Add users to a "
            "group from the Accounts and Groups tab."
        )
        explanation.setWordWrap(True)

        self._groups_table = QTableWidget()
        self._groups_table.setColumnCount(5)
        self._groups_table.setHorizontalHeaderLabels(
            ["Group", "Type", "GID", "Members", "Primary Users"]
        )
        self._groups_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._groups_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._groups_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._groups_table.verticalHeader().setVisible(False)
        header = self._groups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._groups_table.itemSelectionChanged.connect(
            self._group_selection_changed
        )

        create_group = QGroupBox("Create Group")
        create_form = QFormLayout(create_group)
        self._new_group_name = QLineEdit()
        self._new_group_system = QCheckBox(
            "Create as a system/service group"
        )
        self._new_group_system.setChecked(True)
        create_button = QPushButton("Create Group")
        create_button.clicked.connect(self._create_group)
        create_form.addRow("Group name:", self._new_group_name)
        create_form.addRow("", self._new_group_system)
        create_form.addRow("", create_button)

        modify_group = QGroupBox("Modify Selected Group")
        modify_form = QFormLayout(modify_group)
        self._rename_group_name = QLineEdit()
        self._rename_group_button = QPushButton("Rename Group")
        self._rename_group_button.setEnabled(False)
        self._rename_group_button.clicked.connect(self._rename_group)
        self._delete_group_button = QPushButton("Delete Group")
        self._delete_group_button.setEnabled(False)
        self._delete_group_button.clicked.connect(self._delete_group)
        modify_buttons = QHBoxLayout()
        modify_buttons.addWidget(self._rename_group_button)
        modify_buttons.addWidget(self._delete_group_button)
        modify_form.addRow("New name:", self._rename_group_name)
        modify_form.addRow("", modify_buttons)

        lower = QHBoxLayout()
        lower.addWidget(create_group, 1)
        lower.addWidget(modify_group, 1)

        layout.addWidget(explanation)
        layout.addWidget(self._groups_table, 1)
        layout.addLayout(lower)
        return container

    def _build_folder_access_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        explanation = QLabel(
            "Grant one user access to a folder using Linux ACLs. "
            "This adds access for the selected account without "
            "changing the folder's owner or removing anyone else's access."
        )
        explanation.setWordWrap(True)

        self._acl_dependency = QLabel()
        self._acl_dependency.setWordWrap(True)

        self._folder_user = QComboBox()
        self._folder_user.currentIndexChanged.connect(
            self._update_acl_status
        )

        self._folder_path = QLineEdit()
        self._folder_path.textChanged.connect(
            self._update_acl_status
        )

        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(
            self._browse_folder
        )

        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(
            self._folder_path,
            1,
        )
        path_layout.addWidget(browse_button)

        self._access_level = QComboBox()
        self._access_level.addItem(
            "Read only",
            "read",
        )
        self._access_level.addItem(
            "Read and write",
            "write",
        )

        self._recursive = QCheckBox(
            "Apply to files and subfolders that already exist"
        )

        self._inherit = QCheckBox(
            "Apply automatically to new files and subfolders"
        )
        self._inherit.setChecked(True)

        self._traverse = QCheckBox(
            "Allow traversal through parent folders when needed"
        )
        self._traverse.setChecked(True)

        form_group = QGroupBox("Access Grant")
        form = QFormLayout(form_group)
        form.addRow("User:", self._folder_user)
        form.addRow("Folder:", path_row)
        form.addRow(
            "Access level:",
            self._access_level,
        )
        form.addRow("", self._recursive)
        form.addRow("", self._inherit)
        form.addRow("", self._traverse)

        self._current_acl = QLabel(
            "Select a user and folder to inspect current access."
        )
        self._current_acl.setWordWrap(True)

        self._grant_button = QPushButton(
            "Grant or Update Access"
        )
        self._grant_button.clicked.connect(
            self._grant_folder_access
        )

        self._remove_acl_button = QPushButton(
            "Remove This User's Folder Access"
        )
        self._remove_acl_button.clicked.connect(
            self._remove_folder_access
        )

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(
            self._remove_acl_button
        )
        buttons.addWidget(self._grant_button)

        layout.addWidget(explanation)
        layout.addWidget(self._acl_dependency)
        layout.addWidget(form_group)
        layout.addWidget(self._current_acl)
        layout.addLayout(buttons)
        layout.addStretch()
        return container

    def _build_create_account_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        heading = QLabel("Create a Service Account")
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        explanation = QLabel(
            "A service account has no interactive login and receives "
            "only the folder and group access you explicitly assign."
        )
        explanation.setWordWrap(True)

        self._new_username = QLineEdit()
        self._new_username.setPlaceholderText(
            "jellyfin-custom"
        )

        self._new_description = QLineEdit()
        self._new_description.setPlaceholderText(
            "Account used by Jellyfin"
        )

        self._create_home = QCheckBox(
            "Create a private home/data directory"
        )
        self._create_home.toggled.connect(
            self._home_option_changed
        )

        self._home_directory = QLineEdit()
        self._home_directory.setPlaceholderText(
            "/var/lib/account-name"
        )
        self._home_directory.setEnabled(False)

        form = QFormLayout()
        form.addRow(
            "Account name:",
            self._new_username,
        )
        form.addRow(
            "Description:",
            self._new_description,
        )
        form.addRow("", self._create_home)
        form.addRow(
            "Home/data directory:",
            self._home_directory,
        )

        note = QLabel(
            "LEC creates a system account with its own primary group "
            "and the nologin shell. No password is created."
        )
        note.setWordWrap(True)

        self._create_account_button = QPushButton(
            "Create Service Account"
        )
        self._create_account_button.clicked.connect(
            self._create_service_account
        )

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(
            self._create_account_button
        )

        layout.addWidget(heading)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addLayout(button_row)
        layout.addStretch()
        return container

    def reload(self) -> None:
        selected_name = self._selected_username()

        self._accounts = self._repository.accounts()
        self._groups = self._repository.local_groups()
        self._populate_account_table()
        self._populate_groups_table()
        self._populate_folder_users()

        acl_available = (
            self._repository.acl_tools_available()
        )

        if acl_available:
            self._acl_dependency.setText(
                "ACL support is available."
            )
            self._grant_button.setEnabled(True)
            self._remove_acl_button.setEnabled(True)
        else:
            self._acl_dependency.setText(
                "ACL tools are not installed. Run: "
                "sudo apt install acl"
            )
            self._grant_button.setEnabled(False)
            self._remove_acl_button.setEnabled(False)

        if selected_name:
            self._select_account_by_name(
                selected_name
            )

        self._update_acl_status()

    def _populate_account_table(self) -> None:
        account_type = str(
            self._account_filter.currentData()
        )

        visible = [
            account
            for account in self._accounts
            if (
                account_type == "All"
                or account.account_type == account_type
            )
        ]

        self._account_table.setRowCount(
            len(visible)
        )

        for row, account in enumerate(visible):
            values = (
                account.name,
                account.account_type,
                str(account.uid),
                account.primary_group,
                (
                    "Allowed"
                    if account.login_allowed
                    else "Disabled"
                ),
                account.home,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    account.name,
                )
                self._account_table.setItem(
                    row,
                    column,
                    item,
                )

        if visible:
            self._account_table.selectRow(0)
        else:
            self._clear_account_details()

    def _populate_groups_table(self) -> None:
        self._groups_table.setRowCount(len(self._groups))

        for row, group in enumerate(self._groups):
            values = (
                group.name,
                group.group_type,
                str(group.gid),
                ", ".join(group.members) or "None",
                ", ".join(group.primary_users) or "None",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, group.name)
                self._groups_table.setItem(row, column, item)

        if self._groups:
            self._groups_table.selectRow(0)

    def _selected_group(self) -> LocalGroup | None:
        rows = self._groups_table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self._groups_table.item(rows[0].row(), 0)
        if item is None:
            return None
        name = item.data(Qt.ItemDataRole.UserRole)
        return next((group for group in self._groups if group.name == name), None)

    def _group_selection_changed(self) -> None:
        group = self._selected_group()
        enabled = group is not None and not self._busy
        self._rename_group_button.setEnabled(enabled)
        self._delete_group_button.setEnabled(
            enabled and not bool(group and group.primary_users)
        )
        self._rename_group_name.setText(group.name if group else "")

    def _create_group(self) -> None:
        name = self._new_group_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Group Name Required", "Enter a group name.")
            return
        self._run_task(
            task_id="user_permissions.create_group",
            arguments={
                "name": name,
                "system_group": self._new_group_system.isChecked(),
            },
            success_title="Group Created",
            refresh=True,
            on_success=self._new_group_name.clear,
        )

    def _rename_group(self) -> None:
        group = self._selected_group()
        new_name = self._rename_group_name.text().strip()
        if group is None or not new_name:
            return
        response = QMessageBox.question(
            self,
            "Rename Group",
            f"Rename {group.name} to {new_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        self._run_task(
            task_id="user_permissions.rename_group",
            arguments={"old_name": group.name, "new_name": new_name},
            success_title="Group Renamed",
            refresh=True,
        )

    def _delete_group(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        response = QMessageBox.warning(
            self,
            "Delete Group",
            f"Delete the local group {group.name}?\n\n"
            "Supplementary memberships in this group will be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        self._run_task(
            task_id="user_permissions.delete_group",
            arguments={"name": group.name},
            success_title="Group Deleted",
            refresh=True,
        )

    def _populate_folder_users(self) -> None:
        selected = self._folder_user.currentData()
        self._folder_user.blockSignals(True)
        self._folder_user.clear()

        for account in self._accounts:
            if account.uid == 0:
                continue

            self._folder_user.addItem(
                (
                    f"{account.name} "
                    f"({account.account_type})"
                ),
                account.name,
            )

        if selected:
            index = self._folder_user.findData(
                selected
            )
            if index >= 0:
                self._folder_user.setCurrentIndex(
                    index
                )

        self._folder_user.blockSignals(False)

    def _account_selected(self) -> None:
        account = self._selected_account()

        if account is None:
            self._clear_account_details()
            return

        self._account_heading.setText(
            account.name
        )
        self._account_details.setText(
            f"<b>Type:</b> {account.account_type}<br>"
            f"<b>UID:</b> {account.uid}<br>"
            f"<b>Primary group:</b> "
            f"{account.primary_group}<br>"
            f"<b>Home:</b> {account.home}<br>"
            f"<b>Shell:</b> {account.shell}<br>"
            f"<b>Description:</b> "
            f"{account.description or 'None'}"
        )

        self._group_list.clear()

        memberships = set(
            account.supplementary_groups
        )

        for group_name in self._repository.groups():
            item = QListWidgetItem(group_name)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if group_name in memberships
                else Qt.CheckState.Unchecked
            )
            self._group_list.addItem(item)

        editable = (
            account.uid != 0
            and not self._busy
        )
        self._group_list.setEnabled(editable)
        self._save_groups_button.setEnabled(
            editable
        )
        self._filter_group_list(
            self._group_filter.text()
        )

    def _filter_group_list(
        self,
        text: str,
    ) -> None:
        needle = text.strip().casefold()

        for index in range(
            self._group_list.count()
        ):
            item = self._group_list.item(index)
            item.setHidden(
                bool(
                    needle
                    and needle
                    not in item.text().casefold()
                )
            )

    def _save_group_memberships(self) -> None:
        account = self._selected_account()

        if account is None:
            return

        groups = [
            self._group_list.item(index).text()
            for index in range(
                self._group_list.count()
            )
            if (
                self._group_list.item(index).checkState()
                == Qt.CheckState.Checked
            )
        ]

        warning = QMessageBox.question(
            self,
            "Save Group Memberships",
            (
                f"Replace {account.name}'s supplementary group "
                "memberships with the checked groups?\n\n"
                "Changes affect new processes and login sessions. "
                "A running service may need to be restarted."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if warning != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            task_id="user_permissions.set_groups",
            arguments={
                "username": account.name,
                "groups": groups,
            },
            success_title="Group Memberships Updated",
            refresh=True,
        )

    def _browse_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            self._folder_path.text().strip()
            or "/",
        )

        if path:
            self._folder_path.setText(path)

    def _update_acl_status(self) -> None:
        username = self._folder_user.currentData()
        path = self._folder_path.text().strip()

        if not username or not path:
            self._current_acl.setText(
                "Select a user and folder to inspect "
                "current access."
            )
            return

        filesystem = self._repository.filesystem_info(path)

        if filesystem.is_remote:
            self._recursive.setChecked(False)
            self._inherit.setChecked(False)
            self._traverse.setChecked(False)
            self._recursive.setEnabled(False)
            self._inherit.setEnabled(False)
            self._traverse.setEnabled(False)
            self._grant_button.setEnabled(False)
            self._remove_acl_button.setEnabled(False)
            self._current_acl.setText(
                "<b>Remote filesystem detected:</b> "
                f"{filesystem.filesystem or 'network'} ({filesystem.source})<br>"
                "LEC will not apply local ACL changes to remote files. "
                "Create a local group, add the service account to it, and "
                "configure the network mount to use that group."
            )
            return

        acl_available = self._repository.acl_tools_available()
        self._recursive.setEnabled(acl_available)
        self._inherit.setEnabled(acl_available)
        self._traverse.setEnabled(acl_available)
        self._grant_button.setEnabled(acl_available)
        self._remove_acl_button.setEnabled(acl_available)

        access = self._repository.folder_access(
            path=path,
            username=str(username),
        )

        current = access.access_permissions or "none"
        inherited = (
            access.default_permissions
            or "none"
        )

        self._current_acl.setText(
            f"<b>Current explicit ACL:</b> {current}<br>"
            f"<b>Default access for new items:</b> "
            f"{inherited}"
        )

    def _grant_folder_access(self) -> None:
        username = self._folder_user.currentData()
        path = self._folder_path.text().strip()

        if not username or not path:
            QMessageBox.warning(
                self,
                "Folder Access Is Incomplete",
                "Select a user and folder.",
            )
            return

        recursive_notice = (
            "\n\nApplying access recursively may take time "
            "for a large folder."
            if self._recursive.isChecked()
            else ""
        )

        response = QMessageBox.question(
            self,
            "Grant Folder Access",
            (
                f"Grant {username} "
                f"{self._access_level.currentText().lower()} "
                f"access to:\n{path}?"
                f"{recursive_notice}"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            task_id=(
                "user_permissions.apply_folder_access"
            ),
            arguments={
                "username": str(username),
                "path": path,
                "access_level": str(
                    self._access_level.currentData()
                ),
                "recursive": (
                    self._recursive.isChecked()
                ),
                "inherit": (
                    self._inherit.isChecked()
                ),
                "traverse_parents": (
                    self._traverse.isChecked()
                ),
            },
            success_title="Folder Access Updated",
            refresh=True,
        )

    def _remove_folder_access(self) -> None:
        username = self._folder_user.currentData()
        path = self._folder_path.text().strip()

        if not username or not path:
            QMessageBox.warning(
                self,
                "Folder Access Is Incomplete",
                "Select a user and folder.",
            )
            return

        response = QMessageBox.warning(
            self,
            "Remove Folder Access",
            (
                f"Remove {username}'s explicit ACL access "
                f"from:\n{path}?\n\n"
                "This does not change ownership, primary group "
                "permissions, or access inherited through groups."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            task_id=(
                "user_permissions.remove_folder_access"
            ),
            arguments={
                "username": str(username),
                "path": path,
                "recursive": (
                    self._recursive.isChecked()
                ),
                "remove_default": True,
            },
            success_title="Folder Access Removed",
            refresh=True,
        )

    def _home_option_changed(
        self,
        enabled: bool,
    ) -> None:
        self._home_directory.setEnabled(enabled)

    def _create_service_account(self) -> None:
        username = self._new_username.text().strip()

        if not username:
            QMessageBox.warning(
                self,
                "Account Name Required",
                "Enter a service account name.",
            )
            return

        response = QMessageBox.question(
            self,
            "Create Service Account",
            (
                f"Create the system account {username}?\n\n"
                "The account will have no password and cannot "
                "log in interactively."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            task_id=(
                "user_permissions.create_service_account"
            ),
            arguments={
                "username": username,
                "description": (
                    self._new_description.text()
                ),
                "create_home": (
                    self._create_home.isChecked()
                ),
                "home_directory": (
                    self._home_directory.text()
                ),
            },
            success_title="Service Account Created",
            refresh=True,
            on_success=self._clear_create_form,
        )

    def _run_task(
        self,
        *,
        task_id: str,
        arguments: dict[str, Any],
        success_title: str,
        refresh: bool,
        on_success=None,
    ) -> None:
        if self._busy:
            return

        self._set_busy(True)

        worker = _TaskWorker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            )
        )

        worker.signals.succeeded.connect(
            lambda message: self._task_succeeded(
                success_title,
                message,
                refresh,
                on_success,
            )
        )
        worker.signals.failed.connect(
            self._task_failed
        )
        worker.signals.finished.connect(
            self._task_finished
        )

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _task_succeeded(
        self,
        title: str,
        message: str,
        refresh: bool,
        on_success,
    ) -> None:
        QMessageBox.information(
            self,
            title,
            message,
        )

        if on_success is not None:
            on_success()

        if refresh:
            self.reload()

    def _task_failed(
        self,
        message: str,
    ) -> None:
        QMessageBox.critical(
            self,
            "Permission Change Failed",
            message,
        )

    def _task_finished(self) -> None:
        self._active_worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._tabs.setEnabled(not busy)

    def _selected_account(
        self,
    ) -> UserAccount | None:
        rows = (
            self._account_table.selectionModel()
            .selectedRows()
        )

        if not rows:
            return None

        item = self._account_table.item(
            rows[0].row(),
            0,
        )

        if item is None:
            return None

        username = item.data(
            Qt.ItemDataRole.UserRole
        )

        return next(
            (
                account
                for account in self._accounts
                if account.name == username
            ),
            None,
        )

    def _selected_username(self) -> str:
        account = self._selected_account()
        return account.name if account else ""

    def _select_account_by_name(
        self,
        username: str,
    ) -> None:
        for row in range(
            self._account_table.rowCount()
        ):
            item = self._account_table.item(
                row,
                0,
            )

            if (
                item is not None
                and item.data(
                    Qt.ItemDataRole.UserRole
                )
                == username
            ):
                self._account_table.selectRow(row)
                return

    def _clear_account_details(self) -> None:
        self._account_heading.setText(
            "Select an account"
        )
        self._account_details.clear()
        self._group_list.clear()
        self._group_list.setEnabled(False)
        self._save_groups_button.setEnabled(False)

    def _clear_create_form(self) -> None:
        self._new_username.clear()
        self._new_description.clear()
        self._create_home.setChecked(False)
        self._home_directory.clear()
