from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_dir


SETTINGS_PATH = (
    Path(user_config_dir("linuxeasyconfig"))
    / "settings.json"
)


@dataclass
class LECSettings:
    appearance: str = "system"
    icon_size: str = "small"
    confirm_destructive_actions: bool = True
    show_advanced_options: bool = False


def load_settings() -> LECSettings:
    try:
        raw = json.loads(
            SETTINGS_PATH.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return LECSettings()

    appearance = str(
        raw.get("appearance", "system")
    ).strip().lower()

    if appearance not in {"system", "light", "dark"}:
        appearance = "system"

    icon_size = str(
        raw.get("icon_size", "small")
    ).strip().lower()

    if icon_size not in {"none", "small", "large"}:
        icon_size = "small"

    return LECSettings(
        appearance=appearance,
        icon_size=icon_size,
        confirm_destructive_actions=bool(
            raw.get(
                "confirm_destructive_actions",
                True,
            )
        ),
        show_advanced_options=bool(
            raw.get(
                "show_advanced_options",
                False,
            )
        ),
    )


def save_settings(settings: LECSettings) -> None:
    SETTINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = SETTINGS_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            asdict(settings),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(SETTINGS_PATH)
