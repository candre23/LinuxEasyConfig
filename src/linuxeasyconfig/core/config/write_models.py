from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WritePreview:
    """Description of a proposed configuration-file write."""

    module_id: str
    destination: Path
    rendered_text: str
    destination_exists: bool
    contents_changed: bool
    current_sha256: str | None
    proposed_sha256: str


@dataclass(frozen=True)
class WriteResult:
    """Record of a completed configuration-file write."""

    revision: int
    timestamp: str
    module_id: str
    action: str
    destination: Path
    backup_path: Path | None
    previous_sha256: str | None
    new_sha256: str
    bytes_written: int
