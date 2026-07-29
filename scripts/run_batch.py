#!/usr/bin/env python3
"""Compatibility wrapper for the installed ``bia-brief-batch`` command."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from Brief.cli import run_batch_cli


if __name__ == "__main__":
    raise SystemExit(run_batch_cli())
