#!/usr/bin/env python3
"""Run BIA-Brief reports for multiple projects."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_PROJECT = REPO_ROOT / "scripts" / "run_project.py"
sys.path.insert(0, str(REPO_ROOT / "src"))

from Brief.pipeline.runner_config import DEFAULT_CONFIG_PATH, load_runner_config


def _discover_projects(projects_root: Path, input_dirs: list[str]) -> list[str]:
    if not projects_root.is_dir():
        return []
    projects = []
    for path in sorted(projects_root.iterdir()):
        if path.is_dir() and any((path / name).is_dir() for name in input_dirs):
            projects.append(path.name)
    return projects


def _build_command(args: argparse.Namespace, project: str) -> list[str]:
    command = [
        sys.executable,
        str(RUN_PROJECT),
        project,
        "--config",
        args.config,
        "--template",
        args.template,
        "--lang",
        args.lang,
    ]
    if args.interactive_review:
        command.append("--interactive-review")
    if args.no_delivery_copy:
        command.append("--no-delivery-copy")
    return command


def _log_path(project: str, batch_log_dir: Path, batch_id: str) -> Path:
    batch_log_dir.mkdir(parents=True, exist_ok=True)
    return batch_log_dir / f"{batch_id}_{project}.log"


def _run_with_log(command: list[str], log_path: Path, env: dict[str, str]) -> int:
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
            log_file.write(line)
            log_file.flush()
        return proc.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate BIA-Brief reports for multiple projects.")
    parser.add_argument(
        "projects",
        nargs="*",
        help="Project ids under projects/. Omit with --all to run every discovered project.",
    )
    parser.add_argument("--all", action="store_true", help="Run every project under projects/.")
    parser.add_argument(
        "--template",
        default=None,
        help="Template key (scRNA/spatial) or template path. Default comes from run_config.yaml.",
    )
    parser.add_argument("--lang", default=None, help="Output language")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to run_config.yaml",
    )
    parser.add_argument(
        "--interactive-review",
        action="store_true",
        help="Keep HITL review prompts instead of auto-approving them",
    )
    parser.add_argument(
        "--no-delivery-copy",
        action="store_true",
        help="Do not copy generated PDFs to deliverables/",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop the batch after the first failed project",
    )
    args = parser.parse_args()

    runtime_config = load_runner_config(args.config)
    runner_cfg = runtime_config.get("runner", {})
    projects_root = (REPO_ROOT / runner_cfg.get("projects_root", "projects")).resolve()
    input_dirs = runner_cfg.get("project_input_dirs", ["figures", "pics"])
    batch_log_dir = (REPO_ROOT / runner_cfg.get("batch_log_dir", "logs/batch")).resolve()
    template_name = args.template or runner_cfg.get("default_template", "scRNA")
    output_lang = args.lang or runner_cfg.get("default_lang", "zh-CN")

    if args.all:
        projects = _discover_projects(projects_root, input_dirs)
    else:
        projects = args.projects

    if not projects:
        print("No projects selected. Use --all or pass project ids.", file=sys.stderr)
        return 2

    env = os.environ.copy()
    if bool(runner_cfg.get("auto_approve", True)) and not args.interactive_review:
        env.setdefault("BRIEF_AUTO_APPROVE", "1")
    env.setdefault("PYTHONUTF8", "1")

    print("\n" + "=" * 60)
    print(f"Batch projects: {', '.join(projects)}")
    print("=" * 60 + "\n")

    results: list[tuple[str, int, float, Path]] = []
    batch_start = time.time()
    batch_id = time.strftime("%Y%m%d_%H%M%S")
    log_root = batch_log_dir

    for project in projects:
        print("\n" + "-" * 60)
        print(f"Project: {project}")
        print("-" * 60 + "\n")

        start = time.time()
        log_path = _log_path(project, log_root, batch_id)
        command_args = argparse.Namespace(
            config=args.config,
            template=template_name,
            lang=output_lang,
            interactive_review=args.interactive_review,
            no_delivery_copy=args.no_delivery_copy,
        )
        completed = _run_with_log(_build_command(command_args, project), log_path, env)
        elapsed = time.time() - start
        results.append((project, completed, elapsed, log_path))

        if completed != 0 and args.stop_on_failure:
            break

    print("\n" + "=" * 60)
    print("Batch summary")
    print("=" * 60)
    failed = 0
    for project, returncode, elapsed, log_path in results:
        status = "OK" if returncode == 0 else f"FAIL({returncode})"
        if returncode != 0:
            failed += 1
        print(f"  {project:30s} | {status:8s} | {elapsed:.1f}s | {log_path}")
    print(f"\nTotal: {time.time() - batch_start:.1f}s")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
