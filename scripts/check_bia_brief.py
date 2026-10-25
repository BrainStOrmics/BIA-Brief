"""Check that the installed BIA-Brief CLI and its packaged resources are usable."""

from __future__ import annotations

import importlib.resources
import importlib.metadata
import shutil
import sys


EXPECTED_VERSION = "0.2.6"


def main() -> int:
    try:
        import Brief  # noqa: F401
    except ImportError as exc:
        print(f"bia-brief is not installed: {exc}", file=sys.stderr)
        return 1

    try:
        installed_version = importlib.metadata.version("bia-brief")
    except importlib.metadata.PackageNotFoundError:
        print("bia-brief package metadata is missing", file=sys.stderr)
        return 1
    if installed_version != EXPECTED_VERSION:
        print(
            f"bia-brief version mismatch: expected {EXPECTED_VERSION}, "
            f"found {installed_version}",
            file=sys.stderr,
        )
        return 1

    command = shutil.which("bia-brief-project")
    resource_root = importlib.resources.files("Brief.resources")
    templates = [
        resource_root.joinpath("templates/scRNA/report.md"),
        resource_root.joinpath("templates/spatial/report.md"),
        resource_root.joinpath("templates/standard/report.md"),
    ]
    if not command or not all(template.is_file() for template in templates):
        print("bia-brief installation is incomplete", file=sys.stderr)
        return 1
    print(f"bia-brief {installed_version} is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
