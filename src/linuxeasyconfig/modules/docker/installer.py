from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from linuxeasyconfig.core.config.managed import (
    write_text,
)
from typing import Any

from .presets import validate_preset
from .storage import (
    ManagedContainer,
    remove_managed_container,
    upsert_managed_container,
)


SNAPSHOT_PATH = Path(
    "/var/lib/linuxeasyconfig/docker/status.json"
)
MODULE_ID = "org.linuxeasyconfig.docker"
APPLICATION_ROOT = Path(
    "/opt/linuxeasyconfig/docker/apps"
)

_NAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$"
)
_IMAGE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._/:@-]{0,254}$"
)


def install_docker() -> str:
    environment = os.environ.copy()
    environment["DEBIAN_FRONTEND"] = "noninteractive"

    _run(
        [
            "apt-get",
            "update",
        ],
        timeout=600,
        environment=environment,
    )
    _run(
        [
            "apt-get",
            "install",
            "-y",
            "ca-certificates",
            "curl",
        ],
        timeout=600,
        environment=environment,
    )

    keyring = Path("/etc/apt/keyrings/docker.asc")
    source = Path(
        "/etc/apt/sources.list.d/docker.sources"
    )

    keyring.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not keyring.is_file():
        _run(
            [
                "curl",
                "-fsSL",
                "https://download.docker.com/linux/ubuntu/gpg",
                "-o",
                str(keyring),
            ],
            timeout=120,
        )
        os.chmod(keyring, 0o644)

    architecture = _output(
        ["dpkg", "--print-architecture"],
        timeout=30,
    )
    codename = _output(
        [
            "bash",
            "-lc",
            (
                ". /etc/os-release && "
                "printf '%s' \"${UBUNTU_CODENAME:-$VERSION_CODENAME}\""
            ),
        ],
        timeout=30,
    )

    write_text(
        module_id=MODULE_ID,
        destination=source,
        text=(
            "Types: deb\n"
            "URIs: https://download.docker.com/linux/ubuntu\n"
            f"Suites: {codename}\n"
            "Components: stable\n"
            f"Architectures: {architecture}\n"
            f"Signed-By: {keyring}\n"
        ),
        mode=0o644,
    )

    _run(
        ["apt-get", "update"],
        timeout=600,
        environment=environment,
    )
    _run(
        [
            "apt-get",
            "install",
            "-y",
            "docker-ce",
            "docker-ce-cli",
            "containerd.io",
            "docker-buildx-plugin",
            "docker-compose-plugin",
        ],
        timeout=1200,
        environment=environment,
    )
    _run(
        [
            "systemctl",
            "enable",
            "--now",
            "docker",
        ],
        timeout=120,
    )

    refresh_snapshot()

    return (
        "Docker Engine and Docker Compose were installed "
        "and started."
    )


def service_action(*, action: str) -> str:
    if action not in {
        "start",
        "stop",
        "restart",
        "enable",
        "disable",
    }:
        raise ValueError(
            "The selected Docker service action is invalid."
        )

    _run(
        [
            "systemctl",
            action,
            "docker",
        ],
        timeout=120,
    )
    refresh_snapshot()

    return f"Docker was {action}ed."


def container_action(
    *,
    container: str,
    action: str,
) -> str:
    _validate_container_reference(container)

    if action not in {
        "start",
        "stop",
        "restart",
    }:
        raise ValueError(
            "The selected container action is invalid."
        )

    _run(
        [
            "docker",
            "container",
            action,
            container,
        ],
        timeout=180,
    )
    refresh_snapshot()

    return (
        f"Container {container} was {action}ed."
    )


def remove_container(
    *,
    container: str,
    force: bool,
    remove_volumes: bool,
    remove_image: bool,
    remove_data: bool,
) -> str:
    _validate_container_reference(container)

    details = _container_removal_details(container)
    image = str(details.get("image", "")).strip()
    mounts = details.get("mounts", [])

    command = [
        "docker",
        "container",
        "rm",
    ]

    if force:
        command.append("--force")
    if remove_volumes:
        command.append("--volumes")

    command.append(container)

    _run(command, timeout=180)

    messages = [
        f"Container {container} was removed."
    ]

    if remove_data:
        removed_data, skipped_data = (
            _remove_container_data(mounts)
        )

        if removed_data:
            messages.append(
                "Deleted data: "
                + ", ".join(removed_data)
                + "."
            )

        if skipped_data:
            messages.append(
                "Data not deleted: "
                + ", ".join(skipped_data)
                + "."
            )

    if remove_image and image:
        result = subprocess.run(
            [
                "docker",
                "image",
                "rm",
                image,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )

        if result.returncode == 0:
            messages.append(
                f"Image {image} was removed."
            )
        else:
            detail = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Docker could not remove the image."
            )
            messages.append(
                "The container was removed, but the image "
                f"was retained: {detail}"
            )

    remove_managed_container(container)
    refresh_snapshot()

    return "\n\n".join(messages)



def _container_removal_details(
    container: str,
) -> dict[str, Any]:
    result = subprocess.run(
        [
            "docker",
            "container",
            "inspect",
            container,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Docker could not inspect the container."
        )

    try:
        values = json.loads(
            result.stdout or "[]"
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Docker returned invalid container details."
        ) from exc

    if (
        not isinstance(values, list)
        or not values
        or not isinstance(values[0], dict)
    ):
        raise RuntimeError(
            "Docker returned no container details."
        )

    item = values[0]
    config = item.get("Config", {})
    mounts = item.get("Mounts", [])

    image = ""

    if isinstance(config, dict):
        image = str(config.get("Image", ""))

    return {
        "image": image,
        "mounts": (
            mounts
            if isinstance(mounts, list)
            else []
        ),
    }


def _remove_container_data(
    mounts: list[Any],
) -> tuple[list[str], list[str]]:
    removed: list[str] = []
    skipped: list[str] = []

    for item in mounts:
        if not isinstance(item, dict):
            continue

        mount_type = str(
            item.get("Type", "")
        ).strip()
        source = str(
            item.get("Source", "")
        ).strip()
        name = str(
            item.get("Name", "")
        ).strip()

        if mount_type == "volume" and name:
            result = subprocess.run(
                [
                    "docker",
                    "volume",
                    "rm",
                    name,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            if result.returncode == 0:
                removed.append(
                    f"volume {name}"
                )
            else:
                detail = (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "could not be removed"
                )
                skipped.append(
                    f"volume {name} ({detail})"
                )

        elif mount_type == "bind" and source:
            path = Path(source)

            try:
                resolved = path.resolve(
                    strict=False
                )
            except OSError:
                skipped.append(source)
                continue

            if not _safe_data_path(resolved):
                skipped.append(
                    f"{source} (protected path)"
                )
                continue

            try:
                if resolved.is_dir():
                    shutil.rmtree(resolved)
                elif resolved.exists():
                    resolved.unlink()
                removed.append(source)
            except OSError as exc:
                skipped.append(
                    f"{source} ({exc})"
                )

    return removed, skipped


def _safe_data_path(path: Path) -> bool:
    protected = {
        Path("/"),
        Path("/bin"),
        Path("/boot"),
        Path("/dev"),
        Path("/etc"),
        Path("/home"),
        Path("/lib"),
        Path("/lib64"),
        Path("/opt"),
        Path("/proc"),
        Path("/root"),
        Path("/run"),
        Path("/sbin"),
        Path("/srv"),
        Path("/sys"),
        Path("/tmp"),
        Path("/usr"),
        Path("/var"),
    }

    return (
        path.is_absolute()
        and path not in protected
        and len(path.parts) >= 3
    )

def create_container(
    *,
    name: str,
    image: str,
    host_port: int,
    container_port: int,
    protocol: str,
    host_path: str,
    container_path: str,
    environment_lines: str,
    restart_policy: str,
    access_scope: str,
    bind_address: str,
    service_protocol: str,
    reverse_proxy_compatible: bool,
    public_host: str,
) -> str:
    name = name.strip()
    image = image.strip()

    if not _NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Container names may contain letters, numbers, "
            "periods, underscores, and hyphens."
        )
    if not _IMAGE_PATTERN.fullmatch(image):
        raise ValueError(
            "Enter a valid container image name."
        )
    if protocol not in {"tcp", "udp"}:
        raise ValueError(
            "The selected network protocol is invalid."
        )
    if restart_policy not in {
        "no",
        "unless-stopped",
        "always",
        "on-failure",
    }:
        raise ValueError(
            "The selected restart behavior is invalid."
        )
    if access_scope not in {
        "localhost",
        "local_network",
        "all_networks",
    }:
        raise ValueError(
            "The selected network access scope is invalid."
        )
    if service_protocol not in {
        "http",
        "https",
        "tcp",
        "udp",
    }:
        raise ValueError(
            "The selected service type is invalid."
        )

    bind_address = bind_address.strip()

    if access_scope == "localhost":
        bind_address = "127.0.0.1"
    elif access_scope == "local_network":
        if not bind_address:
            raise ValueError(
                "LEC could not determine the computer's "
                "local-network address."
            )
    else:
        bind_address = "0.0.0.0"

    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        name,
        "--restart",
        restart_policy,
    ]

    if host_port or container_port:
        if not (
            1 <= host_port <= 65535
            and 1 <= container_port <= 65535
        ):
            raise ValueError(
                "Both published ports must be between 1 and 65535."
            )

        command.extend(
            [
                "--publish",
                (
                    f"{bind_address}:{host_port}:"
                    f"{container_port}/{protocol}"
                ),
            ]
        )

    host_path = host_path.strip()
    container_path = container_path.strip()

    if host_path or container_path:
        if not host_path or not container_path:
            raise ValueError(
                "Enter both the host folder and container folder."
            )
        if not host_path.startswith("/"):
            raise ValueError(
                "The host folder must be an absolute Linux path."
            )
        if not container_path.startswith("/"):
            raise ValueError(
                "The container folder must begin with /."
            )

        Path(host_path).mkdir(
            parents=True,
            exist_ok=True,
        )
        command.extend(
            [
                "--volume",
                f"{host_path}:{container_path}",
            ]
        )

    for raw_line in environment_lines.splitlines():
        line = raw_line.strip()

        if not line:
            continue
        if "=" not in line:
            raise ValueError(
                f"Environment entry {line!r} must use NAME=value."
            )

        key, _, value = line.partition("=")

        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            key,
        ):
            raise ValueError(
                f"{key!r} is not a valid environment variable name."
            )

        command.extend(
            [
                "--env",
                f"{key}={value}",
            ]
        )

    command.append(image)

    _run(
        [
            "docker",
            "pull",
            image,
        ],
        timeout=1200,
    )
    _run(
        command,
        timeout=600,
    )

    upsert_managed_container(
        ManagedContainer(
            name=name,
            image=image,
            host_address=bind_address,
            host_port=host_port,
            container_port=container_port,
            protocol=protocol,
            access_scope=access_scope,
            service_protocol=service_protocol,
            reverse_proxy_compatible=(
                reverse_proxy_compatible
            ),
            public_host=public_host.strip(),
        )
    )

    refresh_snapshot()

    return f"Container {name} was created and started."


def container_logs(
    *,
    container: str,
    lines: int,
) -> str:
    _validate_container_reference(container)

    if not 1 <= lines <= 5000:
        raise ValueError(
            "Log line count must be between 1 and 5000."
        )

    return _output(
        [
            "docker",
            "container",
            "logs",
            "--tail",
            str(lines),
            container,
        ],
        timeout=60,
        include_stderr=True,
    )



def deploy_preset(
    *,
    preset: dict[str, Any],
    values: dict[str, Any],
) -> str:
    validate_preset(preset)

    if preset.get("type") != "compose":
        raise ValueError(
            "This preset does not define a Compose application."
        )

    normalized = _normalize_preset_values(
        preset,
        values,
    )

    application_name = str(
        normalized.get("application_name", "")
    ).strip()

    if not _NAME_PATTERN.fullmatch(application_name):
        raise ValueError(
            "Application names may contain letters, numbers, "
            "periods, underscores, and hyphens."
        )

    access_scope = str(
        normalized.get("access_scope", "localhost")
    )

    if access_scope == "localhost":
        bind_address = "127.0.0.1"
    elif access_scope == "local_network":
        bind_address = _primary_local_address()
        if not bind_address:
            raise RuntimeError(
                "LEC could not determine this computer's "
                "local-network address."
            )
    elif access_scope == "all_networks":
        bind_address = "0.0.0.0"
    else:
        raise ValueError(
            "The selected network access scope is invalid."
        )

    normalized["bind_address"] = bind_address

    compose = preset["compose"]
    template = str(compose["template"])
    rendered = _render_preset_template(
        template,
        normalized,
    )

    application_directory = (
        APPLICATION_ROOT / application_name
    )
    application_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(application_directory, 0o750)

    compose_path = (
        application_directory / "compose.yaml"
    )
    environment_path = (
        application_directory / ".env"
    )

    write_text(
        module_id=MODULE_ID,
        destination=compose_path,
        text=rendered.rstrip() + "\n",
        mode=0o640,
    )

    environment_values = compose.get(
        "environment",
        [],
    )
    environment_lines: list[str] = []
    existing_environment = _read_environment_file(
        environment_path
    )

    if not isinstance(environment_values, list):
        raise ValueError(
            "Preset Compose environment definition is invalid."
        )

    for key in environment_values:
        key_text = str(key)
        if key_text not in normalized:
            raise ValueError(
                f"Preset value {key_text!r} is missing."
            )

        environment_key = key_text.upper()
        value = str(
            existing_environment.get(
                environment_key,
                normalized[key_text],
            )
        )
        normalized[key_text] = value

        if "\n" in value or "\r" in value:
            raise ValueError(
                f"Preset value {key_text!r} contains a line break."
            )

        environment_lines.append(
            f"{environment_key}={value}"
        )

    write_text(
        module_id=MODULE_ID,
        destination=environment_path,
        text="\n".join(environment_lines) + "\n",
        mode=0o600,
    )

    initialization = compose.get("initialization")

    if initialization == "guacamole_postgresql_schema":
        _initialize_guacamole_schema(
            application_directory=application_directory,
            image=str(
                compose.get(
                    "initialization_image",
                    "guacamole/guacamole:1.6.0",
                )
            ),
        )
    elif initialization not in {None, ""}:
        raise ValueError(
            "This preset requests an unsupported "
            "initialization method."
        )

    _run(
        [
            "docker",
            "compose",
            "--project-name",
            application_name,
            "--env-file",
            str(environment_path),
            "--file",
            str(compose_path),
            "up",
            "--detach",
        ],
        timeout=1800,
    )

    service = preset.get("service", {})

    if isinstance(service, dict):
        host_port = int(
            normalized.get("host_port", 0)
        )
        container_port = int(
            service.get("container_port", 0)
        )
        service_protocol = str(
            service.get("protocol", "http")
        )

        if host_port and container_port:
            upsert_managed_container(
                ManagedContainer(
                    name=application_name,
                    image=(
                        "Application preset: "
                        + str(preset["name"])
                    ),
                    host_address=bind_address,
                    host_port=host_port,
                    container_port=container_port,
                    protocol=str(
                        service.get(
                            "transport_protocol",
                            "tcp",
                        )
                    ),
                    access_scope=access_scope,
                    service_protocol=service_protocol,
                    reverse_proxy_compatible=bool(
                        service.get(
                            "reverse_proxy_compatible",
                            False,
                        )
                    ),
                    public_host=str(
                        normalized.get(
                            "public_host",
                            "",
                        )
                    ),
                )
            )

    refresh_snapshot()

    return (
        f"{preset['name']} was deployed successfully "
        f"as {application_name}."
    )



def _read_environment_file(
    path: Path,
) -> dict[str, str]:
    if not path.is_file():
        return {}

    result: dict[str, str] = {}

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return {}

    for raw_line in lines:
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, _, value = line.partition("=")
        key = key.strip()

        if key:
            result[key] = value

    return result

def _normalize_preset_values(
    preset: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for field in preset["fields"]:
        field_id = str(field["id"])
        field_type = str(
            field.get("type", "text")
        )
        value = values.get(
            field_id,
            field.get("default", ""),
        )

        if field_type in {"integer", "port"}:
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{field['label']} must be a number."
                ) from exc

            if field_type == "port" and not 1 <= number <= 65535:
                raise ValueError(
                    f"{field['label']} must be between "
                    "1 and 65535."
                )

            normalized[field_id] = number
        elif field_type == "boolean":
            normalized[field_id] = bool(value)
        elif field_type == "choice":
            choices = field.get("choices", [])
            allowed = {
                str(item.get("value", ""))
                for item in choices
                if isinstance(item, dict)
            }

            if str(value) not in allowed:
                raise ValueError(
                    f"{field['label']} has an invalid selection."
                )

            normalized[field_id] = str(value)
        else:
            normalized[field_id] = str(value).strip()

        if field.get("required") and normalized[field_id] in {
            "",
            None,
        }:
            raise ValueError(
                f"{field['label']} is required."
            )

    return normalized


def _render_preset_template(
    template: str,
    values: dict[str, Any],
) -> str:
    pattern = re.compile(
        r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}"
    )
    missing: set[str] = set()

    def replacement(match: re.Match[str]) -> str:
        key = match.group(1)

        if key not in values:
            missing.add(key)
            return match.group(0)

        value = values[key]

        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value)

    rendered = pattern.sub(
        replacement,
        template,
    )

    if missing:
        raise ValueError(
            "Preset template values are missing: "
            + ", ".join(sorted(missing))
        )

    return rendered


def _initialize_guacamole_schema(
    *,
    application_directory: Path,
    image: str,
) -> None:
    schema_path = (
        application_directory / "initdb.sql"
    )

    if schema_path.is_file() and schema_path.stat().st_size > 0:
        return

    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            image,
            "/opt/guacamole/bin/initdb.sh",
            "--postgresql",
        ],
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Guacamole database initialization failed."
        )

    if not result.stdout.strip():
        raise RuntimeError(
            "Guacamole produced an empty database schema."
        )

    write_text(
        module_id=MODULE_ID,
        destination=schema_path,
        text=result.stdout,
        mode=0o644,
    )


def _primary_local_address() -> str:
    result = subprocess.run(
        [
            "ip",
            "-j",
            "-4",
            "route",
            "get",
            "1.1.1.1",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    try:
        values = json.loads(
            result.stdout or "[]"
        )
    except json.JSONDecodeError:
        return ""

    if not isinstance(values, list):
        return ""

    for item in values:
        if not isinstance(item, dict):
            continue

        address = str(
            item.get("prefsrc", "")
        ).strip()

        if address:
            return address

    return ""

def refresh_snapshot() -> str:
    installed = (
        subprocess.run(
            ["bash", "-lc", "command -v docker"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        ).returncode
        == 0
    )

    active = _systemctl_state(
        "is-active"
    ) == "active"
    enabled = _systemctl_state(
        "is-enabled"
    ) == "enabled"

    version = "Not installed"
    compose_version = "Unavailable"
    containers: list[dict[str, Any]] = []

    if installed:
        version = _output(
            [
                "docker",
                "version",
                "--format",
                "{{.Server.Version}}",
            ],
            timeout=30,
        ) or "Installed"

        compose_version = _output(
            [
                "docker",
                "compose",
                "version",
                "--short",
            ],
            timeout=30,
        ) or "Unavailable"

        if active:
            result = subprocess.run(
                [
                    "docker",
                    "container",
                    "ls",
                    "--all",
                    "--format",
                    (
                        "{{json .ID}}\t{{json .Names}}\t"
                        "{{json .Image}}\t{{json .State}}\t"
                        "{{json .Status}}\t{{json .Ports}}"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode == 0:
                for raw_line in result.stdout.splitlines():
                    fields = raw_line.split("\t")

                    if len(fields) != 6:
                        continue

                    try:
                        values = [
                            json.loads(field)
                            for field in fields
                        ]
                    except json.JSONDecodeError:
                        continue

                    containers.append(
                        {
                            "id": values[0],
                            "name": values[1],
                            "image": values[2],
                            "state": values[3],
                            "status": values[4],
                            "ports": values[5],
                        }
                    )

    payload = {
        "installed": installed,
        "active": active,
        "enabled": enabled,
        "version": version,
        "compose_version": compose_version,
        "containers": containers,
    }

    SNAPSHOT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(
        SNAPSHOT_PATH.parent,
        0o755,
    )

    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o644)
    temporary.replace(SNAPSHOT_PATH)
    os.chmod(SNAPSHOT_PATH, 0o644)

    return "Docker status was refreshed."


def _validate_container_reference(
    value: str,
) -> None:
    if not _NAME_PATTERN.fullmatch(
        value.strip()
    ):
        raise ValueError(
            "The selected container is invalid."
        )


def _systemctl_state(
    action: str,
) -> str:
    result = subprocess.run(
        [
            "systemctl",
            action,
            "docker",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    return result.stdout.strip()


def _output(
    command: list[str],
    *,
    timeout: int,
    include_stderr: bool = False,
) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"{' '.join(command)} failed."
        )

    if include_stderr:
        return (
            result.stdout
            + (
                "\n" + result.stderr
                if result.stderr
                else ""
            )
        ).strip()

    return result.stdout.strip()


def _run(
    command: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    process_environment = os.environ.copy()

    if environment:
        process_environment.update(environment)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=process_environment,
    )

    if result.returncode == 0:
        return

    raise RuntimeError(
        result.stderr.strip()
        or result.stdout.strip()
        or f"{' '.join(command)} failed."
    )
