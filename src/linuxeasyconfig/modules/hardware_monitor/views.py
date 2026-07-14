from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .collector import HardwareCollector


class _SampleSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class _SampleWorker(QRunnable):
    def __init__(self, collector: HardwareCollector) -> None:
        super().__init__()
        self._collector = collector
        self.signals = _SampleSignals()

    def run(self) -> None:
        try:
            sample = self._collector.sample()
            self.signals.succeeded.emit(sample)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class HardwareMonitorView(QWidget):
    """Live, display-only hardware dashboard."""

    def __init__(
        self,
        collector: HardwareCollector,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._collector = collector
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)
        self._sample_in_progress = False

        self._cpu_overall = QLabel("Loading…")
        self._cpu_frequency = QLabel("Loading…")
        self._cpu_cores_container = QWidget()
        self._cpu_cores_layout = QGridLayout(
            self._cpu_cores_container
        )
        self._cpu_cores_layout.setContentsMargins(0, 0, 0, 0)
        self._cpu_core_labels: list[QLabel] = []

        self._ram = QLabel("Loading…")
        self._swap = QLabel("Loading…")

        self._network_container = QWidget()
        self._network_layout = QFormLayout(
            self._network_container
        )
        self._network_layout.setContentsMargins(0, 0, 0, 0)
        self._network_labels: list[QLabel] = []

        self._disk_io = QLabel("Loading…")

        self._filesystems_container = QWidget()
        self._filesystems_layout = QFormLayout(
            self._filesystems_container
        )
        self._filesystems_layout.setContentsMargins(0, 0, 0, 0)
        self._filesystem_labels: list[QLabel] = []

        self._temperatures_container = QWidget()
        self._temperatures_layout = QFormLayout(
            self._temperatures_container
        )
        self._temperatures_layout.setContentsMargins(0, 0, 0, 0)
        self._temperature_labels: list[QLabel] = []

        self._graphics_container = QWidget()
        self._graphics_layout = QVBoxLayout(
            self._graphics_container
        )
        self._graphics_layout.setContentsMargins(0, 0, 0, 0)
        self._graphics_widgets: list[QWidget] = []

        heading = QLabel("Hardware Monitor")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Live hardware statistics updated once per second."
        )
        description.setWordWrap(True)

        dashboard = QWidget()
        dashboard_layout = QGridLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setHorizontalSpacing(16)
        dashboard_layout.setVerticalSpacing(16)

        dashboard_layout.addWidget(
            self._build_cpu_group(),
            0,
            0,
        )
        dashboard_layout.addWidget(
            self._build_memory_group(),
            0,
            1,
        )
        dashboard_layout.addWidget(
            self._build_network_group(),
            1,
            0,
        )
        dashboard_layout.addWidget(
            self._build_storage_group(),
            1,
            1,
        )
        dashboard_layout.addWidget(
            self._build_graphics_group(),
            2,
            0,
        )
        dashboard_layout.addWidget(
            self._build_temperature_group(),
            2,
            1,
        )

        dashboard_layout.setColumnStretch(0, 1)
        dashboard_layout.setColumnStretch(1, 1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(dashboard)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(heading)
        # layout.addWidget(description)
        layout.addWidget(scroll_area, 1)

        self._status = QLabel()
        self._status.setStyleSheet("color: palette(mid);")
        layout.addWidget(self._status)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._request_sample)
        self._timer.start(1000)

        self._request_sample()

    def _build_cpu_group(self) -> QGroupBox:
        group = QGroupBox("CPU")
        layout = QVBoxLayout(group)

        summary = QFormLayout()
        summary.addRow("Overall:", self._cpu_overall)
        summary.addRow("Frequency:", self._cpu_frequency)

        layout.addLayout(summary)
        layout.addWidget(self._cpu_cores_container)

        return group

    def _build_memory_group(self) -> QGroupBox:
        group = QGroupBox("Memory")
        layout = QFormLayout(group)
        layout.addRow("RAM:", self._ram)
        layout.addRow("Swap:", self._swap)
        return group

    def _build_network_group(self) -> QGroupBox:
        group = QGroupBox("Network")
        layout = QVBoxLayout(group)
        layout.addWidget(self._network_container)
        return group

    def _build_storage_group(self) -> QGroupBox:
        group = QGroupBox("Storage")
        layout = QVBoxLayout(group)

        io_layout = QFormLayout()
        io_layout.addRow("Disk activity:", self._disk_io)

        layout.addLayout(io_layout)
        layout.addWidget(self._filesystems_container)
        return group

    def _build_graphics_group(self) -> QGroupBox:
        group = QGroupBox("Graphics")
        layout = QVBoxLayout(group)
        layout.addWidget(self._graphics_container)
        return group

    def _build_temperature_group(self) -> QGroupBox:
        group = QGroupBox("Temperatures")
        layout = QVBoxLayout(group)
        layout.addWidget(self._temperatures_container)
        return group

    def _request_sample(self) -> None:
        if self._sample_in_progress:
            return

        self._sample_in_progress = True

        worker = _SampleWorker(self._collector)
        worker.signals.succeeded.connect(self._sample_succeeded)
        worker.signals.failed.connect(self._sample_failed)
        worker.signals.finished.connect(self._sample_finished)

        self._thread_pool.start(worker)

    def _sample_succeeded(self, sample: object) -> None:
        if not isinstance(sample, dict):
            self._status.setText("Invalid hardware sample.")
            return

        section_updates = (
            ("CPU", lambda: self._update_cpu(sample.get("cpu", {}))),
            (
                "Memory",
                lambda: self._update_memory(sample.get("memory", {})),
            ),
            (
                "Network",
                lambda: self._update_network(sample.get("network", [])),
            ),
            (
                "Storage",
                lambda: self._update_storage(
                    sample.get("disk_io", {}),
                    sample.get("filesystems", []),
                ),
            ),
            (
                "Graphics",
                lambda: self._update_graphics(
                    sample.get("gpus", [])
                ),
            ),
            (
                "Temperatures",
                lambda: self._update_temperatures(
                    sample.get("temperatures", [])
                ),
            ),
        )

        errors: list[str] = []

        for section_name, update in section_updates:
            try:
                update()
            except Exception as exc:
                errors.append(f"{section_name}: {exc}")

        if errors:
            self._status.setText(
                "Some sections could not be updated: "
                + "; ".join(errors)
            )
        else:
            self._status.setText("Updated just now")

    def _sample_failed(self, message: str) -> None:
        self._status.setText(
            f"Hardware update failed: {message}"
        )

    def _sample_finished(self) -> None:
        self._sample_in_progress = False

    def _update_cpu(self, cpu: Any) -> None:
        if not isinstance(cpu, dict):
            return

        overall = float(cpu.get("overall_percent", 0.0))
        frequency = cpu.get("frequency_mhz")

        self._cpu_overall.setText(f"{overall:.1f}%")

        if frequency is None:
            self._cpu_frequency.setText("Unavailable")
        else:
            self._cpu_frequency.setText(
                self._format_frequency(float(frequency))
            )

        per_core = cpu.get("per_core_percent", [])

        if not isinstance(per_core, list):
            per_core = []

        self._ensure_core_labels(len(per_core))

        for index, percent in enumerate(per_core):
            self._cpu_core_labels[index].setText(
                f"Core {index + 1}: {float(percent):.1f}%"
            )

    def _update_memory(self, memory: Any) -> None:
        if not isinstance(memory, dict):
            return

        ram = memory.get("ram", {})
        swap = memory.get("swap", {})

        if isinstance(ram, dict):
            self._ram.setText(
                self._format_usage(
                    ram.get("used", 0),
                    ram.get("total", 0),
                    ram.get("percent", 0),
                )
            )

        if isinstance(swap, dict):
            self._swap.setText(
                self._format_usage(
                    swap.get("used", 0),
                    swap.get("total", 0),
                    swap.get("percent", 0),
                )
            )

    def _update_network(self, network: Any) -> None:
        rows = network if isinstance(network, list) else []
        self._clear_form_rows(
            self._network_layout,
            self._network_labels,
        )

        if not rows:
            label = QLabel("No active interfaces")
            self._network_layout.addRow(label)
            self._network_labels.append(label)
            return

        for interface in rows:
            if not isinstance(interface, dict):
                continue

            name = str(interface.get("name", "Unknown"))
            receive = self._format_rate(
                interface.get("receive_rate", 0)
            )
            send = self._format_rate(
                interface.get("send_rate", 0)
            )

            value = QLabel(f"↓ {receive}   ↑ {send}")
            self._network_layout.addRow(f"{name}:", value)
            self._network_labels.append(value)

    def _update_storage(
        self,
        disk_io: Any,
        filesystems: Any,
    ) -> None:
        if isinstance(disk_io, dict):
            read_rate = self._format_rate(
                disk_io.get("read_rate", 0)
            )
            write_rate = self._format_rate(
                disk_io.get("write_rate", 0)
            )
            self._disk_io.setText(
                f"Read {read_rate}   Write {write_rate}"
            )

        rows = (
            filesystems
            if isinstance(filesystems, list)
            else []
        )

        self._clear_form_rows(
            self._filesystems_layout,
            self._filesystem_labels,
        )

        if not rows:
            label = QLabel("No filesystems available")
            self._filesystems_layout.addRow(label)
            self._filesystem_labels.append(label)
            return

        for filesystem in rows:
            if not isinstance(filesystem, dict):
                continue

            mountpoint = str(
                filesystem.get("mountpoint", "Unknown")
            )
            value = QLabel(
                self._format_usage(
                    filesystem.get("used", 0),
                    filesystem.get("total", 0),
                    filesystem.get("percent", 0),
                )
            )

            self._filesystems_layout.addRow(
                f"{mountpoint}:",
                value,
            )
            self._filesystem_labels.append(value)

    def _update_graphics(self, gpus: Any) -> None:
        rows = gpus if isinstance(gpus, list) else []

        while self._graphics_layout.count():
            item = self._graphics_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self._graphics_widgets.clear()

        if not rows:
            label = QLabel("No graphics devices detected")
            self._graphics_layout.addWidget(label)
            self._graphics_widgets.append(label)
            return

        for index, gpu in enumerate(rows):
            if not isinstance(gpu, dict):
                continue

            if index:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                self._graphics_layout.addWidget(line)
                self._graphics_widgets.append(line)

            name = QLabel(str(gpu.get("name", "Graphics device")))
            name.setStyleSheet("font-weight: bold;")
            name.setWordWrap(True)
            self._graphics_layout.addWidget(name)
            self._graphics_widgets.append(name)

            form_widget = QWidget()
            form = QFormLayout(form_widget)
            form.setContentsMargins(0, 0, 0, 0)

            form.addRow(
                "Driver:",
                QLabel(str(gpu.get("driver", "Unknown"))),
            )

            status = str(gpu.get("status", "unsupported"))

            if status == "ok":
                self._add_optional_gpu_row(
                    form,
                    "GPU utilization:",
                    gpu.get("utilization_percent"),
                    "%",
                )
                self._add_optional_gpu_row(
                    form,
                    "Render engine:",
                    gpu.get("render_percent"),
                    "%",
                )
                self._add_optional_gpu_row(
                    form,
                    "Video engine:",
                    gpu.get("video_percent"),
                    "%",
                )
                self._add_optional_gpu_row(
                    form,
                    "Copy engine:",
                    gpu.get("copy_percent"),
                    "%",
                )
                self._add_optional_gpu_row(
                    form,
                    "GPU frequency:",
                    gpu.get("frequency_mhz"),
                    " MHz",
                )
                self._add_optional_gpu_row(
                    form,
                    "Temperature:",
                    gpu.get("temperature_c"),
                    " °C",
                )
                self._add_optional_gpu_row(
                    form,
                    "Power:",
                    gpu.get("power_w"),
                    " W",
                )

                used = gpu.get("memory_used_bytes")
                total = gpu.get("memory_total_bytes")

                if used is not None and total is not None:
                    form.addRow(
                        f"{gpu.get('memory_type', 'Memory')}:",
                        QLabel(
                            f"{self._format_bytes(float(used))} / "
                            f"{self._format_bytes(float(total))}"
                        ),
                    )
                elif gpu.get("memory_type"):
                    form.addRow(
                        "Memory:",
                        QLabel(str(gpu["memory_type"])),
                    )
            else:
                message = QLabel(
                    str(
                        gpu.get(
                            "message",
                            "Detailed GPU monitoring is unavailable.",
                        )
                    )
                )
                message.setWordWrap(True)
                form.addRow(message)

                install_command = gpu.get("install_command")

                if install_command:
                    command = QLabel(
                        f"<code>{install_command}</code>"
                    )
                    command.setWordWrap(True)
                    command.setTextInteractionFlags(
                        command.textInteractionFlags()
                        | Qt.TextInteractionFlag.TextSelectableByMouse
                    )
                    form.addRow("Run:", command)

                additional_note = gpu.get("additional_note")

                if additional_note:
                    note = QLabel(str(additional_note))
                    note.setWordWrap(True)
                    form.addRow(note)

            self._graphics_layout.addWidget(form_widget)
            self._graphics_widgets.append(form_widget)

    @staticmethod
    def _add_optional_gpu_row(
        form: QFormLayout,
        title: str,
        value: Any,
        suffix: str,
    ) -> None:
        if value is None:
            return

        form.addRow(
            title,
            QLabel(f"{float(value):.1f}{suffix}"),
        )

    def _update_temperatures(
        self,
        temperatures: Any,
    ) -> None:
        rows = (
            temperatures
            if isinstance(temperatures, list)
            else []
        )

        self._clear_form_rows(
            self._temperatures_layout,
            self._temperature_labels,
        )

        if not rows:
            label = QLabel("No temperature sensors available")
            self._temperatures_layout.addRow(label)
            self._temperature_labels.append(label)
            return

        for reading in rows:
            if not isinstance(reading, dict):
                continue

            group = str(reading.get("group", "sensor"))
            label_text = str(reading.get("label", "Sensor"))
            current = reading.get("current")

            if current is None:
                value_text = "Unavailable"
            else:
                value_text = f"{float(current):.1f} °C"

            value = QLabel(value_text)
            self._temperatures_layout.addRow(
                f"{group} — {label_text}:",
                value,
            )
            self._temperature_labels.append(value)

    def _ensure_core_labels(self, count: int) -> None:
        while len(self._cpu_core_labels) < count:
            label = QLabel()
            label.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )

            index = len(self._cpu_core_labels)
            row = index // 2
            column = index % 2

            self._cpu_cores_layout.addWidget(
                label,
                row,
                column,
            )
            self._cpu_core_labels.append(label)

        while len(self._cpu_core_labels) > count:
            label = self._cpu_core_labels.pop()
            self._cpu_cores_layout.removeWidget(label)
            label.deleteLater()

    @staticmethod
    def _clear_form_rows(
        layout: QFormLayout,
        labels: list[QLabel],
    ) -> None:
        while layout.rowCount():
            layout.removeRow(0)

        labels.clear()

    @staticmethod
    def _format_usage(
        used: Any,
        total: Any,
        percent: Any,
    ) -> str:
        return (
            f"{HardwareMonitorView._format_bytes(float(used))} / "
            f"{HardwareMonitorView._format_bytes(float(total))} "
            f"({float(percent):.1f}%)"
        )

    @staticmethod
    def _format_rate(value: Any) -> str:
        return (
            f"{HardwareMonitorView._format_bytes(float(value))}/s"
        )

    @staticmethod
    def _format_frequency(mhz: float) -> str:
        if mhz >= 1000:
            return f"{mhz / 1000:.2f} GHz"

        return f"{mhz:.0f} MHz"

    @staticmethod
    def _format_bytes(value: float) -> str:
        units = ("B", "KB", "MB", "GB", "TB")
        amount = max(value, 0.0)

        for unit in units:
            if amount < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{amount:.0f} {unit}"

                return f"{amount:.1f} {unit}"

            amount /= 1024

        return f"{amount:.1f} TB"
