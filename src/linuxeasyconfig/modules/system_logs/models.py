from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LogEvent:
    timestamp: str
    first_timestamp: str
    last_timestamp: str
    priority: int
    severity: str
    source: str
    unit: str
    process: str
    pid: str
    category: str
    summary: str
    explanation: str
    suggestion: str
    confidence: str
    message: str
    count: int
    boot_id: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LogEvent":
        return cls(
            timestamp=str(value.get("timestamp", "")),
            first_timestamp=str(
                value.get("first_timestamp", "")
            ),
            last_timestamp=str(
                value.get("last_timestamp", "")
            ),
            priority=int(value.get("priority", 6)),
            severity=str(value.get("severity", "Info")),
            source=str(value.get("source", "")),
            unit=str(value.get("unit", "")),
            process=str(value.get("process", "")),
            pid=str(value.get("pid", "")),
            category=str(value.get("category", "Other")),
            summary=str(value.get("summary", "")),
            explanation=str(value.get("explanation", "")),
            suggestion=str(value.get("suggestion", "")),
            confidence=str(
                value.get("confidence", "Raw message only")
            ),
            message=str(value.get("message", "")),
            count=int(value.get("count", 1)),
            boot_id=str(value.get("boot_id", "")),
        )
