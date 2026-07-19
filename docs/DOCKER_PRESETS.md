# Docker Presets

LEC Docker presets use the `.lecdock` extension and contain JSON.

A preset provides a reusable, guided deployment for either:

- a single Docker container
- a Docker Compose application

Presets are intended to turn a known-good Docker configuration into a simple form that ordinary users can complete without writing command lines or Compose files.

## 1. Preset Types

LEC supports two preset types.

### `container`

Fills the standard single-container builder.

Use this for applications that can be deployed as one container with straightforward ports, volumes, environment variables, and restart behavior.

### `compose`

Displays preset-defined fields and deploys a Docker Compose application.

Use this for applications that require:

- multiple containers
- custom networks
- named volumes
- generated configuration files
- database dependencies
- more complex startup relationships

## 2. Required Top-Level Fields

Every preset must contain:

```json
{
  "format_version": 1,
  "id": "org.example.application",
  "name": "Application Name",
  "type": "container",
  "description": "What this preset installs.",
  "fields": []
}
```

Field meanings:

- `format_version` — preset format version; currently `1`
- `id` — stable, unique preset identifier
- `name` — user-facing application name
- `type` — `container` or `compose`
- `description` — short explanation of what the preset deploys
- `fields` — values the user must provide before deployment

Use a reverse-domain style ID when possible:

```text
org.example.application
```

Do not change the ID between releases of the same preset.

## 3. Supported Field Types

Preset fields may use:

- `text`
- `password`
- `integer`
- `port`
- `boolean`
- `choice`

Example:

```json
{
  "id": "admin_password",
  "label": "Administrator password",
  "type": "password",
  "required": true
}
```

Choice example:

```json
{
  "id": "timezone",
  "label": "Time zone",
  "type": "choice",
  "required": true,
  "choices": [
    {
      "label": "Eastern",
      "value": "America/New_York"
    },
    {
      "label": "Central",
      "value": "America/Chicago"
    }
  ]
}
```

Use the exact field structure found in current built-in presets. Copying a working preset is safer than inventing new keys.

## 4. Preset Responsibilities

A preset may define or generate:

- container images
- container names
- ports
- bind mounts
- named volumes
- environment variables
- restart policies
- networks
- Docker Compose content
- application configuration files
- related local service metadata

A preset should expose only values the user actually needs to choose.

Keep technical defaults inside the preset when they are safe and broadly applicable.

## 5. Paths and Storage

Imported presets are copied to:

```text
~/.local/share/linuxeasyconfig/docker-presets/
```

A preset may create application files under a managed location such as:

```text
/etc/linuxeasyconfig/docker/
```

or another module-defined location appropriate to the deployment.

Do not embed the developer's own:

- home directory
- username
- hostname
- LAN address
- public IP address
- credentials
- domain names
- local volume paths

Use fields or neutral defaults instead.

## 6. Ports and Access Scope

Presets should define sensible default ports while allowing the user to change them when practical.

LEC supports these general access scopes:

- local or reverse-proxy only
- LAN
- all networks

The Docker module maps these scopes to the appropriate bind address and can integrate with Firewall and Reverse Proxy.

Do not hard-code public exposure unless that is essential to the application and clearly explained.

Prefer local or reverse-proxy-only access for administrative interfaces.

## 7. Volumes and Persistent Data

Applications that store important data must use persistent bind mounts or named volumes.

Presets should clearly distinguish:

- application configuration
- user-created data
- caches
- temporary files
- databases

Never place important data only inside the writable container layer.

Removal actions should not delete persistent data unless the user explicitly chooses that option.

## 8. Secrets

Use `password` fields for credentials and secret tokens.

Presets must not contain real credentials.

Do not:

- place secrets directly in the preset JSON
- log secret field values
- expose passwords in generated status output
- commit generated `.env` files containing real values

Generated secret files should use restrictive permissions.

Use application-scoped credentials where possible.

## 9. Container Presets

A `container` preset should map cleanly to the normal Docker builder.

Typical settings include:

- image
- container name
- command
- environment variables
- ports
- volumes
- restart policy
- access scope

Keep the preset simple. Use `compose` when the application requires several coordinated resources or generated files.

## 10. Compose Presets

A `compose` preset may generate a Compose application from user-supplied fields.

The deployment should:

1. validate all fields
2. create the application directory
3. generate Compose and related configuration
4. create required networks or volumes
5. run Docker Compose
6. verify container status
7. publish local service information when appropriate
8. report partial failures clearly

Generated Compose files and persistent configuration should use LEC's audited configuration API where they affect long-term behavior.

Do not use unrestricted shell fragments supplied by preset users.

## 11. Integration with Other Modules

A preset may be designed to work with:

- Firewall
- Reverse Proxy
- Dynamic DNS
- Port Usage
- Remote Access

Examples:

- publish a web service as a local service
- allow the user to expose a port through Firewall
- create a Caddy reverse proxy
- use a hostname managed by Dynamic DNS
- show the resulting listener in Port Usage

Integrations should remain optional. The deployment must explain when another module or service is unavailable.

## 12. Security and Trust

A Docker preset can create containers, networks, volumes, application files, and services.

Import only presets from trusted sources.

Before distributing a preset, inspect:

- container images and tags
- mounted host paths
- Linux capabilities
- privileged mode
- device access
- host networking
- exposed ports
- environment variables
- downloaded scripts
- generated commands

Avoid:

- `privileged: true`
- mounting the Docker socket
- broad host-filesystem mounts
- host networking
- unnecessary Linux capabilities
- unpinned or untrusted images

When elevated access is genuinely required, explain why in the preset description.

## 13. Versioning and Updates

Keep `format_version` at `1` unless the preset schema itself changes.

The preset's application ID should remain stable.

When updating a preset:

- preserve existing field IDs where possible
- avoid silently changing data locations
- avoid destructive migration behavior
- document image or configuration changes
- verify both fresh installation and upgrade behavior

Use specific image versions when stability matters. Avoid relying on `latest` for production-oriented presets unless the application explicitly recommends it.

## 14. Development Workflow

Recommended process:

1. Deploy the application manually or from its official Compose example.
2. Confirm the application works.
3. Identify only the values the user must choose.
4. Convert those values into preset fields.
5. Move safe defaults into the preset.
6. add persistent storage.
7. choose the safest practical access scope.
8. add optional module integrations.
9. test on a clean machine.
10. remove all machine-specific and secret data.
11. import the final `.lecdock` file into LEC.
12. verify deployment and removal behavior.

Existing presets in the project are the authoritative examples for the current schema.

## 15. Release Checklist

Before publishing a preset, verify:

- [ ] The file uses the `.lecdock` extension.
- [ ] `format_version` is `1`.
- [ ] The preset ID is unique and stable.
- [ ] The type is `container` or `compose`.
- [ ] Every required field has a clear label.
- [ ] Passwords and tokens use password fields.
- [ ] No real credentials or machine-specific values are included.
- [ ] Important data is stored persistently.
- [ ] Default port exposure is no broader than necessary.
- [ ] The deployment works on a clean LEC installation.
- [ ] Missing optional integrations are handled gracefully.
- [ ] Removal does not delete user data without confirmation.
- [ ] Generated persistent configuration appears in Recovery where applicable.
- [ ] The preset contains no unnecessary privileged access.
