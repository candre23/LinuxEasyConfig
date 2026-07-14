from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from linuxeasyconfig.core.privileged.task import PrivilegedTask


class PrivilegedTaskError(RuntimeError):
    """Raised when a privileged task cannot be completed."""


class PrivilegedRunner:
    """Run approved LEC administrative tasks through pkexec."""

    def run(
        self,
        task: PrivilegedTask,
        *,
        timeout: int = 120,
    ) -> str:
        payload_path = self._write_payload(task)

        try:
            result = subprocess.run(
                [
                    "pkexec",
                    sys.executable,
                    "-m",
                    "linuxeasyconfig.core.privileged.helper",
                    "--payload",
                    str(payload_path),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise PrivilegedTaskError(
                f"Administrative task timed out after {timeout} seconds."
            ) from exc
        finally:
            payload_path.unlink(missing_ok=True)

        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or f"Privileged helper exited with code {result.returncode}."
            )
            raise PrivilegedTaskError(message)

        return result.stdout.strip()

    @staticmethod
    def _write_payload(task: PrivilegedTask) -> Path:
        payload = {
            "task_id": task.task_id,
            "arguments": task.arguments,
        }

        file_descriptor, filename = tempfile.mkstemp(
            prefix="lec-privileged-",
            suffix=".json",
        )
        path = Path(filename)

        try:
            os.fchmod(file_descriptor, 0o600)

            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
            ) as payload_file:
                json.dump(payload, payload_file)
                payload_file.flush()
                os.fsync(payload_file.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise

        return path
