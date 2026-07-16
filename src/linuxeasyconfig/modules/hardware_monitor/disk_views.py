from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
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

from .disk_health import load_disk_health_snapshot


class _Signals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _Worker(QRunnable):
    def __init__(
        self,
        task: PrivilegedTask,
        *,
        timeout: int,
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


class DiskHealthView(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._busy = False
        self._active_worker: _Worker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._disk_rows: list[dict[str, Any]] = []

        explanation = QLabel(
            "Physical-drive health reported by SMART and NVMe "
            "diagnostics. A passing result does not guarantee that "
            "a drive will not fail, so important data still needs "
            "reliable backups."
        )
        explanation.setWordWrap(True)

        self._dependency_status = QLabel()
        self._dependency_status.setWordWrap(True)

        self._install = QPushButton(
            "Install Disk Health Tools"
        )
        self._install.clicked.connect(
            self._install_tools
        )

        self._refresh = QPushButton(
            "Refresh Drive Health"
        )
        self._refresh.clicked.connect(
            self._refresh_health
        )

        setup = QGroupBox("Disk Health Tools")
        setup_layout = QHBoxLayout(setup)
        setup_layout.addWidget(
            self._dependency_status,
            1,
        )
        setup_layout.addWidget(self._install)
        setup_layout.addWidget(self._refresh)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            [
                "Device",
                "Model",
                "Type",
                "Capacity",
                "Health",
                "Temperature",
                "Remaining Life",
            ]
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
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

        self._detail_title = QLabel(
            "Select a physical drive"
        )
        self._detail_title.setStyleSheet(
            "font-size: 17px; font-weight: bold;"
        )

        self._serial = QLabel("—")
        self._transport = QLabel("—")
        self._power_hours = QLabel("—")
        self._self_test = QLabel("—")
        self._reallocated = QLabel("—")
        self._pending = QLabel("—")
        self._uncorrectable = QLabel("—")
        self._media_errors = QLabel("—")
        self._unsafe_shutdowns = QLabel("—")
        self._assessment = QLabel("—")
        self._assessment.setWordWrap(True)

        details = QGroupBox("Selected Drive Details")
        details_layout = QVBoxLayout(details)
        details_layout.addWidget(
            self._detail_title
        )

        form = QFormLayout()
        form.addRow("Serial number:", self._serial)
        form.addRow("Interface:", self._transport)
        form.addRow("Power-on hours:", self._power_hours)
        form.addRow(
            "Latest self-test:",
            self._self_test,
        )
        form.addRow(
            "Reallocated sectors:",
            self._reallocated,
        )
        form.addRow(
            "Pending sectors:",
            self._pending,
        )
        form.addRow(
            "Uncorrectable sectors:",
            self._uncorrectable,
        )
        form.addRow(
            "Media/data errors:",
            self._media_errors,
        )
        form.addRow(
            "Unsafe shutdowns:",
            self._unsafe_shutdowns,
        )
        form.addRow("Assessment:", self._assessment)
        details_layout.addLayout(form)

        self._enable_smart = QPushButton(
            "Enable SMART"
        )
        self._enable_smart.clicked.connect(
            self._enable_selected_smart
        )

        self._short_test = QPushButton(
            "Start Short Self-Test"
        )
        self._short_test.clicked.connect(
            lambda: self._start_test("short")
        )

        self._long_test = QPushButton(
            "Start Extended Self-Test"
        )
        self._long_test.clicked.connect(
            lambda: self._start_test("long")
        )

        action_layout = QHBoxLayout()
        action_layout.addWidget(
            self._enable_smart
        )
        action_layout.addStretch()
        action_layout.addWidget(
            self._short_test
        )
        action_layout.addWidget(
            self._long_test
        )
        details_layout.addLayout(action_layout)

        self._status = QLabel()
        self._status.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(explanation)
        layout.addWidget(setup)
        layout.addWidget(self._table, 1)
        layout.addWidget(details)
        layout.addWidget(self._status)

        self.reload()

    def reload(self) -> None:
        payload = load_disk_health_snapshot()
        dependencies = payload.get(
            "dependencies",
            {},
        )

        smartctl = bool(
            dependencies.get("smartctl", False)
        )
        nvme = bool(
            dependencies.get("nvme", False)
        )

        if smartctl and nvme:
            self._dependency_status.setText(
                "smartmontools and NVMe tools are installed."
            )
        elif smartctl:
            self._dependency_status.setText(
                "smartmontools is installed. NVMe tools are "
                "missing, so some NVMe-specific information "
                "may be unavailable."
            )
        else:
            self._dependency_status.setText(
                "Disk health tools are not installed."
            )

        self._install.setText(
            "Repair or Reinstall Tools"
            if smartctl
            else "Install Disk Health Tools"
        )
        self._refresh.setEnabled(
            smartctl and not self._busy
        )

        values = payload.get("disks", [])
        self._disk_rows = [
            value
            for value in values
            if isinstance(value, dict)
        ] if isinstance(values, list) else []

        self._table.setRowCount(0)

        for disk in self._disk_rows:
            row = self._table.rowCount()
            self._table.insertRow(row)

            remaining = disk.get(
                "remaining_life_percent"
            )
            temperature = disk.get(
                "temperature_c"
            )

            values = [
                str(disk.get("device", "Unknown")),
                str(disk.get("model", "Unknown")),
                str(disk.get("drive_type", "Unknown")),
                self._format_bytes(
                    disk.get("capacity_bytes")
                ),
                str(disk.get("health", "Unknown")),
                (
                    f"{float(temperature):.1f} °C"
                    if temperature is not None
                    else "Unavailable"
                ),
                (
                    f"{int(remaining)}%"
                    if remaining is not None
                    else "Not reported"
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(256, row)
                self._table.setItem(
                    row,
                    column,
                    item,
                )

        if self._disk_rows:
            self._status.setText(
                f"{len(self._disk_rows)} physical drive(s) "
                "reported. Select a drive for details."
            )
            self._table.selectRow(0)
        elif smartctl:
            self._status.setText(
                "No saved drive-health records are available. "
                "Select Refresh Drive Health."
            )
            self._clear_details()
        else:
            self._status.setText(
                "Install the disk health tools to begin."
            )
            self._clear_details()

        self._selection_changed()

    def _selected_disk(
        self,
    ) -> dict[str, Any] | None:
        row = self._table.currentRow()

        if not 0 <= row < len(self._disk_rows):
            return None

        return self._disk_rows[row]

    def _selection_changed(self) -> None:
        disk = self._selected_disk()

        if disk is None:
            self._clear_details()
            return

        self._detail_title.setText(
            f"{disk.get('model', 'Physical drive')} "
            f"({disk.get('device', '')})"
        )
        self._serial.setText(
            str(disk.get("serial", "Unknown"))
        )
        self._transport.setText(
            str(disk.get("transport", "Unknown"))
        )
        self._power_hours.setText(
            self._format_integer(
                disk.get("power_on_hours")
            )
        )
        self._self_test.setText(
            str(
                disk.get(
                    "self_test_status",
                    "Not reported",
                )
            )
        )
        self._reallocated.setText(
            self._format_integer(
                disk.get("reallocated_sectors")
            )
        )
        self._pending.setText(
            self._format_integer(
                disk.get("pending_sectors")
            )
        )
        self._uncorrectable.setText(
            self._format_integer(
                disk.get("uncorrectable_sectors")
            )
        )
        self._media_errors.setText(
            self._format_integer(
                disk.get("media_errors")
            )
        )
        self._unsafe_shutdowns.setText(
            self._format_integer(
                disk.get("unsafe_shutdowns")
            )
        )
        self._assessment.setText(
            str(disk.get("assessment", "Unknown"))
        )

        supported = bool(
            disk.get("smart_supported", False)
        )
        enabled = bool(
            disk.get("smart_enabled", False)
        )
        self._enable_smart.setVisible(
            supported and not enabled
        )
        self._enable_smart.setEnabled(
            not self._busy
        )
        self._short_test.setEnabled(
            supported and enabled and not self._busy
        )
        self._long_test.setEnabled(
            supported and enabled and not self._busy
        )

    def _clear_details(self) -> None:
        self._detail_title.setText(
            "Select a physical drive"
        )

        for label in (
            self._serial,
            self._transport,
            self._power_hours,
            self._self_test,
            self._reallocated,
            self._pending,
            self._uncorrectable,
            self._media_errors,
            self._unsafe_shutdowns,
            self._assessment,
        ):
            label.setText("—")

        self._enable_smart.setVisible(False)
        self._short_test.setEnabled(False)
        self._long_test.setEnabled(False)

    def _install_tools(self) -> None:
        self._run_task(
            "hardware_monitor.install_disk_health_tools",
            {},
            "Disk Health Tools Installed",
            timeout=1000,
        )

    def _refresh_health(self) -> None:
        self._run_task(
            "hardware_monitor.refresh_disk_health",
            {},
            "Disk Health Refreshed",
            timeout=180,
        )

    def _enable_selected_smart(self) -> None:
        disk = self._selected_disk()
        if disk is None:
            return

        self._run_task(
            "hardware_monitor.enable_smart",
            {
                "device": str(
                    disk.get("device", "")
                )
            },
            "SMART Enabled",
            timeout=180,
        )

    def _start_test(
        self,
        test_type: str,
    ) -> None:
        disk = self._selected_disk()
        if disk is None:
            return

        label = (
            "extended"
            if test_type == "long"
            else "short"
        )

        response = QMessageBox.question(
            self,
            "Start Drive Self-Test",
            (
                f"Start the {label} self-test on "
                f"{disk.get('device', '')}?\n\n"
                "The drive performs the test in the background. "
                "An extended test may take several hours."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._run_task(
            "hardware_monitor.start_self_test",
            {
                "device": str(
                    disk.get("device", "")
                ),
                "test_type": test_type,
            },
            "Drive Self-Test Started",
            timeout=180,
        )

    def _run_task(
        self,
        task_id: str,
        arguments: dict[str, Any],
        title: str,
        *,
        timeout: int,
    ) -> None:
        if self._busy:
            return

        self._busy = True
        self._set_controls_enabled(False)

        worker = _Worker(
            PrivilegedTask(
                task_id=task_id,
                arguments=arguments,
            ),
            timeout=timeout,
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

    def _failed(self, message: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(
            "Disk Health Operation Failed"
        )
        dialog.resize(720, 440)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(message)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(dialog.reject)

        layout = QVBoxLayout(dialog)
        layout.addWidget(text, 1)
        layout.addWidget(buttons)
        dialog.exec()

    def _finished(self) -> None:
        self._active_worker = None
        self._busy = False
        self.reload()
        self._set_controls_enabled(True)

    def _set_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        self._install.setEnabled(enabled)
        self._refresh.setEnabled(enabled)
        self._table.setEnabled(enabled)
        self._selection_changed()

    @staticmethod
    def _format_integer(value: Any) -> str:
        if value is None:
            return "Not reported"

        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_bytes(value: Any) -> str:
        if value is None:
            return "Unknown"

        try:
            amount = float(value)
        except (TypeError, ValueError):
            return "Unknown"

        units = ("B", "KB", "MB", "GB", "TB", "PB")

        for unit in units:
            if amount < 1000 or unit == units[-1]:
                return (
                    f"{amount:.0f} {unit}"
                    if unit == "B"
                    else f"{amount:.1f} {unit}"
                )
            amount /= 1000

        return f"{amount:.1f} PB"
