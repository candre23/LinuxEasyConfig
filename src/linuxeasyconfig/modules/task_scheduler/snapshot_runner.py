from __future__ import annotations

from .collector import collect_status


def main() -> int:
    collect_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
