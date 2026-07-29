"""Installation and project health checks used by the public CLI."""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check BIA-Brief installation and project layout.")
    parser.add_argument("--project", default=None, help="Optional project directory to inspect")
    args = parser.parse_args(argv)

    failed = False
    for module in ("deepagents", "langchain_core", "langchain_openai", "langgraph", "yaml", "pypdf"):
        try:
            importlib.import_module(module)
            print(f"PASS dependency: {module}")
        except Exception as exc:
            failed = True
            print(f"FAIL dependency: {module} ({exc})")

    package_root = Path(__file__).resolve().parent
    template = package_root / "resources" / "templates" / "scRNA" / "report.md"
    if template.is_file():
        print(f"PASS resource: {template}")
    else:
        failed = True
        print(f"FAIL resource: {template}")

    if args.project:
        project = Path(args.project).expanduser().resolve()
        if not project.is_dir():
            failed = True
            print(f"FAIL project: {project}")
        elif not any((project / name).is_dir() for name in ("figures", "pics")):
            failed = True
            print(f"FAIL project inputs: {project}")
        else:
            print(f"PASS project: {project}")

    return 1 if failed else 0
