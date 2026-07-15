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
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linuxeasyconfig.core.privileged.runner import PrivilegedRunner
from linuxeasyconfig.core.privileged.task import PrivilegedTask

from .repository import (
    RecoveryRepository,
    RecoveryRevision,
)


class _RestoreSignals(QObject):
    succeeded = Signal(str)
    failed = Signal(str)
    finished = Signal()


class _RestoreWorker(QRunnable):
    def __init__(
        self,
        revision: RecoveryRevision,
    ) -> None:
        super().__init__()
        self._revision = revision
        self.signals = _RestoreSignals()

    def run(self) -> None:
        try:
            task = PrivilegedTask(
                task_id="recovery.restore",
                arguments={
                    "module_id": (
                        self._revision.module_id
                    ),
                    "revision": (
                        self._revision.revision
                    ),
                    "destination": str(
                        self._revision.destination
                    ),
                    "backup_path": (
                        str(self._revision.backup_path)
                        if self._revision.backup_path
                        else ""
                    ),
                    "restore_mode": (
                        self._revision.restore_mode
                    ),
                },
            )

            message = PrivilegedRunner().run(task)
            self.signals.succeeded.emit(message)
        except Exception as exc:
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()


class RecoveryView(QWidget):
    """Review and restore LEC configuration revisions."""

    def __init__(
        self,
        repository: RecoveryRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._revisions: list[RecoveryRevision] = []
        self._selected: RecoveryRevision | None = None
        self._active_worker: _RestoreWorker | None = None
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(1)

        heading = QLabel("LEC Recovery")
        heading.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        description = QLabel(
            "Review files changed by Linux Easy Config and restore "
            "an earlier snapshot. Restoring a snapshot creates a new "
            "backup of the current state first."
        )
        description.setWordWrap(True)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            [
                "Time",
                "Module",
                "Operation",
                "Destination",
                "Revision",
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
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.itemSelectionChanged.connect(
            self._selection_changed
        )

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap
        )
        self._preview.setPlaceholderText(
            "Select a revision to inspect its backup."
        )

        splitter = QSplitter(
            Qt.Orientation.Vertical
        )
        splitter.addWidget(self._table)
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 330])

        self._status = QLabel()
        self._status.setWordWrap(True)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(
            self.reload
        )

        self._restore_button = QPushButton(
            "Revert To Selected Snapshot"
        )
        self._restore_button.setEnabled(False)
        self._restore_button.clicked.connect(
            self._begin_restore
        )

        buttons = QHBoxLayout()
        buttons.addWidget(self._status, 1)
        buttons.addWidget(refresh_button)
        buttons.addWidget(self._restore_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(description)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)

        self.reload()

    def reload(self) -> None:
        self._selected = None
        self._restore_button.setEnabled(False)
        self._preview.clear()

        self._revisions = (
            self._repository.revisions()
        )

        self._table.setSortingEnabled(False)
        self._table.setRowCount(
            len(self._revisions)
        )

        for row_number, revision in enumerate(
            self._revisions
        ):
            values = (
                revision.display_timestamp,
                _friendly_module_name(
                    revision.module_id
                ),
                revision.operation.title(),
                str(revision.destination),
                str(revision.revision),
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    revision.key,
                )
                self._table.setItem(
                    row_number,
                    column,
                    item,
                )

        self._table.setSortingEnabled(False)

        if self._revisions:
            self._status.setText(
                f"{len(self._revisions)} revisions available."
            )
            self._table.selectRow(0)
        else:
            self._status.setText(
                "No LEC revisions were found."
            )

    def _selection_changed(self) -> None:
        selected_rows = (
            self._table.selectionModel().selectedRows()
        )

        if not selected_rows:
            self._selected = None
            self._restore_button.setEnabled(False)
            self._preview.clear()
            return

        row = selected_rows[0].row()
        item = self._table.item(row, 0)

        if item is None:
            return

        key = item.data(
            Qt.ItemDataRole.UserRole
        )

        self._selected = next(
            (
                revision
                for revision in self._revisions
                if revision.key == key
            ),
            None,
        )

        if self._selected is None:
            self._restore_button.setEnabled(False)
            return

        self._preview.setPlainText(
            self._repository.preview_text(
                self._selected
            )
        )
        self._restore_button.setEnabled(
            self._selected.restore_mode
            in {"file", "delete"}
            and (
                self._selected.restore_mode == "delete"
                or self._selected.backup_available
            )
        )

    def _begin_restore(self) -> None:
        revision = self._selected

        if revision is None:
            return

        later = (
            self._repository.later_revisions_for_file(
                revision
            )
        )

        if later:
            warning = QMessageBox.warning(
                self,
                "Later Changes Will Be Reverted",
                (
                    f"{revision.destination} has "
                    f"{len(later)} later LEC modification"
                    f"{'s' if len(later) != 1 else ''}.\n\n"
                    "Restoring this snapshot will replace the current "
                    "file state and therefore undo all later changes "
                    "to this file.\n\n"
                    "Continue?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if warning != QMessageBox.StandardButton.Yes:
                return
        else:
            confirmation = QMessageBox.question(
                self,
                "Restore Selected Snapshot",
                (
                    f"Restore {revision.destination} to the state "
                    f"before revision {revision.revision}?\n\n"
                    "LEC will back up the current state before "
                    "restoring this snapshot."
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if (
                confirmation
                != QMessageBox.StandardButton.Yes
            ):
                return

        self._set_busy(True)

        worker = _RestoreWorker(revision)
        worker.signals.succeeded.connect(
            self._restore_succeeded
        )
        worker.signals.failed.connect(
            self._restore_failed
        )
        worker.signals.finished.connect(
            self._restore_finished
        )

        self._active_worker = worker
        self._thread_pool.start(worker)

    def _restore_succeeded(
        self,
        message: str,
    ) -> None:
        QMessageBox.information(
            self,
            "Snapshot Restored",
            message,
        )

    def _restore_failed(
        self,
        message: str,
    ) -> None:
        QMessageBox.critical(
            self,
            "Restore Failed",
            message,
        )

    def _restore_finished(self) -> None:
        self._active_worker = None
        self._set_busy(False)
        self.reload()

    def _set_busy(self, busy: bool) -> None:
        self._table.setEnabled(not busy)
        self._restore_button.setEnabled(
            not busy and self._selected is not None
        )
        self._restore_button.setText(
            "Restoring…"
            if busy
            else "Revert To Selected Snapshot"
        )


def _friendly_module_name(
    module_id: str,
) -> str:
    prefix = "org.linuxeasyconfig."

    if module_id.startswith(prefix):
        module_id = module_id[
            len(prefix):
        ]

    return module_id.replace(
        "_",
        " ",
    ).replace(
        "-",
        " ",
    ).title()
