# Audited configuration changes in LEC modules

All persistent system configuration created or changed by an LEC module must use
`linuxeasyconfig.core.config.managed`.

## Required module identifier

Use the exact manifest ID:

```python
MODULE_ID = "org.linuxeasyconfig.example"
```

## Text files

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

## JSON files

```python
from linuxeasyconfig.core.config.managed import write_json

write_json(
    module_id=MODULE_ID,
    destination=Path("/etc/linuxeasyconfig/example/settings.json"),
    value=settings,
    mode=0o600,
)
```

## Deleting a managed file

```python
from linuxeasyconfig.core.config.managed import remove_file

remove_file(
    module_id=MODULE_ID,
    destination=Path("/etc/example/obsolete.conf"),
)
```

`remove_file()` records the prior file through the standard writer before
removing it, so Recovery has a revision to restore.

## Files that should be audited

Audit all persistent files whose contents affect system or application behavior:

- `/etc/linuxeasyconfig/**`
- `/etc/systemd/system/**`
- application configuration under `/etc/**`
- firewall, Caddy, Samba, SSH, VNC, Docker, and scheduler configuration
- scripts installed for later execution
- package repository files written by LEC

## Files that normally should not be audited

Do not use the configuration writer for transient or regenerated data:

- `/var/lib/linuxeasyconfig/**/status.json`
- monitoring snapshots
- caches
- temporary files
- logs
- runtime PID or socket files

## Operational actions

Commands such as `systemctl restart`, `docker start`, or `apt-get install` are
not file revisions. They may be recorded separately as informational audit
events in a future operational-audit API, but they must not bypass audited file
writes that precede them.

## Third-party provider requirement

A third-party module that writes persistent configuration directly with
`Path.write_text()`, `shutil.copyfile()`, shell redirection, or similar methods
will not be recoverable through LEC. Provider documentation should treat use of
the audited configuration API as mandatory.
