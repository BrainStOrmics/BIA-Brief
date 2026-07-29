"""Check that the installed BIA-Brief CLI and its packaged resources are usable."""

from __future__ import annotations

import importlib.resources
import sys
from pathlib import Path


def main() -> int:
    try:
        import Brief  # noqa: F401
    except ImportError as exc:
        print(f"bia-brief is not installed: {exc}", file=sys.stderr)
        return 1

    environment_root = Path(sys.executable).resolve().parent
    scripts_dir = environment_root / "Scripts" if sys.platform == "win32" else environment_root
    command = next(
        (
            candidate
            for candidate in (
                scripts_dir / "bia-brief-project.exe",
                scripts_dir / "bia-brief-project",
            )
            if candidate.is_file()
        ),
        None,
    )
    template = importlib.resources.files("Brief.resources").joinpath(
        "templates/scRNA/report.md"
    )
    if not command or not template.is_file():
        print("bia-brief installation is incomplete", file=sys.stderr)
        return 1
    print("bia-brief is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
