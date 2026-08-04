# Developing LEC Modules

This document describes how to create a module for Linux Easy Config (LEC).

A module should provide a graphical interface for Linux tasks that would otherwise require terminal commands, protected-file editing, or knowledge of low-level system configuration.

Do not recreate a working application GUI or web interface. Focus on the missing system-integration work around the application.

## 1. Choose the Module Category

LEC has two user-facing categories:

- **System** — operating-system functions and low-level infrastructure.
- **Application** — configuration gaps for an optional application.

Most third-party modules should be Application modules.

Examples of appropriate module tasks:

- install or remove a system service
- create or edit protected configuration
- configure startup behavior
- expose folders or ports
- connect the application to Firewall or Reverse Proxy
- inspect status and logs
- provide guided setup for features not exposed by the application itself

## 2. Start from an Existing Module

The most reliable approach is to copy the built-in module that most closely resembles the new one.

Built-in modules are stored under:

```text
src/linuxeasyconfig/modules/
```

Useful references include:

- `background_services` for service tables and actions
- `docker` for complex custom views and cross-module integration
- `dynamic_dns` for plugin-style providers and background services
- `firewall` for audited system changes
- `mounts_shares` for forms and protected configuration
- `reverse_proxy` for Caddy integration
- `task_scheduler` for generated systemd units
- `system_logs` for read-only system inspection
- `lec_settings` for application settings and Recovery integration

Keep the new module self-contained in its own directory.

## 3. Recommended Module Layout

A typical module looks like:

```text
my_application/
├── __init__.py
├── manifest.json
├── module.py
├── views.py
├── repository.py
├── installer.py
├── privileged.py
├── capabilities.py
├── services.py
├── icon.png
└── other module-specific files
```

Only include files the module actually needs.

Common responsibilities:

- `module.py` — module class and feature registration
- `views.py` — Qt pages and dialogs
- `repository.py` — read-only discovery and status collection
- `installer.py` — installation and configuration orchestration
- `privileged.py` — administrator-only task functions
- `capabilities.py` — actions exposed to other modules
- `services.py` — local services published to the registry

Do not place application data, credentials, logs, caches, or machine-specific files in the module directory.

## 4. Manifest

Every module requires a root-level `manifest.json`.

Use a stable reverse-domain ID and a Python entry point.

Example:

```json
{
  "format_version": 1,
  "id": "org.example.my_application",
  "name": "My Application",
  "version": "1.0.0",
  "description": "Configure system integration for My Application.",
  "category": "Application",
  "entry_point": "linuxeasyconfig.modules.my_application.module:MyApplicationModule"
}
```

Use the exact field names and conventions found in current built-in manifests. Copying an existing manifest is safer than inventing additional fields.

Requirements:

- The ID must remain stable across releases.
- The entry point must import successfully.
- The display name and description should use plain language.
- The category must be `System` or `Application`.
- Increment the module version when behavior or compatibility changes.

## 5. Module Class

The entry-point class registers the module's pages and optional integrations.

Follow the current module interface used by built-in modules. Do not import internal window objects or modify global UI state directly.

A module normally registers:

- one or more pages
- navigation labels
- optional capabilities
- optional local services

Prefer a clear landing page that explains the current state and provides the main actions.

Keep module-specific behavior inside the module. Shared infrastructure belongs in LEC Core.

## 6. User Interface

LEC uses PySide6 and Qt Widgets.

Modules may use:

- forms
- tables
- lists
- messages
- custom Qt widgets

UI requirements:

- use plain-language labels
- avoid requiring Linux terminology for ordinary tasks
- place technical details behind advanced views where practical
- show current status before offering changes
- validate user input before privileged execution
- provide clear success and error messages
- keep long-running work off the UI thread
- do not freeze the interface during service, network, or discovery operations

Use standard LEC styling and shared widgets where available.

The module icon should be stored in the module root using one of:

```text
icon.svg
icon.png
icon.webp
icon.jpg
icon.jpeg
```

No manifest change is required when using these conventional names.

## 7. Read-Only Discovery

Normal status collection should run as the desktop user whenever possible.

Use ordinary subprocess or file-reading operations for information the user can already access, such as:

- `systemctl` status
- journal entries available to the user
- Docker inspection available through group membership
- network listeners
- readable configuration
- public status snapshots

Do not request administrator authorization merely to display information.

Put reusable discovery logic in `repository.py` or a similarly focused file.

Return structured data to the UI rather than raw command output.

## 8. Privileged Tasks

The main GUI must not run as root.

Administrator-only operations are exposed through the module's `privileged.py`.

The module publishes a mapping named:

```python
PRIVILEGED_TASKS
```

Example shape:

```python
PRIVILEGED_TASKS = {
    "my_application.install": install_application,
    "my_application.save_settings": save_settings,
    "my_application.remove": remove_application,
}
```

Task names must be unique and should use the module name as a prefix.

Privileged task rules:

- validate all arguments
- accept structured values, not shell command strings
- never trust paths supplied by the UI without validation
- avoid `shell=True`
- use absolute command paths where practical
- return structured success or error information
- keep privileged code as narrow as possible
- do not expose a generic command-execution task

The helper discovers privileged tasks dynamically from active modules.

## 9. Persistent Configuration and Recovery

All persistent configuration changes must use:

```python
linuxeasyconfig.core.config.managed
```

Use:

```python
write_text(...)
write_json(...)
remove_file(...)
```

Use external-change capture when an approved system command modifies configuration files indirectly.

Audit configuration such as:

- files under `/etc/linuxeasyconfig/`
- systemd units
- Caddy, firewall, Samba, SSH, VNC, or Docker configuration
- generated scripts
- application configuration under `/etc`
- package-repository definitions

Do not audit transient data such as:

- status snapshots
- logs
- caches
- monitoring data
- PID files
- sockets
- temporary files

Use the exact manifest ID as the `module_id` for audited writes.

See [`AUDITED_CONFIGURATION_API.md`](AUDITED_CONFIGURATION_API.md).

## 10. Installation and Removal

A module that installs software should:

1. detect whether the application is already installed
2. show the current state
3. explain what will be installed or changed
4. perform package installation through a privileged task
5. write configuration through the audited API
6. enable or restart required services
7. verify the result
8. report partial failures clearly

Removal should distinguish between:

- removing LEC-managed integration
- removing the application package
- deleting application data

Never delete user data unless the user explicitly selects that action.

## 11. Capabilities

Capabilities allow one module to expose an action to another without direct implementation imports.

Examples in LEC include:

```text
firewall.allow_service
firewall.allow_docker_service
firewall.remove_docker_service
reverse_proxy.create_http_proxy
```

Create a capability when another module may reasonably need the action.

A capability should:

- have a stable name
- accept structured arguments
- validate input
- return structured results
- describe one clear operation
- avoid exposing internal implementation details

Use the core capability registry rather than importing another module's classes.

## 12. Local Services

Publish a local service when the module creates or discovers an endpoint that other modules may use.

Useful service metadata may include:

- service name
- host or bind address
- port
- protocol
- source module
- container name
- whether the endpoint is local, LAN-accessible, or public

This allows Firewall, Reverse Proxy, Port Usage, and other modules to work with the service without duplicating discovery logic.

Service registrations are established at application startup. Restart LEC after changing registration code.

## 13. Cross-Module Integration

Use existing capabilities and local services where appropriate.

Examples:

- expose a port through Firewall
- publish a local service through Reverse Proxy
- use a Dynamic DNS hostname
- show port ownership in Port Usage
- link to an existing application interface instead of rebuilding it

Integration should be optional. The module must handle missing capabilities gracefully and explain what additional module or service is required.

Do not create hard imports between independently distributed modules.

## 14. Background Services

A module may install systemd services or timers for work that must continue when LEC is closed.

Generated units and scripts must:

- use stable names prefixed with `lec-` or the module name
- use absolute paths
- run under the least privilege required
- write status to a documented location
- avoid importing PySide6 in background processes
- avoid package-level imports that pull in UI modules

Keep package `__init__.py` files import-free when the package is also executed with:

```bash
python -m package.module
```

This prevents background services from importing GUI-only dependencies.

## 15. Data and Secrets

Use these locations consistently:

```text
/etc/linuxeasyconfig/<module>/
    Protected persistent configuration and credentials

/var/lib/linuxeasyconfig/<module>/
    Generated state and public status snapshots

~/.config/linuxeasyconfig/
    Per-user LEC settings

~/.local/share/linuxeasyconfig/
    User-installed presets, providers, and extensions

~/.cache/linuxeasyconfig/
    Disposable caches
```

Rules:

- never store credentials in the source tree
- never write secrets to logs or status snapshots
- use restrictive permissions for secret files
- use provider- or application-scoped tokens where possible
- do not embed real hostnames, usernames, home paths, or IP addresses in examples

## 16. Error Handling

A module must fail safely.

- Catch expected subprocess, file, network, and parsing errors.
- Convert technical errors into clear user-facing explanations.
- Preserve detailed diagnostics for troubleshooting.
- Do not crash the full application because one module failed.
- Verify success after installation or configuration changes.
- Report when a change succeeded but a restart or verification step failed.

Read-only pages should remain usable even when optional dependencies are missing.

## 17. Packaging as `.lec`

A `.lec` file is a ZIP-compatible archive with `manifest.json` at its root.

During development, keep the module unpacked.

Package it only for distribution.

The archive must not contain:

- an extra top-level wrapper directory
- symbolic links
- absolute paths
- `..` traversal paths
- `__pycache__`
- `.pyc` files
- logs
- credentials
- local configuration
- test output

LEC extracts archives into its module cache and validates paths before loading them.

Use the project's module-packaging tool rather than creating archives manually when possible.

## 18. Testing Checklist

Before release, verify:

- [ ] The module loads without errors.
- [ ] The manifest ID and entry point are correct.
- [ ] The icon displays correctly.
- [ ] The landing page clearly explains the current state.
- [ ] Read-only views do not trigger administrator prompts.
- [ ] Input validation rejects invalid values.
- [ ] Privileged task arguments are validated.
- [ ] Persistent writes appear in Recovery.
- [ ] Rollback restores the previous configuration.
- [ ] Services and timers survive reboot where intended.
- [ ] Background processes do not import PySide6.
- [ ] Missing dependencies produce useful explanations.
- [ ] Cross-module integrations work when available.
- [ ] The module still works when optional integrations are absent.
- [ ] No credentials, logs, caches, or machine-specific data are packaged.
- [ ] The final `.lec` archive loads successfully.
