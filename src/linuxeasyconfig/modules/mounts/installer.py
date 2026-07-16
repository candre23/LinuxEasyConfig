from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from linuxeasyconfig.core.config.audit_log import AuditLog
from linuxeasyconfig.core.config.base import ConfigurationDocument
from linuxeasyconfig.core.config.writer import ConfigurationWriter


MODULE_ID = "org.linuxeasyconfig.mounts"
BACKUP_ROOT = Path("/var/lib/linuxeasyconfig/backups")
AUDIT_PATH = Path("/var/lib/linuxeasyconfig/audit.jsonl")
FSTAB_PATH = Path("/etc/fstab")
CREDENTIAL_ROOT = Path("/etc/linuxeasyconfig/credentials")


class RenderedConfiguration(ConfigurationDocument):
    def __init__(self, text: str) -> None:
        self._text = text

    def render(self) -> str:
        return (
            self._text
            if self._text.endswith("\n")
            else self._text + "\n"
        )


def install_network_share(
    *,
    protocol: str,
    source: str,
    mountpoint: str,
    filesystem: str,
    fstab_line: str,
    credential_path: str,
    credential_text: str,
    mount_now: bool,
) -> str:
    return _save_network_share(
        protocol=protocol,
        source=source,
        mountpoint=mountpoint,
        filesystem=filesystem,
        fstab_line=fstab_line,
        credential_path=credential_path,
        credential_text=credential_text,
        mount_now=mount_now,
        original_source="",
        original_mountpoint="",
    )


def update_network_share(
    *,
    protocol: str,
    source: str,
    mountpoint: str,
    filesystem: str,
    fstab_line: str,
    credential_path: str,
    credential_text: str,
    mount_now: bool,
    original_source: str,
    original_mountpoint: str,
) -> str:
    return _save_network_share(
        protocol=protocol,
        source=source,
        mountpoint=mountpoint,
        filesystem=filesystem,
        fstab_line=fstab_line,
        credential_path=credential_path,
        credential_text=credential_text,
        mount_now=mount_now,
        original_source=original_source,
        original_mountpoint=original_mountpoint,
    )


def install_local_folder_mount(
    *,
    source: str,
    mountpoint: str,
    fstab_line: str,
    mount_now: bool,
) -> str:
    return _save_local_folder_mount(
        source=source,
        mountpoint=mountpoint,
        fstab_line=fstab_line,
        mount_now=mount_now,
        original_source="",
        original_mountpoint="",
    )


def update_local_folder_mount(
    *,
    source: str,
    mountpoint: str,
    fstab_line: str,
    mount_now: bool,
    original_source: str,
    original_mountpoint: str,
) -> str:
    return _save_local_folder_mount(
        source=source,
        mountpoint=mountpoint,
        fstab_line=fstab_line,
        mount_now=mount_now,
        original_source=original_source,
        original_mountpoint=original_mountpoint,
    )


def _save_local_folder_mount(
    *,
    source: str,
    mountpoint: str,
    fstab_line: str,
    mount_now: bool,
    original_source: str,
    original_mountpoint: str,
) -> str:
    source_path = Path(source)

    if not source_path.is_absolute() or not source_path.is_dir():
        raise ValueError(
            "The source folder must be an existing absolute directory."
        )

    mountpoint_path = _validate_mountpoint(mountpoint)
    _validate_fstab_line(fstab_line)

    fields = fstab_line.split()

    if (
        len(fields) < 6
        or fields[2] != "none"
        or "bind" not in fields[3].split(",")
    ):
        raise ValueError(
            "The generated bind-mount entry is invalid."
        )

    current = FSTAB_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )
    editing = bool(
        original_source and original_mountpoint
    )

    if editing:
        new_fstab = _replace_lec_entry(
            current,
            original_source=original_source,
            original_mountpoint=original_mountpoint,
            protocol="LOCAL FOLDER",
            source=source,
            fstab_line=fstab_line,
        )
    else:
        _ensure_not_duplicate(
            current_fstab=current,
            source=source,
            mountpoint=mountpoint,
        )
        new_fstab = _append_entry(
            current,
            protocol="LOCAL FOLDER",
            source=source,
            fstab_line=fstab_line,
        )

    mountpoint_existed = mountpoint_path.exists()

    if mountpoint_existed and not mountpoint_path.is_dir():
        raise ValueError(
            "The selected mount point exists but is not a directory."
        )

    if not mountpoint_existed:
        mountpoint_path.mkdir(
            parents=True,
            exist_ok=False,
        )

    try:
        _verify_fstab(new_fstab)
    except Exception:
        if not mountpoint_existed:
            try:
                mountpoint_path.rmdir()
            except OSError:
                pass
        raise

    result = _writer().write(
        module_id=MODULE_ID,
        destination=FSTAB_PATH,
        document=RenderedConfiguration(new_fstab),
    )

    _run(
        ["systemctl", "daemon-reload"],
        timeout=30,
    )

    if editing and mount_now:
        _run(
            ["umount", original_mountpoint],
            timeout=60,
            allow_failure=True,
        )

    if mount_now:
        _run(["mount", mountpoint], timeout=60)

    verb = "Updated" if editing else "Saved"
    return (
        f"{verb} local folder mount {source} at "
        f"{mountpoint}; fstab revision {result.revision}."
    )


def mount_entry(*, mountpoint: str) -> str:
    path = _validate_mountpoint(mountpoint)
    _run(["mount", str(path)], timeout=60)
    return f"Mounted {path}."


def unmount_entry(*, mountpoint: str) -> str:
    path = _validate_mountpoint(mountpoint)
    _run(["umount", str(path)], timeout=60)
    return f"Unmounted {path}."


def remove_mount_entry(
    *,
    source: str,
    mountpoint: str,
    credential_path: str,
    unmount_first: bool,
) -> str:
    current = FSTAB_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if unmount_first:
        _run(
            ["umount", mountpoint],
            timeout=60,
            allow_failure=True,
        )

    updated = _remove_lec_entry(
        current,
        source=source,
        mountpoint=mountpoint,
    )
    _verify_fstab(updated)

    writer = _writer()
    result = writer.write(
        module_id=MODULE_ID,
        destination=FSTAB_PATH,
        document=RenderedConfiguration(updated),
    )

    if credential_path:
        credential = Path(credential_path)
        if (
            credential.parent == CREDENTIAL_ROOT
            and credential.is_file()
            and not credential.is_symlink()
        ):
            writer.delete(
                module_id=MODULE_ID,
                destination=credential,
            )

    _run(["systemctl", "daemon-reload"], timeout=30)

    path = Path(mountpoint)
    try:
        path.rmdir()
    except OSError:
        pass

    return (
        f"Removed {source} from /etc/fstab. "
        f"Backup revision {result.revision} was created."
    )


def _save_network_share(
    *,
    protocol: str,
    source: str,
    mountpoint: str,
    filesystem: str,
    fstab_line: str,
    credential_path: str,
    credential_text: str,
    mount_now: bool,
    original_source: str,
    original_mountpoint: str,
) -> str:
    _validate_protocol(protocol)
    _validate_source(source)
    mountpoint_path = _validate_mountpoint(mountpoint)
    _validate_filesystem(protocol, filesystem)
    _validate_fstab_line(fstab_line)

    current = FSTAB_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    editing = bool(original_source and original_mountpoint)

    if editing:
        new_fstab = _replace_lec_entry(
            current,
            original_source=original_source,
            original_mountpoint=original_mountpoint,
            protocol=protocol,
            source=source,
            fstab_line=fstab_line,
        )
    else:
        _ensure_not_duplicate(
            current_fstab=current,
            source=source,
            mountpoint=mountpoint,
        )
        new_fstab = _append_entry(
            current,
            protocol=protocol,
            source=source,
            fstab_line=fstab_line,
        )

    mountpoint_existed = mountpoint_path.exists()

    if mountpoint_existed and not mountpoint_path.is_dir():
        raise ValueError(
            "The selected mount point exists but is not a directory."
        )

    if not mountpoint_existed:
        mountpoint_path.mkdir(parents=True, exist_ok=False)

    try:
        _verify_fstab(new_fstab)
    except Exception:
        if not mountpoint_existed:
            try:
                mountpoint_path.rmdir()
            except OSError:
                pass
        raise

    writer = _writer()

    if credential_path and credential_text:
        destination = _validate_credential_path(credential_path)
        CREDENTIAL_ROOT.mkdir(
            parents=True,
            exist_ok=True,
            mode=0o700,
        )
        writer.write(
            module_id=MODULE_ID,
            destination=destination,
            document=RenderedConfiguration(credential_text),
        )
        os.chmod(destination, 0o600)

    fstab_result = writer.write(
        module_id=MODULE_ID,
        destination=FSTAB_PATH,
        document=RenderedConfiguration(new_fstab),
    )

    _run(["systemctl", "daemon-reload"], timeout=30)

    if editing and mount_now:
        _run(
            ["umount", original_mountpoint],
            timeout=60,
            allow_failure=True,
        )

    if mount_now:
        _run(["mount", mountpoint], timeout=60)

    verb = "Updated" if editing else "Saved"
    return (
        f"{verb} {source}; fstab revision "
        f"{fstab_result.revision}."
    )


def _writer() -> ConfigurationWriter:
    return ConfigurationWriter(
        backup_root=BACKUP_ROOT,
        audit_log=AuditLog(AUDIT_PATH),
    )


def _append_entry(
    current: str,
    *,
    protocol: str,
    source: str,
    fstab_line: str,
) -> str:
    text = current
    if text and not text.endswith("\n"):
        text += "\n"
    if text and not text.endswith("\n\n"):
        text += "\n"

    return (
        text
        + "# Created by Linux Easy Config\n"
        + "# Module: org.linuxeasyconfig.mounts\n"
        + f"# Network share: {protocol.upper()} {source}\n"
        + f"{fstab_line}\n"
    )


def _replace_lec_entry(
    current: str,
    *,
    original_source: str,
    original_mountpoint: str,
    protocol: str,
    source: str,
    fstab_line: str,
) -> str:
    lines = current.splitlines()
    index = _find_lec_entry_index(
        lines,
        source=original_source,
        mountpoint=original_mountpoint,
    )
    start = max(0, index - 3)
    replacement = [
        "# Created by Linux Easy Config",
        "# Module: org.linuxeasyconfig.mounts",
        f"# Network share: {protocol.upper()} {source}",
        fstab_line,
    ]
    lines[start:index + 1] = replacement
    return "\n".join(lines).rstrip() + "\n"


def _remove_lec_entry(
    current: str,
    *,
    source: str,
    mountpoint: str,
) -> str:
    lines = current.splitlines()
    index = _find_lec_entry_index(
        lines,
        source=source,
        mountpoint=mountpoint,
    )
    start = max(0, index - 3)
    del lines[start:index + 1]

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines) + "\n"


def _find_lec_entry_index(
    lines: list[str],
    *,
    source: str,
    mountpoint: str,
) -> int:
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        fields = line.split()
        if len(fields) < 2:
            continue

        if fields[1] == mountpoint:
            preceding = lines[max(0, index - 3):index]

            if "# Created by Linux Easy Config" not in preceding:
                raise ValueError(
                    "LEC will only modify or remove entries it created."
                )

            return index

    raise ValueError(
        "The selected persistent entry could not be found in /etc/fstab."
    )


def _verify_fstab(text: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="lec-fstab-",
        delete=False,
    ) as temporary:
        temporary.write(text)
        temporary.flush()
        path = Path(temporary.name)

    try:
        result = subprocess.run(
            [
                "findmnt",
                "--verify",
                "--verbose",
                "--tab-file",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        path.unlink(missing_ok=True)

    if result.returncode != 0:
        details = "\n".join(
            item
            for item in (
                result.stdout.strip(),
                result.stderr.strip(),
            )
            if item
        )
        raise RuntimeError(
            "The generated /etc/fstab configuration "
            f"did not pass validation:\n\n{details}"
        )


def _ensure_not_duplicate(
    *,
    current_fstab: str,
    source: str,
    mountpoint: str,
) -> None:
    for raw in current_fstab.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        fields = line.split()
        if len(fields) < 2:
            continue

        if fields[0] == source:
            raise ValueError(
                "This network source is already present in /etc/fstab."
            )
        if fields[1] == mountpoint:
            raise ValueError(
                "This mount point is already present in /etc/fstab."
            )


def _validate_protocol(protocol: str) -> None:
    if protocol not in {"smb", "nfs"}:
        raise ValueError("The network-share protocol is invalid.")


def _validate_filesystem(protocol: str, filesystem: str) -> None:
    expected = "cifs" if protocol == "smb" else "nfs"
    if filesystem != expected:
        raise ValueError(
            "The filesystem type does not match the selected protocol."
        )


def _validate_source(source: str) -> None:
    if not source or any(char in source for char in "\n\r\0"):
        raise ValueError("The network-share source is invalid.")


def _validate_mountpoint(mountpoint: str) -> Path:
    path = Path(mountpoint)
    if not path.is_absolute() or path == Path("/"):
        raise ValueError(
            "The mount point must be an absolute path other than /."
        )
    return path


def _validate_fstab_line(fstab_line: str) -> None:
    if (
        not fstab_line.strip()
        or any(char in fstab_line for char in "\n\r\0")
        or len(fstab_line.split()) < 6
    ):
        raise ValueError("The generated fstab line is invalid.")


def _validate_credential_path(value: str) -> Path:
    path = Path(value)
    if path.parent != CREDENTIAL_ROOT or path.suffix != ".cred":
        raise ValueError("The credential-file path is invalid.")
    return path


def _run(
    command: list[str],
    *,
    timeout: int,
    allow_failure: bool = False,
) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode == 0 or allow_failure:
        return

    message = (
        result.stderr.strip()
        or result.stdout.strip()
        or f"{command[0]} exited with code {result.returncode}"
    )
    raise RuntimeError(
        f"{' '.join(command)} failed:\n\n{message}"
    )
