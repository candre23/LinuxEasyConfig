from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from linuxeasyconfig.core.table_actions import TableAction


class ActionBar(QWidget):
    """Reusable action bar arranged in rows without affecting window width."""

    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}
        self._base_enabled: dict[str, bool] = {}

        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(8)
        self._layout.setVerticalSpacing(6)

        self.hide()

    def set_actions(self, actions: Sequence[TableAction]) -> None:
        """Replace the currently displayed actions."""

        self._clear_buttons()

        columns_per_row = 3

        for index, action in enumerate(actions):
            button = QPushButton(action.label)
            button.setEnabled(action.enabled)
            button.setMinimumWidth(0)
            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            button.clicked.connect(
                lambda checked=False, action_id=action.id: (
                    self.action_requested.emit(action_id)
                )
            )

            self._buttons[action.id] = button
            self._base_enabled[action.id] = action.enabled

            row = index // columns_per_row
            column = index % columns_per_row
            self._layout.addWidget(button, row, column)

        self.setVisible(bool(actions))

    def set_action_enabled(
        self,
        action_id: str,
        enabled: bool,
    ) -> None:
        """Change the normal enabled state of one action."""

        self._base_enabled[action_id] = enabled

        button = self._buttons.get(action_id)

        if button is not None:
            button.setEnabled(enabled)

    def set_all_enabled(self, enabled: bool) -> None:
        """Temporarily enable or disable every displayed action."""

        for action_id, button in self._buttons.items():
            button.setEnabled(
                enabled and self._base_enabled.get(action_id, True)
            )

    def _clear_buttons(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self._buttons.clear()
        self._base_enabled.clear()
