"""Linux Easy Config Port Usage package.

This package intentionally performs no eager imports.

Background systemd services execute submodules with ``python -m``. Python
loads this package's ``__init__.py`` before the requested submodule, so
importing the graphical module here would unnecessarily require PySide6 in
the system Python environment.

LEC loads the graphical module through the manifest entry point instead.
"""

__all__: list[str] = []
