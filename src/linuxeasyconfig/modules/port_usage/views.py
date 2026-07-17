from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import PortUsageRepository


class PortUsageView(QWidget):
    def __init__(
        self,
        repository: PortUsageRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository

        heading = QLabel("Port Usage")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Every listening TCP and UDP port detected on this "
            "machine, correlated with applications, Docker, the "
            "firewall, and Reverse Proxy rules."
        )
        description.setWordWrap(True)

        self._summary = QLabel()
        self._summary.setWordWrap(True)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText(
            "Filter by port, application, address, hostname, or exposure…"
        )
        self._filter.textChanged.connect(
            self._apply_filter
        )

        self._only_warnings = QCheckBox(
            "Show only uncertain or potentially exposed ports"
        )
        self._only_warnings.toggled.connect(
            self._apply_filter
        )

        install = QPushButton(
            "Install or Repair Port Monitor"
        )
        install.clicked.connect(
            self._install_monitor
        )

        refresh = QPushButton("Refresh Now")
        refresh.clicked.connect(
            self._refresh_now
        )

        controls = QHBoxLayout()
        controls.addWidget(self._filter, 1)
        controls.addWidget(self._only_warnings)
        controls.addWidget(refresh)
        controls.addWidget(install)

        self._table = QTableWidget(0, 12)
        self._table.setHorizontalHeaderLabels(
            [
                "Protocol",
                "Bind Address",
                "Internal Port",
                "Application",
                "Service / Container",
                "Application Scope",
                "Firewall",
                "Caddy Hostname",
                "Caddy Path",
                "External Port",
                "Port Translation",
                "Overall Exposure",
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
        self._table.setWordWrap(True)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)

        widths = [
            80, 150, 100, 180, 170, 150,
            160, 220, 120, 100, 230, 220,
        ]
        for index, width in enumerate(widths):
            self._table.setColumnWidth(index, width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(self._summary)
        layout.addLayout(controls)
        layout.addWidget(self._table, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(30000)
        self._timer.timeout.connect(self.reload)
        self._timer.start()

        self.reload()

    def reload(self) -> None:
        snapshot = self._repository.snapshot()
        rows = snapshot.get("rows", [])

        if not isinstance(rows, list):
            rows = []

        generated = str(
            snapshot.get("generated_at", "")
        )
        monitor = self._repository.monitor_status()
        summary = snapshot.get("summary", {})

        if isinstance(summary, dict):
            self._summary.setText(
                f"Monitor: {monitor}   •   "
                f"Listening sockets: {summary.get('listening_sockets', 0)}   •   "
                f"LAN accessible: {summary.get('lan_accessible', 0)}   •   "
                f"Through Caddy: {summary.get('caddy_exposed', 0)}   •   "
                f"Potential direct exposure: "
                f"{summary.get('potentially_direct', 0)}   •   "
                f"Last snapshot: {generated or 'Never'}"
            )

        self._table.setRowCount(0)

        for item in rows:
            if not isinstance(item, dict):
                continue

            service_or_container = (
                str(item.get("container_name", ""))
                or str(item.get("service_name", ""))
            )
            hostnames = ", ".join(
                str(value)
                for value in item.get(
                    "proxy_hostnames",
                    [],
                )
            )
            paths = ", ".join(
                str(value)
                for value in item.get(
                    "proxy_paths",
                    [],
                )
            )
            public_ports = ", ".join(
                str(value)
                for value in item.get(
                    "public_ports",
                    [],
                )
            )
            translation = str(
                item.get("docker_mapping", "")
            )

            values = (
                str(item.get("protocol", "")).upper(),
                str(item.get("bind_address", "")),
                str(item.get("port", "")),
                str(item.get("application", "")),
                service_or_container,
                str(item.get("scope", "")),
                str(item.get("firewall_status", "")),
                hostnames,
                paths,
                public_ports,
                translation,
                str(item.get("overall_exposure", "")),
            )

            row = self._table.rowCount()
            self._table.insertRow(row)

            tooltip = "\n".join(
                value
                for value in (
                    str(item.get("command", "")),
                    str(item.get("firewall_detail", "")),
                    str(item.get("proxy_detail", "")),
                )
                if value
            )

            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(tooltip)
                self._table.setItem(
                    row,
                    column,
                    cell,
                )

        self._apply_filter()

    def _apply_filter(self) -> None:
        needle = self._filter.text().strip().lower()
        warnings_only = self._only_warnings.isChecked()

        for row in range(self._table.rowCount()):
            combined = " ".join(
                (
                    self._table.item(row, column).text()
                    if self._table.item(row, column)
                    else ""
                )
                for column in range(
                    self._table.columnCount()
                )
            ).lower()

            warning = any(
                phrase in combined
                for phrase in (
                    "potentially directly exposed",
                    "exposure uncertain",
                    "firewall inactive",
                    "unmanaged/unknown",
                )
            )

            visible = (
                (not needle or needle in combined)
                and (not warnings_only or warning)
            )
            self._table.setRowHidden(
                row,
                not visible,
            )

    def _install_monitor(self) -> None:
        self._run_task(
            "port_usage.install_monitor",
            "Port Monitor Installed",
        )

    def _refresh_now(self) -> None:
        self._run_task(
            "port_usage.refresh",
            "Port Usage Refreshed",
        )

    def _run_task(
        self,
        task_id: str,
        title: str,
    ) -> None:
        try:
            result = PrivilegedRunner().run(
                PrivilegedTask(
                    task_id,
                    {},
                ),
                timeout=180,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Port Usage Operation Failed",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            title,
            str(result),
        )
        self.reload()
