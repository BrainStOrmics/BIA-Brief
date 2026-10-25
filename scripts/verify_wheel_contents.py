#!/usr/bin/env python3
"""Verify that the newest built wheel contains the intended runtime files."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist"

REQUIRED_FILES = {
    "Brief/pipeline/review_gate.py",
    "Brief/pipeline/template_spec.py",
    "Brief/prompts/agent.md",
    "Brief/prompts/agent_generic.md",
    "Brief/prompts/agent_spatial.md",
    "Brief/prompts/report.md",
    "Brief/prompts/report_generic.md",
    "Brief/prompts/report_spatial.md",
    "Brief/resources/templates/scRNA/report.md",
    "Brief/resources/templates/spatial/report.md",
    "Brief/resources/templates/standard/report.md",
}

FORBIDDEN_FILES = {
    "Brief/tools/file_ops.py",
    "Brief/tools/task_ops.py",
    "Brief/utils/filemanager.py",
    "Brief/prompts/thesis.md",
}


def _project_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml has no project version")
    return match.group(1)


def main() -> int:
    version = _project_version()
    wheel = DIST_DIR / f"bia_brief-{version}-py3-none-any.whl"
    if not wheel.is_file():
        print(f"Wheel not found: {wheel}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_FILES - names)
        forbidden = sorted(FORBIDDEN_FILES & names)
        dist_info = f"bia_brief-{version}.dist-info/METADATA"

    if missing:
        print(f"Wheel is missing files: {', '.join(missing)}", file=sys.stderr)
        return 1
    if forbidden:
        print(f"Wheel contains removed files: {', '.join(forbidden)}", file=sys.stderr)
        return 1
    if dist_info not in names:
        print(f"Wheel metadata is missing: {dist_info}", file=sys.stderr)
        return 1

    print(f"Wheel contents verified: {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
