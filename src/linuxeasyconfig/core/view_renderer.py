from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from linuxeasyconfig.core.module_api import ViewDefinition
from linuxeasyconfig.core.table_provider import TableDataProvider
from linuxeasyconfig.widgets.data_table import DataTable


class ViewRenderError(ValueError):
    """Raised when LEC cannot render a view definition."""


class ViewRenderer:
    def render(self, view: ViewDefinition) -> QWidget:
        if view.view_type == "message":
            return self._render_message_view(view)

        if view.view_type == "table":
            return self._render_table_view(view)

        if view.view_type == "custom":
            return self._render_custom_view(view)

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
        heading_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )

        message_label = QLabel(str(message))
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        message_label.setStyleSheet("font-size: 15px;")

        layout.addWidget(heading_label)
        layout.addWidget(message_label)
        layout.addStretch()

        return container

    def _render_table_view(self, view: ViewDefinition) -> QWidget:
        heading = view.data.get("heading", view.title)
        description = view.data.get("description", "")
        provider = view.data.get("provider")

        if not isinstance(provider, TableDataProvider):
            raise ViewRenderError(
                f"Table view {view.id!r} is missing a valid "
                "TableDataProvider."
            )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        heading_label = QLabel(str(heading))
        heading_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(heading_label)

        if description:
            description_label = QLabel(str(description))
            description_label.setWordWrap(True)
            description_label.setStyleSheet("font-size: 14px;")
            layout.addWidget(description_label)

        table = DataTable(
            provider=provider,
            selectable=bool(view.data.get("selectable", True)),
            sortable=bool(view.data.get("sortable", True)),
        )
        layout.addWidget(table)

        return container

    def _render_custom_view(self, view: ViewDefinition) -> QWidget:
        factory = view.data.get("factory")

        if not isinstance(factory, Callable):
            raise ViewRenderError(
                f"Custom view {view.id!r} is missing a callable factory."
            )

        try:
            widget = factory()
        except Exception as exc:
            raise ViewRenderError(
                f"Custom view {view.id!r} could not be created: {exc}"
            ) from exc

        if not isinstance(widget, QWidget):
            raise ViewRenderError(
                f"Custom view {view.id!r} did not return a QWidget."
            )

        return widget
