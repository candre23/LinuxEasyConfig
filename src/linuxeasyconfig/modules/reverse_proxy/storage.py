from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATE_DIR = Path("/etc/linuxeasyconfig/reverse_proxy")
RULES_STATE = STATE_DIR / "routes.json"
CREDENTIALS_STATE = STATE_DIR / "credentials.json"
SETTINGS_STATE = STATE_DIR / "settings.json"


@dataclass
class ProxyCredential:
    username: str
    password_hash: str


@dataclass
class ProxyRule:
    name: str
    public_host: str
    route_type: str
    backend_host: str
    backend_port: int
    backend_https: bool
    enabled: bool = True
    path: str = ""
    strip_path: bool = True
    require_login: bool = False
    credential_username: str = ""
    credential_usernames: list[str] | None = None

    def __post_init__(self) -> None:
        usernames = [
            str(value).strip()
            for value in (self.credential_usernames or [])
            if str(value).strip()
        ]

        if self.credential_username.strip():
            legacy = self.credential_username.strip()
            if legacy not in usernames:
                usernames.insert(0, legacy)

        self.credential_usernames = list(dict.fromkeys(usernames))

        if self.route_type == "credential":
            self.credential_username = (
                self.credential_usernames[0]
                if self.credential_usernames
                else ""
            )
        elif not self.credential_username and len(self.credential_usernames) == 1:
            self.credential_username = self.credential_usernames[0]


@dataclass
class ProtectionSettings:
    enabled: bool = True
    preset: str = "Balanced"
    max_attempts: int = 5
    find_minutes: int = 10
    ban_minutes: int = 60
    permanent: bool = False
    incremental: bool = True
    never_block: list[str] | None = None

    def __post_init__(self) -> None:
        if self.never_block is None:
            self.never_block = ["127.0.0.1/8", "::1"]


def load_credentials() -> list[ProxyCredential]:
    return [
        ProxyCredential(**item)
        for item in _load_list(CREDENTIALS_STATE)
    ]


def load_rules() -> list[ProxyRule]:
    return [
        ProxyRule(**item)
        for item in _load_list(RULES_STATE)
    ]


def load_settings() -> ProtectionSettings:
    if not SETTINGS_STATE.exists():
        return ProtectionSettings()

    data = json.loads(
        SETTINGS_STATE.read_text(encoding="utf-8")
    )
    return ProtectionSettings(**data)


def save_credentials(
    credentials: list[ProxyCredential],
) -> None:
    _save_json(
        CREDENTIALS_STATE,
        [asdict(item) for item in credentials],
    )


def save_rules(rules: list[ProxyRule]) -> None:
    _save_json(
        RULES_STATE,
        [asdict(item) for item in rules],
    )


def save_settings(
    settings: ProtectionSettings,
) -> None:
    _save_json(
        SETTINGS_STATE,
        asdict(settings),
    )


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, list):
        raise ValueError(
            f"{path} does not contain a list."
        )

    return data


def _save_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o755,
    )
    path.parent.chmod(0o755)

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.chmod(0o644)
    temporary.replace(path)
    path.chmod(0o644)
