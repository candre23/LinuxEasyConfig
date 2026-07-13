from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from linuxeasyconfig.core.module_api import ViewDefinition


class ViewRenderError(ValueError):
    """Raised when LEC cannot render a view definition."""


class ViewRenderer:
    def render(self, view: ViewDefinition) -> QWidget:
        if view.view_type == "message":
            return self._render_message_view(view)

        raise ViewRenderError(
            f"Unsupported view type {view.view_type!r} for view {view.id!r}."
        )

    def _render_message_view(self, view: ViewDefinition) -> QWidget:
        heading = view.data.get("heading", view.title)
        message = view.data.get("message", "")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        heading_label = QLabel(str(heading))
        heading_label.setStyleSheet("font-size: 24px; font-weight: bold;")

        message_label = QLabel(str(message))
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        message_label.setStyleSheet("font-size: 15px;")

        layout.addWidget(heading_label)
        layout.addWidget(message_label)
        layout.addStretch()

        return container
