from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
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

from .repository import TaskSchedulerRepository


class TaskSchedulerView(QWidget):
    def __init__(
        self,
        repository: TaskSchedulerRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._editing_task_id = ""

        heading = QLabel("Task Scheduler")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        description = QLabel(
            "Create and manage scheduled tasks through systemd, "
            "and inspect existing systemd timers and cron entries."
        )
        description.setWordWrap(True)

        self._tabs = QTabWidget()
        self._tabs.addTab(
            self._build_overview(),
            "Overview",
        )
        self._tabs.addTab(
            self._build_lec_tasks(),
            "LEC Tasks",
        )
        self._tabs.addTab(
            self._build_existing(),
            "Existing Schedules",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._tabs, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(30000)
        self._timer.timeout.connect(self.reload)
        self._timer.start()

        self.reload()

    def _build_overview(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._overview_summary = QLabel()
        self._overview_summary.setWordWrap(True)

        self._overview_note = QLabel(
            "LEC-created tasks are editable and use dedicated systemd "
            "service and timer units. Existing Ubuntu and application "
            "timers and cron entries are shown for reference but are "
            "not edited directly, because many are package-managed."
        )
        self._overview_note.setWordWrap(True)

        install = QPushButton(
            "Install or Repair Schedule Monitor"
        )
        install.clicked.connect(
            lambda: self._run_task(
                "task_scheduler.install_monitor",
                {},
                "Schedule Monitor Installed",
            )
        )

        refresh = QPushButton("Refresh Schedule Inventory")
        refresh.clicked.connect(
            lambda: self._run_task(
                "task_scheduler.refresh",
                {},
                "Schedule Inventory Refreshed",
            )
        )

        buttons = QHBoxLayout()
        buttons.addWidget(install)
        buttons.addWidget(refresh)
        buttons.addStretch()

        layout.addWidget(self._overview_summary)
        layout.addLayout(buttons)
        layout.addWidget(self._overview_note)
        layout.addStretch()
        return container

    def _build_lec_tasks(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self._lec_table = QTableWidget(0, 9)
        self._lec_table.setHorizontalHeaderLabels(
            [
                "Name",
                "Schedule",
                "Run As",
                "Enabled",
                "Runtime Status",
                "Next Run",
                "Last Result",
                "Command",
                "ID",
            ]
        )
        self._lec_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._lec_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._lec_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        header = self._lec_table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)

        for index, width in enumerate(
            [180, 180, 100, 80, 120, 190, 120, 300, 100]
        ):
            self._lec_table.setColumnWidth(index, width)

        self._lec_table.itemSelectionChanged.connect(
            self._load_selected_task
        )

        form_group = QGroupBox("Create or Edit LEC Task")
        form = QFormLayout(form_group)

        self._task_name = QLineEdit()
        self._task_description = QLineEdit()
        self._task_command = QTextEdit()
        self._task_command.setMaximumHeight(100)
        self._working_directory = QLineEdit("/")
        self._run_as_user = QLineEdit("root")

        self._schedule_type = QComboBox()
        self._schedule_type.addItem(
            "Every N minutes",
            "minutes",
        )
        self._schedule_type.addItem(
            "Hourly",
            "hourly",
        )
        self._schedule_type.addItem(
            "Daily",
            "daily",
        )
        self._schedule_type.addItem(
            "Weekly",
            "weekly",
        )
        self._schedule_type.addItem(
            "Monthly",
            "monthly",
        )
        self._schedule_type.addItem(
            "After boot",
            "boot",
        )
        self._schedule_type.addItem(
            "Advanced systemd calendar expression",
            "calendar",
        )
        self._schedule_type.currentIndexChanged.connect(
            self._update_schedule_help
        )

        self._schedule_value = QLineEdit()
        self._schedule_help = QLabel()
        self._schedule_help.setWordWrap(True)

        self._task_enabled = QCheckBox(
            "Enable this task"
        )
        self._task_enabled.setChecked(True)

        form.addRow("Task name:", self._task_name)
        form.addRow(
            "Description:",
            self._task_description,
        )
        form.addRow("Command:", self._task_command)
        form.addRow(
            "Working directory:",
            self._working_directory,
        )
        form.addRow(
            "Run as user:",
            self._run_as_user,
        )
        form.addRow(
            "Schedule type:",
            self._schedule_type,
        )
        form.addRow(
            "Schedule value:",
            self._schedule_value,
        )
        form.addRow("", self._schedule_help)
        form.addRow("", self._task_enabled)

        save = QPushButton("Save Task")
        save.clicked.connect(self._save_task)
        clear = QPushButton("Clear Form")
        clear.clicked.connect(self._clear_form)
        run_now = QPushButton("Run Selected Now")
        run_now.clicked.connect(self._run_selected_now)
        toggle = QPushButton(
            "Enable or Disable Selected"
        )
        toggle.clicked.connect(
            self._toggle_selected
        )
        delete = QPushButton("Delete Selected")
        delete.clicked.connect(
            self._delete_selected
        )

        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(clear)
        buttons.addWidget(run_now)
        buttons.addWidget(toggle)
        buttons.addStretch()
        buttons.addWidget(delete)

        layout.addWidget(self._lec_table, 1)
        layout.addWidget(form_group)
        layout.addLayout(buttons)

        self._update_schedule_help()
        return container

    def _build_existing(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        note = QLabel(
            "This inventory includes systemd timers, /etc/crontab, "
            "/etc/cron.d entries, and user crontabs visible to the "
            "privileged collector. Existing schedules are displayed "
            "read-only to avoid overwriting package-managed files."
        )
        note.setWordWrap(True)

        self._existing_filter = QLineEdit()
        self._existing_filter.setPlaceholderText(
            "Filter by source, timer, command, user, or schedule…"
        )
        self._existing_filter.textChanged.connect(
            self._apply_existing_filter
        )

        self._existing_table = QTableWidget(0, 8)
        self._existing_table.setHorizontalHeaderLabels(
            [
                "Source",
                "Name",
                "Schedule / Next Run",
                "Status",
                "Runs / Activates",
                "User",
                "Last Run",
                "Location / Detail",
            ]
        )
        self._existing_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._existing_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        header = self._existing_table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)

        for index, width in enumerate(
            [100, 220, 240, 110, 360, 100, 200, 240]
        ):
            self._existing_table.setColumnWidth(index, width)

        layout.addWidget(note)
        layout.addWidget(self._existing_filter)
        layout.addWidget(self._existing_table, 1)
        return container

    def reload(self) -> None:
        snapshot = self._repository.snapshot()
        summary = snapshot.get("summary", {})

        if isinstance(summary, dict):
            self._overview_summary.setText(
                f"LEC tasks: {summary.get('lec_tasks', 0)}   •   "
                f"Enabled LEC tasks: "
                f"{summary.get('enabled_lec_tasks', 0)}   •   "
                f"Systemd timers: "
                f"{summary.get('systemd_timers', 0)}   •   "
                f"Cron entries: {summary.get('cron_entries', 0)}   •   "
                f"Last inventory: "
                f"{snapshot.get('generated_at', 'Never')}"
            )

        lec_tasks = snapshot.get("lec_tasks", [])
        self._lec_table.setRowCount(0)

        if isinstance(lec_tasks, list):
            for task in lec_tasks:
                if not isinstance(task, dict):
                    continue

                values = (
                    str(task.get("name", "")),
                    self._display_schedule(task),
                    str(task.get("run_as_user", "")),
                    "Yes"
                    if task.get("enabled", False)
                    else "No",
                    str(
                        task.get(
                            "runtime_status",
                            "",
                        )
                    ),
                    str(task.get("next_run", "")),
                    str(
                        task.get(
                            "last_result",
                            "",
                        )
                    ),
                    str(task.get("command", "")),
                    str(task.get("id", "")),
                )

                row = self._lec_table.rowCount()
                self._lec_table.insertRow(row)

                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(
                        str(
                            task.get(
                                "description",
                                "",
                            )
                        )
                    )
                    self._lec_table.setItem(
                        row,
                        column,
                        item,
                    )

        existing: list[dict[str, Any]] = []
        for key in (
            "systemd_timers",
            "cron_entries",
        ):
            values = snapshot.get(key, [])
            if isinstance(values, list):
                existing.extend(
                    item
                    for item in values
                    if isinstance(item, dict)
                )

        self._existing_table.setRowCount(0)

        for item in existing:
            values = (
                str(item.get("source", "")),
                str(item.get("name", "")),
                str(
                    item.get("schedule", "")
                    or item.get("next_run", "")
                ),
                str(item.get("status", "")),
                str(item.get("activates", "")),
                str(item.get("user", "")),
                str(item.get("last_run", "")),
                str(item.get("detail", "")),
            )
            row = self._existing_table.rowCount()
            self._existing_table.insertRow(row)

            for column, value in enumerate(values):
                self._existing_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self._apply_existing_filter()

    def _display_schedule(
        self,
        task: dict[str, Any],
    ) -> str:
        schedule_type = str(
            task.get("schedule_type", "")
        )
        value = str(
            task.get("schedule_value", "")
        )

        labels = {
            "minutes": f"Every {value} minute(s)",
            "hourly": "Hourly",
            "daily": f"Daily at {value or '03:00'}",
            "weekly": f"Weekly: {value or 'Mon 03:00'}",
            "monthly": f"Monthly: {value or '1 03:00'}",
            "boot": f"After boot: {value or '2min'}",
            "calendar": value,
        }
        return labels.get(schedule_type, value)

    def _update_schedule_help(self) -> None:
        schedule_type = str(
            self._schedule_type.currentData()
        )

        help_text = {
            "minutes": (
                "Enter the number of minutes, such as 15."
            ),
            "hourly": (
                "No value is required."
            ),
            "daily": (
                "Enter a 24-hour time, such as 03:30."
            ),
            "weekly": (
                "Enter a weekday and time, such as Mon 03:30."
            ),
            "monthly": (
                "Enter a day of the month and time, such as 1 03:30."
            ),
            "boot": (
                "Enter a delay after boot, such as 2min or 30s."
            ),
            "calendar": (
                "Enter a systemd OnCalendar expression, such as "
                "Mon..Fri *-*-* 18:00:00."
            ),
        }

        self._schedule_help.setText(
            help_text.get(schedule_type, "")
        )
        self._schedule_value.setEnabled(
            schedule_type != "hourly"
        )

    def _save_task(self) -> None:
        self._run_task(
            "task_scheduler.save",
            {
                "original_id": self._editing_task_id,
                "name": self._task_name.text(),
                "description": (
                    self._task_description.text()
                ),
                "command": (
                    self._task_command.toPlainText()
                ),
                "working_directory": (
                    self._working_directory.text()
                ),
                "run_as_user": (
                    self._run_as_user.text()
                ),
                "schedule_type": str(
                    self._schedule_type.currentData()
                ),
                "schedule_value": (
                    self._schedule_value.text()
                ),
                "enabled": (
                    self._task_enabled.isChecked()
                ),
            },
            "Scheduled Task Saved",
        )

    def _load_selected_task(self) -> None:
        row = self._lec_table.currentRow()

        if row < 0:
            return

        task_id = self._lec_table.item(
            row,
            8,
        ).text()
        snapshot = self._repository.snapshot()
        tasks = snapshot.get("lec_tasks", [])

        if not isinstance(tasks, list):
            return

        task = next(
            (
                item
                for item in tasks
                if isinstance(item, dict)
                and str(item.get("id", ""))
                == task_id
            ),
            None,
        )

        if task is None:
            return

        self._editing_task_id = task_id
        self._task_name.setText(
            str(task.get("name", ""))
        )
        self._task_description.setText(
            str(task.get("description", ""))
        )
        self._task_command.setPlainText(
            str(task.get("command", ""))
        )
        self._working_directory.setText(
            str(
                task.get(
                    "working_directory",
                    "/",
                )
            )
        )
        self._run_as_user.setText(
            str(task.get("run_as_user", "root"))
        )

        schedule_type = str(
            task.get("schedule_type", "minutes")
        )
        index = self._schedule_type.findData(
            schedule_type
        )

        if index >= 0:
            self._schedule_type.setCurrentIndex(index)

        self._schedule_value.setText(
            str(task.get("schedule_value", ""))
        )
        self._task_enabled.setChecked(
            bool(task.get("enabled", True))
        )

    def _clear_form(self) -> None:
        self._editing_task_id = ""
        self._task_name.clear()
        self._task_description.clear()
        self._task_command.clear()
        self._working_directory.setText("/")
        self._run_as_user.setText("root")
        self._schedule_type.setCurrentIndex(0)
        self._schedule_value.clear()
        self._task_enabled.setChecked(True)
        self._lec_table.clearSelection()

    def _selected_task_id(self) -> str:
        row = self._lec_table.currentRow()

        if row < 0:
            QMessageBox.warning(
                self,
                "Select a Task",
                "Select an LEC task first.",
            )
            return ""

        return self._lec_table.item(row, 8).text()

    def _run_selected_now(self) -> None:
        task_id = self._selected_task_id()
        if task_id:
            self._run_task(
                "task_scheduler.run_now",
                {"task_id": task_id},
                "Task Completed",
            )

    def _toggle_selected(self) -> None:
        row = self._lec_table.currentRow()

        if row < 0:
            self._selected_task_id()
            return

        task_id = self._lec_table.item(row, 8).text()
        enabled = (
            self._lec_table.item(row, 3).text()
            != "Yes"
        )
        self._run_task(
            "task_scheduler.enable",
            {
                "task_id": task_id,
                "enabled": enabled,
            },
            (
                "Task Enabled"
                if enabled
                else "Task Disabled"
            ),
        )

    def _delete_selected(self) -> None:
        task_id = self._selected_task_id()

        if not task_id:
            return

        row = self._lec_table.currentRow()
        name = self._lec_table.item(row, 0).text()
        response = QMessageBox.question(
            self,
            "Delete Scheduled Task",
            (
                f"Delete {name} and its systemd service, "
                "timer, and command script?"
            ),
        )

        if (
            response
            != QMessageBox.StandardButton.Yes
        ):
            return

        self._run_task(
            "task_scheduler.delete",
            {"task_id": task_id},
            "Scheduled Task Deleted",
        )
        self._clear_form()

    def _apply_existing_filter(self) -> None:
        needle = (
            self._existing_filter.text()
            .strip()
            .lower()
        )

        for row in range(
            self._existing_table.rowCount()
        ):
            combined = " ".join(
                (
                    self._existing_table.item(
                        row,
                        column,
                    ).text()
                    if self._existing_table.item(
                        row,
                        column,
                    )
                    else ""
                )
                for column in range(
                    self._existing_table.columnCount()
                )
            ).lower()
            self._existing_table.setRowHidden(
                row,
                bool(needle and needle not in combined),
            )

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
    ) -> None:
        try:
            result = PrivilegedRunner().run(
                PrivilegedTask(
                    task_id,
                    arguments,
                ),
                timeout=240,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Task Scheduler Operation Failed",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            title,
            str(result),
        )
        self.reload()
