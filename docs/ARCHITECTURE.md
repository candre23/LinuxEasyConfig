# Linux Easy Config Architecture

**Project:** Linux Easy Config  
**Abbreviation:** LEC  
**Python namespace:** `linuxeasyconfig`  
**Command:** `lec`  
**Target platform:** Ubuntu Desktop 26.04 LTS  
**Language and toolkit:** Python 3.14, PySide6, Qt Widgets  

## 1. Purpose

Linux Easy Config is a native desktop application that provides graphical controls for Linux administration tasks that would otherwise require terminal commands, direct configuration-file editing, or detailed knowledge of Linux internals.

LEC is task-oriented. It presents plain-language controls while keeping technical details available where useful.

LEC does not attempt to replace an application's existing graphical or web interface. Application modules should focus on configuration gaps that otherwise require low-level Linux work.

## 2. Major Components

LEC consists of:

1. **LEC Core**
2. **Modules**
3. **The privileged helper**
4. **Shared capability and service registries**
5. **Audited configuration and recovery services**

### 2.1 LEC Core

LEC Core provides:

- Main window and module navigation
- Module discovery and loading
- Theme and application settings
- Shared page and widget rendering
- Capability registration
- Local service registration
- Privileged-task dispatch
- Configuration revision history
- Recovery and rollback
- Module archive extraction and validation
- Error isolation

The graphical application runs as the logged-in desktop user.

### 2.2 Modules

Modules provide the interface and implementation for a specific system function or application.

A module may contain:

- `manifest.json`
- Python code
- Qt views
- repositories and data providers
- privileged tasks
- capability providers
- local service definitions
- templates and static data
- icons and other assets

LEC uses two user-facing categories:

- **System modules** manage operating-system functions and low-level infrastructure.
- **Application modules** manage configuration gaps for optional applications.

Docker is classified as a System module because container infrastructure is a common foundation for modern Linux applications.

## 3. Built-in System Modules

The core release includes:

- Background Services
- Docker
- Dynamic DNS
- Firewall
- Hardware Monitor
- LEC Settings
- Mounts & Shares
- Port Usage
- Remote Access
- Reverse Proxy
- System Logs
- Task Scheduler
- User Permissions

Optional Application modules are distributed separately.

## 4. Module Discovery and Packaging

During development, modules are stored as folders under:

```text
src/linuxeasyconfig/modules/
```

LEC also supports `.lec` archives. A `.lec` file is a ZIP-compatible archive with `manifest.json` at its root.

At runtime, LEC discovers both unpacked folders and `.lec` archives. When both exist for the same manifest ID, the unpacked folder takes precedence.

Archives are extracted to:

```text
~/.cache/linuxeasyconfig/module-cache/
```

Extraction uses content-based cache invalidation and rejects unsafe paths, traversal attempts, and symbolic links.

The Debian package may convert built-in module folders into `.lec` archives while leaving the Git repository unpacked.

## 5. Manifest and Entry Point

Each module contains a root-level `manifest.json`.

The manifest supplies module metadata and an entry point used by the module manager to load the module class. Typical metadata includes:

- stable module ID
- display name
- version
- description
- category
- entry point
- icon information

LEC automatically checks the module root for:

```text
icon.svg
icon.png
icon.webp
icon.jpg
icon.jpeg
```

A module registers its pages, capabilities, local services, and related features through the module interface provided by LEC Core.

## 6. Capabilities and Local Services

LEC uses two shared registries.

### 6.1 Capability Registry

A capability describes an action one module can expose to another.

Examples include:

```text
firewall.allow_service
firewall.allow_docker_service
reverse_proxy.create_http_proxy
```

Capabilities allow modules to cooperate without directly importing one another's implementation.

### 6.2 Local Service Registry

A local service describes a service or endpoint available on the current machine.

Modules may publish local services so other modules can discover targets, ports, protocols, and related metadata.

Registries are established during startup. Changes to registrations take effect after LEC restarts.

## 7. Privileged Operations

The main GUI does not run as root.

Administrative actions are routed through a generic privileged helper. The helper dynamically discovers privileged task registries exposed by active modules.

Each privileged module component publishes a `PRIVILEGED_TASKS` mapping. Task arguments are validated before execution.

Authorization is handled through Polkit.

## 8. Audited Configuration and Recovery

Persistent system configuration changes must use:

```python
linuxeasyconfig.core.config.managed
```

The managed configuration API supports:

- writing text files
- writing JSON files
- deleting managed files
- capturing changes made by approved external commands

Before a managed change is applied, LEC records the previous state as a revision.

Backups are stored under:

```text
/var/lib/linuxeasyconfig/backups/
```

The append-only audit log is stored at:

```text
/var/lib/linuxeasyconfig/audit.jsonl
```

Recovery is provided through LEC Settings and supports revision browsing, protected previews, and restoration.

Transient data such as status snapshots, caches, monitoring results, logs, PID files, and sockets is not treated as recoverable configuration.

## 9. Data Locations

```text
/etc/linuxeasyconfig/
    Persistent system configuration and protected module data

/var/lib/linuxeasyconfig/
    Backups, audit history, public status snapshots, and generated state

~/.config/linuxeasyconfig/
    Per-user LEC settings

~/.cache/linuxeasyconfig/
    Module extraction cache and other disposable caches

~/.local/share/linuxeasyconfig/
    User-installed providers, presets, and other user-level extensions
```

Module-specific files should remain inside an appropriate LEC-owned subdirectory unless they must be installed in a standard system location.

## 10. UI Structure

The application shell displays modules in the navigation pane and renders the selected module's pages in the main content area.

Modules may use:

- standard forms
- tables
- lists
- messages
- custom Qt views

Live data providers run outside the UI thread where necessary to avoid interface stalls.

LEC Settings controls appearance, module icon size, destructive-action confirmations, advanced-option visibility, and Recovery.

A failure in one module should not prevent the rest of LEC from starting.

## 11. Security and Trust Model

LEC modules may contain executable Python code and privileged tasks. Installing a module is therefore equivalent to installing software.

LEC reduces risk through:

- manifest validation
- archive path validation
- strict task argument validation
- narrow privileged-task dispatch
- audited persistent writes
- revision backups
- module error isolation
- separation of user and privileged execution

LEC does not sandbox arbitrary third-party module code.

## 12. Distribution Model

The main repository contains:

- LEC Core
- built-in System modules
- development and packaging tools
- project documentation

Built-in modules remain unpacked in the source repository for readability.

The Debian build may package them as `.lec` archives. Optional Application modules are published and installed separately.

Release packages should be built from a clean Git checkout so that untracked files, local settings, logs, caches, credentials, and machine-specific data cannot enter the package.

## 13. Architectural Boundaries

- The GUI runs as the desktop user.
- Privileged work is delegated to narrowly defined tasks.
- Persistent configuration changes are audited.
- Modules own feature-specific behavior.
- Core owns shared infrastructure.
- Cross-module cooperation uses capabilities and local services.
- Existing application interfaces are not unnecessarily duplicated.
- Ordinary tasks use plain language while technical details remain available.
