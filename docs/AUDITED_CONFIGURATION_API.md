# Audited Configuration API

Persistent system configuration created, changed, or removed by an LEC module must use the shared audited configuration API:

```python
linuxeasyconfig.core.config.managed
```

This API records revisions for Recovery and prevents modules from implementing their own inconsistent backup logic.

## 1. Required Module Identifier

Use the exact module ID from `manifest.json`:

```python
MODULE_ID = "org.example.my_application"
```

The ID is stored with each audit event and revision.

## 2. Writing Text Files

Use `write_text()` for configuration files, scripts, and other text content.

```python
from pathlib import Path

from linuxeasyconfig.core.config.managed import write_text


write_text(
    module_id=MODULE_ID,
    destination=Path("/etc/example/example.conf"),
    text=rendered_configuration,
    mode=0o644,
)
```

Use an explicit mode appropriate for the file.

Common examples:

```text
0o644    ordinary configuration
0o600    credentials or secrets
0o755    executable scripts
```

## 3. Writing JSON Files

Use `write_json()` for managed JSON configuration.

```python
from pathlib import Path

from linuxeasyconfig.core.config.managed import write_json


write_json(
    module_id=MODULE_ID,
    destination=Path(
        "/etc/linuxeasyconfig/example/settings.json"
    ),
    value=settings,
    mode=0o600,
)
```

Pass normal Python values such as dictionaries and lists. Do not pre-serialize the value unless the API specifically requires text.

## 4. Removing Managed Files

Use `remove_file()` instead of calling `Path.unlink()` directly.

```python
from pathlib import Path

from linuxeasyconfig.core.config.managed import remove_file


remove_file(
    module_id=MODULE_ID,
    destination=Path(
        "/etc/example/obsolete.conf"
    ),
)
```

The previous file state is recorded before removal so Recovery can restore it.

## 5. Changes Made by External Commands

Some approved system utilities modify configuration indirectly.

Examples include:

- `ufw`
- package-management tools
- application-specific configuration commands
- utilities that rewrite multiple files

When a command changes persistent files, capture those files through the managed external-change API around the command execution.

The exact helper name and call pattern should be copied from a current built-in module using external change capture, such as Firewall.

The required sequence is:

1. declare the files that may change
2. capture their current state
3. run the approved command
4. capture the resulting state
5. record only actual changes
6. propagate command failures clearly

Do not use external-change capture as a substitute for direct managed writes when LEC already controls the file content.

## 6. What Must Be Audited

Audit persistent files whose contents affect system or application behavior.

Typical examples include:

```text
/etc/linuxeasyconfig/**
/etc/systemd/system/**
/etc/ufw/**
/etc/caddy/**
/etc/samba/**
/etc/ssh/**
```

Also audit:

- application configuration under `/etc`
- generated systemd services and timers
- scripts installed for later execution
- firewall configuration
- reverse-proxy configuration
- mount and share definitions
- Docker integration metadata that controls behavior
- scheduler definitions
- package-repository files written by LEC
- protected credentials managed by LEC

A useful rule is:

> If changing the file changes how the system or application behaves after LEC closes, it should normally be audited.

## 7. What Must Not Be Audited

Do not use the configuration writer for transient, regenerated, or observational data.

Examples include:

```text
/var/lib/linuxeasyconfig/**/status.json
```

Also exclude:

- monitoring snapshots
- cached discovery data
- public status summaries
- logs
- temporary files
- PID files
- sockets
- lock files
- module extraction caches
- data that can be recreated without losing configuration

These files may still live under `/var/lib/linuxeasyconfig/`, but they are not configuration revisions.

## 8. Revision Storage

Managed backups are stored under:

```text
/var/lib/linuxeasyconfig/backups/
```

A revision path follows the module and revision sequence, preserving the original absolute path beneath it.

Conceptually:

```text
/var/lib/linuxeasyconfig/backups/
└── <module>/
    └── revNNNNNN/
        └── etc/
            └── example/
                └── example.conf
```

The audit history is append-only and stored at:

```text
/var/lib/linuxeasyconfig/audit.jsonl
```

Modules must not edit backup revisions or the audit log directly.

## 9. Recovery Behavior

Recovery is provided through the LEC Settings module.

Users can:

- inspect revision history
- preview readable revisions
- request administrator-authorized previews for protected files
- restore a previous revision

A module does not need to implement its own Recovery UI.

A successful managed write should appear in Recovery. If it does not, the module probably bypassed the audited API.

## 10. Operational Actions

Commands such as these are not file revisions:

```text
systemctl restart
systemctl enable
docker start
docker stop
apt install
mount
umount
```

They may be operationally significant, but they do not by themselves create a restorable file revision.

The configuration changes that precede such commands must still use the audited API.

Examples:

- write a service unit, then run `systemctl daemon-reload`
- write Caddy configuration, then reload Caddy
- write a timer, then enable it
- write firewall integration files, then apply them

Do not create fake revisions merely to represent a command execution.

## 11. Atomicity and Validation

The managed API should be treated as the only supported path for persistent writes.

Before writing:

- validate all user input
- render the complete final content
- validate syntax where possible
- use deterministic output
- avoid partial updates

After writing:

- run any required application validation
- restart or reload the related service
- verify the resulting state
- report partial failures clearly

If a file must be changed as part of a larger operation, complete validation before making the first persistent change whenever practical.

## 12. Paths and Permissions

Privileged tasks must validate destination paths.

Do not allow an arbitrary path supplied by the UI to be passed directly to a managed write.

Use:

- fixed paths
- paths derived from validated identifiers
- allowlisted parent directories
- normalized paths checked against expected roots

Avoid following unexpected symbolic links.

Secret files should normally use:

```text
0o600
```

Executable scripts should normally use:

```text
0o755
```

Ordinary configuration should normally use:

```text
0o644
```

Use more restrictive modes when appropriate.

## 13. Direct Writes Are Not Allowed

The following bypass Recovery and must not be used for persistent configuration:

```python
Path.write_text(...)
Path.write_bytes(...)
shutil.copyfile(...)
open(..., "w")
os.replace(...)
subprocess.run(["sh", "-c", "echo ... > file"])
```

Shell redirection is especially unsafe because it bypasses path validation, revision capture, and consistent error handling.

Direct writes are acceptable only for transient data that is intentionally excluded from auditing.

## 14. Background Services

Background services may write status and monitoring output directly when that data is transient.

They must not directly rewrite persistent configuration.

If a background service needs to change configuration, it should call a narrowly defined privileged task or another approved managed path rather than implementing its own writer.

Keep background package imports free of GUI-only dependencies such as PySide6.

## 15. Third-Party Module Requirement

Third-party modules must use the audited configuration API for all persistent system changes.

A module that writes configuration directly will not provide reliable:

- backup history
- protected previews
- rollback
- audit attribution
- revision consistency

Use of the audited API should therefore be treated as mandatory for LEC-compatible modules.

## 16. Minimal Review Checklist

Before releasing a module, verify:

- [ ] Every persistent write uses `write_text()`, `write_json()`, `remove_file()`, or approved external-change capture.
- [ ] The exact manifest ID is passed as `module_id`.
- [ ] Destination paths are validated.
- [ ] Secret files use restrictive permissions.
- [ ] Transient status and log files are not audited.
- [ ] Managed changes appear in LEC Settings → Recovery.
- [ ] Restoring a revision produces the expected prior configuration.
- [ ] No direct shell redirection or unmanaged protected writes remain.
