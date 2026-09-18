# Linux Easy Config

**Linux Easy Config (LEC)** is a native graphical administration tool for Ubuntu that turns common Linux configuration tasks into clear, guided interfaces.

Modern desktop users should not need to memorize terminal commands, edit protected text files, or understand the internal layout of `/etc` just to perform ordinary computer tasks. LEC provides a safer and more approachable way to manage services, storage, networking, containers, remote access, scheduled tasks, and other system functions without hiding what the computer is actually doing.

LEC is built for people who want the flexibility of Linux without having to become a Linux administrator first.

> **Supported platforms:**
> - Ubuntu Desktop 26.04 LTS
> - Ubuntu Desktop 24.04 LTS and Linux Mint 22.3 with the optional compatibility runtime
>    
> **Interface:** Native PySide6 / Qt desktop application   
> **Latest:** 1.0.2

---

<img width="1189" height="993" alt="lec1" src="https://github.com/user-attachments/assets/67c3bf8c-a283-469f-a991-3e94c4ae034e" />

<img width="1191" height="992" alt="lec2" src="https://github.com/user-attachments/assets/0151dfa3-bcc4-44cb-8206-69e0b70bceee" />

<img width="1190" height="990" alt="lec3" src="https://github.com/user-attachments/assets/b94ae441-a2d6-4a57-a8ec-1291b2d2822e" />

<img width="1193" height="996" alt="lec4" src="https://github.com/user-attachments/assets/1bbe8832-4376-4e0d-a6ce-8700d008a97c" />

---

## What LEC Does

LEC replaces many command-line and configuration-file workflows with purpose-built graphical tools.

Instead of manually:

- editing systemd unit files
- changing firewall rules
- configuring Docker port exposure
- writing Caddy reverse-proxy entries
- creating mount definitions
- managing Dynamic DNS records
- inspecting journal logs
- building timers and scheduled jobs
- changing user and group permissions

LEC presents those tasks through plain-language forms, tables, status views, and guided actions.

Administrative operations are performed through a controlled privileged helper rather than by running the entire application as root. Persistent configuration changes are audited and recoverable.

---

## Built Around Modules

LEC is modular by design.

The core application provides:

- navigation and shared UI components
- module discovery and loading
- secure privileged-task execution
- cross-module capabilities
- local service discovery
- configuration auditing
- backup and recovery
- support for packaged `.lec` modules

Each module supplies the interface and logic for one system function or application.

Built-in modules remain unpacked in the source repository so their components are easy to inspect. Distributed modules can be packaged as `.lec` archives, which are standard ZIP-compatible files with a different extension.

Optional application modules can be developed and distributed separately without changing LEC Core.

LEC Application Module repo:  https://github.com/candre23/LEC_Modules

LEC Docker Preset repo:  https://github.com/candre23/LEC_Docker_Presets

---

## Integrated System Setup

LEC is designed to make formerly complicated Linux services feel like ordinary desktop features.

Examples include:

- installing and managing Docker
- creating containers from guided forms
- deploying applications from `.lecdock` presets
- configuring Docker-aware firewall access
- publishing services through Caddy
- creating HTTPS reverse proxies
- connecting hostnames from Dynamic DNS
- exposing services locally, across the LAN, or through the internet
- linking related modules without duplicating configuration

Modules communicate through shared capability and service registries. For example, a container created in Docker can be exposed through the Firewall module and published through Reverse Proxy without requiring the user to manually coordinate ports, addresses, or configuration files.

---

## Built-in System Modules

### Background Services

View and manage systemd services in plain language. Search services, inspect status, start or stop them, change startup behavior, and review relevant details without using `systemctl`.

### Docker

Install and manage Docker, create containers through a graphical builder, control port exposure, inspect running containers, and deploy reusable `.lecdock` presets. Docker integrates directly with Firewall, Reverse Proxy, and Port Usage.

### Dynamic DNS

Configure and monitor Dynamic DNS hostnames using supported provider plugins. LEC can create or update records, track the public IP address, and make configured hostnames available to other modules.

### Firewall

Manage UFW rules through a clear graphical interface. Create service rules, inspect current access, and manage Docker-specific exposure through a dedicated Docker-aware firewall chain.

### Hardware Monitor

View system resource usage and hardware status, including processor, memory, storage, temperature, and disk-health information.

### LEC Settings

Control LEC appearance, module icon size, advanced-option visibility, and confirmation behavior. This module also contains Recovery, where audited configuration revisions can be previewed and restored.

### Mounts & Shares

Manage local mounts, network storage, and hosted Samba shares. Create persistent mount definitions and shared folders without manually editing mount tables or Samba configuration.

### Port Usage

See which ports are in use, which processes or containers own them, and how those ports relate to firewall rules, reverse proxies, and local services.

### Remote Access

Configure and inspect SSH, VNC, and Guacamole-related remote-access services from one place. The module provides status information and guided setup for supported methods.

### Reverse Proxy

Create and manage Caddy reverse-proxy rules for local services and containers. Configure HTTP or HTTPS access, use hostnames from Dynamic DNS, and inspect the certificate currently served by Caddy.

### System Logs

Review system events without digging through raw journal output. Logs are grouped, categorized, and explained in clearer language, while the original messages remain available for technical inspection.

### Task Scheduler

Create and manage scheduled commands and recurring tasks through systemd timers. LEC provides common schedules, custom timing options, execution status, and visibility into existing timers and cron jobs.

### User Permissions

Manage users, groups, and access relationships through a graphical interface. Inspect membership and make permission-related changes without relying on low-level account commands.

---

## Safety and Recovery

LEC is designed to make administrative changes more understandable and recoverable.

Persistent configuration changes made by LEC use a shared audited configuration API. Before a managed file is changed, LEC records the previous state.

LEC provides:

- revision history
- protected configuration previews
- backup copies
- rollback through LEC Settings
- validation before privileged actions
- error isolation between modules

The graphical interface runs as the normal desktop user. Only narrowly defined administrative tasks are elevated through Polkit.

LEC does not sandbox arbitrary third-party module code. A third-party module should be treated like any other software installation and installed only from a trusted source.

---

## Installation

LEC 1.0.0 is distributed as a Debian package. Ubuntu Desktop 26.04 LTS uses the distribution-provided Qt/PySide6 packages. Ubuntu Desktop 24.04 LTS and Linux Mint 22.3 require the separate `linuxeasyconfig-qt-runtime` compatibility package, which only needs to be installed once.

On Ubuntu 26.04, install LEC directly:

```bash
sudo apt install ./linuxeasyconfig_1.0.0_all.deb
```

On Ubuntu 24.04 or Linux Mint 22.3, install the compatibility runtime first:

```bash
sudo apt install ./linuxeasyconfig-qt-runtime_6.11.1-1_amd64.deb
sudo apt install ./linuxeasyconfig_1.0.0_all.deb
```

Launch LEC from the desktop application menu or run:

```bash
lec
```

---

## Module and Preset Formats

### `.lec` modules

A `.lec` file is a packaged LEC module. It is a ZIP-compatible archive containing a root-level `manifest.json`, Python code, assets, and any other files required by the module.

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/MODULE_DEVELOPMENT.md`](docs/MODULE_DEVELOPMENT.md)

### `.lecdock` Docker presets

A `.lecdock` file describes a reusable Docker container or Compose application that can be deployed through LEC's Docker module.

See:

- [`docs/DOCKER_PRESETS.md`](docs/DOCKER_PRESETS.md)

### Dynamic DNS provider plugins

Dynamic DNS providers can be extended with trusted Python adapters.

See:

- [`docs/DYNAMIC_DNS_PROVIDER_PLUGINS.md`](docs/DYNAMIC_DNS_PROVIDER_PLUGINS.md)

---

## AI & Safety Disclaimer

The code and documentation included in this project is primarily vibeslop. The human writing this sentence in particular can barely code and doesn't really understand how any of this works. It Works On My Machine and hasn't caused my genitals to explode, but your mileage may vary. I make absolutely no guarantee as to the safety or security of the contents of this project. Use at your own risk. Or don't.

With great power comes great responsibility.  Linux will happily allow you to irreparably fuck up your machine.  LEC attempts to minimize the capacity for self-harm, but if you're determined to make a mess, you absolutely still can.  If you do, that's on you.

---

## Documentation

- [User Manual](docs/USER_MANUAL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Module development](docs/MODULE_DEVELOPMENT.md)
- [Audited configuration API](docs/AUDITED_CONFIGURATION_API.md)
- [Dynamic DNS provider plugins](docs/DYNAMIC_DNS_PROVIDER_PLUGINS.md)
- [Docker presets](docs/DOCKER_PRESETS.md)

---

## Scope

LEC exists to provide graphical controls where Linux currently expects terminal commands, protected-file editing, or low-level system knowledge.

It is not intended to replace a working application GUI or web interface. When an application already provides a good interface for a setting, LEC leaves that setting where it belongs and focuses on the configuration gaps around it.

---

## License

Linux Easy Config is released into the public domain under the [`Unlicense`](LICENSE).   
Copyleft 2026   
No Rights Reserved
