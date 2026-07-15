from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter


MODULE_ID = "org.linuxeasyconfig.reverse_proxy"
BACKUP_ROOT = Path(
    "/var/lib/linuxeasyconfig/backups"
)
AUDIT_PATH = Path(
    "/var/lib/linuxeasyconfig/audit.jsonl"
)

CADDYFILE = Path("/etc/caddy/Caddyfile")
LEC_CADDY_DIR = Path("/etc/caddy/lec")
ROUTES_FILE = LEC_CADDY_DIR / "routes.caddy"

FAIL2BAN_FILTER = Path(
    "/etc/fail2ban/filter.d/lec-caddy-auth.conf"
)
FAIL2BAN_JAIL = Path(
    "/etc/fail2ban/jail.d/lec-caddy-auth.local"
)

CADDY_LOG_DIR = Path("/var/log/caddy")
ACCESS_LOG = CADDY_LOG_DIR / "lec-access.json"

CADDY_KEYRING = Path(
    "/usr/share/keyrings/"
    "caddy-stable-archive-keyring.gpg"
)
CADDY_SOURCE = Path(
    "/etc/apt/sources.list.d/"
    "caddy-stable.list"
)

_IMPORT_MARKER = (
    "# Created by Linux Easy Config\n"
    "import /etc/caddy/lec/*.caddy"
)


class TextConfiguration(ConfigurationDocument):
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        return (
            self._text
            if self._text.endswith("\n")
            else self._text + "\n"
        )


def install_reverse_proxy_system() -> str:
    """
    Install Caddy and Fail2Ban and create LEC's base configuration.

    This function is intentionally restartable. Every phase checks the
    current system state before performing work.
    """

    _install_required_packages()
    _install_caddy_repository()
    _install_caddy_and_fail2ban()
    _create_runtime_paths()
    _write_base_configuration()
    _set_caddy_configuration_permissions()
    _set_fail2ban_configuration_permissions()
    _validate_configuration()
    _enable_and_start_services()

    return (
        "Reverse proxy system installed successfully. "
        "Caddy and Fail2Ban are enabled and running."
    )


def service_action(
    *,
    service: str,
    action: str,
) -> str:
    if service not in {
        "caddy",
        "fail2ban",
    }:
        raise ValueError(
            "The selected service is invalid."
        )

    if action not in {
        "start",
        "stop",
        "restart",
        "enable",
        "disable",
    }:
        raise ValueError(
            "The selected service action is invalid."
        )

    _run(
        [
            "systemctl",
            action,
            service,
        ],
        timeout=90,
    )

    labels = {
        "start": "started",
        "stop": "stopped",
        "restart": "restarted",
        "enable": "enabled at startup",
        "disable": "disabled at startup",
    }

    return (
        f"{service.title()} was "
        f"{labels[action]}."
    )


def reload_reverse_proxy_system() -> str:
    _validate_configuration()

    _run(
        [
            "systemctl",
            "reload",
            "caddy",
        ],
        timeout=60,
    )
    _run(
        [
            "fail2ban-client",
            "reload",
        ],
        timeout=60,
    )

    return (
        "Caddy and Fail2Ban reloaded successfully."
    )


def unban_address(
    *,
    address: str,
) -> str:
    address = address.strip()

    if not address or any(
        character.isspace()
        for character in address
    ):
        raise ValueError(
            "The selected address is invalid."
        )

    _run(
        [
            "fail2ban-client",
            "set",
            "lec-caddy-auth",
            "unbanip",
            address,
        ],
        timeout=30,
    )

    return f"Unbanned {address}."


def _install_required_packages() -> None:
    _run(
        [
            "apt-get",
            "update",
        ],
        timeout=600,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )

    _run(
        [
            "apt-get",
            "install",
            "-y",
            "debian-keyring",
            "debian-archive-keyring",
            "apt-transport-https",
            "curl",
            "gnupg",
            "ca-certificates",
        ],
        timeout=900,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )


def _install_caddy_repository() -> None:
    if (
        CADDY_KEYRING.is_file()
        and CADDY_SOURCE.is_file()
    ):
        return

    with tempfile.TemporaryDirectory(
        prefix="lec-caddy-repo-"
    ) as temporary_directory:
        temporary = Path(
            temporary_directory
        )
        key = temporary / "caddy.key"
        keyring = temporary / "caddy.gpg"
        source = temporary / "caddy.list"

        _run(
            [
                "curl",
                "-1sLf",
                (
                    "https://dl.cloudsmith.io/public/"
                    "caddy/stable/gpg.key"
                ),
                "-o",
                str(key),
            ],
            timeout=120,
        )

        _run(
            [
                "gpg",
                "--batch",
                "--yes",
                "--dearmor",
                "--output",
                str(keyring),
                str(key),
            ],
            timeout=120,
        )

        _run(
            [
                "curl",
                "-1sLf",
                (
                    "https://dl.cloudsmith.io/public/"
                    "caddy/stable/debian.deb.txt"
                ),
                "-o",
                str(source),
            ],
            timeout=120,
        )

        CADDY_KEYRING.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        CADDY_SOURCE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copyfile(
            keyring,
            CADDY_KEYRING,
        )
        shutil.copyfile(
            source,
            CADDY_SOURCE,
        )

        os.chmod(CADDY_KEYRING, 0o644)
        os.chmod(CADDY_SOURCE, 0o644)


def _install_caddy_and_fail2ban() -> None:
    _run(
        [
            "apt-get",
            "update",
        ],
        timeout=600,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )

    _run(
        [
            "apt-get",
            "install",
            "-y",
            "caddy",
            "fail2ban",
        ],
        timeout=1200,
        environment={
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )


def _create_runtime_paths() -> None:
    LEC_CADDY_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o755,
    )
    CADDY_LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o750,
    )

    ACCESS_LOG.touch(
        exist_ok=True,
    )

    try:
        shutil.chown(
            CADDY_LOG_DIR,
            user="caddy",
            group="caddy",
        )
        shutil.chown(
            ACCESS_LOG,
            user="caddy",
            group="caddy",
        )
    except LookupError as exc:
        raise RuntimeError(
            "The Caddy package did not create its "
            "expected caddy user and group."
        ) from exc

    os.chmod(CADDY_LOG_DIR, 0o750)
    os.chmod(ACCESS_LOG, 0o640)


def _write_base_configuration() -> None:
    writer = ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )

    current_caddyfile = (
        CADDYFILE.read_text(
            encoding="utf-8",
            errors="replace",
        )
        if CADDYFILE.exists()
        else ""
    )

    if _IMPORT_MARKER not in current_caddyfile:
        caddyfile = current_caddyfile

        if (
            caddyfile
            and not caddyfile.endswith("\n")
        ):
            caddyfile += "\n"

        if (
            caddyfile
            and not caddyfile.endswith("\n\n")
        ):
            caddyfile += "\n"

        caddyfile += _IMPORT_MARKER + "\n"

        writer.write(
            module_id=MODULE_ID,
            destination=CADDYFILE,
            document=TextConfiguration(
                caddyfile
            ),
        )

    if not ROUTES_FILE.exists():
        writer.write(
            module_id=MODULE_ID,
            destination=ROUTES_FILE,
            document=TextConfiguration(
                "# LEC-managed proxy routes\n"
                "# Rules created in the GUI appear here.\n"
            ),
        )

    writer.write(
        module_id=MODULE_ID,
        destination=FAIL2BAN_FILTER,
        document=TextConfiguration(
            _fail2ban_filter_text()
        ),
    )

    writer.write(
        module_id=MODULE_ID,
        destination=FAIL2BAN_JAIL,
        document=TextConfiguration(
            _fail2ban_jail_text()
        ),
    )



def _set_caddy_configuration_permissions() -> None:
    """
    ConfigurationWriter may preserve restrictive root-only modes.
    Caddy's systemd reload runs as the caddy user, so every imported
    directory must be traversable and every imported file readable.
    """
    LEC_CADDY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(LEC_CADDY_DIR, 0o755)

    for path in LEC_CADDY_DIR.glob("*.caddy"):
        if path.is_file():
            os.chmod(path, 0o644)

    if CADDYFILE.exists():
        os.chmod(CADDYFILE, 0o644)


def _set_fail2ban_configuration_permissions() -> None:
    for directory in (
        FAIL2BAN_FILTER.parent,
        FAIL2BAN_JAIL.parent,
    ):
        if directory.exists():
            os.chmod(directory, 0o755)

    for path in (
        FAIL2BAN_FILTER,
        FAIL2BAN_JAIL,
    ):
        if path.exists():
            os.chmod(path, 0o644)

def _validate_configuration() -> None:
    _run(
        [
            "caddy",
            "validate",
            "--config",
            str(CADDYFILE),
            "--adapter",
            "caddyfile",
        ],
        timeout=60,
    )

    _test_fail2ban_filter()

    _run(
        [
            "fail2ban-client",
            "-t",
        ],
        timeout=60,
    )


def _test_fail2ban_filter() -> None:
    sample = (
        '{"ts":1730000000.0,"request":'
        '{"remote_ip":"203.0.113.25"},'
        '"status":401}\n'
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="lec-caddy-log-",
        delete=False,
    ) as temporary:
        temporary.write(sample)
        temporary.flush()
        sample_path = Path(
            temporary.name
        )

    try:
        result = subprocess.run(
            [
                "fail2ban-regex",
                str(sample_path),
                str(FAIL2BAN_FILTER),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        sample_path.unlink(
            missing_ok=True
        )

    output = (
        result.stdout + "\n" + result.stderr
    )

    if (
        result.returncode != 0
        or "1 matched" not in output
    ):
        raise RuntimeError(
            "The generated Fail2Ban filter did not "
            "match the expected Caddy authentication "
            f"failure log entry.\n\n{output.strip()}"
        )


def _enable_and_start_services() -> None:
    caddy_was_active = _service_is_active("caddy")
    fail2ban_was_active = _service_is_active("fail2ban")

    _run(
        ["systemctl", "enable", "--now", "caddy"],
        timeout=120,
    )
    _run(
        ["systemctl", "enable", "--now", "fail2ban"],
        timeout=120,
    )

    # A newly started service has already loaded the generated
    # configuration. Reload only when it was running before setup.
    if caddy_was_active:
        _run_service_command(
            ["systemctl", "reload", "caddy"],
            service="caddy",
            timeout=60,
        )

    if fail2ban_was_active:
        _run_service_command(
            ["fail2ban-client", "reload"],
            service="fail2ban",
            timeout=60,
        )

    for service in ("caddy", "fail2ban"):
        if not _service_is_active(service):
            raise RuntimeError(
                _service_failure_details(
                    service,
                    (
                        f"{service}.service did not remain "
                        "active after setup."
                    ),
                )
            )


def _service_is_active(service: str) -> bool:
    result = subprocess.run(
        [
            "systemctl",
            "is-active",
            "--quiet",
            service,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.returncode == 0


def _run_service_command(
    command: list[str],
    *,
    service: str,
    timeout: int,
) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode == 0:
        return

    primary = (
        result.stderr.strip()
        or result.stdout.strip()
        or (
            f"{command[0]} exited with code "
            f"{result.returncode}"
        )
    )

    raise RuntimeError(
        _service_failure_details(
            service,
            (
                f"{' '.join(command)} failed:\n\n"
                f"{primary}"
            ),
        )
    )


def _service_failure_details(
    service: str,
    heading: str,
) -> str:
    status = subprocess.run(
        [
            "systemctl",
            "status",
            f"{service}.service",
            "--no-pager",
            "--full",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    journal = subprocess.run(
        [
            "journalctl",
            "-u",
            f"{service}.service",
            "--no-pager",
            "--lines",
            "40",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    return "\n".join(
        [
            heading,
            "",
            "Service status:",
            (
                status.stdout.strip()
                or status.stderr.strip()
                or "Unavailable"
            ),
            "",
            "Recent service log:",
            (
                journal.stdout.strip()
                or journal.stderr.strip()
                or "Unavailable"
            ),
        ]
    )

def _fail2ban_filter_text() -> str:
    return """# Created by Linux Easy Config
# Module: org.linuxeasyconfig.reverse_proxy

[Definition]
failregex = ^.*"remote_ip":"<HOST>".*"status":401.*$
ignoreregex =
datepattern = "ts":{EPOCH}
"""


def _fail2ban_jail_text() -> str:
    return f"""# Created by Linux Easy Config
# Module: org.linuxeasyconfig.reverse_proxy

[lec-caddy-auth]
enabled = true
filter = lec-caddy-auth
logpath = {ACCESS_LOG}
backend = auto
port = http,https
maxretry = 5
findtime = 10m
bantime = 1h
"""


def _run(
    command: list[str],
    *,
    timeout: int,
    environment: dict[str, str] | None = None,
) -> None:
    process_environment = os.environ.copy()

    if environment:
        process_environment.update(
            environment
        )

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

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or (
            f"{command[0]} exited with code "
            f"{result.returncode}"
        )
    )

    raise RuntimeError(
        f"{' '.join(command)} failed:\n\n"
        f"{message}"
    )
