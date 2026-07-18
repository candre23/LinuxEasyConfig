from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor
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
    QListWidget,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .models import LogEvent
from .repository import SystemLogsRepository


@dataclass(frozen=True)
class _TaskResult:
    operation: str
    value: Any


class _Signals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(
        self,
        operation: str,
        function: Callable[[], Any],
    ) -> None:
        super().__init__()
        self._operation = operation
        self._function = function
        self.signals = _Signals()

    def run(self) -> None:
        try:
            value = self._function()
            self.signals.succeeded.emit(
                _TaskResult(
                    operation=self._operation,
                    value=value,
                )
            )
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class SystemLogsView(QWidget):
    def __init__(
        self,
        repository: SystemLogsRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        heading = QLabel("System Logs")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Browse system events with severity markup, duplicate "
            "grouping, plain-English explanations, and suggested "
            "troubleshooting steps. The original log message is "
            "always retained."
        )
        description.setWordWrap(True)

        tabs = QTabWidget()
        tabs.addTab(
            OverviewTab(repository),
            "Overview",
        )
        tabs.addTab(
            JournalTab(
                repository,
                mode="live",
                title="Live Logs",
                default_since="30 minutes ago",
                auto_refresh=True,
            ),
            "Live Logs",
        )
        tabs.addTab(
            ServiceLogsTab(repository),
            "Service Logs",
        )
        tabs.addTab(
            JournalTab(
                repository,
                mode="boot",
                title="Boot & Kernel",
                default_since="",
                current_boot=True,
            ),
            "Boot & Kernel",
        )
        tabs.addTab(
            JournalTab(
                repository,
                mode="security",
                title="Authentication & Security",
                default_since="24 hours ago",
                current_boot=True,
            ),
            "Authentication & Security",
        )
        tabs.addTab(
            RawSourcesTab(repository),
            "Raw Sources",
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(tabs, 1)


class _AsyncTab(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._busy = False

    def _run(
        self,
        operation: str,
        function: Callable[[], Any],
    ) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_busy(True)

        worker = _Worker(operation, function)
        worker.signals.succeeded.connect(
            self._task_succeeded
        )
        worker.signals.failed.connect(
            self._task_failed
        )
        worker.signals.finished.connect(
            self._task_finished
        )
        self._thread_pool.start(worker)

    def _task_succeeded(
        self,
        result: _TaskResult,
    ) -> None:
        raise NotImplementedError

    def _task_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Log Operation Failed",
            message,
        )

    def _task_finished(self) -> None:
        self._busy = False
        self._set_busy(False)

    def _clear_selected_markers(self) -> None:
        units: list[str] = []

        for index in self._failed_table.selectionModel().selectedRows():
            item = self._failed_table.item(index.row(), 0)

            if item is not None and item.text().strip():
                units.append(item.text().strip())

        if not units:
            QMessageBox.information(
                self,
                "No Units Selected",
                "Select one or more failed units first.",
            )
            return

        self._confirm_and_reset(units)

    def _clear_all_markers(self) -> None:
        units = [
            self._failed_table.item(row, 0).text().strip()
            for row in range(self._failed_table.rowCount())
            if self._failed_table.item(row, 0) is not None
            and self._failed_table.item(row, 0).text().strip()
        ]

        if units:
            self._confirm_and_reset(units)

    def _confirm_and_reset(
        self,
        units: list[str],
    ) -> None:
        answer = QMessageBox.question(
            self,
            "Clear Failed Markers",
            (
                "Clear systemd's stored failed marker for "
                f"{len(units)} unit"
                f"{'s' if len(units) != 1 else ''}?\n\n"
                "This does not start, stop, restart, enable, or disable "
                "the units. A unit will reappear here if it fails again."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self._run(
            "reset_failed",
            lambda: self._repository.reset_failed(units),
        )

    def _set_busy(self, busy: bool) -> None:
        del busy


class OverviewTab(_AsyncTab):
    def __init__(
        self,
        repository: SystemLogsRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository

        self._critical = QLabel("—")
        self._errors = QLabel("—")
        self._warnings = QLabel("—")
        self._failed_services = QLabel("—")

        cards = QHBoxLayout()
        cards.addWidget(
            _metric_group("Critical events", self._critical)
        )
        cards.addWidget(
            _metric_group("Errors", self._errors)
        )
        cards.addWidget(
            _metric_group("Warnings", self._warnings)
        )
        cards.addWidget(
            _metric_group(
                "Failed services",
                self._failed_services,
            )
        )

        self._failed_table = QTableWidget(0, 8)
        self._failed_table.setHorizontalHeaderLabels(
            [
                "Unit",
                "Description",
                "Result",
                "Exit Status",
                "Last Failure",
                "Associated Timer",
                "Timer Status",
                "Next Run",
            ]
        )
        _configure_table(self._failed_table)
        self._failed_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        failed_header = self._failed_table.horizontalHeader()

        for column in (0, 2, 3, 4, 5, 6, 7):
            failed_header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        failed_header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        self._events = EventBrowser()

        refresh = QPushButton("Refresh Overview")
        refresh.clicked.connect(self.reload)

        self._clear_selected = QPushButton(
            "Clear Selected Markers"
        )
        self._clear_selected.clicked.connect(
            self._clear_selected_markers
        )

        self._clear_all = QPushButton(
            "Clear All Old Markers"
        )
        self._clear_all.clicked.connect(
            self._clear_all_markers
        )

        self._status = QLabel()

        buttons = QHBoxLayout()
        buttons.addWidget(self._status, 1)
        buttons.addWidget(self._clear_selected)
        buttons.addWidget(self._clear_all)
        buttons.addWidget(refresh)

        failed_group = QGroupBox(
            "Systemd Units Marked Failed"
        )
        failed_layout = QVBoxLayout(failed_group)
        failed_note = QLabel(
            "These are units that systemd still remembers as failed. "
            "A module may currently be working if a later run succeeded "
            "or its timer remains active. Clearing a marker does not "
            "disable or restart the service."
        )
        failed_note.setWordWrap(True)
        failed_layout.addWidget(failed_note)
        failed_layout.addWidget(self._failed_table)

        events_group = QGroupBox(
            "Important Events From The Last 24 Hours"
        )
        events_layout = QVBoxLayout(events_group)
        events_layout.addWidget(self._events)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.addLayout(cards)
        layout.addWidget(failed_group)
        layout.addWidget(events_group, 1)
        layout.addLayout(buttons)

        QTimer.singleShot(0, self.reload)

    def reload(self) -> None:
        self._run("overview", self._repository.overview)

    def _task_succeeded(
        self,
        result: _TaskResult,
    ) -> None:
        if result.operation == "reset_failed":
            QMessageBox.information(
                self,
                "Failed Markers Cleared",
                str(result.value),
            )
            QTimer.singleShot(0, self.reload)
            return

        data = result.value
        summary = data.get("summary", {})

        self._critical.setText(
            str(summary.get("critical", 0))
        )
        self._errors.setText(
            str(summary.get("errors", 0))
        )
        self._warnings.setText(
            str(summary.get("warnings", 0))
        )

        failed = data.get("failed_units", [])
        self._failed_services.setText(str(len(failed)))
        self._failed_table.setRowCount(len(failed))

        for row, item in enumerate(failed):
            values = (
                item.get("unit", ""),
                item.get("description", ""),
                item.get("result", ""),
                item.get("exit_status", ""),
                item.get("last_failure", ""),
                item.get("timer", ""),
                item.get("timer_status", ""),
                item.get("next_run", ""),
            )

            for column, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setData(
                    Qt.ItemDataRole.UserRole,
                    str(item.get("unit", "")),
                )
                self._failed_table.setItem(
                    row,
                    column,
                    table_item,
                )

        has_failed = bool(failed)
        self._clear_selected.setEnabled(has_failed)
        self._clear_all.setEnabled(has_failed)

        events = [
            LogEvent.from_dict(item)
            for item in data.get("events", [])
        ]
        self._events.set_events(events)
        self._status.setText(
            f"Updated {data.get('generated_at', '')}"
        )

    def _set_busy(self, busy: bool) -> None:
        has_rows = self._failed_table.rowCount() > 0
        self._clear_selected.setEnabled(
            not busy and has_rows
        )
        self._clear_all.setEnabled(
            not busy and has_rows
        )
        self._status.setText(
            "Reading system journal..."
            if busy
            else self._status.text()
        )


class JournalTab(_AsyncTab):
    def __init__(
        self,
        repository: SystemLogsRepository,
        *,
        mode: str,
        title: str,
        default_since: str,
        current_boot: bool = False,
        auto_refresh: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._mode = mode
        self._current_boot_default = current_boot

        filters = QGroupBox("Filters")
        form = QFormLayout(filters)

        self._since = QComboBox()
        self._since.setEditable(True)
        self._since.addItems(
            [
                "10 minutes ago",
                "30 minutes ago",
                "1 hour ago",
                "6 hours ago",
                "24 hours ago",
                "7 days ago",
            ]
        )
        self._since.setCurrentText(default_since)

        self._severity = QComboBox()
        self._severity.addItem(
            "Warnings and more severe",
            4,
        )
        self._severity.addItem(
            "Notices and more severe",
            5,
        )
        self._severity.addItem(
            "Information and more severe",
            6,
        )
        self._severity.addItem(
            "Include debug messages",
            7,
        )
        self._severity.setCurrentIndex(
            2 if mode == "live" else 0
        )

        self._keyword = QLineEdit()
        self._keyword.setPlaceholderText(
            "Optional text, service, address, or error"
        )

        self._limit = QSpinBox()
        self._limit.setRange(100, 5000)
        self._limit.setSingleStep(100)
        self._limit.setValue(1000)

        self._grouped = QCheckBox(
            "Group repeated messages"
        )
        self._grouped.setChecked(True)

        self._current_boot = QCheckBox(
            "Current boot only"
        )
        self._current_boot.setChecked(current_boot)

        form.addRow("Time range:", self._since)
        form.addRow("Severity:", self._severity)
        form.addRow("Contains:", self._keyword)
        form.addRow("Maximum events:", self._limit)
        form.addRow("", self._grouped)
        form.addRow("", self._current_boot)

        self._browser = EventBrowser()
        self._status = QLabel()

        self._refresh = QPushButton("Refresh")
        self._refresh.clicked.connect(self.reload)

        self._auto_refresh = QCheckBox(
            "Refresh every 10 seconds"
        )
        self._auto_refresh.setChecked(auto_refresh)
        self._auto_refresh.toggled.connect(
            self._auto_refresh_changed
        )

        buttons = QHBoxLayout()
        buttons.addWidget(QLabel(title))
        buttons.addWidget(self._status, 1)
        buttons.addWidget(self._auto_refresh)
        buttons.addWidget(self._refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.addWidget(filters)
        layout.addWidget(self._browser, 1)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self.reload)

        if auto_refresh:
            self._timer.start()

        QTimer.singleShot(0, self.reload)

    def reload(self) -> None:
        self._run(
            "journal",
            lambda: self._repository.journal(
                mode=self._mode,
                since=self._since.currentText().strip(),
                priority=int(
                    self._severity.currentData()
                ),
                keyword=self._keyword.text().strip(),
                limit=self._limit.value(),
                current_boot=(
                    self._current_boot.isChecked()
                ),
                grouped=self._grouped.isChecked(),
            ),
        )

    def _task_succeeded(
        self,
        result: _TaskResult,
    ) -> None:
        data = result.value
        events = data.get("events", [])
        self._browser.set_events(events)
        summary = data.get("summary", {})
        self._status.setText(
            f"{summary.get('total', 0)} events; "
            f"{summary.get('errors', 0)} errors; "
            f"{summary.get('warnings', 0)} warnings"
        )

    def _set_busy(self, busy: bool) -> None:
        self._refresh.setEnabled(not busy)

        if busy:
            self._status.setText("Reading logs...")

    def _auto_refresh_changed(
        self,
        enabled: bool,
    ) -> None:
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()


class ServiceLogsTab(JournalTab):
    def __init__(
        self,
        repository: SystemLogsRepository,
        parent: QWidget | None = None,
    ) -> None:
        self._unit = QComboBox()
        self._unit.setEditable(True)
        self._unit.setMinimumContentsLength(30)

        super().__init__(
            repository,
            mode="service",
            title="Service Logs",
            default_since="24 hours ago",
            parent=parent,
        )

        filters = self.findChildren(QGroupBox)[0]
        form = filters.layout()
        form.insertRow(
            0,
            "Systemd service:",
            self._unit,
        )

        QTimer.singleShot(100, self._load_units)

    def _load_units(self) -> None:
        self._run(
            "units",
            lambda: self._repository.journal(
                mode="service",
                since="1 minute ago",
                priority=7,
                limit=1,
                grouped=False,
            ),
        )

    def reload(self) -> None:
        unit = self._unit.currentText().strip()

        if not unit:
            return

        self._run(
            "journal",
            lambda: self._repository.journal(
                mode="service",
                since=self._since.currentText().strip(),
                priority=int(
                    self._severity.currentData()
                ),
                unit=unit,
                keyword=self._keyword.text().strip(),
                limit=self._limit.value(),
                current_boot=(
                    self._current_boot.isChecked()
                ),
                grouped=self._grouped.isChecked(),
            ),
        )

    def _task_succeeded(
        self,
        result: _TaskResult,
    ) -> None:
        if result.operation == "units":
            units = result.value.get("units", [])
            current = self._unit.currentText()
            self._unit.clear()
            self._unit.addItems(units)

            if current:
                self._unit.setCurrentText(current)
            elif units:
                preferred = next(
                    (
                        unit
                        for unit in units
                        if unit in {
                            "caddy.service",
                            "docker.service",
                            "ssh.service",
                        }
                    ),
                    units[0],
                )
                self._unit.setCurrentText(preferred)
                QTimer.singleShot(0, self.reload)
            return

        super()._task_succeeded(result)


class RawSourcesTab(_AsyncTab):
    def __init__(
        self,
        repository: SystemLogsRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._sources: list[dict[str, Any]] = []

        self._list = QListWidget()
        self._list.currentRowChanged.connect(
            self._source_selected
        )

        self._content = QPlainTextEdit()
        self._content.setReadOnly(True)
        self._content.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._list)
        splitter.addWidget(self._content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([350, 800])

        self._lines = QSpinBox()
        self._lines.setRange(50, 5000)
        self._lines.setValue(500)

        refresh_sources = QPushButton(
            "Refresh Sources"
        )
        refresh_sources.clicked.connect(
            self.reload_sources
        )

        read_source = QPushButton(
            "Read Selected Source"
        )
        read_source.clicked.connect(
            self._read_selected
        )

        self._status = QLabel()

        buttons = QHBoxLayout()
        buttons.addWidget(QLabel("Lines:"))
        buttons.addWidget(self._lines)
        buttons.addWidget(self._status, 1)
        buttons.addWidget(refresh_sources)
        buttons.addWidget(read_source)

        note = QLabel(
            "Raw Sources provides advanced access to regular files "
            "beneath /var/log. Journal tabs are preferred because "
            "they add structured fields, grouping, and interpretation."
        )
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.addWidget(note)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

        QTimer.singleShot(0, self.reload_sources)

    def reload_sources(self) -> None:
        self._run(
            "sources",
            self._repository.raw_sources,
        )

    def _source_selected(self, row: int) -> None:
        if row >= 0:
            self._status.setText(
                self._sources[row].get("path", "")
            )

    def _read_selected(self) -> None:
        row = self._list.currentRow()

        if row < 0 or row >= len(self._sources):
            return

        path = str(self._sources[row].get("path", ""))
        self._run(
            "raw",
            lambda: self._repository.raw_read(
                path=path,
                lines=self._lines.value(),
            ),
        )

    def _task_succeeded(
        self,
        result: _TaskResult,
    ) -> None:
        if result.operation == "sources":
            self._sources = list(result.value)
            self._list.clear()

            for source in self._sources:
                self._list.addItem(
                    str(source.get("path", ""))
                )

            self._status.setText(
                f"{len(self._sources)} log files"
            )
            return

        data = result.value
        prefix = (
            "[Only the final portion of this large file "
            "was read.]\n\n"
            if data.get("truncated")
            else ""
        )
        self._content.setPlainText(
            prefix + str(data.get("text", ""))
        )
        self._status.setText(
            str(data.get("path", ""))
        )


class EventBrowser(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._events: list[LogEvent] = []

        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            [
                "Time",
                "Severity",
                "Category",
                "Source",
                "Summary",
                "Count",
                "Confidence",
                "Original Message",
            ]
        )
        _configure_table(self._table)
        self._table.itemSelectionChanged.connect(
            self._selection_changed
        )

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            6,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            7,
            QHeaderView.ResizeMode.Stretch,
        )

        self._details = QPlainTextEdit()
        self._details.setReadOnly(True)
        self._details.setPlaceholderText(
            "Select an event to see its explanation and "
            "suggested next step."
        )

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._table)
        splitter.addWidget(self._details)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([450, 220])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

    def set_events(
        self,
        events: list[LogEvent],
    ) -> None:
        self._events = list(events)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(events))

        for row, event in enumerate(events):
            values = (
                event.last_timestamp or event.timestamp,
                event.severity,
                event.category,
                event.source or event.unit,
                event.summary,
                str(event.count),
                event.confidence,
                event.message,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    row,
                )
                _apply_severity_markup(
                    item,
                    event.priority,
                )
                self._table.setItem(
                    row,
                    column,
                    item,
                )

        self._table.setSortingEnabled(True)
        self._details.clear()

    def _selection_changed(self) -> None:
        rows = self._table.selectionModel().selectedRows()

        if not rows:
            self._details.clear()
            return

        item = self._table.item(rows[0].row(), 0)

        if item is None:
            return

        index = int(
            item.data(Qt.ItemDataRole.UserRole)
        )

        if index < 0 or index >= len(self._events):
            return

        event = self._events[index]
        repeated = (
            f"\nOccurrences: {event.count}\n"
            f"First seen: {event.first_timestamp}\n"
            f"Last seen: {event.last_timestamp}\n"
            if event.count > 1
            else ""
        )

        self._details.setPlainText(
            f"{event.severity} — {event.summary}\n\n"
            f"Category: {event.category}\n"
            f"Source: {event.source or 'Unknown'}\n"
            f"Service: {event.unit or 'Not identified'}\n"
            f"Process: {event.process or 'Not identified'}"
            f"{' (' + event.pid + ')' if event.pid else ''}\n"
            f"Confidence: {event.confidence}\n"
            f"{repeated}\n"
            f"What it means\n"
            f"------------------------------------------------------------\n"
            f"{event.explanation}\n\n"
            f"Suggested next step\n"
            f"------------------------------------------------------------\n"
            f"{event.suggestion}\n\n"
            f"Original message\n"
            f"------------------------------------------------------------\n"
            f"{event.message}"
        )


def _metric_group(
    title: str,
    value_label: QLabel,
) -> QGroupBox:
    value_label.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    value_label.setStyleSheet(
        "font-size: 26px; font-weight: bold;"
    )

    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(value_label)
    return group


def _configure_table(table: QTableWidget) -> None:
    table.setEditTriggers(
        QAbstractItemView.EditTrigger.NoEditTriggers
    )
    table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectRows
    )
    table.setSelectionMode(
        QAbstractItemView.SelectionMode.SingleSelection
    )
    table.verticalHeader().setVisible(False)
    table.setWordWrap(False)
    table.setAlternatingRowColors(True)


def _apply_severity_markup(
    item: QTableWidgetItem,
    priority: int,
) -> None:
    if priority <= 2:
        item.setBackground(QColor("#6d1f2a"))
        item.setForeground(QColor("#ffffff"))
    elif priority == 3:
        item.setBackground(QColor("#7a2f2f"))
        item.setForeground(QColor("#ffffff"))
    elif priority == 4:
        item.setBackground(QColor("#72520f"))
        item.setForeground(QColor("#ffffff"))
    elif priority == 5:
        item.setBackground(QColor("#244a68"))
        item.setForeground(QColor("#ffffff"))
