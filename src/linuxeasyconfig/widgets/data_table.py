from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import (
    QItemSelectionModel,
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from linuxeasyconfig.core.table_actions import TableAction
from linuxeasyconfig.core.table_provider import TableDataProvider
from linuxeasyconfig.widgets.action_bar import ActionBar


class _RefreshSignals(QObject):
    succeeded = Signal(object, str)
    failed = Signal(str)
    finished = Signal()


class _RefreshWorker(QRunnable):
    """Run provider refresh work outside Qt's main UI thread."""

    def __init__(self, provider: TableDataProvider) -> None:
        super().__init__()
        self._provider = provider
        self.signals = _RefreshSignals()

    def run(self) -> None:
        try:
            self._provider.refresh()
            rows = self._provider.rows()

            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                raise TypeError("Provider returned invalid rows.")

            copied_rows = [
                dict(row)
                for row in rows
                if isinstance(row, dict)
            ]

            try:
                status_text = self._provider.status_text()
            except Exception:
                status_text = f"{len(copied_rows)} items"

            self._safe_emit(self.signals.succeeded, copied_rows, status_text)
        except Exception as exc:
            self._safe_emit(self.signals.failed, str(exc))
        finally:
            self._safe_emit(self.signals.finished)

    @staticmethod
    def _safe_emit(signal: Any, *args: Any) -> None:
        try:
            signal.emit(*args)
        except RuntimeError:
            pass


class _ActionSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _ActionWorker(QRunnable):
    """Execute a provider action outside Qt's main UI thread."""

    def __init__(
        self,
        provider: TableDataProvider,
        action_id: str,
        row: dict[str, Any],
    ) -> None:
        super().__init__()
        self._provider = provider
        self._action_id = action_id
        self._row = dict(row)
        self.signals = _ActionSignals()

    def run(self) -> None:
        try:
            message = self._provider.execute_action(
                self._action_id,
                self._row,
            )
            self._safe_emit(self.signals.succeeded, str(message))
        except Exception as exc:
            self._safe_emit(self.signals.failed, str(exc))
        finally:
            self._safe_emit(self.signals.finished)

    @staticmethod
    def _safe_emit(signal: Any, *args: Any) -> None:
        try:
            signal.emit(*args)
        except RuntimeError:
            pass


class DataTable(QWidget):
    """Searchable, refreshable table backed by a TableDataProvider."""

    def __init__(
        self,
        provider: TableDataProvider,
        *,
        selectable: bool = True,
        sortable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._provider = provider
        self._columns = tuple(provider.columns())
        self._rows: list[dict[str, Any]] = []
        self._sortable = sortable
        self._refresh_in_progress = False
        self._action_in_progress = False
        self._closing = False
        self._active_refresh_worker: _RefreshWorker | None = None
        self._active_action_worker: _ActionWorker | None = None
        self._current_actions: dict[str, TableAction] = {}

        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(2)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search…")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.textChanged.connect(self._apply_filter)

        self._refresh_button = QPushButton("Refresh")
        self._refresh_button.clicked.connect(self.reload)

        refresh_interval = provider.refresh_interval_ms
        auto_refresh_enabled = (
            refresh_interval is not None
            and refresh_interval > 0
        )

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(self._search_box, 1)

        if not auto_refresh_enabled:
            controls_layout.addWidget(self._refresh_button)
        else:
            self._refresh_button.hide()

        self._table = QTableWidget()
        self._table.setColumnCount(len(self._columns))
        self._table.setHorizontalHeaderLabels(
            [
                str(column.get("title", column.get("id", "")))
                for column in self._columns
            ]
        )

        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(False)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        if selectable:
            self._table.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )
        else:
            self._table.setSelectionMode(
                QAbstractItemView.SelectionMode.NoSelection
            )

        self._table.itemSelectionChanged.connect(
            self._update_actions_for_selection
        )

        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)

        for index, column in enumerate(self._columns):
            resize_mode = column.get("resize", "contents")

            if resize_mode == "stretch":
                header.setSectionResizeMode(
                    index,
                    QHeaderView.ResizeMode.Stretch,
                )
            elif resize_mode == "fixed":
                header.setSectionResizeMode(
                    index,
                    QHeaderView.ResizeMode.Fixed,
                )

                width = column.get("width")
                if isinstance(width, int):
                    self._table.setColumnWidth(index, width)
            else:
                header.setSectionResizeMode(
                    index,
                    QHeaderView.ResizeMode.ResizeToContents,
                )

        self._action_bar = ActionBar()
        self._action_bar.action_requested.connect(
            self._on_action_requested
        )

        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: palette(mid);")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(controls_layout)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._action_bar)
        layout.addWidget(self._status_label)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.reload)

        if auto_refresh_enabled:
            self._timer.start(refresh_interval)

        self.reload()

    def reload(self) -> None:
        """Refresh provider data without blocking the interface."""

        if (
            self._closing
            or self._refresh_in_progress
            or self._action_in_progress
        ):
            return

        self._refresh_in_progress = True
        self._refresh_button.setEnabled(False)

        if not self._rows:
            self._status_label.setText("Loading…")

        worker = _RefreshWorker(self._provider)
        worker.signals.succeeded.connect(self._refresh_succeeded)
        worker.signals.failed.connect(self._refresh_failed)
        worker.signals.finished.connect(self._refresh_finished)

        self._active_refresh_worker = worker
        self._thread_pool.start(worker)

    def selected_row_data(self) -> dict[str, Any] | None:
        """Return the complete provider row for the current selection."""

        selected_id = self._selected_row_id()

        if selected_id is None:
            return None

        for row in self._rows:
            if str(row.get("_id", "")) == selected_id:
                return dict(row)

        return None

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop scheduled updates before the table is destroyed."""

        self._closing = True
        self._timer.stop()
        self._thread_pool.waitForDone(1500)

        super().closeEvent(event)

    def _refresh_succeeded(
        self,
        rows: object,
        status_text: str,
    ) -> None:
        if self._closing:
            return

        if not isinstance(rows, list):
            self._status_label.setText(
                "Refresh failed: invalid worker result."
            )
            return

        selected_id = self._selected_row_id()
        vertical_scroll = self._table.verticalScrollBar().value()
        horizontal_scroll = self._table.horizontalScrollBar().value()
        self._rows = rows

        sorting_enabled = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)

        self._table.clearContents()
        self._table.setRowCount(len(self._rows))

        for row_index, row in enumerate(self._rows):
            row_id = str(row.get("_id", ""))

            for column_index, column in enumerate(self._columns):
                column_id = str(column.get("id", ""))
                value = row.get(column_id, "")

                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole + 1, row_id)

                alignment = column.get("alignment")
                if alignment == "center":
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                elif alignment == "right":
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                sort_value = row.get(f"{column_id}_sort")
                if sort_value is not None:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        sort_value,
                    )

                self._table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self._table.setSortingEnabled(
            sorting_enabled or self._sortable
        )

        self._status_label.setText(status_text)
        self._apply_filter(self._search_box.text())

        if selected_id:
            self._restore_selection(selected_id)

        self._table.verticalScrollBar().setValue(vertical_scroll)
        self._table.horizontalScrollBar().setValue(horizontal_scroll)
        self._update_actions_for_selection()

    def _refresh_failed(self, message: str) -> None:
        if not self._closing:
            self._status_label.setText(f"Refresh failed: {message}")

    def _refresh_finished(self) -> None:
        self._refresh_in_progress = False

        if not self._closing:
            self._refresh_button.setEnabled(True)

        self._active_refresh_worker = None

    def _update_actions_for_selection(self) -> None:
        row = self.selected_row_data()

        try:
            actions = tuple(self._provider.actions_for_row(row))
        except Exception as exc:
            self._current_actions = {}
            self._action_bar.set_actions(())
            self._status_label.setText(
                f"Could not load actions: {exc}"
            )
            return

        self._current_actions = {
            action.id: action
            for action in actions
        }
        self._action_bar.set_actions(actions)
        self._action_bar.set_all_enabled(
            not self._action_in_progress
        )

    def _on_action_requested(self, action_id: str) -> None:
        if self._closing or self._action_in_progress:
            return

        action = self._current_actions.get(action_id)
        row = self.selected_row_data()

        if action is None or row is None or not action.enabled:
            return

        if action.confirmation_message:
            title = action.confirmation_title or "Confirm Action"
            response = QMessageBox.question(
                self,
                title,
                action.confirmation_message,
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if response != QMessageBox.StandardButton.Yes:
                return

        self._action_in_progress = True
        self._action_bar.set_all_enabled(False)
        self._refresh_button.setEnabled(False)
        self._status_label.setText(f"{action.label} in progress…")

        worker = _ActionWorker(
            self._provider,
            action_id,
            row,
        )
        worker.signals.succeeded.connect(self._action_succeeded)
        worker.signals.failed.connect(self._action_failed)
        worker.signals.finished.connect(self._action_finished)

        self._active_action_worker = worker
        self._thread_pool.start(worker)

    def _action_succeeded(self, message: str) -> None:
        if self._closing:
            return

        self._status_label.setText(
            message or "Action completed successfully."
        )

    def _action_failed(self, message: str) -> None:
        if self._closing:
            return

        QMessageBox.critical(
            self,
            "Action Failed",
            message,
        )
        self._status_label.setText(f"Action failed: {message}")

    def _action_finished(self) -> None:
        self._action_in_progress = False
        self._active_action_worker = None

        if self._closing:
            return

        self._refresh_button.setEnabled(True)
        self._update_actions_for_selection()
        self.reload()

    def _apply_filter(self, text: str) -> None:
        query = text.strip().casefold()
        visible_count = 0

        for row_index in range(self._table.rowCount()):
            values: list[str] = []

            for column_index in range(self._table.columnCount()):
                item = self._table.item(row_index, column_index)
                if item is not None:
                    values.append(item.text().casefold())

            matches = not query or any(
                query in value for value in values
            )

            self._table.setRowHidden(row_index, not matches)

            if matches:
                visible_count += 1

        if query:
            self._status_label.setText(
                f"{visible_count} of {len(self._rows)} items shown"
            )

    def _selected_row_id(self) -> str | None:
        selected_rows = self._table.selectionModel().selectedRows()

        if not selected_rows:
            return None

        row_index = selected_rows[0].row()
        item = self._table.item(row_index, 0)

        if item is None:
            return None

        row_id = item.data(Qt.ItemDataRole.UserRole + 1)
        return str(row_id) if row_id else None

    def _restore_selection(self, row_id: str) -> None:
        selection_model = self._table.selectionModel()

        if selection_model is None:
            return

        for row_index in range(self._table.rowCount()):
            item = self._table.item(row_index, 0)

            if item is None:
                continue

            item_row_id = item.data(
                Qt.ItemDataRole.UserRole + 1
            )

            if str(item_row_id) == row_id:
                index = self._table.model().index(row_index, 0)
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                self._table.setCurrentIndex(index)
                return
