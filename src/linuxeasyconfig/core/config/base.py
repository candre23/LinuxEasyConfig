from __future__ import annotations

from abc import ABC, abstractmethod


class ConfigurationDocument(ABC):
    """Base class for renderable configuration documents."""

    @abstractmethod
    def render(self) -> str:
        """Render the complete configuration document as text."""

    def preview(self) -> str:
        """Return the text shown in a configuration preview."""

        return self.render()

    def __str__(self) -> str:
        return self.render()
