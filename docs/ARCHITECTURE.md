# Linux Easy Config Architecture

**Project:** Linux Easy Config
**Abbreviation:** LEC
**Internal Python namespace:** `linuxeasyconfig`
**Document status:** Initial architecture reference
**Initial target platform:** Ubuntu Desktop 26.04 LTS
**Initial implementation language:** Python 3.14
**Graphical toolkit:** PySide6 / Qt 6

## 1. Purpose

Linux Easy Config is a native graphical configuration framework intended to make common Linux administration and application-configuration tasks understandable to ordinary computer users.

LEC should allow users to perform tasks such as:

* Managing background services
* Mounting local and network storage
* Managing user accounts
* Granting applications access to files and folders
* Editing protected configuration files
* Managing reverse proxies
* Configuring installed applications

These tasks should not require the user to know:

* Terminal commands
* Shell syntax
* Linux configuration-file locations
* Permission modes
* Service-unit syntax
* Mount commands
* Internal Linux terminology

LEC should present tasks using familiar, descriptive language.

For example:

* “Start this application when the computer starts”
* “Mount a network drive”
* “Let this application access this folder”
* “Restart this background service”

Technical Linux details may remain available through advanced views, but they should not be required for ordinary use.

## 2. Core Architectural Principle

LEC consists of two primary concepts:

1. **LEC Core**
2. **LEC Modules**

LEC Core owns the graphical framework and the reusable system-management capabilities.

LEC Modules describe how those capabilities should be assembled and presented for a particular Linux function or installed application.

A module normally acts as a structured roadmap or workflow definition rather than as an independent application.

A module may tell LEC Core:

* Which pages to display
* Which information to collect
* How to validate that information
* Which built-in operations to perform
* Which files to read or modify
* Which templates to render
* Which services to restart
* How to verify success
* Which help text and explanations to show

LEC Core performs the actual operations.

## 3. Project Scope

### 3.1 Initial scope

The initial version of LEC will target:

* Ubuntu Desktop 26.04 LTS
* Traditional, writable Ubuntu installations
* systemd
* D-Bus
* Polkit
* Local graphical use
* Python-based modules
* Qt Widgets through PySide6

### 3.2 Initial exclusions

The first version will not attempt to support:

* Every Linux distribution
* Non-systemd init systems
* Immutable Linux distributions
* Ubuntu Core
* Remote web administration
* WSL as a primary target
* Mobile interfaces
* A public module marketplace
* Automatic execution of arbitrary downloaded shell commands

Support for additional distributions may be considered later, but the initial architecture should not delay Ubuntu development in pursuit of theoretical universality.

## 4. User Experience Principles

### 4.1 Task-oriented design

LEC should organize features around user goals rather than Linux implementation details.

Preferred:

* Background Services
* Mount a Network Drive
* Folder Access
* Run at Startup
* Application Settings

Avoid as primary user-facing labels:

* systemd Units
* CIFS Entries
* POSIX Permissions
* UID and GID
* `/etc/fstab`
* `chmod`
* `ExecStart`

### 4.2 Progressive disclosure

Each feature should expose only the information needed for the ordinary task.

More technical settings should appear under an Advanced section.

A novice should be able to complete a common task without understanding the underlying Linux mechanism.

An experienced user should still be able to inspect and adjust technical details.

### 4.3 Plain-language errors

LEC should translate technical failures into meaningful explanations.

Instead of:

> Permission denied while opening `/etc/example/example.conf`.

Prefer:

> LEC could not update the application’s settings because administrator access was not granted.

Technical details may be available through an expandable section.

### 4.4 Preview before modification

Whenever practical, LEC should show what it plans to change before applying a configuration.

A preview might include:

* Files to be created
* Files to be modified
* Services to be restarted
* Users or groups to be created
* Permissions to be changed
* Packages to be installed
* Validation checks to be performed

### 4.5 Safe recovery

Administrative changes should support:

* Backups
* Atomic writes
* Validation
* Conflict detection
* Rollback
* Change history

These features improve usability as much as security.

## 5. LEC Core Responsibilities

LEC Core is the installed graphical application and supporting framework.

It should provide the following categories of functionality.

### 5.1 Application shell

The application shell provides:

* Main window
* Navigation
* Module listing
* Page display
* Search
* Notifications
* Status messages
* Dialogs
* Application settings
* Error reporting

### 5.2 Module management

LEC Core should:

* Discover installed modules
* Validate module packages
* Read module manifests
* Check module compatibility
* Enable and disable modules
* Install `.lec` packages
* Remove installed modules
* Report module errors without crashing the full application
* Reload the module catalog when appropriate

### 5.3 Graphical rendering

LEC Core should provide reusable widgets and page types, including:

* Forms
* Tables
* Detail pages
* Checkboxes
* Dropdown menus
* File and folder selectors
* Password and secret fields
* Status indicators
* Confirmation pages
* Change previews
* Log viewers
* Help panels
* Advanced configuration editors

Simple module pages should be definable through JSON.

Complex pages may use Python classes that create custom Qt widgets.

### 5.4 Workflow execution

LEC Core should execute structured module workflows.

A workflow may contain steps such as:

* Read a file
* Render a template
* Validate content
* Back up an existing file
* Write a protected file
* Change ownership or permissions
* Create a folder
* Start or restart a service
* Test a network connection
* Verify that an application is responding
* Roll back previous steps after failure

Workflows should use named operations rather than unrestricted shell strings.

### 5.5 Protected operations

LEC Core will eventually include a privileged helper component.

The graphical application should normally run as the logged-in user.

Privileged operations should be performed through a controlled helper using D-Bus and Polkit authorization.

This allows LEC to modify protected system settings without running the entire graphical interface as root.

The authorization experience should be designed to minimize disruption. A user should not be required to reauthenticate for every individual step within one approved operation.

### 5.6 Protected file management

LEC Core should provide reusable operations for:

* Reading protected files
* Detecting symbolic links
* Recording ownership and permissions
* Calculating content hashes
* Detecting external modifications
* Creating backups
* Writing temporary files
* Atomically replacing original files
* Preserving metadata
* Restoring previous versions

Modules should not independently implement protected file writing unless absolutely necessary.

### 5.7 Validation

LEC Core should support several validation levels:

* JSON Schema validation
* Form-field validation
* File syntax validation
* Module-specific validation
* External application validation
* Post-application health checks

Validation failures should prevent unsafe changes whenever possible.

### 5.8 Transaction management

A workflow that modifies multiple system components should be treated as a transaction where practical.

A transaction should record:

* Planned actions
* Completed actions
* Backups
* Generated files
* Validation results
* Errors
* Rollback status

Not every Linux operation can be perfectly reversed, but LEC should make reasonable efforts to restore the previous state.

### 5.9 Shared system capabilities

LEC Core should gradually provide a library of reusable capabilities.

Examples include:

```text
files.read
files.read_protected
files.write
files.write_protected
files.backup
files.restore
files.create_directory
files.set_owner
files.set_permissions

services.list
services.inspect
services.start
services.stop
services.restart
services.enable
services.disable
services.create
services.remove

users.list
users.create
users.delete
users.add_to_group
users.remove_from_group

mounts.list
mounts.test
mounts.mount
mounts.unmount
mounts.create_persistent
mounts.remove_persistent

network.test_host
network.test_port

validation.schema
validation.file
validation.command
validation.health_check

transactions.preview
transactions.apply
transactions.rollback
```

The exact list will evolve as real modules reveal common requirements.

## 6. LEC Module Responsibilities

A LEC module describes a feature, Linux function, or installed application.

Examples include:

* Background Services
* Mount Management
* User Accounts
* Folder Permissions
* Caddy Reverse Proxy
* Copyparty
* Watchstream
* Samba Shares

A module may provide:

* Metadata
* Navigation entries
* Pages
* Forms
* Tables
* Workflows
* Schemas
* Templates
* Help text
* Icons
* Images
* Validators
* Parsers
* Optional Python extension code

A module should not normally duplicate functionality already provided by LEC Core.

For example, a Caddy module should not implement its own protected-file backup system. It should request LEC Core’s file backup and protected-write operations.

## 7. Module Types

LEC should distinguish between two major module types.

### 7.1 Declarative modules

Declarative modules contain no executable extension code.

They may contain:

* JSON
* Markdown
* Templates
* Images
* Icons
* Schemas
* Static data files

Declarative modules may use only capabilities already provided by LEC Core.

These modules are easier to inspect, validate, distribute, and trust.

### 7.2 Extended modules

Extended modules include executable Python code or another executable component.

They may be required for:

* Complex custom interfaces
* Unusual configuration formats
* Custom parsers
* Complex discovery
* Application-specific APIs
* Specialized validation
* Behavior not supported by existing LEC capabilities

An extended module should be clearly identified during installation.

Executable code inside a module should be treated as installed software rather than harmless configuration data.

### 7.3 Privileged extensions

A future module may require new privileged operations that LEC Core does not provide.

Such a module would require a privileged extension.

Installing a privileged extension is equivalent to installing system-level software and should require explicit administrator approval.

This mechanism should not be implemented until a real module demonstrates that it is necessary.

## 8. The `.lec` Package Format

A `.lec` file will initially be a ZIP-compatible archive using the `.lec` extension.

Example:

```text
caddy-reverse-proxy.lec
```

Using ZIP as the underlying format provides:

* Native Python support
* Easy creation
* Easy extraction
* Cross-platform tooling
* Support for multiple files and directories
* Straightforward inspection during development

A `.lec` package may contain a structure such as:

```text
manifest.json
pages/
    overview.json
    settings.json
    advanced.json
workflows/
    install.json
    apply.json
    remove.json
schemas/
    settings.schema.json
templates/
    application.conf.j2
    application.service.j2
validators/
    configuration.json
help/
    overview.md
    settings.md
assets/
    icon.svg
    banner.png
code/
    module.py
    parser.py
```

Not every module needs every directory.

A simple module might contain only:

```text
manifest.json
pages.json
workflows.json
assets/icon.svg
```

## 9. Module Installation

The intended installation workflow is:

1. The user downloads a `.lec` file.
2. The user opens it or imports it through LEC.
3. LEC opens the archive in a temporary location.
4. LEC validates the archive structure.
5. LEC reads and validates `manifest.json`.
6. LEC checks compatibility requirements.
7. LEC identifies whether executable code is included.
8. LEC displays the module’s requested capabilities.
9. LEC warns about privileged extensions, if any.
10. The user approves installation.
11. LEC copies the module into its managed module directory.
12. LEC records the installed version and source.
13. LEC reloads the module catalog.

Future versions may support:

* Digital signatures
* Publisher identities
* Checksums
* Trusted repositories
* Automatic updates
* Dependency resolution

These features are not required for the initial framework.

## 10. Module Manifest

Every module must contain a root-level `manifest.json`.

The manifest is the module’s primary catalog and entry point.

An initial manifest may contain:

```json
{
  "format_version": 1,
  "id": "org.linuxeasyconfig.services",
  "name": "Background Services",
  "version": "0.1.0",
  "description": "View and manage applications that run in the background.",
  "module_type": "declarative",
  "icon": "assets/icon.svg",
  "entry_page": "pages/service-list.json",
  "supports": {
    "distribution": ["ubuntu"],
    "minimum_version": "26.04"
  },
  "requires": {
    "lec_version": ">=0.1.0",
    "capabilities": [
      "services.list",
      "services.control"
    ],
    "commands": [
      "systemctl"
    ],
    "dbus_services": [
      "org.freedesktop.systemd1"
    ]
  },
  "files": {
    "pages": [
      "pages/service-list.json",
      "pages/service-details.json"
    ],
    "workflows": [
      "workflows/start.json",
      "workflows/stop.json"
    ],
    "help": [
      "help/services.md"
    ]
  }
}
```

The exact schema will evolve during implementation.

### 10.1 Required manifest fields

The first manifest format should require:

* `format_version`
* `id`
* `name`
* `version`
* `description`
* `module_type`
* `entry_page`

### 10.2 Module identifiers

Module identifiers should use reverse-domain notation when possible.

Examples:

```text
org.linuxeasyconfig.services
org.linuxeasyconfig.mounts
org.example.caddy
```

Identifiers should remain stable across module versions.

### 10.3 Compatibility declarations

A module may declare requirements for:

* LEC version
* Ubuntu version
* LEC capabilities
* Installed commands
* Installed packages
* D-Bus services
* Python dependencies
* Other modules

LEC should explain missing requirements in plain language.

## 11. Declarative Pages

Simple pages should be definable through JSON.

Example:

```json
{
  "id": "mount-network-drive",
  "title": "Mount a Network Drive",
  "type": "form",
  "description": "Connect a shared folder from another computer or server.",
  "fields": [
    {
      "id": "server",
      "type": "text",
      "label": "Server address",
      "required": true
    },
    {
      "id": "share",
      "type": "text",
      "label": "Shared folder",
      "required": true
    },
    {
      "id": "username",
      "type": "text",
      "label": "Username"
    },
    {
      "id": "password",
      "type": "secret",
      "label": "Password"
    },
    {
      "id": "mount_point",
      "type": "folder",
      "label": "Local folder",
      "required": true
    },
    {
      "id": "automatic",
      "type": "boolean",
      "label": "Reconnect automatically when the computer starts"
    }
  ],
  "submit": {
    "label": "Mount Drive",
    "workflow": "workflows/create-network-mount.json"
  }
}
```

LEC Core should render this page without module-specific Python code.

## 12. Custom Python Pages

Some pages will require more than declarative forms.

Examples include:

* Live process tables
* Service lists with changing status
* Log viewers
* Route trees
* Visual storage layouts
* Complex permission diagnostics

A module may declare a Python page:

```json
{
  "id": "service-list",
  "title": "Background Services",
  "type": "python",
  "entry_point": "code.service_page:ServicePage"
}
```

Python page classes should use a documented LEC module interface rather than directly modifying LEC Core internals.

## 13. Workflows

A workflow is a structured list of operations performed by LEC Core.

Example:

```json
{
  "id": "apply-settings",
  "title": "Apply Settings",
  "steps": [
    {
      "operation": "files.render_template",
      "template": "templates/example.conf.j2",
      "destination": "/etc/example/example.conf",
      "inputs": {
        "port": "${form.port}",
        "media_path": "${form.media_path}"
      }
    },
    {
      "operation": "validation.file",
      "validator": "example-config",
      "path": "/etc/example/example.conf"
    },
    {
      "operation": "services.restart",
      "service": "example.service"
    },
    {
      "operation": "network.test_port",
      "host": "127.0.0.1",
      "port": "${form.port}"
    }
  ]
}
```

A workflow step should reference a named LEC operation.

Modules should not normally provide unrestricted shell command strings.

## 14. Commands and External Utilities

Some Linux tasks will ultimately require invoking command-line utilities.

LEC Core may internally invoke trusted commands where no better API exists.

Modules should request a named operation or validator rather than construct arbitrary shell commands.

Preferred:

```json
{
  "operation": "services.restart",
  "service": "caddy.service"
}
```

Avoid:

```json
{
  "command": "sudo systemctl restart caddy"
}
```

This provides:

* Better input validation
* Consistent authorization
* Structured error handling
* Safer quoting
* Better logging
* Easier previews
* More reliable rollback behavior

A restricted advanced command capability may be considered later for explicitly trusted extended modules.

## 15. Configuration Editing

LEC should include a reusable Advanced Configuration Editor.

The editor should support:

* Protected files
* Syntax highlighting
* Line numbers
* Search and replace
* Undo and redo
* Diff previews
* Syntax validation
* Contextual help
* Backup history
* External-change detection
* Atomic saving
* Rollback

Modules may register information such as:

* Syntax type
* File parser
* Validator
* Documentation provider
* Reload action
* Default file paths

If a module cannot fully abstract an application’s settings, it should still be able to provide a graphical protected-file editor with validation and help.

## 16. Secrets

Passwords, tokens, and credentials should not be stored casually in module JSON or workflow history.

LEC Core should eventually provide a secrets capability.

Possible storage mechanisms include:

* GNOME Keyring
* Secret Service API
* Secure root-owned credential files
* Application-specific secret stores

Modules should refer to secrets through handles rather than directly embedding plaintext values in generated logs or transaction records.

The initial implementation may defer full secret management until the first module requires it.

## 17. Error Isolation

A broken module should not prevent LEC from starting.

LEC Core should:

* Load modules individually
* Catch module-loading failures
* Disable invalid modules
* Record diagnostic information
* Show a readable module error
* Allow the user to remove or repair the affected module

A module should not receive unrestricted access to internal application objects unless required by its documented interface.

## 18. Capability Discovery

LEC should detect the actual machine environment.

Examples include:

* Ubuntu version
* systemd availability
* D-Bus availability
* Polkit availability
* Installed commands
* Installed packages
* Running services
* Available Python features
* Desktop environment
* Required configuration files

A module should be able to explain why it is unavailable.

Example:

> The Caddy module cannot be activated because Caddy is not installed.

A future module may offer an installation workflow when dependencies are missing.

## 19. First Module: Background Services

The first substantial module will be Background Services.

It is intended to test the module framework, not merely to produce a standalone service manager.

The module should eventually support:

* Listing services
* Searching services
* Displaying plain-language descriptions
* Showing current status
* Showing startup behavior
* Starting services
* Stopping services
* Restarting services
* Enabling startup
* Disabling startup
* Viewing recent logs
* Inspecting unit files
* Editing service overrides
* Creating a service for an application

Nothing specific to the service module should be hard-coded into the main LEC window.

The module should be installed and loaded through the same module mechanisms intended for future modules.

## 20. Second Module

A second, structurally different module will be required to verify that the framework is genuinely reusable.

The likely second module is Mount Management.

It would test:

* Forms
* Credentials
* Protected file editing
* Persistent configuration
* Folder creation
* Validation
* Connectivity testing
* Rollback
* Different workflow patterns from service management

The framework should be revised when the second module exposes assumptions that were specific to the first module.

## 21. Development Strategy

LEC should be built through small vertical milestones.

### Milestone 1

* Application shell
* Module discovery
* Manifest loading
* Manifest validation
* Navigation registration
* Example module
* Error isolation

### Milestone 2

* Declarative page rendering
* Shared form widgets
* Basic page navigation
* Module assets
* Help content

### Milestone 3

* Read-only Background Services module
* systemd D-Bus access
* Live status display
* Search and filtering

### Milestone 4

* Privileged helper
* Polkit authorization
* Named operation registry
* Service-control operations

### Milestone 5

* Change previews
* Transaction records
* Backup and rollback framework
* Protected file operations

### Milestone 6

* Advanced Configuration Editor
* Validation hooks
* Diff display
* Atomic writes

### Milestone 7

* `.lec` archive installation
* Module compatibility checks
* Module removal
* Declarative versus extended module warnings

### Milestone 8

* Second substantial module
* Framework revisions based on reuse

## 22. Current Design Decisions

The following decisions are established unless future implementation reveals a compelling reason to change them:

1. The product name is Linux Easy Config.
2. The product abbreviation is LEC.
3. The Python namespace is `linuxeasyconfig`.
4. The executable command is `lec`.
5. The initial target is Ubuntu Desktop 26.04 LTS.
6. The graphical toolkit is PySide6 with Qt Widgets.
7. The project uses `pyproject.toml`.
8. LEC is a native desktop application, not a web interface.
9. LEC Core performs system operations.
10. Modules primarily describe interfaces and workflows.
11. Modules may optionally include Python extension code.
12. Module archives use the `.lec` extension.
13. The initial `.lec` format is ZIP-compatible.
14. Modules should use named LEC operations rather than unrestricted shell commands.
15. Ordinary interfaces should hide unnecessary Linux terminology.
16. Advanced technical controls should remain available.
17. The first substantial module is Background Services.
18. A second different module will be used to validate the framework architecture.

## 23. Open Questions

The following decisions remain open:

* Exact manifest JSON Schema
* Exact declarative page schema
* Exact workflow schema
* Exact Python module interface
* Location of installed modules
* User-level versus system-level module installation
* Module signing
* Module update behavior
* Secret storage implementation
* Template engine choice
* Privileged helper language and packaging
* D-Bus interface design
* Transaction persistence format
* Backup retention policy
* Module dependency handling
* Whether custom module Python code runs in-process or in an isolated process
* Whether privileged extensions will be supported
* Final Debian package structure

These questions should be resolved incrementally as the first modules demonstrate real requirements.

## 24. Guiding Rule

When choosing between exposing Linux as it currently works and presenting the task as an ordinary user understands it, LEC should prefer the user’s mental model.

The underlying Linux mechanism should remain accurate, inspectable, and available through advanced tools, but it should not become an unnecessary barrier to completing the task.

