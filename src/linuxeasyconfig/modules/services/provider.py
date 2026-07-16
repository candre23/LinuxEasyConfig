from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from linuxeasyconfig.core.table_actions import TableAction
from linuxeasyconfig.core.table_provider import TableDataProvider


_SERVICE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9_.@:-]+\.service$"
)

_SYSTEMD_DIRECTORY = Path("/etc/systemd/system")

_ENABLED_STATES = {
    "enabled",
    "enabled-runtime",
}

_DISABLED_STATES = {
    "disabled",
}


class ServicesTableProvider(TableDataProvider):
    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def columns(self):
        return [
            {
                "id": "name",
                "title": "Service",
                "resize": "stretch",
            },
            {
                "id": "status",
                "title": "Status",
                "alignment": "center",
            },
            {
                "id": "startup",
                "title": "Startup",
                "alignment": "center",
            },
        ]

    def rows(self):
        return tuple(self._rows)

    def refresh(self) -> None:
        unit_files = self._list_unit_files()
        runtime_states = self._list_runtime_states()
        fragment_paths = self._list_fragment_paths(
            tuple(unit_files)
        )

        rows: list[dict[str, Any]] = []

        for unit_name, startup_state in unit_files.items():
            runtime = runtime_states.get(
                unit_name,
                {
                    "active_state": "inactive",
                    "sub_state": "dead",
                    "status": "Stopped",
                    "description": unit_name.removesuffix(
                        ".service"
                    ),
                },
            )

            fragment_path = fragment_paths.get(
                unit_name,
                "",
            )

            rows.append(
                {
                    "_id": unit_name,
                    "name": unit_name.removesuffix(
                        ".service"
                    ),
                    "description": runtime["description"],
                    "status": runtime["status"],
                    "active_state": runtime["active_state"],
                    "sub_state": runtime["sub_state"],
                    "startup": self._format_startup_state(
                        startup_state
                    ),
                    "startup_state": startup_state,
                    "unit_file_path": fragment_path,
                    "removable": self._is_removable_unit(
                        fragment_path
                    ),
                    "lec_managed": self._is_lec_managed(
                        fragment_path
                    ),
                }
            )

        rows.sort(
            key=lambda row: str(row["name"]).casefold()
        )
        self._rows = rows

    def status_text(self) -> str:
        active = sum(
            row.get("active_state") == "active"
            for row in self._rows
        )
        return (
            f"{len(self._rows)} services "
            f"({active} active)"
        )

    @property
    def refresh_interval_ms(self) -> int:
        return 5000

    def actions_for_row(
        self,
        row: dict[str, Any] | None,
    ):
        if row is None:
            return ()

        active_state = str(
            row.get("active_state", "inactive")
        ).lower()
        startup_state = str(
            row.get("startup_state", "unknown")
        ).lower()
        display_name = str(
            row.get("name", "this service")
        )

        active = active_state == "active"
        transitional = active_state in {
            "activating",
            "deactivating",
            "reloading",
        }

        startup_enabled = (
            startup_state in _ENABLED_STATES
        )
        startup_disabled = (
            startup_state in _DISABLED_STATES
        )

        return (
            TableAction(
                id="start",
                label="Start",
                enabled=not active and not transitional,
            ),
            TableAction(
                id="stop",
                label="Stop",
                enabled=active and not transitional,
                confirmation_title=(
                    "Stop Background Service"
                ),
                confirmation_message=(
                    f"Stop {display_name}?\n\n"
                    "Programs or system functions that "
                    "depend on it may stop working."
                ),
            ),
            TableAction(
                id="restart",
                label="Restart",
                enabled=active and not transitional,
                confirmation_title=(
                    "Restart Background Service"
                ),
                confirmation_message=(
                    f"Restart {display_name}?\n\n"
                    "The service may be briefly unavailable."
                ),
            ),
            TableAction(
                id="enable",
                label="Enable at Startup",
                enabled=startup_disabled,
            ),
            TableAction(
                id="disable",
                label="Disable at Startup",
                enabled=startup_enabled,
                confirmation_title=(
                    "Disable Automatic Startup"
                ),
                confirmation_message=(
                    f"Prevent {display_name} from starting "
                    "automatically?\n\n"
                    "This does not stop the service if it "
                    "is currently running."
                ),
            ),
            TableAction(
                id="remove",
                label="Remove Service",
                enabled=bool(
                    row.get("removable", False)
                ),
            ),
        )

    def execute_action(
        self,
        action_id: str,
        row: dict[str, Any],
    ) -> str:
        supported_actions = {
            "start",
            "stop",
            "restart",
            "enable",
            "disable",
        }

        if action_id not in supported_actions:
            raise ValueError(
                f"Unsupported service action: {action_id}"
            )

        unit_name = str(row.get("_id", ""))

        if not _SERVICE_NAME_PATTERN.fullmatch(
            unit_name
        ):
            raise ValueError(
                "The selected service name is invalid."
            )

        result = subprocess.run(
            [
                "pkexec",
                "systemctl",
                action_id,
                unit_name,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error = (
                result.stderr.strip()
                or result.stdout.strip()
                or (
                    "systemctl exited with code "
                    f"{result.returncode}"
                )
            )
            raise RuntimeError(error)

        display_name = str(
            row.get(
                "name",
                unit_name.removesuffix(".service"),
            )
        )

        messages = {
            "start": f"{display_name} was started.",
            "stop": f"{display_name} was stopped.",
            "restart": (
                f"{display_name} was restarted."
            ),
            "enable": (
                f"{display_name} will start "
                "automatically."
            ),
            "disable": (
                f"{display_name} will no longer start "
                "automatically."
            ),
        }

        return messages[action_id]

    def _list_runtime_states(
        self,
    ) -> dict[str, dict[str, str]]:
        result = subprocess.run(
            [
                "systemctl",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--no-legend",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        states: dict[str, dict[str, str]] = {}

        for line in result.stdout.splitlines():
            parts = line.split(None, 4)

            if len(parts) < 4:
                continue

            unit_name = parts[0]

            if not unit_name.endswith(".service"):
                continue

            active_state = parts[2].lower()
            sub_state = parts[3].lower()
            description = (
                parts[4].strip()
                if len(parts) >= 5
                else unit_name.removesuffix(
                    ".service"
                )
            )

            states[unit_name] = {
                "active_state": active_state,
                "sub_state": sub_state,
                "status": self._format_runtime_state(
                    active_state,
                    sub_state,
                ),
                "description": description,
            }

        return states

    def _list_unit_files(self) -> dict[str, str]:
        result = subprocess.run(
            [
                "systemctl",
                "list-unit-files",
                "--type=service",
                "--all",
                "--no-pager",
                "--no-legend",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        unit_files: dict[str, str] = {}

        for line in result.stdout.splitlines():
            parts = line.split()

            if len(parts) < 2:
                continue

            unit_name = parts[0]

            if not unit_name.endswith(".service"):
                continue

            unit_files[unit_name] = (
                parts[1].lower()
            )

        return unit_files

    def _list_fragment_paths(
        self,
        unit_names: tuple[str, ...],
    ) -> dict[str, str]:
        """
        Query unit-file paths in small batches.

        Some aliases or unloaded units can make systemctl return a
        nonzero status. Valid output is still parsed rather than
        discarding the entire service list.
        """

        paths: dict[str, str] = {}
        batch_size = 30

        for start in range(0, len(unit_names), batch_size):
            batch = unit_names[
                start:start + batch_size
            ]

            try:
                result = subprocess.run(
                    [
                        "systemctl",
                        "show",
                        "--no-pager",
                        "--property=Id",
                        "--property=FragmentPath",
                        *batch,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
            except (
                OSError,
                subprocess.TimeoutExpired,
            ):
                continue

            self._parse_fragment_output(
                result.stdout,
                paths,
            )

        return paths

    @staticmethod
    def _parse_fragment_output(
        output: str,
        paths: dict[str, str],
    ) -> None:
        current_id = ""
        current_path = ""

        def commit() -> None:
            if current_id:
                paths[current_id] = current_path

        for line in output.splitlines():
            if not line.strip():
                commit()
                current_id = ""
                current_path = ""
                continue

            key, separator, value = line.partition(
                "="
            )

            if not separator:
                continue

            if key == "Id":
                current_id = value.strip()
            elif key == "FragmentPath":
                current_path = value.strip()

        commit()

    @staticmethod
    def _is_removable_unit(
        fragment_path: str,
    ) -> bool:
        if not fragment_path:
            return False

        path = Path(fragment_path)

        try:
            return (
                not path.is_symlink()
                and path.is_file()
                and path.parent.resolve()
                == _SYSTEMD_DIRECTORY.resolve()
            )
        except OSError:
            return False

    @staticmethod
    def _is_lec_managed(
        fragment_path: str,
    ) -> bool:
        if not fragment_path:
            return False

        path = Path(fragment_path)

        try:
            if not path.is_file() or path.is_symlink():
                return False

            with path.open(
                "r",
                encoding="utf-8",
                errors="replace",
            ) as unit_file:
                header = "".join(
                    unit_file.readline()
                    for _ in range(12)
                )

            return (
                "Created by Linux Easy Config"
                in header
                and
                "org.linuxeasyconfig.services"
                in header
            )
        except OSError:
            return False

    @staticmethod
    def _format_runtime_state(
        active_state: str,
        sub_state: str,
    ) -> str:
        if active_state == "failed":
            return "Failed"

        if active_state == "active":
            if sub_state == "running":
                return "Running"

            if sub_state == "exited":
                return "Completed"

            if sub_state == "listening":
                return "Listening"

            return "Active"

        if active_state == "activating":
            return "Starting"

        if active_state == "deactivating":
            return "Stopping"

        if active_state == "reloading":
            return "Reloading"

        if active_state == "inactive":
            return "Stopped"

        return active_state.replace(
            "-",
            " ",
        ).title()

    @staticmethod
    def _format_startup_state(
        state: str,
    ) -> str:
        labels = {
            "enabled": "Enabled",
            "enabled-runtime": (
                "Enabled temporarily"
            ),
            "disabled": "Disabled",
            "static": "System managed",
            "indirect": "Indirect",
            "generated": "Generated",
            "transient": "Temporary",
            "masked": "Blocked",
            "alias": "Alias",
            "linked": "Linked",
            "linked-runtime": (
                "Linked temporarily"
            ),
            "bad": "Invalid",
            "unknown": "Unknown",
        }

        return labels.get(
            state.lower(),
            state.replace("-", " ").title(),
        )
