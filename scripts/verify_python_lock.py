"""Ensure every direct Python requirement is represented by requirements.lock."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "requirements.txt").is_file():
    # Docker copies this verifier next to the two requirements files rather
    # than copying the complete scripts directory before dependency install.
    ROOT = Path.cwd()
_NAME = re.compile(r"^[A-Za-z0-9_.-]+")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _package_names(path: Path) -> set[str]:
    names: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _NAME.match(line)
        if match is None:
            raise ValueError(f"Unsupported requirement syntax in {path.name}: {line}")
        names.add(_normalize(match.group(0)))
    return names


def main() -> None:
    direct = _package_names(ROOT / "requirements.txt")
    locked = _package_names(ROOT / "requirements.lock")
    missing = sorted(direct - locked)
    if missing:
        raise SystemExit(
            "requirements.lock is missing direct dependencies: " + ", ".join(missing)
        )
    print(f"Python lock covers {len(direct)} direct dependencies and {len(locked)} packages.")


if __name__ == "__main__":
    main()
