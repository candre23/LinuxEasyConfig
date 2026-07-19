from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


USER_PRESET_DIR = (
    Path.home()
    / ".local"
    / "share"
    / "linuxeasyconfig"
    / "docker-presets"
)


@dataclass(frozen=True)
class DockerPreset:
    path: Path
    source: str
    data: dict[str, Any]

    @property
    def preset_id(self) -> str:
        return str(self.data["id"])

    @property
    def name(self) -> str:
        return str(self.data["name"])

    @property
    def description(self) -> str:
        return str(self.data.get("description", ""))

    @property
    def preset_type(self) -> str:
        return str(self.data["type"])


def preset_directories() -> list[tuple[Path, str]]:
    directories: list[tuple[Path, str]] = []

    # Presets stored inside the Docker module. This works both from
    # an unpacked development module and an extracted .lec archive.
    directories.append(
        (
            Path(__file__).resolve().parent
            / "bundled_presets",
            "Included with LEC",
        )
    )

    # Legacy source-tree location used during development.
    try:
        repository_root = Path(__file__).resolve().parents[4]
        directories.append(
            (
                repository_root / "tools" / "docker_presets",
                "Included with LEC",
            )
        )
    except IndexError:
        pass

    # Location suitable for a packaged system installation.
    directories.append(
        (
            Path("/usr/share/linuxeasyconfig/docker-presets"),
            "Included with LEC",
        )
    )

    directories.append(
        (
            USER_PRESET_DIR,
            "Imported",
        )
    )

    return directories


def load_presets() -> list[DockerPreset]:
    by_id: dict[str, DockerPreset] = {}

    for directory, source in preset_directories():
        if not directory.is_dir():
            continue

        for path in sorted(directory.glob("*.lecdock")):
            try:
                data = load_preset_file(path)
            except Exception:
                continue

            preset = DockerPreset(
                path=path,
                source=source,
                data=data,
            )

            # User imports intentionally override shipped presets with
            # the same ID.
            by_id[preset.preset_id] = preset

    return sorted(
        by_id.values(),
        key=lambda item: item.name.lower(),
    )


def load_preset_file(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".lecdock":
        raise ValueError(
            "Docker preset files must use the .lecdock extension."
        )

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} is not valid JSON."
        ) from exc

    validate_preset(data)
    return data


def import_preset(path: Path) -> Path:
    data = load_preset_file(path)

    USER_PRESET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = _safe_filename(
        str(data["id"])
    ) + ".lecdock"
    destination = USER_PRESET_DIR / filename

    shutil.copyfile(path, destination)
    destination.chmod(0o644)
    return destination


def validate_preset(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError(
            "A Docker preset must contain a JSON object."
        )

    if data.get("format_version") != 1:
        raise ValueError(
            "This Docker preset format is not supported."
        )

    for key in ("id", "name", "type", "fields"):
        if key not in data:
            raise ValueError(
                f"Docker preset field {key!r} is missing."
            )

    preset_type = str(data["type"])

    if preset_type not in {"container", "compose"}:
        raise ValueError(
            "Docker preset type must be container or compose."
        )

    if not isinstance(data["fields"], list):
        raise ValueError(
            "Docker preset fields must be a list."
        )

    seen_fields: set[str] = set()

    for field in data["fields"]:
        if not isinstance(field, dict):
            raise ValueError(
                "Each Docker preset field must be an object."
            )

        field_id = str(field.get("id", "")).strip()
        label = str(field.get("label", "")).strip()
        field_type = str(
            field.get("type", "text")
        ).strip()

        if not field_id or not label:
            raise ValueError(
                "Every preset field needs an ID and label."
            )
        if field_id in seen_fields:
            raise ValueError(
                f"Preset field {field_id!r} is duplicated."
            )
        if field_type not in {
            "text",
            "password",
            "integer",
            "port",
            "boolean",
            "choice",
        }:
            raise ValueError(
                f"Preset field type {field_type!r} is invalid."
            )

        if field_type == "choice":
            choices = field.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError(
                    f"Choice field {field_id!r} has no choices."
                )

        seen_fields.add(field_id)

    if preset_type == "container":
        container = data.get("container")
        if not isinstance(container, dict):
            raise ValueError(
                "Container preset settings are missing."
            )
        if not str(container.get("image", "")).strip():
            raise ValueError(
                "Container preset image is missing."
            )

    if preset_type == "compose":
        compose = data.get("compose")
        if not isinstance(compose, dict):
            raise ValueError(
                "Compose preset settings are missing."
            )

        template = str(
            compose.get("template", "")
        )

        if not template.strip():
            raise ValueError(
                "Compose preset template is missing."
            )

        _reject_dangerous_compose(template)


def default_values(
    preset: DockerPreset,
) -> dict[str, Any]:
    values: dict[str, Any] = {}

    for field in preset.data["fields"]:
        field_id = str(field["id"])
        values[field_id] = field.get("default", "")

    return values


def _reject_dangerous_compose(template: str) -> None:
    lowered = template.lower()

    forbidden = {
        "privileged: true": "privileged containers",
        "/var/run/docker.sock": "the Docker control socket",
        "network_mode: host": "host networking",
        "pid: host": "the host process namespace",
        "ipc: host": "the host IPC namespace",
    }

    for fragment, description in forbidden.items():
        if fragment in lowered:
            raise ValueError(
                "This preset requests "
                f"{description}, which LEC presets do not allow."
            )


def _safe_filename(value: str) -> str:
    result = "".join(
        character
        if character.isalnum() or character in "._-"
        else "-"
        for character in value
    ).strip(".-")

    return result or "docker-preset"
