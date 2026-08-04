from __future__ import annotations

import sys
from pathlib import Path


COMPAT_RUNTIME = Path(
    "/opt/linuxeasyconfig/qt-runtime"
)


def enable_compat_runtime() -> None:
    if not COMPAT_RUNTIME.is_dir():
        return

    runtime_path = str(COMPAT_RUNTIME)

    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)


def main() -> int:
    enable_compat_runtime()

    from linuxeasyconfig.app import main as app_main

    result = app_main()
    return int(result) if result is not None else 0
