from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern


@dataclass(frozen=True)
class Interpretation:
    category: str
    summary: str
    explanation: str
    suggestion: str
    confidence: str


@dataclass(frozen=True)
class Rule:
    pattern: Pattern[str]
    interpretation: Interpretation
    sources: tuple[str, ...] = ()


def _rule(
    pattern: str,
    *,
    category: str,
    summary: str,
    explanation: str,
    suggestion: str,
    sources: tuple[str, ...] = (),
) -> Rule:
    return Rule(
        pattern=re.compile(pattern, re.IGNORECASE),
        interpretation=Interpretation(
            category=category,
            summary=summary,
            explanation=explanation,
            suggestion=suggestion,
            confidence="Known pattern",
        ),
        sources=sources,
    )


RULES = (
    _rule(
        r"failed password for|authentication failure",
        category="Security",
        summary="Failed login attempt",
        explanation=(
            "A login attempt was rejected because the account, "
            "password, or authentication method was not accepted."
        ),
        suggestion=(
            "Repeated attempts from unfamiliar addresses may be "
            "internet scanning. Confirm SSH password login and "
            "Fail2ban settings are appropriate."
        ),
        sources=("sshd", "ssh", "sudo", "pam"),
    ),
    _rule(
        r"invalid user",
        category="Security",
        summary="Login attempted for an unknown account",
        explanation=(
            "A remote or local process tried to authenticate as a "
            "user account that does not exist."
        ),
        suggestion=(
            "Isolated attempts are common on internet-facing SSH. "
            "Investigate repeated attempts or unexpected local sources."
        ),
        sources=("sshd", "ssh"),
    ),
    _rule(
        r"accepted (password|publickey)",
        category="Security",
        summary="Successful SSH login",
        explanation=(
            "SSH accepted credentials and opened a user session."
        ),
        suggestion=(
            "Confirm the account, source address, and time are expected."
        ),
        sources=("sshd", "ssh"),
    ),
    _rule(
        r"sudo:.*(command=|session opened)",
        category="Security",
        summary="Administrator command executed",
        explanation=(
            "A user invoked sudo or opened an administrator session."
        ),
        suggestion=(
            "Confirm the user and command are expected if this event "
            "was not caused by an LEC operation."
        ),
        sources=("sudo",),
    ),
    _rule(
        r"out of memory|oom-killer|killed process",
        category="Memory",
        summary="System ran critically low on memory",
        explanation=(
            "Linux invoked its out-of-memory protection and may have "
            "terminated a process to keep the system responsive."
        ),
        suggestion=(
            "Check memory usage, swap availability, and the named "
            "process. Repeated events require capacity or workload changes."
        ),
    ),
    _rule(
        r"i/o error|buffer i/o error|blk_update_request",
        category="Storage",
        summary="Storage input/output error",
        explanation=(
            "The kernel reported that a read or write operation could "
            "not be completed reliably."
        ),
        suggestion=(
            "Check Disk Health immediately and inspect cabling, SMART "
            "data, filesystem status, and recent power interruptions."
        ),
    ),
    _rule(
        r"filesystem.*(error|corrupt)|ext4-fs error|xfs.*corrupt",
        category="Storage",
        summary="Filesystem error detected",
        explanation=(
            "The filesystem reported an inconsistency or damaged metadata."
        ),
        suggestion=(
            "Back up important data and plan an offline filesystem check. "
            "Review disk health before attempting repairs."
        ),
    ),
    _rule(
        r"failed to mount|mount.*failed|dependency failed for .*mount",
        category="Storage",
        summary="A filesystem or network share failed to mount",
        explanation=(
            "Linux could not attach a configured filesystem or share."
        ),
        suggestion=(
            "Check the Mounts & Shares module, target availability, "
            "credentials, and the related systemd mount unit."
        ),
    ),
    _rule(
        r"link is down|network is unreachable|no route to host",
        category="Network",
        summary="Network connectivity was unavailable",
        explanation=(
            "A network interface or route was unavailable when a "
            "connection was attempted."
        ),
        suggestion=(
            "Check interface state, gateway, DNS, and whether the remote "
            "service was reachable at this time."
        ),
    ),
    _rule(
        r"name or service not known|temporary failure in name resolution",
        category="Network",
        summary="DNS lookup failed",
        explanation=(
            "The system could not translate a hostname into an IP address."
        ),
        suggestion=(
            "Check internet connectivity and configured DNS servers. "
            "Transient failures may clear without intervention."
        ),
    ),
    _rule(
        r"certificate.*(expired|not yet valid)|tls.*handshake.*error|acme.*error",
        category="Certificates",
        summary="TLS or certificate operation failed",
        explanation=(
            "A secure connection or automatic certificate operation "
            "could not be completed."
        ),
        suggestion=(
            "Check hostname DNS, system time, ports 80/443, and the "
            "Reverse Proxy certificate details."
        ),
        sources=("caddy",),
    ),
    _rule(
        r"start request repeated too quickly",
        category="Service",
        summary="Service repeatedly failed to start",
        explanation=(
            "systemd stopped restarting a service because it failed too "
            "many times in a short period."
        ),
        suggestion=(
            "Open the service-specific logs and inspect the messages "
            "immediately before this event."
        ),
    ),
    _rule(
        r"failed with result|main process exited.*failure",
        category="Service",
        summary="Service stopped with an error",
        explanation=(
            "A systemd service process exited unsuccessfully."
        ),
        suggestion=(
            "Inspect earlier messages from the same service to find the "
            "underlying application error."
        ),
    ),
    _rule(
        r"segfault|general protection fault",
        category="Application",
        summary="Application crashed",
        explanation=(
            "A process attempted an invalid memory operation and was "
            "terminated by the kernel."
        ),
        suggestion=(
            "Identify the process and package version. Repeated crashes "
            "may require an update, configuration change, or bug report."
        ),
    ),
    _rule(
        r"thermal.*(critical|throttl)|temperature above threshold",
        category="Hardware",
        summary="Hardware temperature warning",
        explanation=(
            "The system reported excessive temperature or reduced "
            "performance to protect hardware."
        ),
        suggestion=(
            "Check airflow, fans, dust, room temperature, and Hardware "
            "Monitor readings."
        ),
    ),
    _rule(
        r"docker.*(failed|error)|container.*(exited|unhealthy)",
        category="Docker",
        summary="Docker container problem",
        explanation=(
            "Docker reported a failed operation, exited container, or "
            "unhealthy application."
        ),
        suggestion=(
            "Open the Docker module and inspect the affected container's "
            "state and application logs."
        ),
        sources=("docker", "dockerd", "containerd"),
    ),
)


def interpret(
    *,
    message: str,
    source: str,
    unit: str,
    severity: str,
) -> Interpretation:
    searchable_source = (
        source + " " + unit
    ).lower()

    for rule in RULES:
        if (
            rule.sources
            and not any(
                token in searchable_source
                for token in rule.sources
            )
        ):
            continue

        if rule.pattern.search(message):
            return rule.interpretation

    category = _infer_category(source, unit, message)

    if severity in {"Emergency", "Alert", "Critical", "Error"}:
        return Interpretation(
            category=category,
            summary="Error reported by " + (source or unit or "the system"),
            explanation=(
                "The source reported an error, but LEC does not yet "
                "have a specific interpretation rule for this message."
            ),
            suggestion=(
                "Review nearby messages from the same source and search "
                "for the exact error text if the problem persists."
            ),
            confidence="Likely interpretation",
        )

    if severity == "Warning":
        return Interpretation(
            category=category,
            summary="Warning reported by " + (source or unit or "the system"),
            explanation=(
                "The source reported a condition worth reviewing, but "
                "it may not indicate an active failure."
            ),
            suggestion=(
                "Check whether the warning repeats or corresponds to "
                "a visible service problem."
            ),
            confidence="Likely interpretation",
        )

    return Interpretation(
        category=category,
        summary=message[:120] or "Log event",
        explanation="No additional interpretation is available.",
        suggestion="No action is normally required for routine information.",
        confidence="Raw message only",
    )


def _infer_category(
    source: str,
    unit: str,
    message: str,
) -> str:
    value = f"{source} {unit} {message}".lower()

    checks = (
        ("Security", ("ssh", "sudo", "pam", "login", "auth")),
        ("Docker", ("docker", "containerd", "container")),
        ("Certificates", ("caddy", "certificate", "tls", "acme")),
        ("Storage", ("disk", "mount", "filesystem", "ext4", "xfs")),
        ("Network", ("network", "ethernet", "wifi", "dns", "dhcp")),
        ("Hardware", ("thermal", "temperature", "usb", "pci", "firmware")),
        ("Kernel", ("kernel",)),
    )

    for category, tokens in checks:
        if any(token in value for token in tokens):
            return category

    return "Service"
