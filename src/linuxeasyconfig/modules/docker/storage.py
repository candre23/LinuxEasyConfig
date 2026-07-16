from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATE_DIR = Path("/etc/linuxeasyconfig/docker")
MANAGED_CONTAINERS_PATH = STATE_DIR / "managed-containers.json"


@dataclass
class ManagedContainer:
    name: str
    image: str
    host_address: str
    host_port: int
    container_port: int
    protocol: str
    access_scope: str
    service_protocol: str
    reverse_proxy_compatible: bool
    public_host: str = ""


def load_managed_containers() -> list[ManagedContainer]:
    if not MANAGED_CONTAINERS_PATH.is_file():
        return []

    try:
        value = json.loads(
            MANAGED_CONTAINERS_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(value, list):
        return []

    result: list[ManagedContainer] = []

    for item in value:
        if not isinstance(item, dict):
            continue

        try:
            result.append(ManagedContainer(**item))
        except (TypeError, ValueError):
            continue

    return result


def save_managed_containers(
    containers: list[ManagedContainer],
) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o755)

    temporary = MANAGED_CONTAINERS_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            [asdict(item) for item in containers],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o644)
    temporary.replace(MANAGED_CONTAINERS_PATH)
    MANAGED_CONTAINERS_PATH.chmod(0o644)


def upsert_managed_container(
    container: ManagedContainer,
) -> None:
    containers = [
        item
        for item in load_managed_containers()
        if item.name != container.name
    ]
    containers.append(container)
    save_managed_containers(containers)


def remove_managed_container(name: str) -> None:
    save_managed_containers(
        [
            item
            for item in load_managed_containers()
            if item.name != name
        ]
    )
