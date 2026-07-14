from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from linuxeasyconfig.core.config.base import ConfigurationDocument


class SystemdUnit(ConfigurationDocument):
    """Builder for systemd unit files."""

    def __init__(self) -> None:
        self._sections: OrderedDict[
            str,
            list[tuple[str | None, str]],
        ] = OrderedDict()

    def add_section(self, name: str) -> None:
        """Add a section if it does not already exist."""

        section_name = self._validate_section_name(name)
        self._sections.setdefault(section_name, [])

    def add(
        self,
        section: str,
        key: str,
        value: object,
    ) -> None:
        """Append a directive, preserving duplicate keys."""

        section_name = self._validate_section_name(section)
        directive_name = self._validate_key(key)
        directive_value = self._format_value(value)

        self._sections.setdefault(section_name, []).append(
            (directive_name, directive_value)
        )

    def set(
        self,
        section: str,
        key: str,
        value: object,
    ) -> None:
        """Replace matching directives, then add the new value."""

        section_name = self._validate_section_name(section)
        directive_name = self._validate_key(key)
        directive_value = self._format_value(value)

        directives = self._sections.setdefault(section_name, [])
        directives[:] = [
            (existing_key, existing_value)
            for existing_key, existing_value in directives
            if existing_key != directive_name
        ]
        directives.append((directive_name, directive_value))

    def add_many(
        self,
        section: str,
        key: str,
        values: Iterable[object],
    ) -> None:
        """Append the same directive for each supplied value."""

        for value in values:
            self.add(section, key, value)

    def add_comment(
        self,
        section: str,
        comment: str,
    ) -> None:
        """Append a comment inside a section."""

        section_name = self._validate_section_name(section)
        text = str(comment).strip()

        if text:
            self._sections.setdefault(section_name, []).append(
                (None, f"# {text}")
            )

    def add_blank_line(self, section: str) -> None:
        """Append a blank line inside a section."""

        section_name = self._validate_section_name(section)
        self._sections.setdefault(section_name, []).append(
            (None, "")
        )

    def render(self) -> str:
        lines: list[str] = []

        for section_index, (section, directives) in enumerate(
            self._sections.items()
        ):
            if section_index:
                lines.append("")

            lines.append(f"[{section}]")

            for key, value in directives:
                if key is None:
                    lines.append(value)
                else:
                    lines.append(f"{key}={value}")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def quote_argument(argument: object) -> str:
        """Quote one argument for an ExecStart-style command."""

        text = str(argument)

        if "\n" in text or "\r" in text:
            raise ValueError("Arguments cannot contain newlines.")

        if not text:
            return '""'

        requires_quotes = any(
            character.isspace() or character in {'"', "\\"}
            for character in text
        )

        if not requires_quotes:
            return text

        escaped = (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
        )
        return f'"{escaped}"'

    @classmethod
    def command(
        cls,
        executable: object,
        *arguments: object,
    ) -> str:
        """Build a safely quoted ExecStart-style command."""

        parts = [
            cls.quote_argument(executable),
            *(
                cls.quote_argument(argument)
                for argument in arguments
            ),
        ]
        return " ".join(parts)

    @staticmethod
    def _validate_section_name(name: str) -> str:
        value = str(name).strip()

        if not value:
            raise ValueError("Section names cannot be empty.")

        if any(character in "[]\r\n" for character in value):
            raise ValueError(
                f"Invalid systemd section name: {value!r}"
            )

        return value

    @staticmethod
    def _validate_key(key: str) -> str:
        value = str(key).strip()

        if not value:
            raise ValueError("Directive names cannot be empty.")

        if any(
            character.isspace() or character in "=[]"
            for character in value
        ):
            raise ValueError(
                f"Invalid systemd directive name: {value!r}"
            )

        return value

    @staticmethod
    def _format_value(value: object) -> str:
        text = str(value)

        if "\n" in text or "\r" in text:
            raise ValueError(
                "Systemd directive values cannot contain newlines."
            )

        return text
