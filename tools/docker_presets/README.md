# LEC Docker preset files

Docker presets use the `.lecdock` extension and contain JSON.

Supported preset types:

- `container`: fills the normal single-container builder.
- `compose`: displays editable preset fields and deploys a Docker Compose application.

Required top-level fields:

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

Field types:

- `text`
- `password`
- `integer`
- `port`
- `boolean`
- `choice`

Imported presets are copied to:

```text
~/.local/share/linuxeasyconfig/docker-presets/
```

Presets can create containers, networks, volumes, and application files. Import only presets from trusted sources.
