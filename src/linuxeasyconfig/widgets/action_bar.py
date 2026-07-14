from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from linuxeasyconfig.core.table_actions import TableAction


class ActionBar(QWidget):
    """Reusable horizontal action-button bar."""

    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}
        self._base_enabled: dict[str, bool] = {}

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.addStretch()

        self.hide()

    def set_actions(self, actions: Sequence[TableAction]) -> None:
        """Replace the currently displayed actions."""

        self._clear_buttons()

        for action in actions:
            button = QPushButton(action.label)
            button.setEnabled(action.enabled)
            button.clicked.connect(
                lambda checked=False, action_id=action.id: (
                    self.action_requested.emit(action_id)
                )
            )

            self._buttons[action.id] = button
            self._base_enabled[action.id] = action.enabled

            self._layout.insertWidget(
                self._layout.count() - 1,
                button,
            )

        self.setVisible(bool(actions))

    def set_action_enabled(self, action_id: str, enabled: bool) -> None:
        """Change the normal enabled state of one action."""

        self._base_enabled[action_id] = enabled

        button = self._buttons.get(action_id)
        if button is not None:
            button.setEnabled(enabled)

    def set_all_enabled(self, enabled: bool) -> None:
        """Temporarily enable or disable all displayed actions."""

        for action_id, button in self._buttons.items():
            button.setEnabled(
                enabled and self._base_enabled.get(action_id, True)
            )

    def _clear_buttons(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self._buttons.clear()
        self._base_enabled.clear()
