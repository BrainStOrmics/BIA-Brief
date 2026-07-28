#!/usr/bin/env python3
"""Check whether the repository is ready to run reports."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from Brief.pipeline.runner_config import DEFAULT_CONFIG_PATH, load_runner_config


def _ok(label: str, message: str) -> None:
    print(f"OK   {label:<24} {message}")


def _warn(label: str, message: str) -> None:
    print(f"WARN {label:<24} {message}")


def _fail(label: str, message: str) -> None:
    print(f"FAIL {label:<24} {message}")


def _check_import(module_name: str, label: str) -> bool:
    if importlib.util.find_spec(module_name) is not None:
        _ok(label, module_name)
        return True
    _fail(label, f"{module_name}: module not found")
    return False


def _check_playwright() -> bool:
    if importlib.util.find_spec("playwright") is not None:
        _ok("playwright", "module import ok")
        return True
    _fail("playwright", "module not found")
    return False


def _check_file(path: Path, label: str) -> bool:
    if path.is_file():
        _ok(label, str(path))
        return True
    _fail(label, str(path))
    return False


def _resolve_project(project: str, projects_root: Path) -> Path:
    candidate = Path(project).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (projects_root / project).resolve()


def _check_project_structure(project_path: Path, input_dirs: list[str]) -> bool:
    if not project_path.is_dir():
        _fail("project", f"missing: {project_path}")
        return False

    print(f"Project: {project_path}")
    has_input = False
    for name in input_dirs:
        exists = (project_path / name).is_dir()
        has_input = has_input or exists
        if exists:
            _ok(f"{name}/", str(project_path / name))
        else:
            _fail(f"{name}/", "missing")

    for name in ("scripts", "tables"):
        if (project_path / name).is_dir():
            _ok(f"{name}/", str(project_path / name))
        else:
            _warn(f"{name}/", "recommended")

    info_path = project_path / "project_info.md"
    if info_path.is_file():
        _ok("project_info.md", str(info_path))
    else:
        _warn("project_info.md", "recommended")

    return has_input


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether BIA-Brief is ready to run.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to run_config.yaml")
    parser.add_argument("--project", default="", help="Project id or project path to check")
    args = parser.parse_args()

    config = load_runner_config(args.config)
    runner_cfg = config.get("runner", {})
    projects_root = (REPO_ROOT / runner_cfg.get("projects_root", "projects")).resolve()
    input_dirs = runner_cfg.get("project_input_dirs", ["figures", "pics"])
    templates = runner_cfg.get("templates", {})

    print("=== BIA-Brief Doctor ===")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Config: {Path(args.config).resolve()}")
    print()

    ok = True
    ok &= _check_import("yaml", "pyyaml")
    ok &= _check_import("langchain_openai", "langchain_openai")
    ok &= _check_import("langchain_core", "langchain_core")
    ok &= _check_import("deepagents", "deepagents")
    ok &= _check_import("PIL", "pillow")
    ok &= _check_import("markdown", "markdown")
    ok &= _check_import("pypdf", "pypdf")
    ok &= _check_playwright()

    print()
    ok &= _check_file(REPO_ROOT / "run_config.yaml", "run_config.yaml")
    ok &= _check_file(REPO_ROOT / "src" / "Brief" / "config" / "config.yaml", "config.yaml")

    print()
    for key, rel_path in templates.items():
        ok &= _check_file(REPO_ROOT / rel_path, f"template[{key}]")

    print()
    if args.project:
        project_path = _resolve_project(args.project, projects_root)
        ok &= _check_project_structure(project_path, input_dirs)
    else:
        _warn("project", "not checked")

    print()
    if ok:
        _ok("result", "ready")
        return 0
    _fail("result", "not ready")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
