# Linux Easy Config User Manual


## Table of contents

- Introduction & General Concepts
- [LEC Settings](#lec-settings)
- [Hardware Monitor](#hardware-monitor)
- [Background Services](#background-services)
- [Port Usage](#port-usage)
- [User Permissions](#user-permissions)
- [Mounts & Shares](#mounts-and-shares)
- [System Logs](#system-logs)
- [Firewall](#firewall)
- [Reverse Proxy](#reverse-proxy)
- [Remote Access](#remote-access)
- [Dynamic DNS](#dynamic-dns)
- [Task Scheduler](#task-scheduler)
- [Docker](#docker)


---


## Introduction

Linux Easy Config (LEC) is designed for people who want the flexibility of Linux without having to memorize terminal commands, edit protected configuration files, or understand every internal system component.

LEC organizes common administration tasks into graphical modules. Each module focuses on one area of the system, such as Docker, firewall rules, storage, remote access, scheduled tasks, or system logs.

You do not need to understand how LEC is built in order to use it. This manual focuses on what each screen does, what the available choices mean, and how the modules work together.

## How LEC Is Organized

The main LEC window has two primary areas:

- **Module list** — the navigation area on the left.
- **Module workspace** — the main area where the selected module appears.

Select a module from the list to open it.

Most modules contain several tabs. Tabs divide the module into related tasks, such as:

- an overview or status page
- setup and configuration
- active items
- logs or diagnostics
- advanced options

Not every module uses the same tabs, because each one is built around a different type of task.

## Administrator Authorization

LEC itself normally runs as your regular desktop user.

Some actions require administrator access, such as:

- installing software
- changing firewall rules
- creating system services
- editing protected configuration
- changing users or groups
- restoring protected files

When needed, Ubuntu displays an administrator authorization prompt.

A status page or read-only information screen should not normally require authorization. Prompts generally appear only when you apply a change or request access to protected information.

Canceling an authorization prompt simply prevents that action from continuing. It does not damage the system.

## Saving and Applying Changes

LEC modules generally separate viewing from changing.

A typical process is:

1. Review the current status.
2. Enter or select the desired settings.
3. Click the relevant Save, Apply, Create, Install, or Remove button.
4. Review any confirmation message.
5. Approve administrator access if requested.
6. Wait for LEC to verify the result.

Do not close LEC while an installation or configuration change is actively running.

## How Modules Work Together

LEC modules can share information and actions.

For example:

- Docker can publish a container port through Firewall.
- Reverse Proxy can route a hostname to a Docker container or local service.
- Dynamic DNS can provide hostnames to Reverse Proxy.
- Port Usage can show which process or container owns a network port.
- LEC Settings can restore configuration changes made by other modules.

These connections are optional. A module should continue to work even when a related module or service is unavailable, although some integration options may not appear.

## Safety and Recovery

LEC records revisions of persistent configuration files that it manages.

This allows many changes to be reviewed and restored through:

```text
LEC Settings → Recovery
```

Recovery is not the same as a full system backup. It restores configuration revisions created through LEC. It does not restore deleted personal files, application databases, or unrelated system changes.

## Advanced Options

Some modules include advanced options or technical details.

These are intended for users who need more control or are troubleshooting a problem. Most routine tasks should not require them.

Advanced options can be shown or hidden from LEC Settings.

## Using This Manual

Each module section explains:

- the purpose of the module
- each tab and its controls
- common workflows
- connections to other modules
- warnings and limitations
- troubleshooting guidance

The exact wording or placement of a control may change slightly between LEC versions, but the general workflow should remain the same.

## AI & safety disclaimer

This software and documentation was almost entirely generated with the assistance of LLMs.  It has been tested in use, but not thoroughly audited by a human.  Bugs may exist in the code and factual inaccuracies may exist in the docs.  LEC is provided as-is, with no warranty or guarentee of any kind.  Use this software at your own risk.  Or don't.  I'm not your mom.


---


<a id="lec-settings"></a>

# 1. LEC Settings Module

## 1.1 Purpose

LEC Settings controls the behavior and appearance of Linux Easy Config itself.

It also contains the Recovery tools used to inspect and restore configuration changes made by LEC.

LEC Settings is normally the first module shown when the application starts.

Its tabs are:

- **Overview**
- **Settings**
- **Recovery**

## 1.2 Overview Tab

The Overview tab displays information about the current LEC installation.

It is primarily informational. It does not change system settings.

### LEC Version

Shows the installed version of Linux Easy Config.

This is useful when:

- checking whether an update was installed
- reporting a problem
- comparing a module's requirements with the installed LEC version

### Python Version

Shows the Python version currently running LEC.

Most users do not need to act on this information. It is mainly useful for troubleshooting.

### Operating System

Shows the detected operating system and version.

LEC 1.0.0 supports Ubuntu Desktop 26.04 LTS natively. Ubuntu Desktop 24.04 LTS and Linux Mint 22.3 are supported with the optional LEC Qt compatibility runtime. Other distributions are not supported by this release and some modules may not work as expected.

### Installation Path

Shows the location from which LEC is running.

This helps distinguish between:

- a development copy
- a manually installed copy
- the packaged system installation

Ordinary users should not need to change this path.

### Installed Modules

The module table lists the modules LEC discovered during startup.

Typical columns include:

- **Name** — the user-facing module name
- **Version** — the module version
- **ID** — the module's internal identifier
- **Source** — whether it was loaded from a folder or `.lec` archive
- **Status** — whether it loaded successfully
- **Path** — where the module was found

### Understanding Module Status

A module with a normal or active status loaded successfully.

A module error may indicate:

- a damaged or incomplete module
- an incompatible version
- a missing dependency
- an invalid manifest
- an import error

A broken optional module should not prevent LEC itself from opening.

Restart LEC after adding, removing, or replacing a module so the module list can be rebuilt.

## 1.3 Settings Tab

The Settings tab controls LEC's appearance and interaction preferences.

After changing a setting, click **Save Settings**.

Changes are stored for the current desktop user.

### Color Mode

Controls the overall LEC theme.

Available choices are:

#### System

LEC follows the desktop's current light or dark appearance when supported.

Use this when you want LEC to match the rest of Ubuntu automatically.

#### Light

Uses LEC's light theme regardless of the desktop setting.

This may be easier to read in bright rooms or on displays where dark themes have poor contrast.

#### Dark

Uses LEC's dark charcoal theme.

This is useful in dim environments or when you prefer dark applications.

The selected theme applies immediately after saving.

### Module Icon Size

Controls the icons shown beside modules in the navigation list.

Available choices are:

#### No Module Icons

Hides module icons entirely.

Use this when:

- you prefer a plain text-only navigation list
- you want the most compact layout
- the navigation pane is narrow

#### Small

Displays the standard icon size.

This is the default setting.

#### Large

Displays larger module icons and increases the height of each module row.

Use this when:

- the icons are an important visual aid
- you use a high-resolution display
- the standard icons are difficult to distinguish

The selected size applies immediately after saving.

### Confirm Destructive Actions

Controls whether LEC asks for confirmation before actions that could remove, overwrite, disable, or substantially alter something.

Examples may include:

- deleting a rule
- removing a service
- deleting a scheduled task
- removing a container
- restoring an older configuration
- uninstalling integration

For most users, this should remain enabled.

Disabling confirmations can make repeated administrative work faster, but it also makes accidental changes easier.

This setting does not bypass administrator authorization.

### Show Advanced Options

Controls whether modules display technical or less commonly used settings.

When disabled, modules should emphasize the ordinary workflow.

When enabled, modules may reveal controls such as:

- bind addresses
- service-unit details
- advanced network settings
- raw configuration
- internal identifiers
- technical diagnostics

Enabling advanced options does not change the system by itself. It only changes what LEC displays.

Leave this disabled unless you need the additional controls.

### Add or Remove LEC Modules

Custom application modules can be added and removed from the LEC interface using these buttons.  The default built-in system modules may also be updated by installing newer system modules. Default modules may not be removed, as doing so would break module interoperability.

## 1.4 Recovery Tab

The Recovery tab displays audited configuration revisions created by LEC.

Use it when:

- a setting worked previously and no longer does
- a configuration change produced an unwanted result
- you want to compare an older file with the current version
- you need to restore a file removed or replaced by LEC

### What Recovery Includes

Recovery covers persistent configuration managed through LEC's audited configuration system.

Examples may include:

- firewall configuration
- systemd services and timers
- Caddy reverse-proxy files
- Samba configuration
- Docker integration metadata
- Dynamic DNS configuration
- scheduled-task definitions
- LEC-managed scripts

### What Recovery Does Not Include

Recovery does not normally include:

- logs
- monitoring snapshots
- cache files
- temporary files
- Docker image contents
- application databases
- personal documents
- files changed outside LEC
- actions that did not modify a managed configuration file

For example, starting or stopping a service does not itself create a file revision.

### Revision List

The Recovery tab shows available revisions.

A revision normally identifies:

- the module that made the change
- the affected file
- the revision number
- the date and time
- the type of change

Select a revision to inspect or restore it.

### Preview

For files readable by your desktop user, LEC can display the saved revision directly.

The preview lets you confirm that you selected the intended file and revision before restoring it.

### Load Protected Preview

Some backups are protected because the original file required administrator access.

Use **Load Protected Preview** to request an administrator-authorized preview.

After authorization, LEC displays the saved content without restoring it.

Use this before rollback whenever the file contents are meaningful to you.

### Restore or Roll Back

Restoring a revision replaces the current managed state with the selected prior state.

Depending on the revision, this may:

- restore an older file
- recreate a file that LEC removed
- restore the absence of a file that LEC later created

Because rollback changes protected system configuration, administrator authorization may be required.

### Before Restoring

Before restoring a revision:

1. Confirm the file path.
2. Confirm the module that created the revision.
3. Preview the contents when possible.
4. Make sure the revision predates the problem.
5. Avoid restoring unrelated files merely because they were changed around the same time.

A rollback restores the selected configuration revision. It does not automatically reverse every operational action associated with that change.

For example, after restoring:

- a service may need to be restarted
- Caddy may need to be reloaded
- a timer may need to be re-enabled
- a container may need to be recreated

The module responsible for that configuration should normally show the resulting status after you return to it.

## 1.5 Common Tasks

### Change LEC to Dark Mode

1. Open **LEC Settings**.
2. Select the **Settings** tab.
3. Set **Color mode** to **Dark**.
4. Click **Save Settings**.

### Make Module Icons Larger

1. Open **LEC Settings**.
2. Select the **Settings** tab.
3. Set **Module icon size** to **Large**.
4. Click **Save Settings**.

### Hide Advanced Controls

1. Open **LEC Settings**.
2. Select the **Settings** tab.
3. Turn off **Show advanced options**.
4. Click **Save Settings**.

### Restore a Previous Configuration

1. Open **LEC Settings**.
2. Select the **Recovery** tab.
3. Locate the affected module and file.
4. Select a revision from before the problem.
5. Preview it.
6. Use **Load Protected Preview** if required.
7. Click the restore or rollback action.
8. Approve administrator authorization.
9. Return to the affected module and verify its status.

## 1.6 Troubleshooting

### A Setting Does Not Persist

Confirm that you clicked **Save Settings**.

LEC settings are stored separately for each desktop user. Running LEC under another user account will show that account's settings.

### The Theme Changed but Some Controls Look Different

Qt and the Ubuntu desktop may style some native controls differently. Restart LEC if a theme change appears incomplete.

### A Newly Installed Module Is Missing

Restart LEC. Module discovery occurs during startup.

Then check the module table on the Overview tab for loading errors.

### Recovery Does Not Show a Change

Possible reasons include:

- the action did not modify a persistent file
- the file is transient and intentionally excluded
- the change was made outside LEC
- the module bypassed the audited configuration API
- the module was an older version that did not yet support auditing

### A Protected Preview Requests a Password

This is expected. The backup may contain configuration that ordinary users cannot read.

Canceling the prompt leaves the revision unchanged.

### A Restored Setting Has Not Taken Effect

The related service may need to reload or restart.

Open the module that owns the setting and check its current status. Use that module's Apply, Reload, Restart, or verification action when available.

## 1.7 Connections to Other Modules

LEC Settings connects to every module through Recovery.

When another module makes an audited persistent change, its revisions can appear here.

Examples:

- Firewall rule changes
- Reverse Proxy configuration
- Dynamic DNS definitions
- Task Scheduler units
- Mount and share configuration
- Remote Access service configuration
- Docker integration files

LEC Settings does not replace the other modules' setup screens. It provides application-wide preferences and a central place to inspect or reverse managed configuration changes.


---


<a id="hardware-monitor"></a>

# 2. Hardware Monitor

## 2.1 Purpose

Hardware Monitor provides a graphical view of the computer's current resource use and storage health.

Use it to answer questions such as:

- Is the processor unusually busy?
- Is the computer running low on memory?
- Is a disk nearly full?
- Is the system becoming too hot?
- Does a physical drive report a health problem?
- Is a drive self-test available or currently running?

Most Hardware Monitor information is read-only. Viewing normal resource information should not require administrator authorization.

The main views cover:

- **Overview**
- **Processor**
- **Memory**
- **Storage**
- **Disk Health**

The exact arrangement may vary slightly with the LEC version and window size.

## 2.2 Refreshing Information

Hardware information changes continuously.

LEC refreshes live resource information automatically where appropriate. Storage-health information may refresh less frequently because querying a physical drive can take longer.

Use a **Refresh** button when one is provided to request an immediate update.

A brief delay does not necessarily indicate a problem. Some disks, especially external drives and sleeping hard drives, may take several seconds to respond.

## 2.3 Overview

The Overview view summarizes the most important information from the computer.

Typical information includes:

- processor use
- memory use
- available storage
- temperatures reported by the system
- general hardware status

Use this page for a quick health check before opening a more detailed view.

### Processor Use

Processor use shows how much work the CPU is performing.

A low or moderate percentage during ordinary desktop use is normal. Short spikes are also normal when:

- opening applications
- installing software
- compressing files
- scanning disks
- starting containers
- loading a complex web page

Sustained use near 100 percent may indicate:

- a demanding application
- a background process that is stuck
- software installation or updates
- a container using excessive resources
- insufficient hardware for the current workload

Hardware Monitor reports the condition but does not automatically stop the process. Use the available process or service information elsewhere in LEC, or close the responsible application.

### Memory Use

Memory use shows how much physical RAM is currently occupied.

Linux deliberately uses otherwise-idle memory for caching, so high memory use does not always mean the computer is in trouble.

Pay particular attention to:

- very little available memory
- heavy swap use
- applications becoming slow
- repeated freezing or disk activity

Available memory is generally more useful than simply comparing used memory with total memory.

### Storage Use

Storage use shows how much space is occupied on mounted filesystems.

A nearly full system disk can cause:

- failed updates
- application errors
- inability to save files
- containers failing to start
- logs or databases becoming corrupted
- severe system slowdown

Try to keep meaningful free space available on the main Ubuntu filesystem.

## 2.4 Processor View

The Processor view provides more detailed CPU information.

It may include:

- overall utilization
- utilization by logical processor
- processor model
- physical and logical core counts
- current or reported frequency
- load averages
- temperature, when available

### Overall Utilization

Overall utilization combines the activity of all logical processors into one percentage.

This is the best first indicator of whether the CPU is overloaded.

### Per-Processor Activity

Per-processor activity shows whether work is spread across all available logical processors.

One logical processor near 100 percent while the others remain mostly idle can be normal for an application that performs only one task at a time.

All processors remaining near maximum use for an extended period indicates a heavily loaded system.

### Load Average

Linux load average measures work that is running or waiting for processor time.

The three values commonly represent approximately:

- the last minute
- the last five minutes
- the last fifteen minutes

Load average is not itself a percentage.

A load of `4.0` means something different on a two-thread processor than on a sixteen-thread processor. Compare the value with the number of logical processors.

### Processor Frequency

Reported frequency can change as Linux saves power or increases performance.

A low frequency while the system is idle is normal.

A processor that never increases frequency under load may indicate:

- aggressive power-saving settings
- thermal throttling
- firmware limitations
- incomplete sensor reporting

### Temperature

Processor temperature appears only when Ubuntu exposes a compatible sensor.

Temperatures vary considerably by processor and computer design. Short increases under load are normal.

Investigate when:

- the temperature remains unusually high at idle
- the computer slows sharply under load
- fans run constantly
- the system shuts down unexpectedly
- LEC or the firmware reports a warning

LEC does not replace the manufacturer's thermal specifications.

## 2.5 Memory View

The Memory view breaks down physical memory and swap use.

Typical values include:

- total memory
- used memory
- available memory
- cached memory
- swap total
- swap used

### Total Memory

Total memory is the amount of RAM Linux can use. It may be slightly lower than the amount advertised for the computer because some memory can be reserved for hardware.

### Used and Available Memory

Used memory includes active applications and system caching.

Available memory estimates how much memory can be assigned to new work without causing significant pressure.

A system can show a large amount of used memory while still having adequate available memory.

### Cached Memory

Linux uses free RAM to cache recently accessed files.

Cached memory improves performance and is released automatically when applications need it. It is not ordinarily something that must be cleared.

### Swap

Swap is disk-backed space used when RAM is under pressure or when Linux moves inactive memory out of the way.

A small amount of swap use is not automatically a problem.

Heavy and increasing swap use combined with poor responsiveness may indicate:

- too many applications open
- a memory-intensive application
- a memory leak
- insufficient RAM

## 2.6 Storage View

The Storage view lists mounted filesystems and their current capacity.

Typical columns include:

- filesystem or device
- mount point
- filesystem type
- total capacity
- used space
- available space
- percentage used

### Device or Filesystem

This identifies the storage source.

It may be:

- a physical disk partition
- a logical volume
- a temporary filesystem
- a network mount
- a container-related mount

### Mount Point

The mount point is the folder where the filesystem appears.

Common examples include:

```text
/
```

for the main Ubuntu filesystem, and:

```text
/home
```

when home directories are stored separately.

Mounted network storage may appear under `/mnt`, `/media`, or another configured location.

### Filesystem Type

The filesystem type identifies the format or source, such as:

- `ext4`
- `xfs`
- `btrfs`
- `tmpfs`
- `cifs`
- `nfs`

Most users do not need to change anything based on this value. It is useful when troubleshooting or distinguishing local from network storage.

### Capacity and Percentage Used

The percentage used provides the fastest indication of storage pressure.

A warning does not necessarily mean the drive itself is failing. It may simply be running out of free space.

Use **Mounts & Shares** when you need to manage mounted storage or network shares. Hardware Monitor only reports current usage.

## 2.7 Disk Health Tab

The Disk Health tab reports health information from physical drives through SMART or NVMe health data.

This is different from storage capacity:

- **Storage use** asks whether the filesystem is full.
- **Disk health** asks whether the physical device reports signs of failure.

A drive can have plenty of free space and still be unhealthy. It can also be nearly full while remaining physically healthy.

## 2.8 Drive List

The drive list identifies physical disks detected by the system.

Typical information may include:

- device path
- manufacturer
- model
- serial number
- connection type
- capacity
- SMART or NVMe support
- overall reported health
- last refresh time

Select a drive to view its details and available actions.

### Device Path

The device path identifies the physical device, such as:

```text
/dev/sda
/dev/nvme0
/dev/nvme0n1
```

Do not confuse a physical disk with one of its partitions.

### Model and Serial Number

These values help distinguish drives when several devices have similar sizes.

A serial number is hardware-specific and may be useful when matching the on-screen drive to a physical label.

### Connection Type

The drive may be connected through:

- SATA
- NVMe
- USB
- another storage controller

Some USB adapters do not pass SMART information through to Linux. In that case, the disk can work normally while health details remain unavailable.

## 2.9 Overall Health Status

A drive may report a status such as:

- healthy or passed
- warning
- failed
- unsupported
- unavailable
- unknown

### Healthy or Passed

The drive has not reported an overall SMART or NVMe failure.

This does not guarantee that the drive cannot fail. Maintain backups of important data.

### Warning

One or more health indicators deserve attention.

Review the detailed values and make sure important data is backed up.

### Failed

The drive has reported a serious health failure.

Back up important data immediately and plan to replace the drive. Avoid unnecessary write-heavy testing until the data is safe.

### Unsupported or Unavailable

LEC could not retrieve health data.

Possible reasons include:

- the drive does not support SMART
- an external USB adapter blocks SMART commands
- the necessary drive utility is not installed
- administrator access was not granted
- the device is sleeping or disconnected
- the storage controller does not expose health information

This status does not itself mean the drive is bad.

## 2.10 SMART and NVMe Details

The exact information varies by drive.

Possible indicators include:

- power-on hours
- temperature
- reallocated sectors
- pending sectors
- uncorrectable errors
- media errors
- percentage used
- remaining spare capacity
- unsafe shutdowns
- self-test history

### Reallocated Sectors

A reallocated sector has been replaced with spare storage because the original area became unreliable.

A small stable number is not always an immediate emergency, but an increasing number can indicate deterioration.

### Pending Sectors

Pending sectors could not be read reliably and are waiting to be re-tested or remapped.

Important data should be backed up promptly when this count is nonzero, especially if it increases.

### Uncorrectable Errors

These indicate data that the drive could not recover.

Treat increasing uncorrectable-error counts seriously.

### Media Errors

NVMe drives may report media or data-integrity errors.

A rising count warrants investigation and backup.

### Percentage Used

Some solid-state drives estimate how much of their rated endurance has been consumed.

This is not the same as filesystem capacity.

A drive can be only partly full while having consumed much of its write endurance.

### Temperature

Disk temperature can rise during long transfers, indexing, backups, or self-tests.

Persistent excessive temperature can shorten drive life and may indicate poor airflow.

## 2.11 Installing Drive-Health Tools

Disk Health depends on standard Linux drive-health utilities.

When required tools are missing, the tab may offer an **Install Tools** action.

Using it may:

1. request administrator authorization
2. install the required Ubuntu package
3. refresh the drive list
4. retry health discovery

Installing the tools does not alter data on the drives.

## 2.12 Enabling SMART

Some compatible drives support SMART but have it disabled.

When available, **Enable SMART** turns on the drive's health-monitoring feature.

This action may require administrator authorization.

Enabling SMART does not format the drive or erase data. It permits the drive to record and report supported health information.

The option may not appear for:

- NVMe devices, which use a different health interface
- drives where SMART is already enabled
- unsupported devices
- devices behind incompatible USB adapters

## 2.13 Drive Self-Tests

Supported drives may offer built-in self-tests.

Common choices include:

- short test
- extended or long test

### Short Test

A short test performs a limited internal check and normally completes relatively quickly.

Use it for:

- a routine health check
- investigating a new warning
- confirming that the drive can run self-diagnostics

### Extended or Long Test

An extended test examines substantially more of the drive.

It may take many minutes or several hours, depending on the drive.

Use it when:

- the short test reports a problem
- health indicators are concerning
- the drive behaves unreliably
- you are evaluating a drive before continued use

### While a Test Is Running

The computer can often continue using the drive, but performance may be reduced.

Do not:

- disconnect an external drive
- power off the computer unnecessarily
- suspend the device if the test depends on continuous power

A self-test is not a backup and should not be used as a reason to delay backing up important data.

### Test Results

After the expected completion time:

1. Refresh the Disk Health tab.
2. Select the drive.
3. Review the self-test history or latest result.

A failed test is a strong reason to replace the drive after securing important data.

## 2.14 Common Tasks

### Check Whether the Computer Is Under Heavy Load

1. Open **Hardware Monitor**.
2. Review the **Overview**.
3. Open the processor view if CPU use is high.
4. Open the memory view if available memory is low.
5. Check storage if the system disk is nearly full.

### Check Available Disk Space

1. Open **Hardware Monitor**.
2. Open **Storage**.
3. Find the mount point `/`.
4. Review available space and percentage used.
5. Check any separate `/home` or data mounts as well.

### Check a Physical Drive's Health

1. Open **Hardware Monitor**.
2. Select **Disk Health**.
3. Install the required tools if prompted.
4. Select the physical drive.
5. Review overall health and detailed indicators.
6. Refresh if the data is old.
7. Back up important data before further testing when warnings appear.

### Run a Short Drive Self-Test

1. Open **Disk Health**.
2. Select the drive.
3. Choose the short self-test.
4. Approve administrator authorization if requested.
5. Wait for the stated completion time.
6. Refresh the drive information.
7. Review the test result.

## 2.15 Connections to Other Modules

### Mounts & Shares

Hardware Monitor reports capacity for mounted filesystems.

Use **Mounts & Shares** to:

- add or remove persistent mounts
- connect network storage
- manage hosted Samba shares
- troubleshoot a mount that is missing

### Docker

Containers can consume processor time, memory, and disk space.

Use **Docker** to identify and manage containers when resource use appears related to containerized applications.

### Background Services

A background service can cause sustained processor or memory use.

Use **Background Services** to inspect, stop, restart, enable, or disable services.

### Port Usage

Hardware Monitor shows system resources but not network listeners.

Use **Port Usage** to identify which process or container owns a network port.

### System Logs

Use **System Logs** when hardware or storage behavior is accompanied by:

- disk errors
- controller resets
- filesystem warnings
- thermal warnings
- repeated service failures

System Logs may provide context that a health summary alone cannot.

### LEC Settings and Recovery

Hardware Monitor is primarily read-only.

Installing health utilities or enabling SMART is an operational change rather than a normal recoverable configuration revision. There may be little or nothing from Hardware Monitor listed under Recovery.

## 2.16 Troubleshooting

### No Temperature Is Displayed

Possible causes include:

- the computer does not expose a compatible sensor
- the sensor driver is unavailable
- the virtual machine does not provide hardware sensors
- the hardware requires vendor-specific support

Missing temperature data does not necessarily indicate a fault.

### A Drive Is Missing from Disk Health

Confirm that:

- the drive is connected
- Ubuntu can see it
- the drive is not hidden behind an unsupported controller
- the external enclosure is powered
- required health tools are installed

A mounted network share will not appear as a local physical drive.

### SMART Information Is Unavailable Through USB

Some USB-to-SATA bridges do not pass SMART commands.

Try:

- refreshing the drive
- reconnecting it
- using a different USB port
- using a compatible enclosure or adapter

Do not assume the drive is unhealthy solely because the adapter blocks health information.

### A Self-Test Does Not Appear to Finish

Long tests can take hours.

Check:

- the estimated completion time
- whether the drive remained powered
- whether the computer slept
- whether the external drive disconnected

Refresh after the expected time.

### Disk Health Says Passed but the Drive Behaves Badly

SMART does not detect every failure.

Take symptoms seriously, including:

- repeated disconnections
- unusual mechanical sounds
- read or write errors
- filesystem corruption
- severe slowdowns
- kernel storage errors

Back up the data and inspect **System Logs**.

### Storage Shows Full but Disk Health Shows Healthy

These statuses describe different conditions.

- Storage is full because files occupy the available capacity.
- Disk Health is healthy because the physical drive has not reported a hardware failure.

Free space or move data. Replacing a healthy drive is unnecessary unless more capacity is needed.


---


<a id="background-services"></a>

# Background Services

## Purpose

The Background Services module lets you view, start, stop, restart, enable, disable, install, and remove systemd services without using `systemctl` or manually creating service files.

A background service is a program that runs without an ordinary desktop window. Services may:

- start automatically with Ubuntu
- provide networking or storage features
- run a server
- monitor hardware
- perform scheduled or continuous work
- support another application

Stopping or removing the wrong service can prevent applications or parts of Ubuntu from working. When in doubt, leave unfamiliar services alone.

The module has two tabs:

- **Services**
- **Install Service**

## Services Tab

The Services tab lists systemd services known to Ubuntu.

The table refreshes automatically, so status changes should appear after a short delay.

### Service

The **Service** column shows the service name without the `.service` suffix.

Examples might include:

```text
docker
caddy
ssh
```

The name is the system identifier, not always the application's marketing name.

### Status

The **Status** column shows the current runtime state.

Common values include:

#### Running

The service is active.

This usually means the service started successfully, although it does not guarantee that every feature it provides is working correctly.

#### Stopped

The service is installed but not currently running.

This may be normal for:

- optional services
- one-time services
- services started only when needed
- software that has been intentionally disabled

#### Starting or Stopping

The service is changing state.

Wait for the table to refresh before attempting another action.

#### Failed

The service attempted to start but encountered an error.

Use **System Logs** to inspect the failure. Restarting may help after the underlying problem is corrected.

### Startup

The **Startup** column shows whether the service is configured to start automatically.

Common meanings are:

#### Enabled

The service is configured to start automatically under its normal systemd target.

#### Disabled

The service does not start automatically.

It can still be started manually.

#### Static

The service cannot be enabled directly because it is started by another service or system event.

This is normal for many Ubuntu components.

#### Masked

The service is deliberately blocked from starting.

Do not attempt to work around a masked system service unless you understand why it was masked.

#### Indirect, Generated, or Other States

Some systemd units use more specialized startup behavior.

These states are normally informational. LEC enables actions only when they are appropriate.

## Searching and Sorting Services

Use the table's search or filter control to narrow the list.

Useful searches include:

- an application name
- part of a service name
- `docker`
- `caddy`
- `ssh`
- `samba`

You can sort the table by clicking a column heading.

Sorting by status or startup behavior can help locate:

- failed services
- currently running services
- services enabled at startup

## Service Actions

Select a service to see the actions available for that row.

LEC disables actions that do not apply to the current state.

Most actions require administrator authorization.

### Start

Starts a service that is currently stopped.

Use this when:

- an installed service is not running
- you intentionally stopped it earlier
- an application requires the service
- you are testing a newly installed service

Starting a service does not necessarily enable it for the next reboot.

### Stop

Stops a running service.

LEC warns before stopping because applications or system functions may depend on it.

Stopping does not normally change startup behavior. An enabled service may start again after reboot.

### Restart

Stops and starts the service in one operation.

Restarting is commonly useful after:

- changing configuration
- updating an application
- correcting a temporary problem
- restoring configuration through Recovery

The service may be briefly unavailable.

### Enable at Startup

Configures the service to start automatically.

This does not necessarily start it immediately. Use **Start** as well when it must run now.

### Disable at Startup

Prevents the service from starting automatically.

This does not stop a service that is already running.

Use **Stop** separately when you also want to end the current session.

### Remove Service

Deletes an eligible service definition.

LEC only enables removal for regular service files stored directly under:

```text
/etc/systemd/system/
```

This restriction helps prevent removal of vendor-supplied services installed elsewhere.

Before removal, LEC displays:

- the service name
- description
- current status
- startup state
- service-definition path

You may choose to:

- stop the service before removal
- disable automatic startup before removal

LEC creates a verified revision before deleting the service definition, so the file can be restored through Recovery.

Removing a service definition does not necessarily uninstall the application or delete its data.

## Removing a Service Safely

Use service removal only when you know why the service exists.

A safe removal process is:

1. Select the service.
2. Confirm that **Remove Selected Service** is enabled.
3. Note the service name and definition path.
4. Continue past the warning.
5. Leave **Stop the service before removal** selected when the service is running.
6. Leave **Disable automatic startup before removal** selected when it is enabled.
7. Click **Remove Service**.
8. Approve administrator authorization.
9. Confirm that the service disappears from the list.
10. Check the related application afterward.

Do not remove a service merely because you do not recognize its name.

## Install Service Tab

The Install Service tab creates a systemd service for a program or script.

This is useful when an application:

- must run continuously in the background
- does not include its own service installer
- should start automatically with Ubuntu
- needs automatic restart after a crash

LEC generates the service configuration, shows a preview, and installs it under:

```text
/etc/systemd/system/
```

## Service Name

Enter a short, unique system name.

Allowed characters include:

- letters
- numbers
- periods
- underscores
- hyphens
- `@`

You may enter the name with or without `.service`.

Example:

```text
my-media-server
```

LEC will install:

```text
my-media-server.service
```

Use lowercase names with hyphens for readability.

Avoid names that match existing services.

## Description

Enter a plain-language description.

Example:

```text
My Media Server
```

LEC automatically creates a suggested description from the service name until you edit the description manually.

The description appears in service listings and status output.

## Launch Type

Choose how the selected file should be launched.

### Executable

Use this for a compiled program or another file that can run directly.

Examples include:

```text
/usr/local/bin/myserver
/opt/example/example-server
```

### Python Script

Use this for a `.py` file.

LEC launches it with:

```text
/usr/bin/python3
```

The script must be compatible with the system Python environment and have access to all required dependencies.

### Shell Script

Use this for a shell script such as `.sh` or `.bash`.

LEC launches it with:

```text
/bin/bash
```

The script does not need to be made executable when it is explicitly launched through Bash, but it must be readable by the selected user.

When you browse to a `.py`, `.sh`, or `.bash` file, LEC selects the likely launch type automatically.

## Program or Script

Choose the file the service should run.

The file must already exist.

Use **Browse** to select it.

The service will fail when:

- the file is later moved or deleted
- the selected user cannot read it
- required libraries or files are missing
- the path points to a directory instead of a file

For a long-term service, place the program in a stable location rather than in Downloads or another temporary folder.

## Arguments

Enter optional command-line arguments passed to the program.

Example:

```text
--config /etc/example/config.json --port 8080
```

LEC parses quoted arguments correctly.

Example:

```text
--name "Living Room Server"
```

Do not include the program path here. Only enter arguments that come after the program name.

Leave this blank when no arguments are required.

## Working Directory

Choose the folder the program should treat as its current directory.

This matters when the program uses relative paths.

If left blank, LEC uses the program or script's parent folder.

Example:

```text
/opt/example
```

Use **Browse** to select an existing folder.

A wrong working directory can cause a program to fail even when its main file is correct.

## Run as User

Choose the Linux user account that will run the service.

LEC defaults to the currently logged-in user.

Running as your own user is usually appropriate when the program needs access to your files.

Use another account only when:

- the application documentation requires it
- you created a dedicated service account
- the program needs a specific set of permissions

Avoid running a custom application as `root` unless it truly requires unrestricted system access.

The selected user must be able to:

- read and execute the program
- access the working directory
- read its configuration
- write to any required data folders
- open any required devices or ports

Use **User Permissions** when group membership or folder access must be adjusted.

## Start Automatically When the Computer Starts

When selected, LEC configures the service to start during normal system startup.

This is enabled by default.

Turn it off when:

- the service should be started manually
- you are testing it
- it is only needed occasionally

A service can be installed without being enabled.

## Start Immediately After Installation

When selected, LEC starts the service as soon as installation finishes.

This is enabled by default.

Turn it off when:

- configuration still needs to be completed
- another dependency is not ready
- you want to inspect the generated file first
- the service should begin only after reboot

## Restart Automatically if the Program Crashes

When selected, systemd restarts the service after an unexpected failure.

LEC uses a short delay before restarting.

This is useful for:

- servers
- monitoring programs
- long-running automation
- applications expected to remain available

Turn it off when repeated restarts could:

- cause data damage
- trigger unwanted actions
- hide a configuration problem
- consume excessive resources

Automatic restart does not fix the underlying error. Use **System Logs** when the service repeatedly crashes.

## Preview Service

After completing the form, click **Preview Service**.

LEC validates:

- the service name
- the description
- the program path
- the working directory
- the run-as user field
- the argument syntax

The preview displays:

- normalized service name
- installation path
- generated systemd configuration
- a warning when a service with the same name already exists

Review the preview before installation.

Changing any form value invalidates the preview, so preview it again before installing.

## Install Service

After a valid preview, click **Install Service**.

LEC will:

1. stage the generated service file securely
2. request administrator authorization
3. create or replace the service definition
4. create a revision when replacing an existing file
5. reload systemd
6. enable startup when selected
7. start the service when selected
8. return to the Services tab
9. refresh the service table

When the name already exists, LEC asks before replacing it.

Replacing an existing service can change how an application starts. Confirm that you selected the correct service name.

## Example: Run a Python Program at Startup

Suppose the program is:

```text
/home/alex/programs/weather_display.py
```

A typical setup would be:

```text
Service name:
weather-display

Description:
Weather Display

Launch type:
Python script

Program or script:
/home/alex/programs/weather_display.py

Arguments:
Leave blank unless required

Working directory:
/home/alex/programs

Run as user:
alex
```

Then leave these selected:

- Start automatically when the computer starts
- Start immediately after installation
- Restart automatically if the program crashes

Preview the service, inspect the generated configuration, and install it.

## Common Workflows

### Restart a Service After Changing Its Configuration

1. Open **Background Services**.
2. Select the **Services** tab.
3. Search for the service.
4. Select it.
5. Click **Restart**.
6. Approve administrator authorization.
7. Wait for the status to return to Running.
8. Check **System Logs** if it fails.

### Stop a Service Without Disabling It

1. Select the running service.
2. Click **Stop**.
3. Confirm the warning.
4. Approve administrator authorization.

The service remains configured to start at the next boot when Startup still shows Enabled.

### Disable a Service but Leave It Running for Now

1. Select the service.
2. Click **Disable at Startup**.
3. Confirm the warning.
4. Approve administrator authorization.

The current process continues running until it is stopped or the computer shuts down.

### Install a Program as a Service

1. Open **Install Service**.
2. Enter a unique service name.
3. Enter a description.
4. choose the launch type.
5. Select the program or script.
6. Add any required arguments.
7. confirm the working directory.
8. Confirm the run-as user.
9. choose startup and restart behavior.
10. Click **Preview Service**.
11. Review the generated definition.
12. Click **Install Service**.
13. Approve administrator authorization.
14. Confirm the service appears on the Services tab.

## Connections to Other Modules

### System Logs

Use **System Logs** when a service:

- fails to start
- repeatedly restarts
- stops unexpectedly
- reports permission errors
- cannot find files or ports
- behaves differently after boot

Search by the service name for the most relevant entries.

### Port Usage

Use **Port Usage** when a service:

- cannot bind to a port
- is expected to provide a network service
- conflicts with another application
- appears to run but cannot be reached

Port Usage can show which process owns the port.

### Firewall

Starting a network service does not automatically make it reachable through the firewall.

Use **Firewall** to allow the intended network access.

Open only the ports and sources actually required.

### Reverse Proxy

A local web service can be published through **Reverse Proxy** without exposing its internal port directly to the internet.

The service should normally listen on a local address or a deliberately chosen LAN address.

### User Permissions

Use **User Permissions** when a service account needs:

- access to a folder
- membership in a group
- access to a device
- permission to read or write application data

### Hardware Monitor

Use **Hardware Monitor** when a service consumes excessive:

- processor time
- memory
- storage
- temperature headroom

### LEC Settings and Recovery

Services installed or removed through LEC create audited configuration revisions.

Use:

```text
LEC Settings → Recovery
```

to inspect or restore a prior service definition.

Restoring a service file may require returning to Background Services to restart, enable, or verify it.

## Troubleshooting

### The Service Starts and Immediately Stops

Possible causes include:

- the program exits normally instead of remaining active
- the program path is wrong
- required arguments are missing
- the working directory is incorrect
- the run-as user lacks permission
- a required port is already in use
- a dependency is unavailable

Check **System Logs** using the service name.

### The Service Shows Failed

Restarting without correcting the cause may fail again.

Check:

- program path
- working directory
- arguments
- permissions
- required configuration
- occupied ports
- application-specific logs

Then restart the service.

### The Service Runs Manually but Not as a Service

A service has a different environment from an interactive terminal.

Common differences include:

- no shell startup files
- a smaller `PATH`
- no graphical session
- no current terminal
- different working directory
- different environment variables
- different user permissions

Use absolute paths and provide required settings explicitly.

### A Python Script Cannot Import a Package

The service uses:

```text
/usr/bin/python3
```

A package installed only inside a virtual environment may not be available.

Possible solutions include:

- use an executable launcher script that activates the environment
- install the package for the system Python when appropriate
- use the virtual environment's Python executable as an Executable launch type

For example:

```text
/home/alex/myapp/.venv/bin/python
```

with the script path entered as the first argument.

### The Service Cannot Access a File or Folder

Confirm that the selected run-as user has permission.

Use **User Permissions** to inspect group membership and access.

Also verify permissions on every parent directory in the path.

### The Service Cannot Open Its Network Port

Use **Port Usage** to check whether another process already owns the port.

A firewall rule does not resolve a port conflict. It only controls network access.

### Start Is Disabled

Start is unavailable when the service is:

- already running
- currently starting
- currently stopping
- in another transitional state

Wait for the table to refresh.

### Remove Service Is Disabled

LEC only removes regular files stored directly under:

```text
/etc/systemd/system/
```

Vendor-installed services, aliases, generated units, and services stored elsewhere are intentionally protected from removal in this module.

Use the application's package manager or official uninstall process instead.

### The Service Was Removed but the Application Still Exists

Removing the service definition does not uninstall the application.

It also does not normally remove:

- application files
- configuration
- user data
- packages
- containers

Use the application's appropriate uninstall method when complete removal is intended.

### The Service Was Restored but Does Not Start Automatically

After restoring a service definition, you may need to:

1. return to Background Services
2. select the service
3. click **Enable at Startup**
4. click **Start**

Recovery restores configuration files, but operational state may still need to be re-applied.


---


<a id="port-usage"></a>

# Port Usage

## Purpose

The Port Usage module shows which network ports are currently in use and what is using them.

Use it to answer questions such as:

- Which program is using port 8080?
- Is a service listening only on this computer or on the whole network?
- Is a Docker container exposing a port?
- Does a firewall rule allow access to that port?
- Is a Caddy reverse proxy already connected to the service?
- Why can one application not start on the port it expects?

Port Usage is primarily a diagnostic module. It does not normally change the system itself.

The module combines information from:

- Linux network listeners
- running processes
- systemd services
- Docker containers
- Firewall
- Reverse Proxy

## Main Port Table

The main table lists active listening ports detected on the computer.

A listening port is a network endpoint waiting for another program or device to connect.

Each row represents a detected listener or a related network endpoint.

Typical columns may include:

- protocol
- address
- port
- process
- process ID
- system service
- Docker container
- exposure
- firewall status
- reverse-proxy status

The exact columns may vary slightly with the installed LEC version and available integrations.

## Refreshing the List

The Port Usage display refreshes automatically.

LEC also maintains a background snapshot of port information so that other modules and services can use a recent view even when the Port Usage screen is not open.

The background scan normally updates every few minutes. The open Port Usage screen refreshes more frequently.

Use **Refresh** when you need the newest possible result immediately.

A port may briefly remain in the list after an application closes, or may not appear until the next refresh after an application starts.

## Search and Filtering

Use the search field to narrow the table.

You can search for:

- a port number
- a process name
- a service name
- a Docker container name
- an address
- a protocol

Examples:

```text
443
docker
caddy
ssh
127.0.0.1
```

Searching by port number is usually the fastest way to troubleshoot a conflict.

## Protocol

The **Protocol** column identifies how the port communicates.

Common values are:

### TCP

TCP creates a connection between two endpoints and confirms delivery.

It is commonly used by:

- web servers
- SSH
- remote desktop
- databases
- file-sharing services
- application servers

### UDP

UDP sends individual packets without creating the same type of persistent connection.

It is commonly used by:

- DNS
- discovery services
- media streaming
- some games
- time synchronization

The same port number can be used separately by TCP and UDP.

For example, TCP port 53 and UDP port 53 are distinct listeners.

## Address

The address shows where the service is listening.

This is one of the most important columns because it indicates who may be able to reach the service.

### `127.0.0.1`

The service listens only on the local computer through IPv4.

Other computers cannot connect directly.

This is often the safest choice for:

- administrative interfaces
- databases
- services published through Reverse Proxy
- private application back ends

### `::1`

The IPv6 equivalent of local-only access.

### `0.0.0.0`

The service listens on all available IPv4 network interfaces.

It may be reachable from other devices if Firewall and the surrounding network allow it.

### `::`

The service listens on all available IPv6 interfaces and may also accept IPv4 connections depending on the application and system configuration.

### A Specific LAN Address

An address such as:

```text
192.168.1.50
```

means the service is bound to that particular interface or address.

It is normally available only through that network path.

### Docker Addresses

Docker may create listeners on:

- `127.0.0.1`
- the computer's LAN address
- `0.0.0.0`
- IPv6 addresses

The selected Docker access scope determines the bind address.

## Port

The port is the numbered network endpoint used by the application.

Examples include:

```text
22     SSH
80     HTTP
443    HTTPS
```

Applications may use any valid port from 1 through 65535.

Ports below 1024 are traditionally reserved for system services and normally require elevated privileges to bind directly.

A port number alone does not identify the application. Port Usage combines it with process, service, and container information whenever possible.

## Process

The **Process** column shows the program that owns the listening socket.

Examples may include:

```text
sshd
caddy
python3
docker-proxy
```

A process name may differ from the user-facing application name.

For example, a Python application may appear as `python3`, while the related systemd service column provides a more useful identity.

## Process ID

The process ID, or PID, is the temporary numeric identifier assigned to a running process.

A PID changes when the program restarts.

It is useful for technical troubleshooting but should not be treated as a permanent identifier.

When no PID is shown, possible reasons include:

- the process ended during the scan
- the current user cannot inspect it
- the listener is represented through another subsystem
- the information was unavailable in the current snapshot

## System Service

When LEC can match a process to systemd, the **Service** column shows the related background service.

This is more useful than the raw process name when an application is managed by systemd.

Use **Background Services** to:

- inspect the service
- restart it
- stop it
- change startup behavior
- investigate a failure

Not every process belongs to a system service.

Desktop applications and manually launched programs may have no service name.

## Docker Container

When a listener belongs to a Docker container, Port Usage displays the container name when it can determine it.

Docker networking can involve several related ports:

- the port used inside the container
- the port published on the Ubuntu host
- the address on which the host port listens

The host port is the one other applications or devices connect to.

Use the **Docker** module to change a container's published ports or access scope.

## Exposure

The exposure information summarizes how broadly a listener may be reachable.

Typical meanings include:

### Local Only

The listener is bound to a loopback address such as `127.0.0.1` or `::1`.

Only programs on the same computer can connect directly.

### LAN or Specific Interface

The listener is bound to a local network address.

Other devices on that network may be able to connect if Firewall permits it.

### All Interfaces

The listener is bound to `0.0.0.0` or `::`.

This does not automatically mean it is reachable from the internet, but it is listening on every applicable interface.

Actual access also depends on:

- Firewall
- router configuration
- network address translation
- cloud-provider rules
- the application's own authentication

### Docker Exposure

A Docker-managed listener may show the scope selected when the container was created:

- local or reverse-proxy only
- LAN
- all networks

## Firewall Information

When Firewall integration is available, Port Usage can show whether a related rule exists.

Possible conditions include:

- allowed
- restricted
- no matching rule
- Docker-managed rule
- unknown

A firewall rule does not create a listener. It only controls access to one that already exists.

Likewise, a program can listen on all interfaces while still being blocked by Firewall.

Use **Firewall** to inspect or change access rules.

## Reverse Proxy Information

Port Usage can identify listeners referenced by Reverse Proxy rules.

This is especially useful for local web applications.

A common secure arrangement is:

```text
Application:
127.0.0.1:8080

Caddy:
HTTPS hostname on port 443
```

In that arrangement:

- the application is not directly exposed to the network
- Caddy accepts the external request
- Reverse Proxy forwards it to the local application

Use **Reverse Proxy** to inspect or change the hostname and destination.

## Understanding Common Port Arrangements

### Local Application Only

```text
127.0.0.1:8080
```

Only this computer can connect.

Use this for private local applications or services that will be published through Reverse Proxy.

### LAN Service

```text
192.168.1.50:8080
```

Devices on the local network may connect, subject to Firewall.

### All IPv4 Interfaces

```text
0.0.0.0:8080
```

The application accepts connections through any IPv4 interface.

This is broader exposure than most administrative interfaces need.

### Reverse-Proxy Front End

```text
Caddy:
0.0.0.0:443

Application:
127.0.0.1:8080
```

Caddy is publicly or locally reachable on HTTPS, while the application itself remains local.

### Docker Port Mapping

```text
Host:
127.0.0.1:8080

Container:
80/tcp
```

Connections to host port 8080 are forwarded to port 80 inside the container.

## Common Tasks

### Find What Is Using a Port

1. Open **Port Usage**.
2. Enter the port number in the search field.
3. Check the protocol.
4. Review the process, service, and container columns.
5. Open the related module for further action.

### Troubleshoot “Address Already in Use”

This error means another listener already owns the same address, protocol, and port.

1. Search for the port.
2. Confirm whether the conflict is TCP or UDP.
3. Identify the process, service, or container.
4. Decide which application should use the port.
5. Stop or reconfigure the conflicting application.
6. Refresh Port Usage.
7. Retry the original application.

Do not solve a port conflict by adding a firewall rule. Firewall rules do not change port ownership.

### Check Whether a Service Is Listening

1. Search by service name or expected port.
2. Confirm that a row appears.
3. Check the address.
4. Confirm that the process or service is correct.
5. Use **Background Services** if the expected listener is missing.

A service can show as Running while failing to create its expected listener. Check **System Logs** when that occurs.

### Check Whether a Docker Container Is Exposed

1. Search by container name.
2. Review the host address and port.
3. Check the exposure field.
4. Check the firewall status.
5. Check whether Reverse Proxy references it.
6. Use **Docker** to change the published port or scope.

### Check Whether an Application Is Local Only

Look for:

```text
127.0.0.1
```

or:

```text
::1
```

in the address column.

A local-only application can still be reached through Reverse Proxy.

### Check Why Another Computer Cannot Connect

1. Confirm that the listener exists.
2. Check that it is not bound only to `127.0.0.1` or `::1`.
3. Confirm that the expected LAN or all-interface address is shown.
4. Check Firewall for a matching rule.
5. Confirm that the other device is using the correct IP address and port.
6. Check whether the application requires HTTPS or authentication.
7. Review System Logs for rejected or failed connections.

### Check a Reverse-Proxy Destination

1. Search for the destination port.
2. Confirm that the application is listening.
3. Confirm that its address matches the Reverse Proxy destination.
4. Open **Reverse Proxy** to inspect the rule.
5. Check Caddy's own listener on ports 80 and 443.
6. Review **System Logs** if Caddy cannot connect to the destination.

## Connections to Other Modules

### Background Services

Use **Background Services** when the listener belongs to systemd.

Typical actions include:

- start
- stop
- restart
- enable at startup
- inspect service status

### Docker

Use **Docker** when the listener belongs to a container.

Docker controls:

- host port
- container port
- bind address
- access scope
- container startup and removal

### Firewall

Use **Firewall** to control which networks may connect.

Remember:

- Port Usage reports listeners.
- Firewall controls access.
- Neither substitutes for the other.

### Reverse Proxy

Use **Reverse Proxy** to publish a local HTTP service through Caddy.

Port Usage helps confirm that:

- the destination is listening
- the address and port are correct
- Caddy itself is listening on the expected web ports

### Dynamic DNS

Dynamic DNS provides a hostname that can point to the network's current public address.

It does not create or open a port.

A complete public service may require:

- a running listener
- Reverse Proxy
- Firewall access
- router port forwarding
- Dynamic DNS

### Remote Access

SSH, VNC, and Guacamole-related listeners appear in Port Usage when active.

Use **Remote Access** to configure those services.

### System Logs

Use **System Logs** when:

- a listener disappears
- a service cannot bind to its port
- connections are rejected
- Caddy cannot reach a destination
- a Docker port mapping fails
- permissions prevent socket creation

### LEC Settings and Recovery

Port Usage is read-only and normally creates no recoverable configuration changes.

Changes made through Firewall, Reverse Proxy, Docker, or other modules may appear in Recovery.

## Troubleshooting

### The Expected Port Is Missing

Possible causes include:

- the application is not running
- the service failed during startup
- the application is configured for a different port
- the application listens only after completing initialization
- the listener exists inside a container but is not published to the host
- the current snapshot has not refreshed

Refresh the page, then check Background Services, Docker, and System Logs.

### The Same Port Appears More Than Once

This can be normal when:

- one row is TCP and another is UDP
- separate IPv4 and IPv6 listeners exist
- different addresses use the same port
- Docker creates related forwarding listeners
- more than one process shares a socket through system features

Compare protocol and address before concluding that a conflict exists.

### The Process Name Is Generic

Interpreted applications may appear as:

```text
python3
node
java
```

Check the service, PID, container, or command details to identify the actual application.

### No Process or PID Is Displayed

Some process details require permissions or may disappear between scans.

Use the service and container columns where available.

A missing process name does not necessarily mean the listener is invalid.

### Firewall Says No Matching Rule, but the Service Works

Possible reasons include:

- Firewall is disabled
- the connection originates from the same computer
- a broader rule allows the traffic
- Docker networking uses its own rule path
- the connection uses another interface or protocol

Open **Firewall** for the authoritative rule list.

### Firewall Shows Allowed, but the Service Cannot Be Reached

Confirm that:

- the service is actually listening
- it is bound to a reachable address
- the client is using the correct port
- the router or upstream firewall allows the connection
- the service accepts the client's protocol
- application authentication is correct

Firewall permission alone does not guarantee the application is working.

### Reverse Proxy Shows a Rule, but the Destination Is Missing

The application may be stopped or configured for another port.

Start or repair the application before changing the proxy rule.

### A Port Remains After the Application Was Closed

Wait for the next refresh.

If it remains, another process may still own it. Check the PID, service, or container.

### The Background Snapshot Is Old

The Port Usage snapshot service normally runs on a timer.

Check **Background Services** or **System Logs** for:

```text
lec-port-usage.service
lec-port-usage.timer
```

A stale snapshot does not prevent the open Port Usage screen from performing its own refresh, but it may affect information shared with other modules.


---


<a id="user-permissions"></a>

# User Permissions

## Purpose

The User Permissions module provides a graphical way to inspect and manage Linux users, groups, and access relationships.

Use it to:

- see which user accounts exist
- review group membership
- add a user to a group
- remove a user from a group
- understand which account a service or application runs under
- grant an application access to folders or devices through group membership
- troubleshoot permission errors without using commands such as `usermod`, `groups`, or `id`

The module does not replace Linux file ownership and permission rules. Instead, it helps you manage the user and group relationships that those rules depend on.

Most read-only information should not require administrator authorization. Changes to users or groups normally do.

## Linux Users and Groups in Plain Language

Linux controls access primarily through:

- users
- groups
- file ownership
- file permissions

A **user** is an account.

A **group** is a collection of users.

A file or folder normally has:

- one owning user
- one owning group
- permission rules for the owner, group members, and everyone else

Applications and services also run as users. That means a background service can be denied access to a folder even when your own desktop account can open it.

## Main Views

The User Permissions module typically organizes information into views for:

- users
- groups
- membership
- access or permission guidance

The exact tab names may vary slightly by LEC version, but the workflow remains the same.

## Users View

The Users view lists accounts detected on the system.

Typical information may include:

- username
- display name
- user ID
- home directory
- login shell
- account type
- primary group
- supplementary groups

## Username

The username is the account's system name.

Examples:

```text
alex
root
www-data
```

Usernames are case-sensitive and normally use lowercase letters.

## Display Name

The display name is the human-readable name associated with the account.

Not every account has one.

## User ID

The user ID, or UID, is the numeric identifier Linux uses internally.

Typical patterns are:

- `0` for `root`
- lower numbers for system accounts
- higher numbers for ordinary desktop users

You normally do not need to edit a UID.

## Home Directory

The home directory is the user's personal folder.

Example:

```text
/home/alex
```

System accounts may have:

- no usable home directory
- a service-specific directory
- a placeholder such as `/nonexistent`

## Login Shell

The shell indicates what happens when the user logs in through a terminal.

Common values include:

```text
/bin/bash
/usr/sbin/nologin
/bin/false
```

A shell such as `nologin` usually means the account exists only to run a service and is not intended for interactive login.

## Account Type

LEC may distinguish between:

- ordinary users
- system users
- service accounts
- administrative users

Do not delete or modify an unfamiliar system account merely because no person uses it directly. Many applications depend on dedicated service accounts.

## Primary Group

Every user has a primary group.

Files created by that user may use this group by default.

The primary group is different from supplementary group membership.

## Supplementary Groups

Supplementary groups provide additional access.

Examples include:

```text
sudo
docker
sambashare
adm
dialout
```

A user can belong to many supplementary groups.

## Groups View

The Groups view lists groups on the system.

Typical information may include:

- group name
- group ID
- member count
- member list
- group type or description where available

## Group Name

The group name is the identifier used by Linux.

Examples:

```text
docker
sudo
sambashare
media
```

## Group ID

The group ID, or GID, is the numeric identifier used internally.

Most users should work with group names rather than numeric IDs.

## Members

The member list shows users explicitly assigned to the group.

A user may also have the group as a primary group even when not shown in the same way as supplementary members.

## Common Groups

### `sudo`

Members can perform administrator actions through `sudo`.

Do not add users to this group unless they should have broad administrative control.

### `docker`

Members can control Docker.

Docker group membership effectively grants very powerful system access. Treat it as administrator-level access.

### `sambashare`

May be used for Samba sharing workflows.

### `adm`

Often grants access to certain system logs.

### `dialout`

Often grants access to serial devices.

Other applications may create their own groups.

## Membership View

The Membership view lets you inspect and change which users belong to which groups.

A typical workflow is:

1. select a user
2. review current groups
3. select a group
4. add or remove membership
5. apply the change
6. approve administrator authorization

## Add User to Group

Use this when a user or service account needs access granted through a group.

Examples:

- allow a desktop user to manage Docker
- allow a service account to access a shared media folder
- allow a user to access a serial device
- allow a user to manage Samba shares

Before adding membership:

- confirm that the group is correct
- understand what access it grants
- avoid broad administrative groups unless necessary

Some membership changes do not take full effect until the user signs out and back in.

For a service account, restart the service after changing membership.

## Remove User from Group

Use this to revoke access previously granted through a group.

Before removing membership:

- confirm that no application depends on it
- check whether the group is the user's primary group
- expect the user to lose related access after sign-out or service restart

Removing a user from `sudo` removes ordinary administrator privileges.

Removing a user from `docker` prevents direct Docker control after the session refreshes.

## Session Refresh

Linux processes inherit group membership when they start.

That means a new membership may not affect programs that are already running.

After changing group membership:

### For a desktop user

Sign out and sign back in.

A full reboot also works but is usually unnecessary.

### For a background service

Restart the service.

### For a terminal

Close the terminal and open a new one after signing back in.

Do not assume the change failed merely because an already-running program still shows the old access.

## Service Accounts

Many applications run under dedicated users such as:

```text
www-data
caddy
samba
```

A dedicated service account improves security by limiting what the application can access.

When configuring a service, check:

- which user it runs as
- which groups that user belongs to
- which group owns the required folder
- whether the group has read, write, or execute access

Avoid solving permission problems by running a service as `root` unless absolutely necessary.

## Folder Access

The User Permissions module may provide access guidance or controls related to folders.

The key concepts are:

- owner
- group
- read permission
- write permission
- execute permission on directories

For a directory, execute permission means the user can enter or traverse it.

A user may have permission on the final folder but still be blocked by a parent directory.

Example:

```text
/srv/media/music
```

Access depends on permissions for:

```text
/srv
/srv/media
/srv/media/music
```

## Read, Write, and Execute

### Read

For a file, read allows the contents to be opened.

For a directory, read allows the names inside it to be listed.

### Write

For a file, write allows the content to be changed.

For a directory, write allows files to be created, removed, or renamed.

### Execute

For a file, execute allows it to run as a program.

For a directory, execute allows access through the directory.

Directory access often requires both read and execute permissions.

## Shared Group Access

A common way to let several users or services share a folder is:

1. create or choose a group
2. add the required users and service accounts
3. assign that group to the folder
4. grant the group the required permissions
5. restart services or refresh user sessions

This is safer than granting unrestricted access to everyone.

## Common Tasks

### Check Which Groups a User Belongs To

1. Open **User Permissions**.
2. Select the user.
3. Review primary and supplementary groups.
4. Search for the group related to the application or device.

### Give a User Docker Access

1. Open **User Permissions**.
2. Select the user.
3. Add the user to the `docker` group.
4. Approve administrator authorization.
5. Sign out and sign back in.
6. Open the Docker module and verify access.

Docker group membership is highly privileged. Grant it only to trusted users.

### Give a Service Access to a Folder

1. Determine which user the service runs as.
2. Determine which group owns the folder.
3. Add the service user to that group.
4. Confirm the folder grants the group the required access.
5. Restart the service.
6. Check **System Logs** if access still fails.

### Remove Unneeded Group Access

1. Select the user.
2. Review current group memberships.
3. Select the group to remove.
4. Confirm that no application depends on it.
5. Apply the change.
6. Sign out and back in, or restart the affected service.

### Troubleshoot “Permission Denied”

1. Identify the user or service account performing the action.
2. Check its group membership.
3. Check the owner and group of the target file or folder.
4. Check permissions on the target and each parent directory.
5. Add the user to the appropriate group when that is the intended design.
6. Restart the service or refresh the user session.
7. Review **System Logs** for the exact denied path.

## Connections to Other Modules

### Background Services

Use **Background Services** to determine which user a service runs as and to restart it after changing group membership.

A service restart is often required before new group membership takes effect.

### Docker

Docker access commonly depends on membership in the `docker` group.

The Docker module may fail to inspect or manage containers when the current user lacks that membership.

### Mounts & Shares

Mounted storage and Samba shares depend on user and group access.

Use **User Permissions** when:

- a user cannot open a mounted folder
- a Samba service account cannot read a share
- shared folders need common group ownership
- network-mounted files appear with unexpected ownership

### Remote Access

SSH, VNC, and Guacamole-related services may run under specific accounts.

Use User Permissions to confirm that those accounts have access to required home folders, certificates, or configuration.

### Task Scheduler

Scheduled tasks run as a particular user.

That user must have access to every file, folder, command, and device used by the task.

### System Logs

Use **System Logs** for:

- permission-denied messages
- failed authentication
- service startup failures
- inaccessible files
- denied devices
- group-related errors

### LEC Settings and Recovery

User and group membership changes are operational account changes and may not appear as ordinary file revisions in Recovery.

Configuration files written by related modules may still appear there.

## Safety Guidance

### Do Not Modify `root`

The `root` account is the system administrator account.

Do not:

- delete it
- change its UID
- change its primary group
- disable it through unfamiliar methods

### Do Not Remove System Accounts Casually

Accounts with no desktop login may still be required by services.

Examples include web servers, databases, package tools, and monitoring services.

### Avoid Broad Permissions

Do not solve access problems by granting write access to everyone.

Prefer:

- a dedicated group
- only the users and services that need access
- the minimum required permissions

### Treat Powerful Groups Carefully

Membership in groups such as these can grant substantial control:

```text
sudo
docker
disk
shadow
```

Only trusted users should receive such membership.

## Troubleshooting

### A New Group Membership Does Not Work

The user's current session may still have the old group list.

Sign out and sign back in.

For a service account, restart the service.

### A User Appears in the Group but Still Cannot Open the Folder

Check:

- folder ownership
- group ownership
- group permissions
- execute permission on parent directories
- whether the application is running under a different user
- whether the filesystem or mount applies its own ownership rules

### A Service Still Reports Permission Denied

Confirm the service's actual run-as user.

Then restart the service after changing membership.

Use **System Logs** to identify the exact path being denied.

### The User Can Read but Cannot Write

The group may have read permission but not write permission.

Also check whether the filesystem is mounted read-only.

### A Network Share Shows Unexpected Ownership

Network filesystems may map users and groups differently.

Use **Mounts & Shares** to inspect mount options and Samba configuration.

### Removing a Group Membership Had No Immediate Effect

Already-running processes retain their original group list.

Sign out or restart the process.

### An Action Is Disabled

Possible reasons include:

- no user is selected
- no group is selected
- the user already belongs to the group
- the user is not a member of the selected group
- the change would affect a protected relationship
- the account or group is not eligible for that action

### Administrator Authorization Was Canceled

No change was applied.

Select the action again when ready and approve the Ubuntu authorization prompt.


---


<a id="mounts-and-shares"></a>

# Mounts & Shares

## Purpose

The Mounts & Shares module helps you connect storage to Ubuntu and share folders with other computers without manually editing `/etc/fstab`, writing Samba configuration, or using mount commands.

Use it to:

- view currently mounted filesystems
- connect local disks and partitions
- connect network shares
- create persistent mounts that return after reboot
- unmount storage safely
- host folders as Samba shares
- review mount and share status
- troubleshoot missing or inaccessible storage

The module combines two related tasks:

- **Mounts** make storage available on this computer.
- **Shares** make folders from this computer available to other devices.

A mounted network share is storage hosted elsewhere and connected to this computer.

A hosted Samba share is a folder on this computer made available to other devices.

## Important Terms

### Device

A device is a local storage source such as a disk or partition.

Examples:

```text
/dev/sdb1
/dev/nvme1n1p1
```

### Mount Point

A mount point is the folder where Linux makes the storage available.

Examples:

```text
/mnt/media
/mnt/backups
```

After the mount succeeds, opening the mount-point folder displays the contents of the connected storage.

### Network Share

A network share is a folder hosted by another computer, server, or NAS.

Common types include:

- SMB or CIFS shares, commonly used by Windows and Samba
- NFS shares, commonly used by Linux and Unix systems

### Persistent Mount

A persistent mount is configured to reconnect automatically, usually during startup.

LEC creates the required system configuration rather than requiring you to edit `/etc/fstab`.

### Samba Share

A Samba share is a folder hosted by this Ubuntu computer and made available using the SMB protocol.

Windows, Linux, macOS, media players, and many NAS devices can connect to SMB shares.

## Module Views

The module may organize its controls into views such as:

- current mounts
- create or manage mounts
- network mounts
- hosted shares
- diagnostics or advanced details

The exact tab names may vary slightly by LEC version.

## Current Mounts

The current-mounts view lists filesystems presently connected to Ubuntu.

Typical columns may include:

- source
- mount point
- filesystem type
- status
- capacity
- persistent status
- mount options

## Source

The source identifies where the storage comes from.

Examples:

```text
/dev/sdb1
//server/media
server:/exports/backups
```

A source beginning with `//` is usually an SMB share.

A source containing a server name followed by `:/` is usually NFS.

## Mount Point

The mount point is the local folder where the storage appears.

A mount point should normally:

- use an absolute path
- be dedicated to that storage
- remain available between reboots
- not contain unrelated files

Common locations include:

```text
/mnt/<name>
/media/<name>
```

LEC may create the mount-point folder when needed.

## Filesystem Type

Common values include:

```text
ext4
xfs
btrfs
ntfs
vfat
cifs
nfs
```

Examples:

- `ext4` — common Linux filesystem
- `ntfs` — common Windows filesystem
- `vfat` — widely compatible removable-media format
- `cifs` — SMB network share
- `nfs` — NFS network share

## Status

The status indicates whether the mount is currently available.

Common conditions include:

### Mounted

The storage is connected and available.

### Unmounted

The configuration exists, but the storage is not currently connected.

### Failed

Ubuntu attempted to mount the storage but encountered an error.

### Unavailable

The source cannot currently be found or reached.

Possible reasons include:

- a local disk is disconnected
- a network server is offline
- credentials are incorrect
- the network is unavailable
- the mount point is invalid

## Persistent Status

A persistent mount is expected to return automatically.

A temporary mount remains only until it is unmounted or the computer restarts.

Use persistent mounts for:

- media libraries
- backup destinations
- always-connected external storage
- NAS folders
- application data

Use temporary mounts for:

- testing
- one-time transfers
- occasionally connected devices

## Mount Options

Mount options control how Linux connects to the storage.

Most users should use LEC's defaults.

Advanced options may affect:

- read-only versus read-write access
- ownership
- file and folder permissions
- network timeouts
- startup behavior
- automatic reconnection
- device handling

Incorrect options can prevent a mount from working or make files inaccessible.

## Creating a Local Mount

Use a local mount for a disk or partition physically attached to the computer.

Typical setup requires:

- storage device or partition
- mount point
- filesystem type
- automatic-startup choice
- optional advanced mount options

### Select the Device

Choose the correct partition rather than the entire disk when appropriate.

Examples:

```text
/dev/sdb1
/dev/nvme1n1p2
```

Be careful when several disks have similar sizes.

Use Hardware Monitor to compare:

- model
- capacity
- device path
- health information

### Choose a Mount Point

Use a clear path such as:

```text
/mnt/media
/mnt/archive
/mnt/backups
```

Avoid mounting over a folder that already contains important files. Files already present in that folder become hidden while the storage is mounted.

They are not deleted, but they are difficult to access until the mount is removed.

### Automatic Mounting

Enable automatic mounting when the disk is expected to be available at startup.

Do not enable it for a removable drive that is rarely connected unless the configuration is designed to tolerate the missing device.

A poorly configured required startup mount can delay boot or create errors when the drive is absent.

### Apply the Mount

A typical workflow is:

1. Select the device.
2. Choose or create the mount point.
3. Confirm the filesystem type.
4. Choose temporary or persistent behavior.
5. Review advanced options only when needed.
6. Preview the change when available.
7. Apply it.
8. Approve administrator authorization.
9. Verify that the mount appears as Mounted.

## Creating an SMB Network Mount

Use an SMB or CIFS mount to connect to:

- a Windows shared folder
- a Samba server
- a NAS
- another device offering SMB storage

Typical information includes:

- server name or IP address
- share name
- local mount point
- username
- password
- domain or workgroup when required
- automatic-mount choice

## Server Address

Enter the network name or address of the host.

Examples:

```text
fileserver
192.168.1.20
nas.example.local
```

A hostname is easier to remember, but an IP address can help determine whether name resolution is the problem.

## Share Name

Enter the remote share name, not a local folder path.

Example:

```text
Media
Backups
Documents
```

The resulting SMB source may resemble:

```text
//fileserver/Media
```

## Username and Password

Enter credentials accepted by the remote server.

LEC should store credentials in a protected file rather than placing the password directly in the public mount definition.

Use a dedicated network-storage account when practical.

Do not use an administrator account when ordinary share access is sufficient.

## Domain or Workgroup

Some SMB environments require a domain or workgroup.

Home networks often use:

```text
WORKGROUP
```

Leave it blank when the server does not require it.

## SMB Version

Advanced settings may allow an SMB protocol version.

Modern servers normally use SMB 2 or SMB 3.

Avoid SMB 1 unless an old device absolutely requires it. SMB 1 is obsolete and less secure.

## Creating an NFS Network Mount

Use NFS when the server exports storage through the Network File System protocol.

Typical information includes:

- server name or IP address
- exported path
- local mount point
- automatic-mount choice
- optional NFS version or mount options

Example source:

```text
server:/exports/media
```

NFS commonly relies on network identity and server-side access rules rather than an SMB-style username and password.

The server must permit this computer to access the export.

## Testing a Network Mount

When a test action is available, use it before saving a persistent mount.

A successful test confirms that:

- the server can be reached
- the share or export exists
- credentials are accepted
- the mount point is usable
- the required client tools are installed

A successful test does not guarantee that the server will always be available during boot.

## Mounting and Unmounting

### Mount Now

Connects a configured but currently unmounted source.

Use this after:

- reconnecting a disk
- correcting credentials
- restoring network access
- changing mount configuration

### Unmount

Disconnects the filesystem from its mount point.

Unmount before:

- disconnecting an external drive
- changing mount configuration
- removing a persistent definition
- repairing a filesystem

Unmounting does not erase data.

### Busy Mounts

A mount cannot be safely unmounted while a program is actively using it.

Possible users include:

- a file manager window
- a terminal located inside the mount
- a media server
- a backup program
- a Docker container
- a Samba share
- another service

Close or stop the activity, then retry.

Do not force an unmount unless you understand the risk of data loss or application errors.

## Removing a Mount Definition

Removing a persistent mount definition stops Ubuntu from reconnecting it automatically.

A typical safe process is:

1. Stop applications using the mount.
2. Unmount the storage.
3. Select the persistent definition.
4. choose Remove.
5. confirm the source and mount point.
6. Approve administrator authorization.
7. Confirm that the definition is gone.

Removing the definition does not normally delete the files stored on the device or server.

LEC may leave the empty mount-point folder in place.

## Hosted Samba Shares

The hosted-shares view lets this computer share a local folder with other devices using SMB.

Use it for:

- a household media folder
- shared documents
- a backup destination
- transferring files between Windows and Ubuntu
- making storage available to another computer

The folder must already be accessible to the Samba service and intended users.

## Share Name

The share name is what other devices see on the network.

Example:

```text
Media
FamilyFiles
Backups
```

Use a short descriptive name.

Avoid characters that may cause compatibility problems on other operating systems.

## Folder to Share

Select the local folder that should be made available.

Example:

```text
/srv/media
/mnt/storage/shared
/home/alex/Public
```

Before sharing a mounted folder, confirm that the underlying mount is available.

A Samba share pointing to an unmounted location may expose the empty mount-point folder instead of the expected storage.

## Share Description

An optional description helps users identify the share.

Example:

```text
Household media library
```

## Read-Only Access

A read-only share lets users view and copy files but not change them.

Use read-only access for:

- media libraries
- reference files
- software installers
- archives

Read-only sharing is safer when remote devices do not need to upload or modify content.

## Read-Write Access

A read-write share allows authorized users to:

- create files
- modify files
- rename files
- delete files

The underlying Linux folder permissions must also permit those actions.

A Samba setting cannot grant write access when Linux itself denies the service account or user.

Use **User Permissions** to correct user, group, and folder-access relationships.

## Guest Access

Guest access allows connections without an individual Samba username and password.

Use it only on a trusted local network and only for folders that are safe for all connected users.

Avoid guest write access for important data.

Do not expose a guest share directly to the internet.

## Allowed Users

A restricted share may allow only selected users.

Those users may need:

- a Linux account
- a Samba password
- permission to access the underlying folder

The exact requirements depend on the share configuration.

## Creating a Hosted Share

A typical workflow is:

1. Open the hosted-shares view.
2. Click Create or Add Share.
3. Enter the share name.
4. Select the local folder.
5. Enter a description if desired.
6. choose read-only or read-write access.
7. choose guest or authenticated access.
8. select allowed users when applicable.
9. Preview the configuration.
10. Apply the share.
11. Approve administrator authorization.
12. Verify that Samba is running.
13. Test from another device.

## Connecting from Another Device

### Windows

In File Explorer, enter:

```text
\\computer-name\ShareName
```

or:

```text
\\192.168.1.50\ShareName
```

### Linux

A file manager may accept:

```text
smb://computer-name/ShareName
```

### macOS

In Finder, use **Connect to Server** and enter:

```text
smb://computer-name/ShareName
```

Use the Ubuntu computer's actual hostname or LAN address.

## Removing a Hosted Share

Removing a Samba share stops advertising and serving that folder through the share name.

It does not delete the folder or its contents.

A safe process is:

1. Confirm no one is actively transferring files.
2. Select the share.
3. Click Remove.
4. Confirm the share name and folder.
5. Approve administrator authorization.
6. Verify from another device that the share is no longer available.

## Common Tasks

### Mount a NAS Folder Automatically

1. Open **Mounts & Shares**.
2. choose the network-mount view.
3. Select SMB or NFS.
4. Enter the server and share information.
5. choose a mount point under `/mnt`.
6. enter credentials when required.
7. Enable automatic mounting.
8. Test the connection.
9. Apply the configuration.
10. Approve administrator authorization.
11. Confirm the mount appears as Mounted.

### Safely Disconnect an External Drive

1. Stop applications using the drive.
2. Open **Mounts & Shares**.
3. Select the mount.
4. Click **Unmount**.
5. Wait until the status shows Unmounted.
6. Disconnect the drive.

### Share a Media Folder on the LAN

1. Confirm the media folder is mounted and accessible.
2. Open the hosted-shares view.
3. Create a share named `Media`.
4. Select the folder.
5. choose read-only access unless uploads are required.
6. choose authenticated or guest access.
7. Apply the share.
8. Allow SMB through Firewall for the local network.
9. Test from another computer.

### Give a Service Access to a Mounted Folder

1. Identify which user the service runs as.
2. Open **User Permissions**.
3. Add the service user to the appropriate folder-access group.
4. Confirm the mount presents compatible ownership and permissions.
5. Restart the service.
6. Check **System Logs** if access is still denied.

## Connections to Other Modules

### Hardware Monitor

Use **Hardware Monitor** to check:

- filesystem capacity
- available space
- physical disk identity
- physical disk health

Mounts & Shares manages availability. Hardware Monitor reports usage and health.

### User Permissions

Use **User Permissions** when:

- a user cannot access a mounted folder
- a service cannot read or write mounted storage
- a Samba user lacks permission
- shared folders need common group access

### Background Services

Mounts and hosted shares may depend on services such as:

- Samba
- network services
- application services using the storage

Use **Background Services** to start, stop, restart, or inspect those services.

### Firewall

Hosted SMB shares may require Firewall access for the local network.

Use **Firewall** to allow only the required Samba service or ports and restrict access to the intended network.

A client mount normally does not require an inbound firewall rule on this computer.

### Docker

Docker containers may use mounted folders as bind mounts.

Before changing or unmounting storage used by Docker:

1. stop the affected container
2. change the mount
3. confirm the storage is available
4. start or recreate the container

### Task Scheduler

Scheduled backups or maintenance tasks may rely on a mounted destination.

Confirm that the mount is available before the task runs.

A task that starts before a network mount is ready may fail.

### Port Usage

Use **Port Usage** to confirm that Samba is listening on the expected network ports.

### System Logs

Use **System Logs** for:

- failed automatic mounts
- authentication errors
- unreachable network shares
- Samba startup failures
- permission-denied messages
- device or filesystem errors

### LEC Settings and Recovery

Persistent mount definitions and hosted-share configuration created by LEC should appear under:

```text
LEC Settings → Recovery
```

Recovery can restore the configuration, but you may still need to:

- mount the source again
- restart Samba
- restart an application using the storage

## Safety Guidance

### Do Not Format Storage Through This Module

Mounting is not formatting.

LEC should not require formatting merely to mount an existing supported filesystem.

Do not use unrelated disk tools to reformat a drive unless you intend to erase it.

### Unmount Before Disconnecting

Disconnecting writable storage while it is mounted can cause:

- incomplete writes
- filesystem corruption
- lost data
- application errors

### Keep Credentials Protected

Do not place SMB passwords directly in public configuration or scripts.

Use the protected credential storage created by LEC.

### Avoid Broad Guest Write Access

Guest write access can allow any device on the network to alter or delete files.

Use authenticated users and group-based access for important data.

### Backups Still Matter

Mount configuration and Samba configuration can be recovered through LEC.

The files stored on the mounted device or shared folder are separate and require their own backups.

## Troubleshooting

### A Local Drive Does Not Appear

Confirm that:

- the drive is connected and powered
- Ubuntu detects it
- the correct partition exists
- another mount is not already using it

Use Hardware Monitor to look for the physical device.

### A Mount Fails After Reboot

Possible causes include:

- the device was disconnected
- the network was not ready
- the server was offline
- credentials changed
- the device name changed
- the mount options are too strict
- required client packages are missing

Check **System Logs** for the mount-point or source name.

### A Network Share Works by IP but Not by Name

This is usually a name-resolution problem.

Use the server's IP address temporarily and check:

- local DNS
- mDNS or `.local` naming
- router hostname records
- spelling

### SMB Credentials Are Rejected

Confirm:

- username
- password
- domain or workgroup
- server permissions
- whether the account is allowed to use the share
- whether the password changed

Try connecting from another device to determine whether the issue is server-side.

### The Mount Is Read-Only

Possible causes include:

- the mount was intentionally configured read-only
- the remote server grants read-only access
- the local filesystem detected errors
- the underlying device is write-protected
- Linux permissions deny writing

Review mount options, server permissions, and System Logs.

### Unmount Says the Target Is Busy

Close:

- file manager windows
- terminals using the folder
- media players
- backup jobs

Stop any service or Docker container using the mount, then retry.

### Files Have the Wrong Owner

Network and non-Linux filesystems may map ownership through mount options.

Use advanced ownership options only when needed.

For Samba-hosted folders, also check User Permissions and the share's access settings.

### Other Computers Cannot See the Samba Share

Confirm that:

- Samba is running
- the share exists
- the computer is on the same network
- Firewall permits SMB from the LAN
- the client is using the correct hostname or IP address
- the network is not configured to isolate devices

Try connecting directly with the full path rather than relying on automatic network discovery.

### Users Can Open the Share but Cannot Write

Check both layers:

1. the Samba share must permit writing
2. Linux folder permissions must permit writing

Use **User Permissions** to correct group membership or folder access.

### The Share Shows an Empty Folder

The share may point to a mount point whose storage is currently unmounted.

Mount the underlying storage, then reconnect from the client.

### Restoring a Mount Revision Did Not Reconnect It

Recovery restores the configuration file.

Return to Mounts & Shares and use **Mount Now**, or restart the relevant service or computer when appropriate.


---


<a id="system-logs"></a>

# System Logs

## Purpose

The System Logs module helps you understand what Ubuntu and installed services are reporting without requiring you to use `journalctl`, search raw log files, or interpret every technical message yourself.

Use it to:

- review recent system events
- find warnings and failures
- inspect logs for a specific service
- review boot and kernel messages
- investigate authentication and security events
- open readable raw log sources
- identify services or timers that systemd currently marks as failed

LEC organizes log entries into clearer categories and provides plain-language interpretations where possible.

The original log message is always retained so you can inspect the exact technical detail when needed.

## Important Limitation

Log interpretation is guidance, not a diagnosis.

Linux applications choose their own log priorities, and some messages marked as errors or critical are harmless in context. Likewise, a serious problem may appear only as a warning.

When an interpretation and the original message seem inconsistent:

1. read the original message
2. check whether the event repeats
3. review nearby entries
4. open the related module
5. verify whether the affected service or feature actually failed

## Module Tabs

The System Logs module includes:

- **Overview**
- **Live Logs**
- **Service Logs**
- **Boot & Kernel**
- **Authentication & Security**
- **Raw Sources**

## Overview Tab

The Overview tab summarizes current log activity and highlights conditions that may need attention.

Typical sections include:

- recent warnings and errors
- event counts by severity or category
- recent interpreted events
- systemd units marked as failed

Use this tab as the starting point when you know something is wrong but do not yet know where to look.

## Event Severity

LEC may label events with severity levels such as:

- Critical
- Error
- Warning
- Notice
- Information

These labels are based primarily on the priority supplied by the original log source.

### Critical

The source marked the event as extremely serious.

Investigate promptly, especially when the message relates to:

- disk or filesystem failure
- kernel failure
- repeated service crashes
- authentication attacks
- hardware errors

Do not assume every Critical label means the system is compromised or unusable. Some applications assign overly severe priorities to canceled or unsuccessful actions.

### Error

An operation failed.

An isolated error may be harmless when the program recovered automatically. Repeated errors usually deserve investigation.

### Warning

Something unusual occurred, but the operation may have continued.

Warnings are often useful early indicators of:

- configuration problems
- unavailable dependencies
- permissions issues
- degraded hardware
- network interruptions

### Notice or Information

These messages usually describe normal activity, state changes, or routine operation.

They are useful when reconstructing what happened before or after a failure.

## Event Categories

LEC groups messages into categories where possible.

Examples include:

- Services
- Security
- Storage
- Network
- Kernel
- Hardware
- Authentication
- General System

Categories make it easier to filter unrelated messages.

A category is based on deterministic interpretation rules and may not always match the application's own terminology.

## Interpreted Event Cards

An interpreted event normally includes:

- severity
- summary
- category
- explanation
- confidence
- suggested action
- source
- original message

### Summary

A short plain-language description of the event.

### Explanation

A longer description of what the event probably means.

### Confidence

Confidence indicates how specifically LEC recognized the message.

Typical meanings are:

#### High Confidence

The message matched a known and specific pattern.

#### Medium Confidence

LEC recognized the general condition but may not know every detail.

#### Low Confidence

The interpretation is broad and should be checked against the original message.

### Suggested Action

A practical next step, such as:

- restart a service
- inspect permissions
- check storage
- review repeated authentication failures
- open another LEC module

Suggested actions do not run automatically.

### Original Message

The exact text recorded by the source.

Use this when:

- reporting a problem
- searching documentation
- comparing repeated entries
- checking whether the interpretation is accurate

## Duplicate Grouping

Repeated identical or nearly identical events may be grouped.

A grouped event shows that the same message occurred multiple times instead of filling the screen with duplicates.

Repeated events are often more important than a one-time event.

Examples include:

- a service restarting every few seconds
- repeated login failures
- a disk repeatedly disconnecting
- a timer failing on every run

## Systemd Units Marked Failed

The Overview tab includes a section for services, timers, or other units that systemd currently marks as failed.

Typical columns include:

- Unit
- Description
- Result
- Exit Status
- Last Failure
- Associated Timer
- Timer Status
- Next Run

## Unit

The systemd unit name.

Examples:

```text
example.service
example.timer
```

## Description

The human-readable description supplied by systemd.

## Result

The general reason systemd recorded the failure.

Examples may include:

- exit-code
- timeout
- signal
- dependency
- resources

## Exit Status

The program's numeric or named exit status when available.

An exit status of zero normally means success. Other values are application-specific.

## Last Failure

The most recent time the unit entered a failed state.

## Associated Timer

For a failed service started by a timer, LEC may show the related timer.

This helps distinguish:

- a permanently running service
- a one-time background scan
- a scheduled job

## Timer Status and Next Run

These columns show whether the timer remains active and when it is expected to run again.

A service can remain marked as failed even while its timer is still active and waiting to retry later.

## Failed-State Markers

Systemd remembers that a unit failed until the marker is cleared or the unit succeeds under some circumstances.

A failed marker does not always mean the service is currently broken.

For example:

- a timer-triggered service failed yesterday
- the underlying issue was corrected
- the unit has not run again yet
- systemd still lists the old failure

Use the log details and current service status to decide whether the problem is active.

## Clear Selected Markers

Clears systemd's failed-state marker for the selected unit.

This does not:

- repair the service
- start the service
- change its configuration
- delete logs

Use it after:

- correcting the cause
- confirming the event is old
- verifying the service now works
- deciding that the marker is no longer useful

If the service fails again, it will reappear.

## Clear All Old Markers

Clears failed-state markers for all listed units.

Use this only after reviewing the list.

This is useful after:

- installing fixes
- completing a development or testing cycle
- removing obsolete failure markers
- verifying that the affected services are now healthy

If several units immediately return to the list, the failures are current rather than historical.

## Live Logs Tab

The Live Logs tab displays recent journal events and updates as new entries arrive.

Use it when:

- reproducing a problem
- starting or restarting a service
- connecting a device
- testing network access
- applying a configuration change
- watching for repeated failures

## Live Filtering

Available filters may include:

- severity
- category
- source
- free-text search

Use narrow filters while reproducing a problem.

Examples:

```text
caddy
docker
permission denied
sda
authentication
```

## Watching a Problem in Real Time

A useful workflow is:

1. Open **Live Logs**.
2. Clear or narrow the current filter.
3. Enter the related service, application, device, or error text.
4. Perform the action that causes the problem.
5. Watch for new entries.
6. inspect the interpreted summary and original message.
7. Open the related module to correct the issue.

## Pausing or Refreshing

When available, use Pause to stop the display from moving while you inspect an event.

Pausing the display does not stop system logging.

Resume or refresh to continue.

## Service Logs Tab

The Service Logs tab shows journal entries for a selected systemd service.

Use it when a service:

- fails to start
- stops unexpectedly
- repeatedly restarts
- cannot open a file or port
- reports configuration errors
- appears Running but does not work

## Selecting a Service

Choose or enter the systemd service name.

Examples:

```text
docker.service
caddy.service
ssh.service
```

LEC may accept the name with or without `.service`, depending on the control.

Use **Background Services** to confirm the exact service name.

## Time Range and Entry Limit

Controls may allow you to choose:

- recent entries
- current boot
- a maximum number of messages
- a date or time range

Start with recent entries. Expand the range when the failure occurred earlier.

## Reading Service Failures

Look for the first meaningful error before a chain of follow-up failures.

A common sequence is:

1. application reports the real problem
2. process exits
3. systemd reports an exit code
4. restart is attempted
5. failure repeats

The earliest application-specific message is often more useful than the later generic systemd messages.

## Boot & Kernel Tab

The Boot & Kernel tab focuses on startup, hardware, driver, filesystem, and kernel messages.

Use it for problems such as:

- slow or failed boot
- missing hardware
- storage errors
- network interface problems
- driver failures
- USB disconnects
- thermal warnings
- filesystem repair
- kernel crashes or hangs

## Current Boot

The current-boot view limits results to messages recorded since the computer last started.

This is useful for:

- startup failures
- devices missing after reboot
- services that failed during boot
- mount failures
- driver initialization

## Previous Boot

When available, reviewing the previous boot is useful after:

- an unexpected restart
- a system freeze
- a crash
- a shutdown caused by power loss
- a kernel panic

The last messages before shutdown may provide clues.

## Kernel Messages

Kernel messages may mention:

- device names
- drivers
- storage controllers
- filesystem names
- network interfaces
- thermal zones

Examples of useful search terms include:

```text
nvme
sda
usb
ext4
thermal
wifi
firmware
```

Kernel messages can be highly technical. Use the exact message when searching official Ubuntu or hardware documentation.

## Authentication & Security Tab

This tab collects events related to:

- login attempts
- sudo
- Polkit authorization
- SSH authentication
- PAM
- account access
- security-related denials

Use it to investigate:

- repeated failed logins
- unexpected administrator prompts
- denied administrative actions
- SSH access problems
- authentication failures
- suspicious repeated attempts

## Normal Authentication Failures

Not every failed authentication event is malicious.

Common harmless causes include:

- canceling a password prompt
- entering the wrong password
- allowing a prompt to time out
- closing a dialog
- an application requesting authorization and then stopping
- attempting SSH with an incorrect saved password

For example, a Polkit event stating that authentication could not identify a password often means the administrator prompt was canceled, closed, or did not receive usable input.

No administrative action was approved in that case.

## When to Investigate Further

Pay more attention when failures:

- repeat many times
- occur when you were not using the computer
- come from an unknown remote address
- target several usernames
- are followed by a successful login
- involve unexpected privilege elevation
- coincide with changed files or services

## SSH Events

SSH authentication logs may show:

- remote address
- attempted username
- authentication method
- success or failure
- connection closure

Occasional automated attempts are common on internet-exposed SSH servers.

Use **Remote Access** and **Firewall** to restrict access appropriately.

## Polkit Events

Polkit is the authorization system Ubuntu uses for graphical administrator prompts.

A failed Polkit event normally means the protected action did not proceed.

Repeated unexpected prompts may indicate:

- an application repeatedly retrying
- a broken administrative workflow
- a background process incorrectly requesting authorization
- an unfamiliar application

## Raw Sources Tab

The Raw Sources tab provides access to readable log files and unprocessed sources.

Use it when:

- the interpreted views omit necessary detail
- an application writes outside the journal
- you need the exact original file
- troubleshooting instructions reference a specific log
- you want to compare LEC's interpretation with the raw source

Only files readable by the current desktop user are shown directly.

Protected logs may require another approved method or may be unavailable in this view.

## Raw Log Cautions

Raw logs may contain:

- usernames
- hostnames
- IP addresses
- file paths
- device serial numbers
- application configuration details
- partial command lines

Review logs before posting them publicly.

Never publish:

- passwords
- API tokens
- private keys
- session cookies
- full authentication headers

## Common Tasks

### Investigate a Failed Service

1. Open **System Logs**.
2. Check **Overview** for the failed unit.
3. Note the unit name, result, and last failure.
4. Open **Service Logs**.
5. Select the service.
6. Review the first meaningful error.
7. Open **Background Services** to restart or manage it.
8. Clear the failed marker only after verifying the problem is resolved.

### Watch Logs While Testing a Change

1. Open **Live Logs**.
2. Filter by the related application or service.
3. Apply the change in another module.
4. Watch for new warnings or errors.
5. inspect the original message.
6. Return to the other module to correct the issue.

### Investigate a Disk or Filesystem Problem

1. Open **Boot & Kernel**.
2. Search for the device name, such as `sda` or `nvme0`.
3. Search for the filesystem type, such as `ext4`.
4. Review repeated errors or resets.
5. Open **Hardware Monitor → Disk Health**.
6. Back up important data before running lengthy tests when errors appear.

### Investigate a Failed Administrator Prompt

1. Open **Authentication & Security**.
2. Find the event at the time of the prompt.
3. Check whether it indicates cancellation, timeout, or wrong credentials.
4. Confirm whether the requested action actually occurred.
5. Retry the action only when you intended to approve it.

### Check the Previous Boot After a Crash

1. Open **Boot & Kernel**.
2. Select the previous boot when available.
3. Review the final messages before the restart.
4. Search for:
   - panic
   - out of memory
   - thermal
   - I/O error
   - watchdog
   - filesystem
5. Compare with Hardware Monitor and service logs.

## Connections to Other Modules

### Background Services

Use **Background Services** to act on a service identified in the logs.

System Logs explains what happened. Background Services lets you:

- start
- stop
- restart
- enable
- disable

### Hardware Monitor

Use **Hardware Monitor** when logs mention:

- disk errors
- temperature
- memory pressure
- hardware resets
- storage health
- resource exhaustion

### Port Usage

Use **Port Usage** when logs mention:

- address already in use
- bind failure
- connection refusal
- occupied ports
- missing listeners

### Firewall

Use **Firewall** when logs suggest:

- blocked network traffic
- denied connections
- missing access rules
- Docker exposure problems

### Docker

Use **Docker** when the source is a container or Docker-managed service.

Container application logs may still need to be viewed through Docker-specific controls.

### Reverse Proxy

Use **Reverse Proxy** when Caddy logs report:

- unreachable upstream
- certificate problems
- hostname errors
- TLS failures
- incorrect destination ports

### Dynamic DNS

Use **Dynamic DNS** when logs indicate:

- provider authentication failure
- hostname update failure
- public-IP discovery problems
- DNS API timeouts

### Mounts & Shares

Use **Mounts & Shares** when logs show:

- failed mounts
- unavailable network shares
- Samba errors
- permission problems
- missing storage

### Remote Access

Use **Remote Access** when logs relate to:

- SSH
- VNC
- Guacamole
- failed remote login
- unavailable remote-access service

### Task Scheduler

Use **Task Scheduler** when a timer-triggered service appears in the failed-units list.

The associated timer, next run, and service logs help determine whether a scheduled task is repeatedly failing.

### LEC Settings and Recovery

System Logs is read-only and does not normally create Recovery revisions.

Use Recovery when logs show that a recent configuration change caused the problem.

## Troubleshooting

### No Logs Appear

Possible causes include:

- filters are too narrow
- the selected time range contains no entries
- the service name is incorrect
- the current user cannot read the source
- the source does not use journald
- the journal is unavailable or empty

Clear filters and expand the time range.

### A Service Is Marked Failed but Works Now

The systemd failed-state marker may be old.

Confirm that:

- the service is currently running
- recent logs show success
- the related timer is healthy

Then clear the selected marker.

### A Cleared Failure Immediately Returns

The service or task is still failing.

Open Service Logs and inspect the newest event.

Do not repeatedly clear the marker without correcting the cause.

### An Event Is Labeled Critical but Seems Harmless

Read the original message and context.

Applications sometimes assign an overly severe journal priority.

Check:

- whether the action actually failed
- whether it was canceled intentionally
- whether the message repeats
- whether the related feature still works

### Logs Show Only Generic systemd Errors

Look earlier in the service log.

The application usually records the specific reason before systemd reports the final exit status.

### A Raw Log File Is Missing

It may be:

- protected
- stored elsewhere
- managed entirely through journald
- created only after the application runs
- unavailable to the current user

Use the relevant module or official application documentation to locate it.

### Log Times Seem Wrong

Confirm:

- system time
- time zone
- whether the application logs in UTC
- whether the event came from another machine or container

### The Live View Moves Too Quickly

Pause the display when available or use a narrow search filter.

You can also switch to Service Logs for a stable, service-specific view.

### Repeated Login Failures Appear from the Internet

For SSH or another exposed service:

1. review the source addresses
2. confirm that no unexpected login succeeded
3. restrict access through Firewall
4. consider key-based SSH authentication
5. disable unnecessary remote-access methods
6. review Remote Access settings


---


<a id="firewall"></a>

# Firewall

## Purpose

The Firewall module provides a graphical way to control which network connections are allowed to reach this computer.

LEC manages Ubuntu's UFW firewall and also includes Docker-aware rules for containers published through Docker.

Use it to:

- see whether the firewall is active
- review existing rules
- allow or block access to a port or service
- limit access to a local network or specific address
- remove rules that are no longer needed
- manage Docker-specific exposure
- verify how firewall settings relate to Port Usage, Docker, Remote Access, and Reverse Proxy

The firewall controls network access. It does not start an application, create a listening port, or configure a router.

A service must already be running and listening before a firewall rule can make it reachable.

## Important Safety Note

Changing firewall rules can:

- expose a service to other devices
- make an internet-facing service reachable
- block your own remote connection
- interrupt access to SSH, VNC, web services, or containers

Before removing or tightening a rule, confirm how you are connected to the computer.

If you are managing the machine remotely, take special care not to remove the rule that permits your current connection.

## Module Views

The Firewall module typically includes views for:

- firewall status
- standard UFW rules
- creating or removing rules
- Docker Rules

The exact tab names may vary slightly by LEC version.

## Firewall Status

The status area shows whether UFW is active.

Common states include:

### Active

The firewall is enforcing its current rules.

### Inactive

UFW is installed but not currently enforcing rules.

Applications may still be protected by:

- their own bind address
- Docker networking
- a router
- another firewall
- cloud-provider rules

An inactive local firewall does not mean the computer is automatically reachable from the internet.

### Unavailable

LEC could not read or manage UFW.

Possible causes include:

- UFW is not installed
- the required command is unavailable
- administrator access was not granted
- a command failed
- the system uses a different firewall manager

## Enable Firewall

Enabling UFW activates the current rule set.

Before enabling:

1. Review existing rules.
2. Confirm that any required remote-access rule exists.
3. Check which services listen on the network.
4. Make sure Docker exposure is understood.

If you use SSH to manage the computer remotely, allow SSH before enabling the firewall.

## Disable Firewall

Disabling UFW stops standard UFW filtering.

This does not:

- stop services
- remove listeners
- remove Docker containers
- close router port forwarding
- disable application authentication
- necessarily remove Docker-specific rules

Disable the firewall only for troubleshooting or when another firewall is intentionally replacing it.

Do not use permanent firewall disabling as the normal solution to a connectivity problem.

## Standard Rules Table

The standard rules table shows UFW rules currently configured.

Typical columns may include:

- action
- direction
- protocol
- port or service
- source
- destination
- IP version
- comment or description

## Action

Common actions include:

### Allow

Permits matching traffic.

### Deny

Blocks matching traffic and normally rejects it silently.

### Reject

Blocks matching traffic and sends a rejection response.

Most LEC workflows use Allow rules for intended services and rely on the firewall's default policy for everything else.

## Direction

### Incoming

Controls connections initiated from another device toward this computer.

Most service rules are incoming rules.

### Outgoing

Controls connections initiated by this computer.

Most Ubuntu desktops allow outgoing traffic by default.

Do not add outgoing restrictions unless you understand the application's requirements.

## Protocol

The rule may apply to:

- TCP
- UDP
- both protocols

Choose the protocol used by the service.

Examples:

```text
SSH        TCP
HTTP       TCP
HTTPS      TCP
DNS        TCP and UDP
```

Do not allow both protocols merely because you are uncertain. Use the service's documentation or Port Usage.

## Port or Service

A rule may refer to:

- a single port
- a port range
- a named UFW application profile
- a known service

Examples:

```text
22
80
443
8000:8010
OpenSSH
```

Using a named service profile is convenient when the installed application supplies one.

A numeric port gives more direct control.

## Source

The source controls which remote addresses may connect.

### Anywhere

Allows matching traffic from any reachable source.

Use this only when the service must be broadly available.

### Local Network

Restricts access to the computer's LAN or a selected private network.

This is appropriate for:

- Samba shares
- local dashboards
- media servers
- VNC
- administrative tools used only at home or work

### Specific Address

Allows only one remote IP address.

Use this for tightly controlled access when the source address is stable.

### Specific Network

Allows an address range such as:

```text
192.168.1.0/24
```

This commonly represents all devices on a home LAN.

## Destination

The destination normally refers to this computer or a specific local address.

Most users do not need to change it.

Advanced destination restrictions can be useful on computers with several network interfaces.

## IPv4 and IPv6

A rule may apply to IPv4, IPv6, or both.

If the computer and network use IPv6, an IPv4-only rule may not protect or permit the equivalent IPv6 traffic.

Review both protocol families when troubleshooting unexpected access.

## Creating a Standard Rule

A typical Add Rule form asks for:

- action
- protocol
- port or service
- source
- optional comment

A safe workflow is:

1. Confirm the service is running.
2. Check its address and port in **Port Usage**.
3. Decide who should be able to connect.
4. Choose the narrowest practical source.
5. Select the correct protocol.
6. Enter the port or service.
7. Review the rule.
8. Apply it.
9. Approve administrator authorization.
10. Test from an allowed device.

## Choosing the Right Scope

Use the narrowest scope that meets the need.

### Local-Only Service

A service bound to:

```text
127.0.0.1
```

does not need a normal inbound firewall rule because other devices cannot connect directly.

### LAN Service

For a service intended only for the local network:

- bind it to a LAN address or all interfaces
- allow only the LAN network in Firewall

### Public Service

For a service intended for internet access:

- prefer Reverse Proxy for HTTP and HTTPS
- expose only required ports
- use authentication
- use TLS
- understand router or cloud firewall rules
- avoid exposing administrative interfaces directly

## Comments

Use a clear comment when the form supports it.

Good examples:

```text
Allow Samba from home LAN
Allow SSH from office VPN
Allow media server on local network
```

Comments make later cleanup much easier.

## Removing a Standard Rule

Remove rules that are obsolete, duplicated, or broader than necessary.

A safe process is:

1. Select the rule.
2. Read the action, port, protocol, and source carefully.
3. Confirm which application depends on it.
4. Verify that removing it will not cut off your current connection.
5. Click Remove.
6. Approve administrator authorization.
7. Test the service afterward.

Removing a rule does not stop the service. It only changes whether matching traffic can reach it.

## Duplicate and Overlapping Rules

UFW may contain rules that overlap.

Examples:

- one rule allows port 22 from anywhere
- another allows port 22 from the LAN
- one rule allows a named profile
- another allows the same numeric port

The broader rule may make the narrower rule irrelevant.

When tightening access:

1. identify every rule that matches
2. remove or replace broad rules
3. keep the intended narrow rule
4. test again

## Docker Rules Tab

Docker networking does not always behave like ordinary host networking.

Published Docker ports can bypass expectations based only on standard UFW rules because Docker manages its own packet-processing chains.

LEC provides a Docker-aware firewall layer to control container exposure more reliably.

The Docker Rules tab shows rules managed through LEC for published container services.

## LEC Docker Firewall Chain

LEC uses a dedicated chain associated with Docker's `DOCKER-USER` path.

This lets LEC apply access restrictions before Docker accepts forwarded traffic.

LEC-managed Docker firewall state is stored separately from ordinary UFW rules.

The module also installs a helper service that reapplies Docker-aware rules when needed.

## Docker Rule Information

Typical Docker-rule columns may include:

- rule name
- container or service
- host port
- protocol
- source scope
- action
- status

## Docker Service

The Docker service or container identifies what the rule protects.

A rule may be linked to metadata created by the Docker module.

## Host Port

The host port is the port published on Ubuntu.

Example:

```text
Host port 8080 → Container port 80
```

The firewall rule applies to host port 8080.

## Source Scope

Common scopes include:

### Local or Reverse Proxy Only

The container is bound to localhost.

Direct network access is not available, and no broad Docker firewall rule is needed.

This is the preferred arrangement for web applications published through Caddy.

### LAN

Allows access only from the selected local network.

Use this for:

- local dashboards
- media services
- private development tools
- services intended only for household or office devices

### All Networks

Allows access from any network path that can reach the computer.

This is the broadest option and should be used only when necessary.

## Adding a Docker Rule

Docker rules are usually created through Docker integration rather than typed manually.

A typical workflow is:

1. Create or edit the container in **Docker**.
2. Choose its access scope.
3. Publish the required host port.
4. Allow Docker to request the corresponding firewall capability.
5. Open **Firewall → Docker Rules** to verify the result.

When a manual Docker-rule form is available:

1. Select the container or service.
2. Confirm the host port and protocol.
3. Choose the source network.
4. Apply the rule.
5. Test from an allowed and disallowed device.

## Removing a Docker Rule

Removing a Docker rule changes access but does not remove the container or port mapping.

After removal:

- the container may still be running
- the host port may still be listening
- localhost access may still work
- access may depend on Docker's remaining networking behavior

Use the Docker module to change or remove the published port itself.

## Firewall and Docker Must Agree

For a Docker service to work as intended, all of these must align:

- the container is running
- the container port is correct
- the host port is published
- the bind address matches the intended scope
- the LEC Docker firewall rule permits the intended source
- the router or upstream firewall permits access when relevant

Use **Port Usage** to verify the actual listener.

## One-Click Integration

Other modules can request Firewall actions through shared LEC capabilities.

Examples include:

- Docker requesting a Docker-aware access rule
- Remote Access requesting SSH or VNC access
- a future application module requesting a service rule

Always review the created rule afterward to confirm that its scope matches your intent.

## Common Tasks

### Allow SSH from the Local Network

1. Open **Port Usage** and confirm SSH listens on TCP port 22.
2. Open **Firewall**.
3. Add an incoming Allow rule.
4. Choose TCP.
5. Select OpenSSH or port 22.
6. Restrict the source to the local network.
7. Apply the rule.
8. Test from another LAN device.
9. Only then remove any broader SSH rule.

### Allow a Samba Share on the LAN

1. Confirm Samba is running.
2. Open **Mounts & Shares** and verify the hosted share.
3. Open **Firewall**.
4. Allow the Samba service or required ports.
5. Restrict the source to the local network.
6. Apply the rule.
7. Test from another device.

### Publish a Local Web Application Safely

Preferred arrangement:

1. Bind the application to `127.0.0.1`.
2. Confirm the local port in **Port Usage**.
3. Create a hostname and HTTPS rule in **Reverse Proxy**.
4. Allow Caddy's web ports as required.
5. Do not expose the application's internal port directly.

### Allow a Docker Service on the LAN

1. Open **Docker**.
2. Edit or create the container.
3. Choose LAN access.
4. Publish the required host port.
5. Apply the configuration.
6. Open **Firewall → Docker Rules**.
7. Verify the source network and port.
8. Test from another LAN device.

### Tighten an Overly Broad Rule

1. Identify the broad rule, such as Anywhere.
2. Add the intended narrow rule first.
3. Test that access still works.
4. Remove the broad rule.
5. Test again from both allowed and disallowed sources.

### Temporarily Test Whether Firewall Is the Problem

Prefer inspecting rules rather than disabling the firewall.

When a temporary disable is unavoidable:

1. Note the current firewall state.
2. Disable it briefly.
3. Test the connection once.
4. Re-enable it immediately.
5. Create or correct the narrow rule.

Do not leave the firewall disabled after testing.

## Connections to Other Modules

### Port Usage

Use **Port Usage** before creating a rule.

It shows:

- whether the port is listening
- protocol
- bind address
- owning process
- systemd service
- Docker container
- related firewall and proxy information

A firewall rule for a port with no listener does nothing.

### Docker

Use **Docker** to control:

- container port
- host port
- bind address
- access scope
- published-port removal

Use Firewall to verify or refine Docker-aware access.

### Reverse Proxy

Use **Reverse Proxy** for HTTP or HTTPS services that should be available through a hostname.

A common secure design is:

```text
Caddy:
ports 80 and 443

Application:
127.0.0.1 on an internal port
```

Only Caddy needs broad inbound access.

### Dynamic DNS

Dynamic DNS points a hostname to the public address.

It does not open a firewall port.

A public service may require all of:

- a running listener
- Firewall permission
- router port forwarding
- Reverse Proxy
- Dynamic DNS

### Remote Access

Remote Access may require firewall rules for:

- SSH
- VNC
- Guacamole-related services

Restrict remote administration to trusted networks whenever practical.

### Mounts & Shares

Hosted Samba shares usually need LAN-only firewall access.

Client mounts connecting outward normally do not require an inbound rule.

### Background Services

Use **Background Services** when the service is not running or needs a restart.

Firewall can permit traffic only to a working listener.

### System Logs

Use **System Logs** when:

- UFW commands fail
- Docker firewall application fails
- a service remains unreachable
- administrator authorization fails
- the LEC Docker firewall helper service fails

### LEC Settings and Recovery

Firewall configuration changes made through LEC are audited.

Use:

```text
LEC Settings → Recovery
```

to inspect or restore prior firewall configuration.

Firewall changes made through UFW commands are captured by LEC around the external command so that Recovery can track the resulting file changes.

After restoring, verify the active firewall status and rules.

## Router and Upstream Firewalls

The local firewall is only one layer.

Internet access may also depend on:

- router port forwarding
- carrier-grade NAT
- cloud security groups
- VPN rules
- workplace network controls
- internet service provider restrictions

LEC manages the Ubuntu computer's firewall. It does not automatically configure every router or external firewall.

## Safety Guidance

### Never Open More Than Necessary

Allow only:

- the required protocol
- the required port
- the narrowest useful source network

### Protect Administrative Services

Avoid exposing these directly to the internet without strong security:

- Docker APIs
- database ports
- private dashboards
- VNC
- development servers
- application administration panels

Prefer VPN access or a properly secured reverse proxy.

### Do Not Rely on Port Numbers Alone

Changing a service to an unusual port may reduce automated noise but is not a substitute for:

- authentication
- encryption
- firewall restrictions
- updates
- secure configuration

### IPv6 Matters

A service may be reachable over IPv6 even when router-style IPv4 port forwarding is absent.

Review IPv6 listeners and rules when the network supports IPv6.

## Troubleshooting

### The Rule Exists but the Service Is Unreachable

Check:

1. Is the service running?
2. Does Port Usage show a listener?
3. Is it bound to a reachable address?
4. Is the protocol correct?
5. Is the client using the correct port?
6. Is another firewall involved?
7. Is router forwarding required?
8. Does the application require authentication or HTTPS?

### The Service Works Locally but Not from Another Device

The service may be bound only to:

```text
127.0.0.1
```

A firewall rule cannot make a localhost-only service directly reachable.

Change the application's bind address or use Reverse Proxy.

### The Service Works on the LAN but Not from the Internet

Possible causes include:

- no router port forwarding
- carrier-grade NAT
- wrong public IP
- Dynamic DNS not updated
- ISP blocking
- upstream firewall
- IPv4 versus IPv6 mismatch

The local firewall may already be correct.

### A Docker Port Is Reachable Despite No Standard UFW Rule

Docker manages separate packet-processing chains.

Use the **Docker Rules** tab and verify the LEC Docker firewall integration.

Do not assume standard UFW output fully describes Docker exposure.

### A Docker Rule Exists but Access Is Still Blocked

Confirm:

- container is running
- host port is published
- bind address is correct
- source network matches
- LEC Docker firewall helper is active
- client address falls within the allowed network

Use Port Usage and System Logs.

### Enabling Firewall Cut Off Remote Access

Access the computer locally if possible.

Then:

1. open Firewall
2. add the required narrow remote-access rule
3. verify the service port
4. reconnect remotely

For future changes, add and test the new rule before removing the old one.

### Removing a Rule Did Not Change Access

Possible reasons include:

- another overlapping rule still allows it
- Docker networking has a separate rule
- the client is connecting locally
- the application is reached through Reverse Proxy
- an upstream path bypasses the expected interface

Review all matching rules and Port Usage.

### Firewall Status Is Active but No Rules Are Listed

The system may rely on default policies, another rule source, or a status-reading problem.

Refresh the module and check System Logs for UFW errors.

### Administrator Authorization Was Canceled

No change was applied.

Retry the intended action and approve the Ubuntu prompt.

### A Restored Firewall Revision Has Not Taken Effect

Recovery restores the managed configuration state.

After restoration:

1. return to Firewall
2. refresh the status
3. reapply or reload rules when offered
4. test the affected service
5. check System Logs if the rule set fails to load


---


<a id="reverse-proxy"></a>

# Reverse Proxy

## Purpose

The Reverse Proxy module provides a graphical way to publish local web applications through Caddy without manually editing Caddy configuration files.

Use it to:

- create a hostname for a local web service
- route HTTP or HTTPS traffic to an application
- publish a Docker container through Caddy
- use hostnames created in Dynamic DNS
- keep an application's internal port private
- inspect active proxy rules
- check the certificate currently served by Caddy
- remove proxy rules that are no longer needed

A reverse proxy accepts a request on one address and forwards it to another service.

A common arrangement is:

```text
User visits:
https://app.example.com

Caddy listens on:
ports 80 and 443

Caddy forwards to:
127.0.0.1:8080
```

The application itself remains on a local port, while Caddy handles the public hostname and HTTPS connection.

## Why Use a Reverse Proxy

A reverse proxy can provide:

- friendly hostnames
- HTTPS certificates
- one public entry point for several applications
- local-only application ports
- simpler firewall rules
- easier Docker integration

Without a reverse proxy, users may need to connect with an address such as:

```text
http://192.168.1.50:8080
```

With a reverse proxy, the same application can be reached as:

```text
https://app.example.com
```

## Module Views

The Reverse Proxy module typically includes views for:

- overview and status
- proxy rules
- creating or editing a rule
- certificate details

The exact tab names may vary slightly by LEC version.

## Caddy Status

The status area shows whether Caddy is installed and running.

Common conditions include:

### Running

Caddy is active.

This means the reverse-proxy service is running, but individual rules may still fail if:

- the destination is unavailable
- the hostname is incorrect
- DNS points elsewhere
- ports 80 or 443 are blocked
- the certificate cannot be obtained

### Stopped

Caddy is installed but not currently running.

Reverse-proxy hostnames will not work until it starts.

Use **Background Services** to start or restart Caddy.

### Not Installed

Caddy is not currently available.

When installation is supported, the module may offer an Install action.

Installing Caddy may require administrator authorization and internet access.

### Error or Unavailable

LEC could not inspect Caddy.

Possible causes include:

- missing packages
- a failed service
- invalid Caddy configuration
- denied administrator access
- unreadable status information

Use **System Logs** and **Background Services** for more detail.

## Proxy Rules

The proxy-rules table shows the hostnames currently managed by LEC.

Typical columns may include:

- hostname
- destination
- protocol
- HTTPS status
- certificate status
- source module or service
- enabled state

## Hostname

The hostname is the address users enter.

Example:

```text
files.example.com
```

The hostname must resolve to the computer or network where Caddy is reachable.

The Reverse Proxy module does not itself guarantee that public DNS is correct.

Use **Dynamic DNS** when the public IP address changes over time.

## Destination

The destination is the local service receiving forwarded traffic.

Examples:

```text
127.0.0.1:8080
192.168.1.25:3000
```

For a service running on the same computer, prefer:

```text
127.0.0.1
```

when possible.

This keeps the application's own port local and reduces direct exposure.

## Protocol

The destination protocol is normally:

- HTTP
- HTTPS

Use HTTP when the local application does not provide its own TLS.

Caddy can still provide HTTPS externally.

Use HTTPS as the destination only when the application itself expects HTTPS and uses a certificate Caddy can connect to successfully.

## Creating a Proxy Rule

A typical rule-creation form asks for:

- hostname
- destination host
- destination port
- destination protocol
- optional service selection
- HTTPS behavior
- optional advanced settings

A safe workflow is:

1. Confirm the application is running.
2. Find its address and port in **Port Usage**.
3. Confirm that the service responds locally.
4. Choose or enter the hostname.
5. Choose the destination protocol.
6. Enter the local host and port.
7. Preview or validate the rule.
8. Apply it.
9. Approve administrator authorization.
10. Verify Caddy reloads successfully.
11. Test the hostname.

## Hostname Selection

The hostname field may allow:

- manual entry
- selection from Dynamic DNS hostnames

When Dynamic DNS integration is available, LEC reads the hostnames already configured there.

You can still type another hostname manually.

Use a fully qualified hostname such as:

```text
app.example.com
```

Avoid entering:

```text
https://
```

or a path such as:

```text
/app
```

unless the form explicitly asks for them.

## Destination Host

Use:

```text
127.0.0.1
```

when the application runs on the same computer and listens locally.

Use the computer's LAN address when:

- the application binds only to that address
- the destination runs on another machine
- Docker or another service exposes it that way

Use another device's address when Caddy is proxying to a service elsewhere on the LAN.

## Destination Port

Enter the port where the application is listening.

Examples:

```text
8080
3000
5000
```

Use **Port Usage** to confirm the actual listener.

A firewall rule does not create the listener.

## Destination Protocol

### HTTP

Use this for most local web applications.

Caddy handles external HTTPS while forwarding internally over HTTP.

### HTTPS

Use this only when the destination service itself uses HTTPS.

The destination certificate must be compatible with the connection Caddy makes.

## HTTPS and Certificates

Caddy normally obtains and renews HTTPS certificates automatically.

For public certificates, the following must generally be true:

- the hostname resolves to the public IP
- Caddy is reachable on ports 80 and/or 443
- router forwarding points to this computer when required
- Firewall permits the traffic
- no other device is receiving those ports
- the certificate authority can reach the hostname

LEC does not manually create ordinary Caddy certificates.

Caddy manages the certificate process.

## Certificate Status

The Overview may show certificate details for a hostname.

Typical fields include:

- hostname
- status
- issuer
- valid from
- valid until
- days remaining
- serial number

LEC checks the certificate actually served by Caddy on the local machine using the requested hostname.

## Certificate Status Meanings

### Valid

Caddy is serving a valid certificate for the hostname.

### Not Available

LEC could not retrieve a certificate from Caddy for that hostname.

Possible causes include:

- Caddy has not obtained it yet
- DNS still points elsewhere
- ports 80 or 443 are forwarded to another computer
- Caddy is not listening on 443
- the rule is new and Caddy is still retrying
- the hostname is not public
- the local certificate handshake failed

### Expiring Soon

The certificate is approaching its expiration date.

Caddy normally renews automatically before expiration.

Investigate when the status remains near expiration and renewal does not occur.

### Invalid or Mismatched

The certificate served does not match the hostname or is not currently valid.

Check:

- the hostname
- Caddy configuration
- DNS
- system date and time
- whether another service is answering on port 443

## Automatic Certificate Retry

Caddy retries certificate acquisition automatically.

You normally do not need to delete and recreate a rule merely because the certificate is not immediately available.

Correct the DNS, forwarding, firewall, or port issue and allow Caddy time to retry.

Restart or reload Caddy only when the configuration itself needs to be re-applied.

## Public DNS

For a public hostname, DNS must point to the public IP address of the network hosting Caddy.

Use **Dynamic DNS** when the address changes.

A DNS record alone does not make the service reachable.

You may also need:

- router port forwarding
- local Firewall permission
- Caddy running
- the application destination running

## Local-Only Hostnames

A reverse proxy can also be used only on a LAN.

In that case, the hostname must resolve locally through:

- router DNS
- local DNS server
- hosts-file entries
- another internal name-resolution method

Public certificate issuance may not work for an internal-only hostname.

Caddy may use local certificates depending on the configuration.

Client devices may need to trust Caddy's local certificate authority.

## Router Port Forwarding

LEC manages the Ubuntu computer, not the router.

For public access, the router may need to forward:

```text
TCP 80  → Caddy computer
TCP 443 → Caddy computer
```

Forward those ports to the computer running Caddy.

Do not forward the application's internal port when Caddy is meant to be the public entry point.

## Firewall Rules

For public or LAN access, Firewall must allow Caddy's incoming ports.

Typical Caddy ports are:

```text
80/tcp
443/tcp
```

The application's internal port can remain local-only.

This is usually safer than opening every application's port individually.

## Creating a Rule from a Local Service

When local-service integration is available, the form may let you select a discovered service.

This can automatically fill:

- service name
- host
- port
- protocol
- related module information

Always review the values before applying.

The selected service may have changed since LEC started.

Use **Port Usage** for the latest listener information.

## Docker Integration

Docker containers can be published through Reverse Proxy.

A recommended container setup is:

```text
Host bind address:
127.0.0.1

Host port:
8080

Container port:
80
```

Then Reverse Proxy forwards:

```text
app.example.com → 127.0.0.1:8080
```

This keeps the container's host port from being directly available across the LAN or internet.

The Docker module may request Reverse Proxy creation through a shared LEC capability.

## Editing a Rule

When editing is supported:

1. Select the rule.
2. confirm the current hostname and destination.
3. change only the required values.
4. Preview or validate.
5. Apply.
6. Confirm Caddy reloads successfully.
7. Test the hostname.

Changing the hostname may require:

- a new DNS record
- a new certificate
- removal of the old DNS record
- updates to bookmarks or applications

## Removing a Rule

Removing a proxy rule stops Caddy from forwarding that hostname.

It does not:

- stop the destination application
- remove the Docker container
- remove the DNS record
- remove router forwarding
- delete application data

A safe removal process is:

1. Select the rule.
2. confirm the hostname and destination.
3. Click Remove.
4. approve administrator authorization.
5. Verify Caddy reloads.
6. Remove the DNS record separately when no longer needed.
7. Review Firewall and router rules for obsolete access.

## Common Tasks

### Publish a Local Web Application with HTTPS

1. Start the application.
2. Confirm it listens on `127.0.0.1` and the expected port.
3. Open **Dynamic DNS** and create the hostname when needed.
4. Open **Reverse Proxy**.
5. Create a rule using the hostname.
6. Set the destination to `127.0.0.1`.
7. Enter the application's port.
8. Select HTTP unless the application itself requires HTTPS.
9. Apply the rule.
10. Allow Caddy through Firewall.
11. Forward ports 80 and 443 on the router when public access is required.
12. Test the hostname.

### Publish a Docker Container

1. Create or edit the container in **Docker**.
2. Bind its host port to `127.0.0.1`.
3. Confirm the listener in **Port Usage**.
4. Open **Reverse Proxy**.
5. Select the container service when available.
6. choose the hostname.
7. Apply the rule.
8. Test HTTPS access.

### Move a Service from Direct Port Access to Reverse Proxy

1. Create and test the proxy rule first.
2. Confirm the hostname works.
3. Change the application or container bind address to `127.0.0.1`.
4. Remove the direct Firewall rule for the internal port.
5. Remove router forwarding for the internal port.
6. Keep only Caddy's required public ports.

### Check Why a Certificate Is Unavailable

1. Confirm the hostname in Dynamic DNS or public DNS.
2. Confirm the public IP is correct.
3. Confirm Caddy is running.
4. Confirm ports 80 and 443 are forwarded to this computer.
5. Confirm Firewall allows them.
6. Check Port Usage for Caddy listeners.
7. Review Caddy logs in **System Logs**.
8. Allow time for automatic retry.

### Change a Destination Port

1. Update the application or container first.
2. Confirm the new listener in Port Usage.
3. Edit the Reverse Proxy rule.
4. Change the destination port.
5. Apply.
6. Test the hostname.
7. Remove any obsolete direct Firewall rule.

## Connections to Other Modules

### Dynamic DNS

Use **Dynamic DNS** to create and maintain hostnames.

Reverse Proxy can offer those hostnames in its rule form.

Dynamic DNS updates the DNS record. Reverse Proxy controls where Caddy sends the request.

### Docker

Use **Docker** to manage:

- container state
- host port
- container port
- bind address
- local-service metadata

Reverse Proxy publishes the resulting web service.

### Firewall

Use **Firewall** to allow Caddy's incoming web ports.

The application's local destination port usually does not need direct inbound access.

### Port Usage

Use **Port Usage** to verify:

- Caddy is listening on 80 and 443
- the destination application is listening
- the destination address and port are correct
- no other process owns the expected port

### Background Services

Use **Background Services** to:

- start Caddy
- stop Caddy
- restart Caddy
- enable it at startup
- inspect status

### System Logs

Use **System Logs** when:

- Caddy fails to reload
- a certificate cannot be obtained
- the destination is unreachable
- the hostname is rejected
- TLS handshakes fail
- ports are already in use

### Remote Access

Guacamole and other web-based remote-access tools may be published through Reverse Proxy.

Keep the internal service local when possible.

### LEC Settings and Recovery

Reverse Proxy configuration changes made through LEC are audited.

Use:

```text
LEC Settings → Recovery
```

to inspect or restore prior Caddy configuration.

After restoring:

1. return to Reverse Proxy
2. refresh the rules
3. reload or restart Caddy when required
4. test the hostname

## Safety Guidance

### Prefer Local Destinations

Use `127.0.0.1` for services on the same machine whenever practical.

This reduces direct exposure.

### Do Not Expose Administrative Interfaces Without Protection

Administrative web interfaces should use:

- HTTPS
- strong authentication
- restricted access where possible
- current software
- minimal direct port exposure

### Keep Internal Ports Private

When Caddy is the intended entry point, avoid also exposing the application's internal port through Firewall or router forwarding.

### Verify the Destination

A typo in the destination can route traffic to the wrong service.

Use Port Usage and local testing before applying.

### Public HTTPS Requires Public Reachability

Caddy cannot obtain an ordinary public certificate when the certificate authority cannot reach the hostname.

Internal-only services may need a different certificate approach.

## Troubleshooting

### The Hostname Does Not Resolve

Check:

- spelling
- DNS record
- Dynamic DNS status
- public IP
- DNS propagation
- local DNS cache

Try resolving the hostname from another device or network.

### The Hostname Resolves to the Wrong IP

Update the DNS or Dynamic DNS record.

If the public IP changed, confirm the Dynamic DNS timer and provider status.

### The Browser Says Connection Refused

Possible causes include:

- Caddy is not running
- Firewall blocks 80 or 443
- router forwarding is missing
- another device receives those ports
- Caddy is not listening on the expected interface

Use Port Usage and Background Services.

### The Browser Reaches Caddy but Shows a Bad Gateway

Caddy is running, but it cannot reach the destination.

Check:

- destination host
- destination port
- application status
- Docker container status
- application bind address
- destination protocol

Test the destination locally.

### HTTPS Certificate Is Not Available

Check:

- DNS points to this network
- ports 80 and 443 reach Caddy
- Firewall allows access
- no other machine receives the forwarded ports
- Caddy logs
- system time

Caddy retries automatically after the issue is corrected.

### The Certificate Is for Another Hostname

Another service or device may be answering on port 443.

Confirm:

- router forwarding
- Caddy listener
- hostname rule
- public IP
- reverse-proxy computer

### The Application Works by Port but Not by Hostname

The destination is probably working.

Focus on:

- DNS
- Caddy rule
- certificate
- Caddy logs
- public routing

### The Hostname Works Locally but Not from the Internet

Possible causes include:

- router forwarding
- carrier-grade NAT
- upstream firewall
- ISP restrictions
- public DNS mismatch
- IPv4 versus IPv6 differences

### The Hostname Works from the Internet but Not Inside the LAN

The router may not support NAT loopback or hairpin NAT.

Possible solutions include:

- local DNS override
- split DNS
- router hostname mapping
- connecting through the local address when inside the LAN

### Caddy Reload Fails

The generated or restored configuration may be invalid.

Review:

- hostname
- destination
- protocol
- duplicate rules
- Caddy logs

Use Recovery only after confirming which revision was previously valid.

### A Removed Rule Still Appears to Work

Possible reasons include:

- browser cache
- another Caddy rule
- another reverse proxy
- DNS points to another server
- Caddy was not successfully reloaded
- the application is directly exposed on its own port

Check Port Usage, Firewall, and Caddy status.

### Restoring a Rule Did Not Restore the Certificate

Recovery restores the configuration.

Caddy must reload and may need to obtain or renew the certificate again.

Confirm DNS and public reachability, then allow time for retry.


---


<a id="remote-access"></a>

# Remote Access

## Purpose

The Remote Access module helps you configure and inspect ways to connect to this Ubuntu computer from another device.

It brings several related technologies into one place:

- **SSH** for command-line and secure file access
- **VNC** for graphical desktop access
- **Guacamole** for browser-based remote access

Use this module to:

- install or enable supported remote-access services
- review whether each service is running
- configure startup behavior
- choose who may connect
- verify listening ports
- connect related Firewall and Reverse Proxy settings
- troubleshoot failed connections

Remote access can expose powerful control of the computer. Enable only the methods you need and restrict them to trusted users and networks.

## Important Safety Note

A remote-access service can allow another person to:

- log in to the computer
- view or control the desktop
- run commands
- read or change files
- administer applications

Before enabling remote access:

1. Use strong account passwords.
2. Prefer key-based SSH authentication where practical.
3. Restrict access through Firewall.
4. Avoid exposing VNC directly to the internet.
5. Keep the system and remote-access software updated.
6. Use HTTPS and authentication for Guacamole.
7. Disable methods you no longer use.

## Module Views

The Remote Access module includes views for:

- **Overview**
- **SSH**
- **VNC**
- **Guacamole**

The exact wording of individual controls may vary slightly by LEC version.

## Overview Tab

The Overview tab summarizes the available remote-access methods and their current status.

Typical information includes:

- whether the required software is installed
- whether the related service is running
- whether it starts automatically
- listening address and port
- related Firewall status
- setup or troubleshooting actions

Use this tab to decide which method best fits your needs.

## Choosing a Remote-Access Method

### Use SSH When

- you need command-line administration
- you want secure file transfer
- you are comfortable using a terminal on the client device
- you need a lightweight connection
- you want to administer the computer without loading its desktop

SSH is usually the safest and most efficient remote-management method.

### Use VNC When

- you need to see and control a graphical desktop
- the client device has a VNC viewer
- the connection stays on a trusted LAN or VPN
- you understand the desktop-session limitations

VNC is useful for direct graphical control, but it should not normally be exposed unprotected to the public internet.

### Use Guacamole When

- you want browser-based access
- you do not want to install a separate client
- you want one web interface for SSH, VNC, or other supported connections
- you are willing to run the required containerized services

Guacamole is typically deployed through Docker and may be published securely through Reverse Proxy.

# SSH

## What SSH Does

SSH, or Secure Shell, provides encrypted remote login.

With SSH, a remote user can:

- open a terminal session
- run commands
- copy files through SFTP or SCP
- use applications that support SSH connections
- create secure tunnels

The standard SSH service is commonly named:

```text
ssh.service
```

and normally listens on:

```text
22/tcp
```

## SSH Status

The SSH view may show:

- installation status
- service status
- startup status
- listening port
- bind address
- firewall access
- configuration path

### Installed and Running

SSH is available and accepting connections, subject to Firewall and network routing.

### Installed but Stopped

The software is present, but the service is not running.

### Not Installed

The SSH server package is missing.

LEC may offer an installation action.

### Failed

The service attempted to start but encountered an error.

Use **System Logs** to inspect the reason.

## Install SSH Server

When SSH is not installed, use the installation action.

LEC may:

1. request administrator authorization
2. install the Ubuntu OpenSSH server package
3. enable the service
4. start the service
5. refresh its status

Installing the server does not automatically make it reachable from every network. Firewall and router settings still apply.

## Start, Stop, and Restart

### Start

Starts the SSH service immediately.

### Stop

Ends new SSH access and disconnects some active sessions depending on service behavior and timing.

Do not stop SSH while it is your only way to reach a remote computer unless you have another access method.

### Restart

Reloads the service by stopping and starting it.

A restart may disconnect active sessions.

Use it after changing SSH configuration.

## Enable at Startup

When enabled, SSH starts automatically with Ubuntu.

This is appropriate for a computer that must remain remotely manageable.

Disable automatic startup when SSH is only occasionally needed.

## SSH Port

The normal port is:

```text
22
```

Changing the port may reduce automated internet scanning, but it is not a substitute for:

- strong authentication
- Firewall restrictions
- updates
- key-based access

When changing the port:

1. add the new Firewall rule first
2. restart SSH
3. test the new port
4. remove the old rule only after success

## SSH Bind Address

SSH may listen on:

- all interfaces
- a LAN address
- localhost
- selected IPv4 or IPv6 addresses

For ordinary LAN access, listening on the LAN interface or all interfaces is common.

Use Firewall to restrict which sources may connect.

## Password Authentication

Password authentication allows users to log in with their Linux username and password.

Advantages:

- simple to understand
- supported by nearly every SSH client

Risks:

- exposed servers receive automated password attempts
- weak passwords are dangerous
- reused passwords can compromise the system

For internet-accessible SSH, key-based authentication is strongly preferred.

## Key-Based Authentication

SSH keys use a private key on the client and a public key on the server.

Benefits include:

- resistance to password guessing
- convenient login
- strong authentication

The private key must remain protected.

Never share the private key or place it in a public repository.

A public key is normally stored for the target user under:

```text
~/.ssh/authorized_keys
```

LEC may provide status or guidance, while key generation and client setup may still depend on the chosen SSH client.

## Root Login

Direct SSH login as `root` should normally remain disabled.

Use an ordinary user account and administrator authorization when needed.

This provides better accountability and reduces risk.

## Allow SSH Through Firewall

For LAN-only SSH:

1. Open **Firewall**.
2. Allow TCP port 22 or the OpenSSH profile.
3. Restrict the source to the local network.
4. Test from another LAN device.

For internet access, prefer:

- VPN
- a restricted source address
- key-based authentication
- rate limiting or other protections

## Connecting with SSH

From another Linux or macOS computer:

```bash
ssh username@computer-address
```

With a custom port:

```bash
ssh -p 2222 username@computer-address
```

On Windows, use:

- Windows Terminal or PowerShell
- an SSH-capable application
- an SFTP client for file transfers

## Common SSH Tasks

### Enable SSH for LAN Use

1. Open **Remote Access → SSH**.
2. Install the SSH server if needed.
3. Start the service.
4. Enable startup when desired.
5. Open **Firewall**.
6. Allow SSH from the LAN only.
7. Find the computer's LAN address.
8. Test from another device.

### Troubleshoot an SSH Login Failure

1. Confirm SSH is Running.
2. Check **Port Usage** for the expected port.
3. Check Firewall.
4. Confirm the username.
5. Confirm the password or key.
6. Review **System Logs → Authentication & Security**.
7. Verify the client is connecting to the correct address and port.

# VNC

## What VNC Does

VNC provides remote graphical access to a desktop session.

A VNC client can show the Ubuntu desktop and send keyboard and mouse input.

VNC behavior depends on:

- the VNC server implementation
- whether it shares the current desktop or creates a separate session
- the desktop environment
- Wayland or X11
- user login state
- display and session permissions

## VNC Status

The VNC view may show:

- server installation status
- service status
- startup status
- display number
- port
- configured user
- network binding
- firewall access

Common VNC ports are based on the display number.

For example:

```text
Display :1 → TCP port 5901
Display :2 → TCP port 5902
```

## Install VNC Components

When supported components are missing, LEC may offer installation.

The installation may:

1. request administrator authorization
2. install the supported VNC server
3. create configuration
4. create or enable a service
5. refresh status

## VNC User

A VNC session normally runs as a selected Linux user.

That user controls:

- desktop files
- home-directory access
- session preferences
- available applications

Do not run an ordinary desktop VNC session as `root`.

## VNC Password

The VNC server may use a separate VNC password rather than the user's normal Linux password.

Use a strong, unique password.

Some VNC protocols limit the effective password length. Strong network restrictions remain important.

## Display Number

The display number selects the graphical session and determines the default port.

Example:

```text
:1
```

normally maps to:

```text
5901/tcp
```

Avoid using a display number already assigned to another VNC session.

## Desktop Session

VNC may need a startup definition for the desktop environment.

If the session opens to:

- a blank screen
- a gray background
- an immediate disconnect

the desktop-session startup may be incorrect or incompatible.

## Wayland and X11

Some VNC servers work only with X11 or behave differently under Wayland.

Ubuntu desktop sessions may use Wayland by default.

A VNC session may therefore:

- create a separate X11 desktop
- require a compatible session type
- be unable to mirror the current Wayland desktop
- need additional configuration

This is a technology limitation rather than a Firewall issue.

## VNC Network Exposure

Avoid exposing raw VNC directly to the public internet.

Safer options include:

- LAN-only access
- VPN
- SSH tunneling
- browser access through Guacamole
- another encrypted remote-access layer

If direct LAN access is required, restrict the Firewall rule to the local network.

## Start, Stop, and Restart VNC

Use the available service controls to:

- start the configured session
- stop it
- restart after changing configuration
- enable or disable startup

Restarting disconnects active VNC clients.

## Connecting with a VNC Client

Enter the computer address and display or port.

Examples:

```text
192.168.1.50:1
```

or:

```text
192.168.1.50:5901
```

The exact notation depends on the client.

## Common VNC Tasks

### Enable VNC on the LAN

1. Open **Remote Access → VNC**.
2. Install the supported server if needed.
3. Select the Linux user.
4. choose a display number.
5. Set the VNC password.
6. Create or apply the configuration.
7. Start the service.
8. Open Firewall.
9. Allow the VNC port from the LAN only.
10. Test with a VNC client.

### Change the VNC Display

1. Stop the current VNC service.
2. Change the display number.
3. Apply the configuration.
4. Confirm the new port in Port Usage.
5. Update Firewall rules.
6. Restart VNC.
7. Update the client connection.

# Guacamole

## What Guacamole Does

Apache Guacamole provides remote access through a web browser.

A user opens a secure webpage and then connects to configured systems through protocols such as:

- SSH
- VNC
- RDP

The client device does not need a dedicated SSH or VNC program.

In LEC, Guacamole is typically deployed through Docker.

## Guacamole Status

The Guacamole view may show:

- whether Docker is available
- whether Guacamole-related containers exist
- whether the containers are running
- the local web address or port
- Reverse Proxy status
- navigation to Docker setup
- related service information

## Guacamole Components

A typical Guacamole deployment includes:

- the Guacamole web application
- the `guacd` proxy daemon
- a database or authentication store

The exact container layout depends on the preset or deployment method.

## Install or Deploy Guacamole

When Guacamole is absent, use the Docker integration or preset.

A typical process is:

1. Open **Remote Access → Guacamole**.
2. Follow the action to the Docker module.
3. Load the Guacamole `.lecdock` preset.
4. Enter required fields.
5. Deploy the containers.
6. Verify their status.
7. Return to Remote Access.
8. Refresh the Guacamole status.

## Local Guacamole Access

The web interface may initially be available on a local host port.

For example:

```text
127.0.0.1:8080
```

Keeping it local is preferred when Reverse Proxy will publish it.

## Publish Guacamole Through Reverse Proxy

A typical secure arrangement is:

```text
Guacamole:
127.0.0.1:8080

Caddy:
https://remote.example.com
```

Workflow:

1. Confirm Guacamole is running in Docker.
2. Confirm its local port in Port Usage.
3. Create or select a Dynamic DNS hostname.
4. Open Reverse Proxy.
5. Create an HTTPS rule to the local Guacamole port.
6. Allow Caddy through Firewall.
7. Test the hostname.
8. Change default Guacamole credentials immediately.

## Guacamole Connections

After logging into Guacamole, configure a connection using:

- protocol
- destination host
- destination port
- username
- authentication settings
- optional display or session settings

For a connection to the same computer:

- SSH can target the host's LAN address or another reachable host address.
- VNC can target the configured VNC service and port.

A container cannot always use `127.0.0.1` to reach the Ubuntu host, because inside the container that address refers to the container itself.

Use the host address or an appropriate Docker host-gateway arrangement.

## Guacamole Security

Guacamole is a powerful administrative gateway.

Before exposing it:

- change all default credentials
- use HTTPS
- use strong unique passwords
- remove unused accounts
- limit Firewall access where possible
- keep images updated
- back up required configuration and database data
- do not expose the database port publicly

## Common Guacamole Tasks

### Deploy Guacamole with Docker

1. Open **Remote Access → Guacamole**.
2. Follow the Docker setup action.
3. Import or select the Guacamole preset.
4. Complete required fields.
5. Deploy.
6. Wait for all containers to become healthy or running.
7. Return to Remote Access and refresh.

### Publish Guacamole with HTTPS

1. Keep the Guacamole host port local.
2. Confirm the port in Port Usage.
3. Create a hostname in Dynamic DNS.
4. Create a Reverse Proxy rule.
5. Confirm Caddy's certificate.
6. Test from another device.
7. Change default credentials.

### Add an SSH Connection in Guacamole

1. Confirm SSH works directly first.
2. Log in to Guacamole.
3. Create a new SSH connection.
4. Enter the target host and port.
5. Enter the Linux username.
6. Configure password or key authentication.
7. Save and test.

### Add a VNC Connection in Guacamole

1. Confirm VNC works directly first.
2. Create a VNC connection in Guacamole.
3. Enter the target host.
4. Enter the VNC port.
5. Enter the VNC password.
6. Save and test.

## Connections to Other Modules

### Background Services

Use **Background Services** to manage:

- SSH
- VNC services
- supporting remote-access services

### Docker

Guacamole is deployed and managed through **Docker**.

Use Docker to:

- create or remove containers
- inspect status
- change ports
- manage persistent volumes
- view container information

### Firewall

Use **Firewall** to permit only the intended access.

Typical examples:

- SSH from the LAN
- VNC from the LAN
- Caddy ports for Guacamole's HTTPS hostname

### Reverse Proxy

Use **Reverse Proxy** to publish Guacamole through a secure hostname.

Do not normally publish the raw Guacamole container port directly to the internet.

### Dynamic DNS

Use **Dynamic DNS** when the public IP changes and Guacamole or SSH must be reached through a stable hostname.

### Port Usage

Use **Port Usage** to verify:

- SSH listener
- VNC listener
- Guacamole host port
- Caddy ports
- port conflicts

### User Permissions

Use **User Permissions** when:

- a service account lacks folder access
- the SSH user needs group membership
- VNC runs under the wrong account
- Docker access is unavailable

### System Logs

Use **System Logs** for:

- SSH login failures
- Polkit authorization failures
- VNC startup problems
- Docker or Guacamole errors
- certificate failures
- connection refusals

### LEC Settings and Recovery

Persistent remote-access configuration created through LEC may appear under:

```text
LEC Settings → Recovery
```

Recovery may restore configuration files, but services or containers may still need to be restarted.

## Common Workflows

### Set Up Safe SSH Access on the LAN

1. Install and start SSH.
2. Enable startup if desired.
3. Allow SSH only from the LAN in Firewall.
4. Test with a normal user account.
5. Configure key-based authentication when practical.
6. Keep direct root login disabled.

### Set Up Browser-Based Remote Administration

1. Deploy Guacamole through Docker.
2. Keep the Guacamole port local.
3. Create a Dynamic DNS hostname when public access is needed.
4. Publish it through Reverse Proxy.
5. Allow only Caddy's ports through Firewall.
6. Change default credentials.
7. Configure SSH or VNC connections inside Guacamole.

### Disable an Unused Remote-Access Method

1. Confirm no one depends on it.
2. Stop the related service or container.
3. Disable startup.
4. Remove its Firewall rule.
5. Remove its Reverse Proxy rule when applicable.
6. Remove its Dynamic DNS hostname when no longer used.
7. Confirm the port disappears from Port Usage.

## Troubleshooting

### SSH Connection Is Refused

Check:

- SSH is installed
- service is Running
- Port Usage shows the expected listener
- the client uses the correct address and port
- Firewall allows the source
- router forwarding exists when connecting from outside

### SSH Password Is Rejected

Check:

- username
- password
- keyboard layout
- whether password authentication is enabled
- whether the account is locked
- authentication logs

Use **System Logs → Authentication & Security**.

### SSH Key Authentication Fails

Check:

- correct public key
- correct user
- permissions on `~/.ssh`
- permissions on `authorized_keys`
- key format
- client-selected private key
- server configuration

### Remote SSH Access Works on the LAN but Not the Internet

Possible causes include:

- no router forwarding
- carrier-grade NAT
- wrong public IP
- Dynamic DNS mismatch
- upstream Firewall
- ISP restrictions
- IPv4 and IPv6 differences

### VNC Shows a Blank or Gray Screen

Possible causes include:

- incompatible desktop-session startup
- Wayland limitations
- missing desktop components
- wrong user
- session startup failure
- display conflict

Review VNC service logs.

### VNC Immediately Disconnects

Check:

- VNC password
- display number
- startup script
- user home permissions
- session logs
- existing display conflict

### VNC Works Locally but Not from Another Device

Check:

- VNC bind address
- Firewall
- correct port
- client syntax
- LAN isolation
- whether the service is local-only

### Guacamole Page Does Not Load

Check:

- containers are running
- host port exists in Port Usage
- Reverse Proxy destination is correct
- Caddy is running
- certificate status
- Firewall and router forwarding

### Guacamole Shows Bad Gateway

Caddy cannot reach the Guacamole web container.

Check:

- container state
- host bind address
- published port
- Reverse Proxy destination
- Docker network
- application startup logs

### Guacamole Cannot Reach SSH or VNC on the Host

Inside a container, `127.0.0.1` refers to the container.

Use:

- the Ubuntu host's LAN address
- a configured host-gateway address
- another reachable host address

Also verify Firewall and service binding.

### Remote Access Worked Until a Firewall Change

Open Firewall locally and review:

- required port
- source network
- protocol
- IPv4 and IPv6 rules
- Docker-specific rules
- overlapping deny rules

### A Restored Configuration Does Not Restore Access

Recovery restores managed files.

You may still need to:

- restart SSH or VNC
- restart Docker containers
- reload Caddy
- re-enable a service
- reapply Firewall rules
- confirm DNS and router forwarding


---


<a id="dynamic-dns"></a>

# Dynamic DNS

## Purpose

The Dynamic DNS module keeps a hostname pointed at your network's current public IP address.

Use it when:

- your internet provider changes your public IP address
- you want a stable hostname for services hosted at home or in a small office
- Reverse Proxy needs a hostname for HTTPS
- Remote Access should be reachable through a memorable address
- you do not want to check and update DNS records manually

A Dynamic DNS hostname might look like:

```text
remote.example.com
```

or:

```text
home.example-provider.net
```

LEC checks the public IP address, compares it with the provider's current record, and updates the record when necessary.

## What Dynamic DNS Does Not Do

Dynamic DNS only updates DNS records.

It does not:

- start an application
- create a listening port
- open Firewall
- configure router port forwarding
- create a Reverse Proxy rule
- guarantee that a service is reachable
- secure the service
- provide authentication

A publicly reachable service may require all of these:

1. the application is running
2. the application or Reverse Proxy is listening
3. Firewall permits access
4. the router forwards the required ports
5. Dynamic DNS points to the correct public IP
6. the service uses appropriate authentication and encryption

## Module Views

The Dynamic DNS module typically includes views for:

- **Overview**
- **Hostnames**
- **Add or Edit Hostname**
- **Providers**

The exact tab names may vary slightly by LEC version.

## Overview Tab

The Overview tab summarizes the current Dynamic DNS state.

Typical information includes:

- current detected public IPv4 address
- current detected public IPv6 address
- last successful check
- last provider update
- next scheduled check
- hostname status
- background service and timer status
- recent errors

## Public IPv4 Address

This is the IPv4 address currently visible to the internet.

Example:

```text
203.0.113.25
```

Your actual public address may change when:

- the modem reconnects
- the router restarts
- the internet provider renews the connection
- the provider changes its network
- you switch networks

LEC updates configured IPv4 DNS records when a change is detected.

## Public IPv6 Address

When available, LEC may also detect a public IPv6 address.

IPv6 behaves differently from IPv4:

- a device may have its own public IPv6 address
- router port forwarding may not be required in the same way
- Firewall rules remain important
- the address may change independently of IPv4

Not every network or provider supports IPv6.

Leave IPv6 disabled for a hostname when:

- the network does not have stable IPv6 connectivity
- the service is not listening on IPv6
- Firewall is not configured for IPv6
- the DNS provider does not support the required record

## Last Check

Shows when LEC last checked the public IP and provider state.

A recent successful check indicates that the background updater is working.

## Last Update

Shows when LEC last changed a provider record.

LEC does not need to write the DNS record every time it checks. It updates only when necessary, with an occasional resynchronization to confirm provider state.

## Scheduled Updates

LEC installs a background systemd timer for Dynamic DNS updates.

The updater normally:

- checks periodically
- updates records when the public IP changes
- performs an occasional refresh even when the address is unchanged
- writes a public status snapshot for the GUI and other modules

The background components may include names similar to:

```text
lec-dynamic-dns.service
lec-dynamic-dns.timer
```

Use **Background Services** or **System Logs** if the timer is not running.

## Hostnames Tab

The Hostnames tab lists hostnames currently managed by LEC.

Typical columns may include:

- hostname
- provider
- zone
- IPv4 status
- IPv6 status
- proxy status
- last update
- current state

## Hostname

The full DNS name managed by LEC.

Example:

```text
files.example.com
```

The hostname normally consists of:

- a host label, such as `files`
- a DNS zone, such as `example.com`

## Provider

The DNS company or service that hosts the record.

Built-in provider support includes:

- deSEC
- Cloudflare

Additional trusted provider plugins may be installed separately.

## Zone

The DNS zone is the parent domain managed by the provider.

Example:

```text
example.com
```

For:

```text
files.example.com
```

the zone is usually:

```text
example.com
```

Some providers use a provider-specific domain or account structure.

## IPv4 Status

Shows whether an A record is being managed.

Common states include:

- enabled and current
- enabled but outdated
- update pending
- disabled
- unavailable
- error

## IPv6 Status

Shows whether an AAAA record is being managed.

Do not enable IPv6 merely because the option exists. Confirm that the service and network are actually reachable over IPv6.

## Proxy Status

Some providers, especially Cloudflare, can proxy supported records through their own network.

When proxying is enabled:

- DNS may return provider proxy addresses instead of your public IP
- the provider can add web security or caching features
- only supported web traffic may work
- direct non-web services may fail

Use provider proxying primarily for supported HTTP and HTTPS services.

Do not enable it for services such as:

- SSH
- raw VNC
- arbitrary TCP applications

unless the provider explicitly supports that use.

## Last Update

Shows the last successful record update for the hostname.

An old timestamp is not automatically a problem when the public IP has not changed.

## Hostname State

Typical states include:

### Current

The provider record matches the detected public address.

### Update Needed

The detected public address differs from the record.

LEC should update it during the next successful run.

### Error

The provider rejected the request or another update step failed.

Open the hostname details and review the message.

### Disabled

The hostname remains saved but is not currently being updated.

## Adding a Hostname

A typical hostname form asks for:

- provider
- credentials
- zone
- hostname
- IPv4 choice
- IPv6 choice
- proxy choice
- optional provider-specific settings

## Select Provider

Choose the DNS provider that controls the zone.

The available list depends on installed provider support.

Use the provider where the domain or hostname is actually hosted.

## Provider Credentials

Providers require an API token or other credential so LEC can manage DNS records.

Use a token with the narrowest permissions possible.

Prefer:

- zone-specific tokens
- DNS-edit permissions only
- separate tokens for LEC
- tokens that can be revoked without affecting other services

Avoid using:

- a full account password
- a global administrative API key
- a token shared with unrelated applications

Credentials are stored in protected LEC configuration and should not appear in public status files or logs.

## Test Credentials

Use **Test Credentials** before creating a hostname.

A successful test confirms that:

- the provider can be reached
- the token is accepted
- the required API access is available

A successful credential test does not guarantee that:

- the zone is correct
- the hostname is available
- the token can edit every zone
- public network access is configured

## Zone Selection

Enter or select the zone managed by the provider.

Examples:

```text
example.com
mydomain.net
```

Some providers can list available zones automatically.

When manual entry is required, enter the zone only, not the full hostname.

## Hostname Entry

Enter the full hostname or the host portion according to the form.

LEC normalizes hostnames before sending them to the provider.

A complete example is:

```text
files.example.com
```

Avoid entering:

```text
https://files.example.com
```

or:

```text
files.example.com/path
```

DNS hostnames do not include protocols or URL paths.

## Create Hostname

When the provider supports hostname creation, LEC can create the required record automatically.

If the record already exists, LEC normally updates or adopts it rather than creating a duplicate.

The exact behavior depends on the provider.

## IPv4

Enable IPv4 to manage an A record.

This is the most common choice for home-hosted services.

## IPv6

Enable IPv6 to manage an AAAA record.

Use it only when:

- public IPv6 is detected
- the destination service listens on IPv6
- Firewall allows intended IPv6 access
- the provider supports AAAA records

## Provider Proxy

When supported, choose whether the provider should proxy the hostname.

For Cloudflare-style proxying:

- use it for compatible web services
- leave it disabled for direct SSH, VNC, or non-web services
- remember that certificate and routing behavior may differ

## Save or Create

After completing the form:

1. validate the credentials
2. confirm the zone
3. review the full hostname
4. choose IPv4 and IPv6 behavior
5. choose proxy behavior
6. click Save or Create
7. approve administrator authorization if requested
8. wait for provider confirmation
9. return to the Hostnames list
10. verify the status

## Editing a Hostname

Use Edit to change:

- provider credentials
- zone
- IPv4 or IPv6 behavior
- proxy status
- other supported settings

Changing the hostname itself may effectively create a new DNS record and leave the old record behind unless removal is included.

When renaming:

1. create and test the new hostname
2. update Reverse Proxy and clients
3. remove the old hostname only after migration is complete

## Updating Now

Use **Update Now** or the equivalent action to perform an immediate check.

This is useful after:

- the public IP changes
- credentials are corrected
- a hostname is created
- the router reconnects
- the scheduled updater previously failed

The normal timer continues to handle future updates.

## Deleting a Hostname

Deleting a hostname from the provider removes the DNS record.

It does not:

- remove Reverse Proxy rules
- stop applications
- close Firewall
- remove router forwarding
- uninstall Dynamic DNS
- delete the underlying domain or zone

Before deletion:

1. confirm which services use the hostname
2. remove or update Reverse Proxy rules
3. update Remote Access or application settings
4. confirm no users depend on it
5. delete the hostname
6. verify that provider removal succeeded

## Providers View

The Providers view lists built-in and installed provider adapters.

Typical information may include:

- provider name
- description
- supported address types
- hostname-creation support
- plugin source
- homepage

## Built-in Providers

### deSEC

deSEC provides DNS hosting and Dynamic DNS support.

A deSEC configuration may use a token associated with the account or zone.

LEC can manage supported A and AAAA records and create hostnames where permitted.

### Cloudflare

Cloudflare manages DNS zones and can optionally proxy supported web traffic.

Use a scoped API token with permission to:

- read the required zone
- edit DNS records in that zone

Avoid using a global API key.

## User-Installed Providers

Trusted Python provider plugins can be installed under:

```text
~/.local/share/linuxeasyconfig/dynamic-dns-providers/
```

Restart LEC after adding or removing a provider plugin.

Provider plugins execute code and may participate in privileged update operations. Install them only from trusted sources.

## Public IP Detection

LEC must determine the public address before it can update DNS.

Public-IP detection may fail when:

- internet access is unavailable
- the detection service is unreachable
- DNS is failing
- a VPN changes the visible address
- a proxy interferes
- IPv6 is partially configured

When using a VPN, consider whether the hostname should point to:

- the normal internet connection
- the VPN exit address
- another externally reachable address

Dynamic DNS records should point to the network that actually receives the incoming connection.

## Update Frequency

LEC normally checks at a moderate interval rather than continuously.

Frequent enough checks reduce downtime after an address change, while avoiding unnecessary provider requests.

The background timer generally runs every few minutes.

The updater may also perform a periodic full resynchronization even when the detected address has not changed.

This helps recover from:

- records edited outside LEC
- provider-side drift
- a previously failed update
- a missed status change

## TTL

DNS TTL controls how long resolvers may cache a record.

LEC's supported providers generally use a default TTL of approximately:

```text
3600 seconds
```

A cached old address may therefore remain visible for some time after an update.

Some providers use automatic TTL behavior.

## DNS Propagation

A successful provider update does not always appear everywhere immediately.

Delays can come from:

- resolver caching
- local DNS cache
- browser cache
- provider propagation
- the previous TTL

When testing after a change:

- wait briefly
- try another network
- use a different DNS resolver
- confirm the provider record directly
- avoid repeatedly deleting and recreating the record

## Using Dynamic DNS with Reverse Proxy

A common workflow is:

1. create a hostname in Dynamic DNS
2. confirm it points to the current public IP
3. open Reverse Proxy
4. select the Dynamic DNS hostname
5. route it to a local service
6. allow Caddy's ports through Firewall
7. configure router forwarding
8. wait for Caddy to obtain the certificate
9. test the HTTPS hostname

Dynamic DNS and Reverse Proxy solve different parts of the problem:

- Dynamic DNS maps the name to the public address.
- Reverse Proxy maps the incoming hostname to the local application.

## Using Dynamic DNS with Remote Access

A hostname can make remote access easier.

Examples:

```text
ssh.example.com
remote.example.com
```

For direct SSH:

- use a non-proxied DNS record
- configure Firewall
- configure router forwarding
- use strong SSH authentication

For Guacamole:

- use Reverse Proxy and HTTPS
- keep the container's internal port local
- use a supported proxied or non-proxied DNS setup

Avoid exposing raw VNC directly to the internet.

## Common Tasks

### Create a Hostname for a Reverse-Proxied Application

1. Open **Dynamic DNS**.
2. Add a hostname.
3. Select the provider.
4. Enter and test credentials.
5. Select the zone.
6. Enter the full hostname.
7. Enable IPv4.
8. Enable IPv6 only when supported and needed.
9. choose provider proxy behavior.
10. Save.
11. Run an immediate update.
12. Confirm the status is Current.
13. Open **Reverse Proxy** and use the hostname.

### Update After the Public IP Changes

Normally no manual action is required.

To force an immediate update:

1. Open Dynamic DNS.
2. Check the detected public IP.
3. Select the hostname.
4. click **Update Now**.
5. Confirm the provider update succeeds.
6. Allow for DNS caching.

### Replace an Expired or Revoked API Token

1. Create a new scoped token at the provider.
2. Open the hostname settings.
3. Replace the credential.
4. Test credentials.
5. Save.
6. Run an immediate update.
7. Revoke the old token at the provider.

### Disable IPv6 for a Hostname

1. Edit the hostname.
2. Turn off IPv6 management.
3. Save.
4. Update the provider.
5. Confirm the AAAA record is removed or no longer managed as intended.
6. Test the service over IPv4.

### Remove an Obsolete Hostname

1. Identify all services using it.
2. update or remove Reverse Proxy rules.
3. update Remote Access bookmarks and clients.
4. select the hostname.
5. Delete it.
6. Confirm provider removal.
7. Remove obsolete router or Firewall rules when appropriate.

## Connections to Other Modules

### Reverse Proxy

Reverse Proxy uses Dynamic DNS hostnames for HTTP and HTTPS publishing.

Dynamic DNS handles the public record. Reverse Proxy handles local routing and certificates.

### Firewall

Dynamic DNS does not open ports.

Use Firewall to allow only the required incoming services.

### Port Usage

Use Port Usage to confirm that the destination service and Caddy are actually listening.

A correct DNS record cannot make a stopped service reachable.

### Remote Access

Use Dynamic DNS to create stable names for:

- SSH
- Guacamole
- other approved remote-access services

### Docker

Docker containers may be published through Reverse Proxy using a Dynamic DNS hostname.

Keep container ports local when Caddy is the intended public entry point.

### Background Services

Use Background Services to inspect:

```text
lec-dynamic-dns.service
lec-dynamic-dns.timer
```

The timer should remain active even though the service itself runs only briefly during each check.

### System Logs

Use System Logs when:

- provider authentication fails
- public-IP detection fails
- a hostname update fails
- the background timer fails
- network requests time out
- a plugin raises an error

### LEC Settings and Recovery

Dynamic DNS configuration written through LEC is audited.

Use:

```text
LEC Settings → Recovery
```

to inspect or restore prior configuration.

Restoring local configuration does not necessarily restore the provider's remote DNS record immediately.

After Recovery:

1. return to Dynamic DNS
2. refresh
3. run Update Now
4. confirm provider state

## Security Guidance

### Use Scoped Tokens

Give LEC only the DNS permissions it needs.

Do not use a provider's full account password when a limited API token is available.

### Protect Credentials

Never post:

- API tokens
- provider authorization headers
- credential files
- screenshots showing secret fields

### Do Not Proxy Unsupported Services

A provider's web proxy is not a general-purpose TCP proxy.

Disable proxying for direct SSH and similar services unless explicitly supported.

### Remove Unused Hostnames

Old records reveal possible service names and may accidentally point to a future address.

Remove hostnames that are no longer needed.

### Dynamic DNS Is Not Security

A difficult-to-guess hostname does not protect a service.

Use:

- authentication
- encryption
- Firewall restrictions
- current software
- secure application configuration

## Troubleshooting

### Public IP Is Not Detected

Check:

- internet connection
- DNS
- VPN status
- system time
- System Logs
- whether the detection service is reachable

Retry after network access is restored.

### Credential Test Fails

Confirm:

- token was copied correctly
- token is active
- token has DNS permissions
- token applies to the selected zone
- provider account is active
- no extra spaces were pasted

Create a new scoped token when uncertain.

### Zone Is Not Listed

Possible causes include:

- token lacks zone-read permission
- wrong provider account
- the zone is hosted elsewhere
- provider API error
- manual zone entry is required

Confirm the zone in the provider's own dashboard.

### Hostname Creation Fails

Check:

- valid hostname format
- correct zone
- provider supports creation
- token has DNS-edit permission
- an incompatible record already exists
- provider error message

### Status Says Error After Previously Working

Possible causes include:

- token expired or was revoked
- provider outage
- internet outage
- changed zone permissions
- malformed external record
- background service failure

Run an immediate update and inspect System Logs.

### DNS Record Updated but the Old Address Still Resolves

This is usually caching.

Wait for the previous TTL to expire and test with another resolver or network.

### Hostname Resolves Correctly but the Service Is Unreachable

Dynamic DNS is working.

Check:

- application status
- Port Usage
- Firewall
- router forwarding
- Reverse Proxy
- certificate status
- IPv4 versus IPv6

### Hostname Works on the LAN but Not Outside

The local network may use an internal DNS override.

Check the public record from another network.

Also confirm router forwarding and upstream connectivity.

### Hostname Works Outside but Not Inside the LAN

The router may not support NAT loopback.

Use:

- local DNS override
- split DNS
- router host mapping
- local service address while on the LAN

### IPv4 Works but IPv6 Fails

Confirm:

- a valid public IPv6 address is detected
- the service listens on IPv6
- Firewall allows IPv6
- the provider AAAA record is correct
- the client actually has IPv6 connectivity

Disable the AAAA record when IPv6 is not fully functional, because some clients may prefer it.

### Provider Proxy Causes Connection Problems

Disable proxying when the service is not supported by the provider's proxy.

For ordinary Reverse Proxy web traffic, confirm that:

- SSL mode is compatible
- Caddy is reachable
- provider proxy settings match the intended design

### Background Updates Stop

Check:

1. Overview for the last check time.
2. Background Services for the Dynamic DNS timer.
3. System Logs for `lec-dynamic-dns`.
4. provider credentials.
5. internet access.

Restart or re-enable the timer when necessary.

### A Restored Configuration Does Not Match the Provider

Recovery restores LEC's local configuration.

Use **Update Now** to reconcile the provider record with the restored settings.


---


<a id="task-scheduler"></a>

# Task Scheduler

## Purpose

The Task Scheduler module lets you create, review, run, disable, and remove scheduled jobs without writing cron entries or systemd timer files by hand.

Use it to:

- run a command at a specific time
- repeat a task every hour, day, week, or month
- create a custom recurring schedule
- run maintenance scripts
- automate backups
- start application jobs on a timer
- inspect existing systemd timers
- review traditional cron jobs
- troubleshoot scheduled work that did not run

LEC uses systemd services and timers for tasks it creates.

A scheduled task normally consists of two related units:

```text
task-name.service
task-name.timer
```

The service performs the work. The timer decides when the service starts.

## Important Safety Note

A scheduled task runs automatically, often when no one is watching.

Before enabling one:

1. Test the command manually.
2. Confirm the run-as user.
3. Use absolute paths.
4. Confirm required files and folders exist.
5. Avoid commands that wait for interactive input.
6. Make sure repeated execution is safe.
7. Check whether missed runs should be handled after reboot.
8. Review logs after the first scheduled run.

A badly designed task can repeatedly fail, fill storage, overwrite files, or perform an action more often than intended.

## Module Views

The Task Scheduler module typically includes views for:

- **Overview**
- **LEC Tasks**
- **Create Task**
- **Existing Timers**
- **Cron Jobs**

The exact tab names may vary slightly by LEC version.

## Overview Tab

The Overview tab summarizes the scheduler's current state.

Typical information includes:

- number of LEC-managed tasks
- active timers
- failed scheduled services
- next upcoming run
- recent task activity
- background scan status

Use this tab for a quick check that scheduled work is functioning.

## LEC-Managed Tasks

LEC stores its task definitions under:

```text
/etc/linuxeasyconfig/task_scheduler/tasks.json
```

For each task, LEC generates:

- a systemd service
- a systemd timer
- any required execution metadata

The task list is the authoritative place to manage jobs created through LEC.

## LEC Tasks Tab

The LEC Tasks tab lists scheduled jobs created through LEC.

Typical columns may include:

- task name
- description
- schedule
- enabled state
- last run
- last result
- next run
- run-as user

## Task Name

The task name is the stable identifier used to create its systemd units.

Example:

```text
nightly-backup
```

LEC may generate:

```text
lec-task-nightly-backup.service
lec-task-nightly-backup.timer
```

Use a short descriptive name.

Recommended characters include:

- lowercase letters
- numbers
- hyphens

Avoid spaces and punctuation.

Do not reuse the same name for unrelated jobs.

## Description

The description explains what the task does.

Example:

```text
Back up the media library every night
```

A clear description makes later troubleshooting easier.

## Schedule

The schedule column shows when the task should run.

Examples may include:

```text
Every hour
Daily at 02:00
Every Monday at 08:30
Monthly on day 1 at 03:00
Custom systemd calendar expression
```

## Enabled State

### Enabled

The timer is active and should trigger according to its schedule.

### Disabled

The task remains defined but will not run automatically.

You can still run it manually.

### Failed or Invalid

The timer or generated configuration could not be loaded correctly.

Review the task details and System Logs.

## Last Run

Shows the most recent time the service was triggered.

No value may appear when the task has not run yet.

## Last Result

Common results include:

- success
- failed
- canceled
- timeout
- unknown

A task can remain enabled even after a failed run.

The timer may try again at the next scheduled time.

## Next Run

Shows the next time systemd expects to trigger the task.

If no next run appears:

- the timer may be disabled
- the schedule may be invalid
- it may be a one-time task that already ran
- systemd may not have reloaded
- the task may be waiting on a condition not represented as a calendar time

## Run-As User

The run-as user controls permissions and environment.

The task can access only what that user can access.

For ordinary personal scripts, use your normal desktop account.

Use a dedicated service account when the task belongs to an application.

Avoid running as `root` unless the task truly needs full administrative access.

## Task Actions

Typical actions include:

- Run Now
- Enable
- Disable
- Edit
- Remove
- Refresh

## Run Now

Starts the task's service immediately without waiting for the timer.

Use this to:

- test a new task
- verify permissions
- confirm output
- reproduce a failure
- run maintenance early

Run Now does not change the schedule.

A task that succeeds manually may still fail on schedule if it depends on a different environment or unavailable mount.

## Enable

Activates the timer.

Use this after:

- creating a task
- correcting a disabled task
- testing the command manually
- completing maintenance

## Disable

Stops future automatic runs.

Disabling does not:

- delete the task
- stop a task already running
- remove its service and timer files
- erase prior logs

Use Disable when you want to pause automation without losing the setup.

## Edit

Changes the task definition.

When editing:

1. Review the current command.
2. Confirm the run-as user.
3. Check the schedule.
4. Save the changes.
5. Confirm systemd reloads.
6. Test with Run Now.
7. Confirm the next run time.

Changing a task while it is running does not necessarily affect the current execution.

## Remove

Deletes the LEC-managed task and its generated units.

Before removal:

1. Confirm the task name.
2. Disable the timer.
3. Check whether the task is currently running.
4. Confirm no application depends on it.
5. Remove the task.
6. Approve administrator authorization.
7. Verify it disappears from the list.

Removing the task does not normally delete:

- scripts
- backup files
- generated application data
- logs
- files produced by earlier runs

## Create Task Tab

The Create Task tab builds a new scheduled job.

A typical form may ask for:

- task name
- description
- command or script
- arguments
- working directory
- run-as user
- schedule type
- time and recurrence
- persistent or catch-up behavior
- enable immediately
- run immediately after creation

## Command or Program

Enter the executable or script to run.

Use an absolute path.

Good:

```text
/usr/bin/rsync
/home/alex/scripts/backup.sh
/opt/example/maintenance
```

Avoid:

```text
rsync
backup.sh
python
```

A scheduled service may not have the same `PATH` as your terminal.

## Running a Python Script

Use either:

```text
/usr/bin/python3
```

as the command and place the script path in Arguments:

```text
/home/alex/scripts/report.py
```

or use the Python interpreter from a virtual environment:

```text
/home/alex/myapp/.venv/bin/python
```

with:

```text
/home/alex/myapp/report.py
```

as the first argument.

A package installed only in a virtual environment will not be available to `/usr/bin/python3`.

## Running a Shell Script

Use the script directly when it is executable and has a valid shebang.

Example:

```text
/home/alex/scripts/backup.sh
```

Alternatively use:

```text
/bin/bash
```

with the script path as an argument.

The script must not require interactive input.

## Arguments

Enter only the arguments that follow the command.

Example command:

```text
/usr/bin/rsync
```

Arguments:

```text
-a --delete /home/alex/Documents/ /mnt/backups/Documents/
```

Use quotation marks around arguments containing spaces.

Example:

```text
--name "Nightly Backup"
```

Avoid shell operators such as:

```text
>
|
&&
*
```

unless the task intentionally runs through a shell and the implications are understood.

Prefer direct commands with structured arguments.

## Working Directory

The working directory is the folder from which the command runs.

Use it when the application expects relative paths.

Example:

```text
/home/alex/scripts
```

If blank, the generated service may use a default location.

Use absolute paths inside the command even when a working directory is set.

## Run-As User

Select the account that should execute the task.

The selected user must be able to:

- execute the command
- read scripts and configuration
- access input files
- write output files
- access mounted storage
- connect to required services
- use required devices

Use **User Permissions** to correct group membership.

## Environment Differences

Scheduled tasks do not run inside your normal terminal session.

They may not have:

- shell startup files
- aliases
- desktop environment variables
- graphical display access
- terminal input
- the same PATH
- the same current directory
- unlocked keyrings
- mounted user-session resources

Design scheduled jobs to run unattended.

## Schedule Types

LEC may provide common schedules and a custom option.

## Hourly

Runs once every hour.

Use for:

- frequent synchronization
- status checks
- lightweight maintenance

Do not use hourly scheduling for expensive work unless the previous run always completes in time.

## Daily

Runs once per day at a selected time.

Use for:

- backups
- reports
- cleanup
- maintenance
- media scans

Choose a time when:

- the computer is likely to be on
- required storage is mounted
- network services are available
- the task will not interfere with active use

## Weekly

Runs on selected day or days at a selected time.

Use for:

- deeper cleanup
- weekly backups
- reports
- integrity checks

## Monthly

Runs on a selected day of the month.

Be cautious with days 29, 30, or 31 because not every month contains them.

Use the first or another consistently available day when practical.

## One-Time

Runs once at a selected date and time.

After it runs, the timer may no longer have a future trigger.

Remove the task afterward if it is no longer needed.

## Custom Schedule

Advanced users may enter a systemd calendar expression.

Examples may resemble:

```text
Mon..Fri 08:00
*-*-01 03:00
hourly
daily
```

Use the common schedule controls unless you need behavior they cannot express.

An invalid expression may prevent the timer from loading.

## Start After Boot

Some tasks may use a delay after startup instead of a calendar time.

This is useful for:

- waiting for network access
- waiting for storage
- starting a recurring scan after boot

A boot delay is not the same as a specific wall-clock time.

## Persistent or Catch-Up Behavior

A persistent timer can run a missed task after the computer starts again.

Example:

- task is scheduled for 2:00 AM
- computer is off at 2:00 AM
- computer starts at 8:00 AM
- systemd runs the missed task shortly after startup

Enable this for tasks that should not be skipped, such as important backups.

Disable it when a late run would be undesirable, such as:

- sending a time-sensitive notification
- starting a job that must occur only during a maintenance window
- repeating an action after it is no longer relevant

## Randomized Delay

Advanced scheduling may allow systemd to delay a task by a random amount.

This can prevent many computers or tasks from starting simultaneously.

Most single-computer users do not need it.

## Preventing Overlapping Runs

A timer does not normally start a second copy of the same systemd service while that service is already active.

However, scripts that launch background work and exit immediately can still create overlap.

Design tasks so the service remains active until the real work finishes.

## Enable Immediately

When selected, the timer becomes active as soon as the task is created.

Leave this enabled for a finished task.

Turn it off when you want to save the definition and test later.

## Run Immediately After Creation

Runs the task once after creation.

This is useful for immediate validation.

Turn it off when:

- the action should occur only at its scheduled time
- the task is destructive
- required resources are not ready
- the command has already been tested separately

## Preview and Create

When preview is available:

1. Complete the form.
2. Click Preview.
3. Review the generated service.
4. Review the generated timer.
5. Confirm the command, user, and schedule.
6. Create the task.
7. Approve administrator authorization.
8. Confirm the next run time.
9. Test with Run Now when appropriate.

## Existing Timers Tab

The Existing Timers tab lists systemd timers on the computer, including timers not created by LEC.

Typical columns may include:

- timer unit
- associated service
- next run
- time remaining
- last run
- active state
- description

This view is primarily informational.

## Timer Unit

The `.timer` unit controls the schedule.

Example:

```text
apt-daily.timer
```

## Associated Service

The service started by the timer.

Example:

```text
apt-daily.service
```

The service can show as inactive most of the time because it runs only when triggered.

This is normal.

## Next Run

Shows when the timer will trigger next.

## Time Remaining

Shows the approximate interval until the next trigger.

## Last Run

Shows the last activation time.

## Active State

An active timer is waiting for its next trigger.

An inactive service paired with an active timer is not necessarily a problem.

## System Timers

Ubuntu and installed applications use timers for:

- updates
- package cleanup
- log rotation
- filesystem maintenance
- certificate renewal
- status scans

Do not disable unfamiliar system timers without understanding them.

## Cron Jobs Tab

The Cron Jobs tab shows traditional cron configuration found on the system.

Cron is an older scheduling system still used by many applications.

LEC may display:

- user crontabs
- system crontab entries
- files under cron directories
- schedule expression
- command
- source location

This view is mainly for inspection.

## Cron Schedule Syntax

Cron commonly uses five time fields:

```text
minute hour day-of-month month day-of-week
```

Example:

```text
0 2 * * *
```

means approximately:

```text
Every day at 2:00 AM
```

LEC-created tasks use systemd timers instead of adding new cron entries.

## Why Existing Cron Jobs Matter

A cron job may:

- duplicate a new LEC task
- use the same files
- start the same backup
- conflict with maintenance
- explain unexpected recurring activity

Before creating a task, check whether similar automation already exists.

## Background Scan

The module may use a background scan service and timer to maintain status information.

Components may include names similar to:

```text
lec-task-scheduler-scan.service
lec-task-scheduler-scan.timer
```

Use **Background Services** and **System Logs** when task status stops updating.

## Common Tasks

### Create a Nightly Backup

1. Test the backup command manually.
2. Open **Task Scheduler → Create Task**.
3. Enter a name such as `nightly-backup`.
4. Add a clear description.
5. Enter the backup command with an absolute path.
6. Enter arguments.
7. choose the correct run-as user.
8. Set the schedule to Daily.
9. choose a time when the destination is available.
10. Enable persistent catch-up if missed backups should run after boot.
11. Preview.
12. Create and enable.
13. Run Now once.
14. Review the result and logs.

### Run a Script Every Hour

1. Confirm the script can run unattended.
2. Use an absolute interpreter or script path.
3. Set Hourly.
4. Create the task.
5. Run it manually.
6. Confirm it completes before the next hour.

### Pause a Scheduled Task

1. Select the task.
2. Click Disable.
3. Confirm the timer becomes inactive.

The task definition remains available.

### Run a Task Early

1. Select the task.
2. Click Run Now.
3. Refresh the task list.
4. Review the last result.
5. Open System Logs if it failed.

### Change a Task's Time

1. Select the task.
2. Click Edit.
3. Change the schedule.
4. Save.
5. Confirm the next run.
6. Check that the old schedule no longer appears.

### Remove an Obsolete Task

1. Disable it.
2. Confirm it is not running.
3. Review the command and generated files.
4. Click Remove.
5. Approve administrator authorization.
6. Confirm it disappears from LEC Tasks and Existing Timers.

## Connections to Other Modules

### Mounts & Shares

Scheduled backups and file jobs may depend on mounted storage.

Confirm that:

- the mount is persistent
- it is available at the scheduled time
- the run-as user has access

A missed or unavailable mount can cause the task to write into an empty mount-point folder on the system disk.

### User Permissions

Use **User Permissions** when the task cannot access:

- source files
- destination folders
- devices
- Docker
- shared storage

Restarting a timer is not usually required after changing membership, but the next service run must start with the updated group list.

### Background Services

Use **Background Services** to inspect:

- generated task services
- generated timers
- scheduler scan service
- scheduler scan timer

### System Logs

Use **System Logs** when:

- a task fails
- a timer does not trigger
- a command cannot be found
- permissions are denied
- a mount is missing
- the service times out
- the generated unit is invalid

### Docker

A scheduled task may run Docker commands or maintenance.

The run-as user must have Docker access.

Treat Docker group membership as highly privileged.

### Hardware Monitor

Use **Hardware Monitor** when scheduled work causes:

- high processor use
- memory pressure
- disk space growth
- high drive activity
- excessive temperature

### Port Usage

Use **Port Usage** when a scheduled job starts a network service or fails because a port is occupied.

### Dynamic DNS

The Dynamic DNS module already uses its own timer.

Do not create a duplicate scheduled task for Dynamic DNS updates unless there is a specific unsupported requirement.

### LEC Settings and Recovery

LEC-created task definitions and generated systemd units are audited.

Use:

```text
LEC Settings → Recovery
```

to inspect or restore earlier task configuration.

After restoration:

1. return to Task Scheduler
2. refresh
3. enable the timer if needed
4. confirm the next run
5. test with Run Now

## Safety Guidance

### Test First

Never rely on the first scheduled run as the first test.

Run the command manually and use Run Now.

### Use Absolute Paths

Scheduled environments are limited.

Use complete paths for:

- commands
- scripts
- configuration
- input
- output
- mounted storage

### Avoid Interactive Commands

A task cannot answer prompts.

Use non-interactive flags and preconfigured credentials.

### Protect Credentials

Do not place passwords or tokens directly in task arguments when avoidable.

Command lines may appear in logs or process listings.

Use protected files or application-specific secret storage.

### Confirm Repetition Is Safe

A task may run again after:

- a failure
- reboot catch-up
- schedule changes
- manual Run Now
- timer reactivation

The command should avoid accidental duplicate work.

### Monitor Disk Use

Repeated jobs can create unlimited:

- backups
- logs
- downloads
- temporary files
- reports

Include retention or cleanup where necessary.

## Troubleshooting

### The Task Never Runs

Check:

- task is enabled
- next run is shown
- computer was on
- timer is active
- schedule is valid
- system time and time zone
- generated units loaded successfully

Use Existing Timers and System Logs.

### The Task Runs Manually but Not on Schedule

Possible causes include:

- timer is disabled
- schedule is invalid
- computer was off
- persistent catch-up is disabled
- system time changed
- systemd was not reloaded

### The Task Runs on Schedule but Fails

The scheduled environment may differ from your terminal.

Check:

- absolute command path
- arguments
- working directory
- run-as user
- permissions
- environment variables
- mounted storage
- network availability
- required virtual environment

### Command Not Found

Use the command's absolute path.

Find it outside LEC using the application's official location or package documentation.

Do not rely on aliases.

### Permission Denied

Confirm:

- run-as user
- script permissions
- folder permissions
- group membership
- mount ownership
- executable access on parent directories

Use User Permissions and System Logs.

### Backup Writes to the Wrong Disk

The intended mount may be unavailable, causing the command to write to the empty mount-point folder.

Before running:

- verify the mount
- make the script confirm the expected filesystem
- fail safely when the mount is absent

### Task Missed While Computer Was Off

Enable persistent catch-up behavior if the task should run after the next boot.

For time-sensitive tasks, a late run may not be appropriate.

### The Task Runs Twice

Check for:

- a duplicate LEC task
- an existing cron job
- another systemd timer
- application-internal scheduling
- a script that launches background work and exits

Search LEC Tasks, Existing Timers, and Cron Jobs.

### No Next Run Is Displayed

Possible causes include:

- timer disabled
- one-time task already completed
- invalid schedule
- timer load failure
- status snapshot is stale

Refresh and check System Logs.

### Last Result Remains Failed After Fixing the Task

Run the task again successfully.

Old failure markers may remain until a new run or explicit reset.

Check System Logs and the failed-unit section.

### The Scheduler Scan Status Is Stale

Check:

```text
lec-task-scheduler-scan.service
lec-task-scheduler-scan.timer
```

in Background Services and System Logs.

### A Restored Task Does Not Run

Recovery restores files.

You may still need to:

1. reload the Task Scheduler view
2. enable the timer
3. confirm the next run
4. use Run Now
5. restart or reload systemd-related state through the module


---


<a id="docker"></a>

# Docker

## Purpose

The Docker module provides a graphical way to create, run, inspect, stop, restart, and remove Docker containers without relying on the command line.

Use it to:

- review Docker installation and service status
- inspect existing containers
- create containers from images
- use guided `.lecdock` presets
- configure ports, storage, environment variables, and restart behavior
- choose whether a service is local-only, available on the LAN, or broadly exposed
- connect containers to Reverse Proxy and Firewall
- inspect container health and runtime state
- remove containers and related configuration safely

Docker packages an application together with its dependencies so it can run in an isolated container.

A container is not a complete virtual machine. It shares the Ubuntu host's kernel while keeping the application's processes, files, and network settings separated.

## Important Safety Note

Docker can provide powerful access to the host computer.

Be cautious with:

- images from unknown publishers
- containers running as root
- host filesystem mounts
- privileged mode
- access to devices
- access to the Docker socket
- exposed administrative ports
- containers using host networking

Membership in the Linux `docker` group effectively grants administrator-level control over the system.

Only trusted users should receive Docker access.

## Module Views

The Docker module typically includes views for:

- **Overview**
- **Containers**
- **Create Container**
- **Presets**
- **Images** or supporting runtime information

The exact tab names may vary slightly by LEC version.

## Overview Tab

The Overview tab summarizes Docker's current state.

Typical information includes:

- Docker installation status
- Docker service status
- Docker version
- number of containers
- running and stopped container counts
- image count
- storage usage
- access or permission status

## Docker Installation Status

### Installed and Running

Docker is available and the daemon is running.

Containers can be inspected and managed.

### Installed but Stopped

Docker is present, but the service is not running.

Existing containers remain stored but are unavailable until Docker starts.

Use **Background Services** or the available Docker action to start it.

### Not Installed

Docker is not installed.

When supported, LEC may offer an installation action.

### Permission Denied

The current user cannot access the Docker daemon.

Use **User Permissions** to review membership in the `docker` group.

After changing group membership, sign out and back in.

### Unavailable or Error

LEC could not query Docker.

Possible causes include:

- Docker service failure
- missing command-line tools
- daemon socket permissions
- incomplete installation
- corrupted Docker state

Use **System Logs** and **Background Services**.

## Docker Service

The Docker daemon normally runs as:

```text
docker.service
```

It manages:

- containers
- images
- networks
- volumes
- port publishing
- restart behavior

The Docker module communicates with this service.

## Containers Tab

The Containers tab lists existing Docker containers.

Typical columns may include:

- name
- image
- state
- health
- created time
- published ports
- access scope
- restart policy
- source or preset

## Container Name

The container name is the stable identifier used to manage it.

Example:

```text
jellyfin
guacamole
postgres
```

Use short descriptive names with lowercase letters and hyphens.

Container names must be unique.

## Image

The image identifies the packaged application and version.

Examples:

```text
nginx:latest
postgres:16
linuxserver/jellyfin:latest
```

The text after the colon is the tag.

A tag may represent:

- a fixed version
- a release family
- `latest`

For important services, a fixed version or controlled release tag may be safer than automatically following `latest`.

## State

Common states include:

### Running

The container's main process is active.

### Exited

The container stopped.

This may be intentional or may indicate failure.

### Restarting

Docker is repeatedly attempting to start it.

Check container logs and configuration.

### Created

The container exists but has not started successfully or has not yet been started.

### Paused

The container's processes are temporarily suspended.

### Dead

Docker considers the container unusable.

Removal and recreation may be required.

## Health

Some images define a health check.

Common values include:

### Healthy

The application's health check is succeeding.

### Unhealthy

The container is running, but its health check is failing.

The application may not be ready or may be malfunctioning.

### Starting

The health check is still within its startup period.

### No Health Check

The image does not define one.

A Running state does not guarantee the application is healthy.

## Published Ports

Published ports connect a port inside the container to an address and port on Ubuntu.

Example:

```text
127.0.0.1:8080 → 80/tcp
```

This means:

- the application listens on port 80 inside the container
- Ubuntu exposes it on host port 8080
- only the local computer can connect directly because it is bound to `127.0.0.1`

## Access Scope

LEC provides simplified access scopes.

### Local or Reverse Proxy Only

The host port is bound to:

```text
127.0.0.1
```

Only the Ubuntu host can connect directly.

Use this for:

- web applications published through Reverse Proxy
- private databases
- administration interfaces
- internal application components

This is the preferred default for web services that Caddy will publish.

### LAN

The service is bound to the computer's LAN address.

Other devices on the local network may connect, subject to Firewall.

Use this for:

- media servers
- household dashboards
- local development tools
- private network applications

### All Networks

The service is bound to:

```text
0.0.0.0
```

or an equivalent all-interface address.

It may be reachable through any network path permitted by Firewall, router, cloud, or upstream rules.

Use this only when broad access is intentionally required.

## Restart Policy

The restart policy tells Docker what to do after the container stops.

Common policies include:

### No

Do not restart automatically.

Use this for testing or one-time containers.

### On Failure

Restart only when the application exits with an error.

### Unless Stopped

Restart after failure and after reboot unless you deliberately stopped the container.

This is a good default for many long-running services.

### Always

Restart whenever possible, including after deliberate stops once Docker restarts.

Use carefully because it can make maintenance less intuitive.

## Container Actions

Typical actions include:

- Start
- Stop
- Restart
- Pause
- Unpause
- View Details
- View Logs
- Edit or Recreate
- Remove

## Start

Starts a stopped container.

If it immediately exits, inspect its logs.

## Stop

Requests a graceful shutdown.

Docker waits for the configured timeout and may then force termination.

Stop a container before:

- changing mounts
- changing published ports
- removing it
- unmounting storage it uses
- performing application-specific maintenance

## Restart

Stops and starts the container.

Use it after:

- changing external configuration
- restoring files
- correcting a temporary issue
- updating a dependency

Restarting does not apply container-definition changes such as new ports or mounts. Those usually require recreation.

## Pause and Unpause

Pause suspends the container's processes without stopping them.

Use it only for brief administrative needs.

A paused application cannot respond normally.

## View Details

Container details may include:

- image
- command
- entry point
- environment variables
- mounts
- networks
- published ports
- labels
- restart policy
- health information
- creation time

Sensitive environment values may be masked.

## View Logs

Container logs show output from the application's standard output and error streams.

Use them when:

- the container exits
- health checks fail
- the application rejects configuration
- a database cannot start
- a dependency is unavailable
- permissions are denied

Not every application writes complete logs to Docker.

Some also store logs inside a mounted data folder.

## Edit or Recreate

Docker does not directly modify many container settings after creation.

Changing these commonly requires recreation:

- published ports
- bind addresses
- environment variables
- mounts
- restart policy
- command
- network configuration

LEC should preserve the definition, stop and replace the container, then start the new one when requested.

Persistent application data must be stored outside the container's writable layer before recreation.

## Remove Container

Removing a container deletes its container instance.

It does not automatically remove:

- the image
- named volumes
- bind-mounted folders
- application data stored in persistent mounts
- Reverse Proxy rules
- Firewall rules
- Dynamic DNS records

Before removal:

1. Identify the container.
2. Confirm where its persistent data is stored.
3. Stop it.
4. Determine whether related proxy or firewall rules should also be removed.
5. Remove the container.
6. Verify that required data remains.

Do not remove a container when its important data exists only inside the container layer.

## Create Container Tab

The Create Container view lets you define a container manually.

Typical fields include:

- container name
- image
- image tag
- command
- environment variables
- ports
- volumes
- restart policy
- access scope
- optional advanced settings
- Reverse Proxy integration
- Firewall integration

## Container Name

Choose a unique name.

Example:

```text
music-server
```

Avoid using the image name alone when several instances may exist.

## Image Name

Enter the image repository.

Examples:

```text
nginx
postgres
linuxserver/jellyfin
```

Use trusted publishers and verify the official documentation.

## Image Tag

Enter a tag such as:

```text
latest
16
1.12.3
```

A blank tag may default to `latest`.

Pinning a version can prevent unexpected major changes.

## Pull Image

Before creating the container, LEC may download the image.

The pull can fail because of:

- no internet access
- incorrect image name
- missing tag
- registry authentication
- rate limits
- insufficient disk space

## Command and Arguments

Most images define their own startup command.

Leave this blank unless the image documentation instructs you to override it.

An incorrect command can prevent the application from starting.

## Environment Variables

Environment variables configure the application.

Examples may include:

```text
TZ=America/New_York
PUID=1000
PGID=1000
APP_PORT=8080
```

Use the image's official documentation.

Environment variables may contain secrets.

Do not expose:

- passwords
- API tokens
- database credentials
- encryption keys

Use secret files or application-supported secure storage when possible.

## Ports

A port mapping typically includes:

- host address or access scope
- host port
- container port
- protocol

Example:

```text
Host port:
8080

Container port:
80

Protocol:
TCP

Access:
Local or Reverse Proxy Only
```

The host port must not already be in use.

Use **Port Usage** before choosing one.

## Host Port

The host port is the port users or other local services connect to on Ubuntu.

It can differ from the container port.

## Container Port

The container port is the port where the application listens inside the container.

Use the image documentation.

## Protocol

Choose TCP or UDP as required.

The same number can be mapped separately for TCP and UDP.

## Multiple Ports

Some applications require several ports.

Examples may include:

- web interface
- discovery
- media streaming
- database
- peer-to-peer traffic

Expose only the ports actually needed.

## Volumes and Bind Mounts

Persistent storage should be mounted outside the container.

Two common approaches are:

- bind mounts
- named volumes

## Bind Mount

A bind mount maps a host folder into the container.

Example:

```text
Host:
/srv/jellyfin/config

Container:
/config
```

Advantages:

- easy to inspect and back up
- clear host location
- convenient for media or user-managed files

Risks:

- host permissions must be correct
- the container may modify host files
- mounting the wrong folder can expose sensitive data

## Named Volume

A named volume is managed by Docker.

Example:

```text
jellyfin-config
```

Advantages:

- Docker manages the storage location
- convenient for application data

Disadvantages:

- less obvious to new users
- requires Docker-aware backup methods

## Read-Only Mount

Use read-only access when the container only needs to read data.

Example:

```text
/srv/media:/media:ro
```

Read-only mounts reduce accidental changes.

## Persistent Data

Store important data outside the container layer.

Common persistent paths include:

- configuration
- database
- uploads
- media
- backups
- certificates

If the container is removed and recreated, only mounted data reliably remains.

## Permissions

The container's application user must have access to mounted folders.

Common problems include:

- wrong owner
- wrong group
- read-only permissions
- missing execute permission on parent directories
- mismatched PUID or PGID values

Use **User Permissions** and the image documentation.

## Restart Behavior

Choose the restart policy based on the service.

For an always-on application, `unless-stopped` is often appropriate.

For testing, use no automatic restart.

## Advanced Options

Advanced options may include:

- working directory
- user ID
- network mode
- hostname
- DNS servers
- device access
- capabilities
- privileged mode
- memory limit
- CPU limit
- labels

Use advanced settings only when the image documentation requires them.

## Privileged Mode

Privileged mode gives the container broad access to the host.

Avoid it unless absolutely necessary.

A container requesting privileged mode deserves careful review.

## Docker Socket Mount

Mounting:

```text
/var/run/docker.sock
```

allows the container to control Docker and often the host itself.

Treat this as administrator-level access.

Only trusted management applications should receive it.

## Device Access

Some containers need hardware such as:

- USB devices
- GPUs
- serial ports
- tun devices

Grant only the specific device required.

Use **User Permissions** and Hardware Monitor when diagnosing access.

## Resource Limits

When supported, set memory or CPU limits for applications that may consume excessive resources.

Use **Hardware Monitor** to observe actual usage.

## Preview and Create

Before creation:

1. Review the container name.
2. Verify the image and tag.
3. Check every environment variable.
4. Confirm ports and protocols.
5. Confirm access scope.
6. Confirm persistent storage.
7. Review restart policy.
8. Review Reverse Proxy and Firewall choices.
9. Create the container.
10. Wait for image pull and startup.
11. Inspect state and health.
12. Test the service.

## Presets Tab

The Presets tab uses `.lecdock` files to provide guided container or Compose setup.

A preset can define:

- image or Compose services
- form fields
- defaults
- ports
- volumes
- environment variables
- validation
- access scope
- Reverse Proxy integration
- Firewall integration
- persistent data requirements

Presets reduce the need to translate a long Docker command manually.

## Preset Sources

Presets may come from:

- LEC's installed preset collection
- an application module
- a manually imported `.lecdock` file
- a trusted third-party source

Only use presets from sources you trust.

A preset can create containers with substantial host access.

## Container Presets

A container preset creates one Docker container.

Use it for applications that do not require several coordinated services.

## Compose Presets

A Compose preset creates a multi-container application.

Examples may include:

- web application
- database
- supporting daemon
- cache

The preset coordinates the services, networks, and persistent storage.

## Preset Form Fields

The form may request:

- application name
- host port
- data folder
- timezone
- username
- password
- hostname
- access scope
- optional features

Required fields must be completed before deployment.

Descriptions and validation come from the preset.

## Secrets in Presets

Secret fields should be treated as sensitive.

Examples include:

- database password
- administrator password
- API token

Do not share screenshots containing those values.

## Preset Storage

LEC can discover `.lecdock` files in supported preset locations.

Imported presets remain separate from the running containers they create.

Removing a preset does not automatically remove deployed containers.

## Deploying a Preset

A typical workflow is:

1. Open **Docker → Presets**.
2. Select the application.
3. Read the description and requirements.
4. Complete the form.
5. Choose storage locations.
6. Choose access scope.
7. Configure a hostname when Reverse Proxy integration is offered.
8. Review the generated definition.
9. Deploy.
10. Wait for all services to start.
11. Inspect health and logs.
12. Test the application.

## Access Scope Integration

LEC uses access scope to coordinate Docker networking with Firewall and Reverse Proxy.

### Local or Reverse Proxy Only

LEC binds the host port to:

```text
127.0.0.1
```

Use Reverse Proxy to publish web access.

### LAN

LEC binds the service for local-network access and can request a Docker-aware Firewall rule.

### All Networks

LEC creates broad exposure.

Review Firewall, router, and security requirements carefully.

## Reverse Proxy Integration

For a web application, a preset or container form may offer Reverse Proxy setup.

A typical workflow is:

1. Choose Local or Reverse Proxy Only.
2. Select or enter a hostname.
3. Deploy the container.
4. Allow LEC to create the proxy rule.
5. Confirm the hostname in Reverse Proxy.
6. Confirm Caddy's certificate.
7. Test HTTPS access.

## Firewall Integration

For LAN or broader access, Docker can request a Docker-aware Firewall rule.

Review the resulting rule under:

```text
Firewall → Docker Rules
```

Standard UFW rules alone may not fully describe Docker exposure.

## Docker-Aware Firewall Behavior

Docker modifies networking rules directly.

LEC uses a dedicated Docker-aware rule chain so LAN and source restrictions can be applied before Docker accepts forwarded traffic.

When changing exposure:

1. update the container bind address or scope
2. update the Docker-aware Firewall rule
3. verify the listener in Port Usage
4. test from an allowed source
5. test from a disallowed source when practical

## Images

The Images view, when available, lists downloaded images.

Typical information may include:

- repository
- tag
- image ID
- creation time
- size
- usage state

## Remove Image

An image can normally be removed only when no container depends on it.

Removing an image:

- frees disk space
- does not remove persistent volumes
- may require downloading the image again later

Do not remove an unfamiliar image until you confirm which containers use it.

## Updating Containers

Docker images do not automatically update the running container definition.

A typical update process is:

1. Review the application's release notes.
2. Back up persistent data.
3. Pull the newer image.
4. Stop the container.
5. Recreate it using the same settings and mounts.
6. Start it.
7. Check logs and health.
8. Test the application.
9. Keep or remove the old image according to rollback needs.

Do not assume `latest` guarantees a safe or compatible update.

## Backups

Back up the persistent data, not merely the container.

Important items may include:

- bind-mounted folders
- named volumes
- Compose configuration
- `.lecdock` values
- environment files
- database dumps

A container can usually be recreated. Application data may not be replaceable.

## Common Tasks

### Create a Local Web Container for Reverse Proxy

1. Open **Create Container**.
2. Enter the container name.
3. Enter the image and tag.
4. Add required environment variables.
5. Add persistent storage.
6. Map the container's web port to an unused host port.
7. Choose **Local or Reverse Proxy Only**.
8. Use `unless-stopped` when appropriate.
9. Create and start the container.
10. Confirm the listener in Port Usage.
11. Create the hostname in Dynamic DNS.
12. Create the rule in Reverse Proxy.
13. Test HTTPS access.

### Create a LAN-Only Service

1. Define the container.
2. Add required ports and storage.
3. Choose **LAN** access.
4. Deploy it.
5. Verify the Docker-aware Firewall rule.
6. Test from another LAN device.
7. Confirm it is not reachable from an unintended network.

### Stop and Restart a Container

1. Select the container.
2. Click Stop.
3. Wait for Exited.
4. Perform the required maintenance.
5. Click Start.
6. Check health and logs.

### Change a Published Port

1. Stop the container.
2. Edit or recreate it.
3. Choose an unused host port.
4. Confirm the container port.
5. Review access scope.
6. Recreate the container.
7. Update Reverse Proxy or client settings.
8. Remove obsolete Firewall rules.
9. Verify in Port Usage.

### Add Persistent Storage

1. Identify the application's required container path.
2. Create or select a host folder.
3. Confirm permissions.
4. Stop the container.
5. Edit or recreate it with the new mount.
6. Start it.
7. Confirm the application uses the mounted location.

Adding an empty mount over a container path can hide files originally stored there. Follow the application's migration instructions.

### Remove a Container Safely

1. Identify all persistent mounts and volumes.
2. Back up important data.
3. Note Reverse Proxy and Firewall integrations.
4. Stop the container.
5. Remove it.
6. Remove obsolete proxy and firewall rules.
7. Remove the image only when no longer needed.
8. Remove data only when intentionally uninstalling the application.

## Connections to Other Modules

### Port Usage

Use **Port Usage** to verify:

- host port
- protocol
- bind address
- container association
- exposure scope
- Firewall status
- Reverse Proxy status

### Firewall

Use **Firewall → Docker Rules** to review Docker-aware access.

Docker's networking behavior requires more than ordinary UFW inspection.

### Reverse Proxy

Use **Reverse Proxy** to publish local-only web containers through Caddy.

This is the preferred design for internet-facing web applications.

### Dynamic DNS

Use **Dynamic DNS** to maintain a public hostname for a reverse-proxied container.

### Mounts & Shares

Containers may use mounted local disks or network shares.

Before stopping or unmounting storage:

1. stop the affected container
2. change the mount
3. confirm storage is available
4. restart the container

### User Permissions

Use **User Permissions** when:

- the current user cannot access Docker
- a container cannot access a bind-mounted folder
- device or group access is required

### Hardware Monitor

Use **Hardware Monitor** to watch:

- CPU usage
- memory use
- disk capacity
- storage health
- temperatures

### Background Services

Use **Background Services** to manage the Docker daemon.

Stopping Docker stops all running containers.

### System Logs

Use **System Logs** for:

- Docker daemon failures
- image pull failures
- networking errors
- container startup problems
- Docker-aware Firewall helper failures

Use container logs for application-specific errors.

### Remote Access

Guacamole is typically deployed through Docker.

Remote Access can guide you into the Docker preset workflow.

### Task Scheduler

Scheduled tasks may perform:

- backups
- image pulls
- maintenance
- container restarts

The task's run-as user must have Docker access.

### LEC Settings and Recovery

LEC audits managed configuration files and integration changes.

Recovery can restore:

- preset-related configuration
- Reverse Proxy configuration
- Firewall configuration
- LEC-managed metadata

Recovery does not automatically recreate every container runtime state or restore application data.

After Recovery, verify:

- container existence
- image availability
- mounts
- ports
- proxy rules
- firewall rules
- service health

## Safety Guidance

### Trust the Image Source

Use official or well-established images.

Review:

- publisher
- repository
- update history
- documentation
- required privileges
- issue reports

### Avoid Unnecessary Privileges

Do not enable:

- privileged mode
- host networking
- Docker socket access
- broad device access

unless the application genuinely requires them.

### Keep Data Outside the Container Layer

Use bind mounts or named volumes for important data.

### Do Not Expose Databases Publicly

Database ports should normally remain local or on a private Docker network.

Publish only the application interface that users need.

### Use Strong Secrets

Change default passwords immediately.

Do not commit secret environment files or `.lecdock` values to a public repository.

### Review Updates

Container updates can include breaking changes.

Back up data and review release notes before recreating important services.

## Troubleshooting

### Docker Shows Permission Denied

The current user may not belong to the `docker` group.

Use **User Permissions**, then sign out and back in.

### Docker Service Is Not Running

Use **Background Services** to start `docker.service`.

Review System Logs if it fails.

### Image Pull Fails

Check:

- internet connection
- image name
- tag
- registry availability
- registry credentials
- disk space
- rate limits

### Container Immediately Exits

Open container logs.

Common causes include:

- missing required environment variables
- invalid command
- wrong permissions
- missing configuration
- unsupported architecture
- inaccessible storage
- database dependency not ready

### Container Is Running but Application Does Not Work

Check:

- health status
- container logs
- published port
- bind address
- application startup time
- required dependencies
- Reverse Proxy destination
- Firewall

### Host Port Is Already in Use

Use Port Usage to identify the conflict.

Choose another host port or stop the conflicting service.

Do not change the container port unless the application supports it.

### Application Works Locally but Not from the LAN

Check:

- access scope
- bind address
- Docker-aware Firewall rule
- client address
- application authentication
- protocol

A localhost-bound container cannot be reached directly from another device.

### Application Works by Port but Not by Hostname

Docker is probably working.

Check Dynamic DNS, Reverse Proxy, Caddy, certificate status, and Firewall.

### Container Cannot Access a Mounted Folder

Check:

- host path
- container path
- read-only setting
- ownership
- group membership
- PUID and PGID
- parent-directory permissions
- whether the underlying mount is active

### Container Sees an Empty Folder

Possible causes include:

- wrong host path
- underlying storage is unmounted
- an empty bind mount covers existing container files
- permissions prevent listing
- the application expects another container path

### Container Keeps Restarting

Inspect logs and health.

Possible causes include:

- invalid configuration
- unavailable database
- permission failure
- port conflict
- missing secret
- corrupted data
- restart policy hiding repeated failure

Temporarily disable automatic restart while troubleshooting when appropriate.

### Reverse Proxy Shows Bad Gateway

Caddy cannot reach the container's host port.

Confirm:

- container is running
- host port exists
- bind address is correct
- destination port matches
- application is ready

### Docker Rule Exists but the Service Is Blocked

Check:

- published host port
- protocol
- source network
- Docker-aware Firewall helper
- client IP
- overlapping rules

### Removing the Container Deleted the Application but Not the Data

This is expected when data is stored in a bind mount or named volume.

Remove persistent data separately only when intentionally uninstalling the application.

### Recreating the Container Lost Data

The data was probably stored only in the old container layer or mounted to the wrong location.

Restore from backup and correct the persistent mount before recreating again.

### A Restored Configuration Does Not Restore the Container

Recovery restores LEC-managed files and metadata, not necessarily Docker runtime objects.

Use the saved preset or container definition to recreate it, then verify persistent data and integrations.


---

The End

Copyleft 2026 - no rights reserved
