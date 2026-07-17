from __future__ import annotations

from .collector import write_snapshot


def main() -> int:
    write_snapshot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
