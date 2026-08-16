from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.writer import ConfigurationWriter

from .installer import (
    ACCESS_LOG,
    AUDIT_PATH,
    BACKUP_ROOT,
    CADDYFILE,
    FAIL2BAN_JAIL,
    MODULE_ID,
    ROUTES_FILE,
    TextConfiguration,
    _run_service_command,
    _set_caddy_configuration_permissions,
)
from .storage import (
    ProtectionSettings,
    ProxyCredential,
    ProxyRule,
    load_credentials,
    load_rules,
    load_settings,
    save_credentials,
    save_rules,
    save_settings,
)


_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
_HOST_PATTERN = re.compile(
    r"^(?:\*\.)?[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
)
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def create_or_update_credential(
    *,
    original_username: str,
    username: str,
    password: str,
) -> str:
    username = username.strip()
    original_username = original_username.strip()

    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Usernames may contain letters, numbers, periods, "
            "underscores, and hyphens."
        )

    credentials = load_credentials()
    existing = next(
        (
            item
            for item in credentials
            if item.username == original_username
        ),
        None,
    )

    duplicate = next(
        (
            item
            for item in credentials
            if item.username == username
            and item is not existing
        ),
        None,
    )
    if duplicate is not None:
        raise ValueError(
            f"A credential named {username} already exists."
        )

    if password:
        password_hash = _hash_password(password)
    elif existing is not None:
        password_hash = existing.password_hash
    else:
        raise ValueError(
            "Enter a password for the new credential."
        )

    previous = load_credentials()
    previous_rules = load_rules()

    if existing is None:
        credentials.append(
            ProxyCredential(
                username=username,
                password_hash=password_hash,
            )
        )
        action = "created"
    else:
        old_name = existing.username
        existing.username = username
        existing.password_hash = password_hash
        for rule in previous_rules:
            if rule.credential_username == old_name:
                rule.credential_username = username
        action = "updated"

    _apply_proxy_configuration(
        credentials=credentials,
        rules=previous_rules,
        previous_credentials=previous,
        previous_rules=load_rules(),
    )

    return f"Credential {username} was {action}."


def delete_credential(*, username: str) -> str:
    username = username.strip()
    credentials = load_credentials()
    rules = load_rules()

    used_by = [
        rule.name
        for rule in rules
        if rule.credential_username == username
    ]
    if used_by:
        raise ValueError(
            "This credential is used by: "
            + ", ".join(used_by)
            + ". Modify or remove those rules first."
        )

    updated = [
        item
        for item in credentials
        if item.username != username
    ]
    if len(updated) == len(credentials):
        raise ValueError(
            f"Credential {username} was not found."
        )

    _apply_proxy_configuration(
        credentials=updated,
        rules=rules,
        previous_credentials=credentials,
        previous_rules=rules,
    )
    return f"Credential {username} was removed."


def create_or_update_rule(
    *,
    original_name: str,
    data: dict[str, object],
) -> str:
    rule = _rule_from_data(data)
    rules = load_rules()
    credentials = load_credentials()
    original_name = original_name.strip()

    existing = next(
        (
            item
            for item in rules
            if item.name == original_name
        ),
        None,
    )

    duplicate = next(
        (
            item
            for item in rules
            if item.name == rule.name
            and item is not existing
        ),
        None,
    )
    if duplicate is not None:
        raise ValueError(
            f"A rule named {rule.name} already exists."
        )

    selected_usernames = list(
        rule.credential_usernames or []
    )

    if rule.require_login or rule.route_type == "credential":
        if not credentials:
            raise ValueError(
                "Create at least one credential before enabling login."
            )
        if not selected_usernames:
            raise ValueError(
                "Select at least one credential for this protected rule."
            )

        known_usernames = {
            item.username
            for item in credentials
        }
        unknown = [
            username
            for username in selected_usernames
            if username not in known_usernames
        ]
        if unknown:
            raise ValueError(
                "These selected credentials do not exist: "
                + ", ".join(unknown)
            )

    if rule.route_type == "credential":
        if len(selected_usernames) != 1:
            raise ValueError(
                "Authenticated-username routing requires exactly "
                "one selected credential."
            )
        rule.credential_username = selected_usernames[0]

    candidate_rules = [
        item
        for item in rules
        if item is not existing
    ] + [rule]

    # Legacy "Authenticated username" routing depends on a hostname-level
    # authentication context. Do not mix that legacy mode with ordinary
    # host/path rules on the same hostname; ordinary rules use per-rule
    # authentication below.
    same_host = [
        item
        for item in candidate_rules
        if item.public_host == rule.public_host
        and item.enabled
    ]
    has_credential_routes = any(
        item.route_type == "credential"
        for item in same_host
    )
    has_ordinary_routes = any(
        item.route_type != "credential"
        for item in same_host
    )
    if has_credential_routes and has_ordinary_routes:
        raise ValueError(
            "Authenticated-username routes cannot share a public "
            "hostname with ordinary host or path routes. Use a "
            "separate hostname for the authenticated-username route."
        )

    previous_rules = load_rules()

    if existing is None:
        rules.append(rule)
        action = "created"
    else:
        index = rules.index(existing)
        rules[index] = rule
        action = "updated"

    _apply_proxy_configuration(
        credentials=credentials,
        rules=rules,
        previous_credentials=credentials,
        previous_rules=previous_rules,
    )
    return f"Proxy rule {rule.name} was {action}."


def delete_rule(*, name: str) -> str:
    rules = load_rules()
    credentials = load_credentials()
    updated = [
        item for item in rules if item.name != name
    ]
    if len(updated) == len(rules):
        raise ValueError(
            f"Proxy rule {name} was not found."
        )

    _apply_proxy_configuration(
        credentials=credentials,
        rules=updated,
        previous_credentials=credentials,
        previous_rules=rules,
    )
    return f"Proxy rule {name} was removed."


def update_protection_settings(
    *,
    data: dict[str, object],
) -> str:
    settings = ProtectionSettings(
        enabled=bool(data.get("enabled", True)),
        preset=str(data.get("preset", "Custom")),
        max_attempts=int(data.get("max_attempts", 5)),
        find_minutes=int(data.get("find_minutes", 10)),
        ban_minutes=int(data.get("ban_minutes", 60)),
        incremental=bool(data.get("incremental", True)),
        never_block=[
            value.strip()
            for value in str(
                data.get("never_block", "")
            ).replace(",", "\n").splitlines()
            if value.strip()
        ],
    )

    if not 1 <= settings.max_attempts <= 100:
        raise ValueError(
            "Failed attempts allowed must be between 1 and 100."
        )
    if not 1 <= settings.find_minutes <= 10080:
        raise ValueError(
            "Failure counting period must be between 1 minute "
            "and 7 days."
        )
    if not 1 <= settings.ban_minutes <= 525600:
        raise ValueError(
            "Block duration must be between 1 minute and 1 year."
        )

    for address in settings.never_block or []:
        try:
            ipaddress.ip_network(
                address,
                strict=False,
            )
        except ValueError as exc:
            raise ValueError(
                f"{address} is not a valid IP address or network."
            ) from exc

    previous = load_settings()
    writer = _writer()

    try:
        writer.write(
            module_id=MODULE_ID,
            destination=FAIL2BAN_JAIL,
            document=TextConfiguration(
                render_fail2ban_jail(settings)
            ),
        )
        os.chmod(FAIL2BAN_JAIL, 0o644)
        _set_fail2ban_configuration_permissions()
        _run(
            ["fail2ban-client", "-t"],
            timeout=60,
        )
        _run_service_command(
            ["fail2ban-client", "reload"],
            service="fail2ban",
            timeout=60,
        )
        save_settings(settings)
        _set_reverse_proxy_state_permissions()
    except Exception:
        writer.write(
            module_id=MODULE_ID,
            destination=FAIL2BAN_JAIL,
            document=TextConfiguration(
                render_fail2ban_jail(previous)
            ),
        )
        os.chmod(FAIL2BAN_JAIL, 0o644)
        _set_fail2ban_configuration_permissions()
        save_settings(previous)
        _set_reverse_proxy_state_permissions()
        raise

    return "Intrusion protection settings were updated."



def read_recent_activity(
    *,
    maximum_lines: int = 300,
) -> str:
    maximum_lines = max(
        1,
        min(int(maximum_lines), 2000),
    )

    try:
        lines = ACCESS_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except FileNotFoundError:
        lines = []
    except OSError as exc:
        raise RuntimeError(
            f"Could not read {ACCESS_LOG}: {exc}"
        ) from exc

    return json.dumps(lines[-maximum_lines:])


def _set_fail2ban_configuration_permissions() -> None:
    """
    Fail2Ban configuration tests may be run by the desktop user,
    while the service reads them as root. Standard Fail2Ban
    configuration files are non-secret and should be readable.
    """
    filter_path = Path(
        "/etc/fail2ban/filter.d/lec-caddy-auth.conf"
    )
    jail_path = Path(
        "/etc/fail2ban/jail.d/lec-caddy-auth.local"
    )

    for directory in (
        filter_path.parent,
        jail_path.parent,
    ):
        if directory.exists():
            os.chmod(directory, 0o755)

    for path in (
        filter_path,
        jail_path,
    ):
        if path.exists():
            os.chmod(path, 0o644)



def _set_reverse_proxy_state_permissions() -> None:
    state_directory = Path(
        "/etc/linuxeasyconfig/reverse_proxy"
    )
    state_directory.mkdir(
        parents=True,
        exist_ok=True,
    )
    os.chmod(state_directory, 0o755)

    for filename in (
        "credentials.json",
        "routes.json",
        "settings.json",
    ):
        path = state_directory / filename
        if path.exists():
            os.chmod(path, 0o644)


def render_routes(
    credentials: list[ProxyCredential],
    rules: list[ProxyRule],
) -> str:
    lines = [
        "# Created by Linux Easy Config",
        "# Module: org.linuxeasyconfig.reverse_proxy",
        "",
    ]

    enabled_rules = [
        rule for rule in rules if rule.enabled
    ]

    credentials_by_username = {
        credential.username: credential
        for credential in credentials
    }

    hosts = sorted(
        {rule.public_host for rule in enabled_rules}
    )

    for host in hosts:
        host_rules = [
            rule
            for rule in enabled_rules
            if rule.public_host == host
        ]
        lines.append(f"{host} {{")
        lines.extend(
            [
                "    log {",
                f"        output file {ACCESS_LOG} {{",
                "            roll_size 10MiB",
                "            roll_keep 10",
                "            roll_keep_for 720h",
                "        }",
                "        format json",
                "    }",
            ]
        )

        legacy_usernames = sorted(
            {
                rule.credential_username
                for rule in host_rules
                if (
                    rule.route_type == "credential"
                    and rule.credential_username
                )
            }
        )
        if legacy_usernames:
            lines.append("    basic_auth {")
            for username in legacy_usernames:
                credential = credentials_by_username.get(
                    username
                )
                if credential is None:
                    raise ValueError(
                        f"Credential {username} is required by an "
                        "enabled proxy rule but does not exist."
                    )
                lines.append(
                    f"        {credential.username} "
                    f"{credential.password_hash}"
                )
            lines.append("    }")

        for index, rule in enumerate(host_rules, 1):
            backend = (
                f"{'https' if rule.backend_https else 'http'}://"
                f"{rule.backend_host}:{rule.backend_port}"
            )

            def append_rule_auth(indent: str) -> None:
                if not rule.require_login:
                    return

                usernames = list(
                    rule.credential_usernames or []
                )
                if not usernames:
                    raise ValueError(
                        f"Rule {rule.name} requires Caddy login but "
                        "has no selected credentials."
                    )

                lines.append(f"{indent}basic_auth {{")
                for username in usernames:
                    credential = credentials_by_username.get(
                        username
                    )
                    if credential is None:
                        raise ValueError(
                            f"Credential {username} is required by "
                            f"rule {rule.name} but does not exist."
                        )
                    lines.append(
                        f"{indent}    {credential.username} "
                        f"{credential.password_hash}"
                    )
                lines.append(f"{indent}}}")

            if rule.route_type == "path":
                directive = (
                    "handle_path"
                    if rule.strip_path
                    else "handle"
                )
                lines.append(
                    f"    {directive} {rule.path}* {{"
                )
                append_rule_auth("        ")
                lines.append(
                    f"        reverse_proxy {backend}"
                )
                lines.append("    }")
            elif rule.route_type == "credential":
                matcher = f"lec_user_{index}"
                lines.append(
                    f"    @{matcher} expression "
                    f'`{{http.auth.user.id}} == '
                    f'"{rule.credential_username}"`'
                )
                lines.append(
                    f"    handle @{matcher} {{"
                )
                lines.append(
                    f"        reverse_proxy {backend}"
                )
                lines.append("    }")
            else:
                lines.append("    handle {")
                append_rule_auth("        ")
                lines.append(
                    f"        reverse_proxy {backend}"
                )
                lines.append("    }")

        lines.append("}")
        lines.append("")

    if not enabled_rules:
        lines.extend(
            [
                "# No enabled proxy rules.",
                "",
            ]
        )

    return "\n".join(lines)

def render_fail2ban_jail(
    settings: ProtectionSettings,
) -> str:
    ignore = " ".join(
        settings.never_block
        or ["127.0.0.1/8", "::1"]
    )
    incremental = (
        "true" if settings.incremental else "false"
    )
    enabled = "true" if settings.enabled else "false"

    return f"""# Created by Linux Easy Config
# Module: org.linuxeasyconfig.reverse_proxy

[lec-caddy-auth]
enabled = {enabled}
filter = lec-caddy-auth
logpath = {ACCESS_LOG}
backend = auto
port = http,https
maxretry = {settings.max_attempts}
findtime = {settings.find_minutes}m
bantime = {settings.ban_minutes}m
bantime.increment = {incremental}
ignoreip = {ignore}
"""


def _apply_proxy_configuration(
    *,
    credentials: list[ProxyCredential],
    rules: list[ProxyRule],
    previous_credentials: list[ProxyCredential],
    previous_rules: list[ProxyRule],
) -> None:
    writer = _writer()

    try:
        writer.write(
            module_id=MODULE_ID,
            destination=ROUTES_FILE,
            document=TextConfiguration(
                render_routes(credentials, rules)
            ),
        )
        _set_caddy_configuration_permissions()
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
        _run_service_command(
            ["systemctl", "reload", "caddy"],
            service="caddy",
            timeout=60,
        )
        save_credentials(credentials)
        save_rules(rules)
        _set_reverse_proxy_state_permissions()
    except Exception:
        writer.write(
            module_id=MODULE_ID,
            destination=ROUTES_FILE,
            document=TextConfiguration(
                render_routes(
                    previous_credentials,
                    previous_rules,
                )
            ),
        )
        _set_caddy_configuration_permissions()
        save_credentials(previous_credentials)
        save_rules(previous_rules)
        _set_reverse_proxy_state_permissions()
        raise


def _rule_from_data(
    data: dict[str, object],
) -> ProxyRule:
    name = str(data.get("name", "")).strip()
    public_host = str(
        data.get("public_host", "")
    ).strip().lower()
    route_type = str(
        data.get("route_type", "host")
    ).strip()
    backend_host = str(
        data.get("backend_host", "")
    ).strip()
    backend_port = int(
        data.get("backend_port", 0)
    )
    path = str(data.get("path", "")).strip()
    raw_usernames = data.get(
        "credential_usernames",
        [],
    )
    if isinstance(raw_usernames, (list, tuple)):
        credential_usernames = [
            str(value).strip()
            for value in raw_usernames
            if str(value).strip()
        ]
    else:
        credential_usernames = []

    credential_username = str(
        data.get("credential_username", "")
    ).strip()
    if (
        credential_username
        and credential_username not in credential_usernames
    ):
        credential_usernames.insert(
            0,
            credential_username,
        )

    if not _NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "Rule names may contain letters, numbers, spaces, "
            "periods, underscores, and hyphens."
        )
    if not _HOST_PATTERN.fullmatch(public_host):
        raise ValueError(
            "Enter a valid public hostname, such as "
            "photos.example.com."
        )
    if route_type not in {
        "host",
        "path",
        "credential",
    }:
        raise ValueError(
            "The selected routing method is invalid."
        )
    if not backend_host or any(
        character.isspace()
        for character in backend_host
    ):
        raise ValueError(
            "Enter a valid internal server name or IP address."
        )
    if not 1 <= backend_port <= 65535:
        raise ValueError(
            "Internal port must be between 1 and 65535."
        )
    if route_type == "path":
        if not path.startswith("/"):
            raise ValueError(
                "URL paths must begin with /."
            )
        path = path.rstrip("/") or "/"

    return ProxyRule(
        name=name,
        public_host=public_host,
        route_type=route_type,
        backend_host=backend_host,
        backend_port=backend_port,
        backend_https=bool(
            data.get("backend_https", False)
        ),
        enabled=bool(data.get("enabled", True)),
        path=path,
        strip_path=bool(
            data.get("strip_path", True)
        ),
        require_login=bool(
            data.get("require_login", False)
        ),
        credential_username=credential_username,
        credential_usernames=credential_usernames,
    )


def _hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError(
            "Passwords must contain at least 8 characters."
        )

    result = subprocess.run(
        [
            "caddy",
            "hash-password",
            "--plaintext",
            password,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "Caddy could not hash the password."
        )
    return result.stdout.strip()


def _writer() -> ConfigurationWriter:
    return ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )


def _run(
    command: list[str],
    *,
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
    raise RuntimeError(
        result.stderr.strip()
        or result.stdout.strip()
        or f"{' '.join(command)} failed."
    )
