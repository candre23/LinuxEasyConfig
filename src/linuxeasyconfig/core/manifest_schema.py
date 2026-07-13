from __future__ import annotations

MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "LEC Module Manifest",
    "type": "object",
    "additionalProperties": True,
    "required": [
        "format_version",
        "id",
        "name",
        "version",
        "description",
        "module_type",
        "entry_page",
    ],
    "properties": {
        "format_version": {
            "type": "integer",
            "const": 1,
        },
        "id": {
            "type": "string",
            "minLength": 1,
            "pattern": r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$",
        },
        "name": {
            "type": "string",
            "minLength": 1,
        },
        "version": {
            "type": "string",
            "minLength": 1,
        },
        "description": {
            "type": "string",
            "minLength": 1,
        },
        "module_type": {
            "type": "string",
            "enum": ["declarative", "extended"],
        },
        "entry_page": {
            "type": "string",
            "minLength": 1,
        },
    },
}
