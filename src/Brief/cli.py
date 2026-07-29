"""Public command-line interface for the installable BIA-Brief package."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from .pipeline.project_info_background import build_project_background
from .pipeline.runner_config import DEFAULT_CONFIG, load_runner_config


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_project(value: str, projects_root: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (projects_root / value).resolve()


def _resolve_template(value: str, templates: dict[str, str]) -> Path:
    configured = templates.get(value, value)
    candidate = Path(configured).expanduser()
    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()
    if candidate.is_file():
        return candidate.resolve()
    repo_candidate = Path.cwd() / candidate
    if repo_candidate.is_file():
        return repo_candidate.resolve()
    packaged = _package_root() / "resources" / "templates" / value / "report.md"
    if packaged.is_file():
        return packaged.resolve()
    raise FileNotFoundError(f"Template not found: {value}")


def _read_report_title(project_path: Path) -> str:
    info = project_path / "project_info.md"
    if info.is_file():
        for line in info.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^报告名称\s*[:：]\s*(.*)$", line)
            if match and match.group(1).strip():
                return match.group(1).strip()
    return project_path.name


def _safe_pdf_name(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', "_", title).strip(" ._")
    return f"{cleaned or 'report'}.pdf"


def _copy_delivery_pdf(pdf_path: str, project_path: Path, delivery_dir: Path) -> Path | None:
    source = Path(pdf_path)
    if not source.is_file():
        return None
    delivery_dir.mkdir(parents=True, exist_ok=True)
    destination = delivery_dir / _safe_pdf_name(_read_report_title(project_path))
    shutil.copy2(source, destination)
    return destination


def _check_project(project_path: Path, input_dirs: list[str]) -> bool:
    if not project_path.is_dir():
        print(f"Project directory not found: {project_path}", file=sys.stderr)
        return False
    if not any((project_path / name).is_dir() for name in input_dirs):
        print(f"Project must contain one of {input_dirs}: {project_path}", file=sys.stderr)
        return False
    return True


def _load_models(config_path: str | None):
    from .config.config import llm_config, load_yaml_config
    from .utils.setup import setup_LLMs

    configured = config_path or os.environ.get("BIA_BRIEF_CONFIG")
    path = Path(configured).expanduser() if configured else None
    if path is not None:
        if not path.is_file():
            raise FileNotFoundError(f"Model config not found: {path}")
        load_yaml_config(str(path))
    else:
        default = _package_root() / "config" / "config.yaml"
        if not default.is_file():
            raise FileNotFoundError(
                "Model config is required. Pass --config or set BIA_BRIEF_CONFIG."
            )
        load_yaml_config(str(default))
    setup_LLMs()
    return llm_config


def run_project_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one BIA-Brief report.")
    parser.add_argument("project", help="Project id or project directory")
    parser.add_argument("--template", default=None, help="Template key or path")
    parser.add_argument("--background", default="", help="Research background")
    parser.add_argument("--print-background", action="store_true")
    parser.add_argument("--lang", default=None)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--runner-config", default=None, help="Path to runner YAML")
    parser.add_argument("--config", default=None, help="Path to model config YAML")
    parser.add_argument("--interactive-review", action="store_true")
    parser.add_argument("--no-delivery-copy", action="store_true")
    args = parser.parse_args(argv)

    runtime = load_runner_config(args.runner_config)["runner"]
    projects_root = Path(runtime.get("projects_root", "projects")).expanduser()
    if not projects_root.is_absolute():
        projects_root = Path.cwd() / projects_root
    project_path = _resolve_project(args.project, projects_root)
    if not _check_project(project_path, runtime.get("project_input_dirs", ["figures", "pics"])):
        return 1

    template = args.template or runtime.get("default_template", "scRNA")
    template_path = _resolve_template(template, runtime.get("templates", DEFAULT_CONFIG["runner"]["templates"]))
    project_id = args.project_id or project_path.name
    if runtime.get("auto_approve", True) and not args.interactive_review:
        os.environ.setdefault("BRIEF_AUTO_APPROVE", "1")

    try:
        llm_config = _load_models(args.config)
        background = args.background or build_project_background(project_path, project_id)
        if args.print_background:
            print(background)
            return 0

        from .core import Brief

        started = time.time()
        brief = Brief(chat_model=llm_config.MODELS["chat_model"], mmchat_model=llm_config.MODELS["mmchat_model"])
        _, report = brief.Run(
            background=background,
            output_lang=args.lang or runtime.get("default_lang", "zh-CN"),
            project_path=str(project_path),
            report_template=str(template_path),
            output_dir=str(runtime.get("project_output_dir", "output")),
            project_id=project_id,
        )
        if not args.no_delivery_copy:
            delivery_root = Path(runtime.get("deliverables_dir", "deliverables"))
            if not delivery_root.is_absolute():
                delivery_root = Path.cwd() / delivery_root
            copied = _copy_delivery_pdf(report.get("report_pdf_path", ""), project_path, delivery_root)
            if copied:
                print(f"delivery.pdf: {copied}")
        print(f"Completed in {time.time() - started:.1f}s")
        for key in ("report_output_path", "report_pdf_path", "report_tex_path"):
            print(f"{key}: {report.get(key, '')}")
        return 0
    except Exception as exc:
        print(f"Report generation failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


def run_batch_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate BIA-Brief reports in batch.")
    parser.add_argument("projects", nargs="*", help="Project ids")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--runner-config", default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--template", default=None)
    parser.add_argument("--lang", default=None)
    parser.add_argument("--interactive-review", action="store_true")
    parser.add_argument("--no-delivery-copy", action="store_true")
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args(argv)
    runtime = load_runner_config(args.runner_config)["runner"]
    root = Path(runtime.get("projects_root", "projects"))
    if not root.is_absolute():
        root = Path.cwd() / root
    projects = args.projects
    if args.all:
        dirs = runtime.get("project_input_dirs", ["figures", "pics"])
        projects = [p.name for p in sorted(root.iterdir()) if p.is_dir() and any((p / d).is_dir() for d in dirs)]
    if not projects:
        print("No projects selected. Use --all or pass project ids.", file=sys.stderr)
        return 2
    failed = 0
    log_root = Path(runtime.get("batch_log_dir", "logs/batch"))
    if not log_root.is_absolute():
        log_root = Path.cwd() / log_root
    batch_id = time.strftime("%Y%m%d_%H%M%S")
    for project in projects:
        cmd = [project]
        for flag, value in (("--runner-config", args.runner_config), ("--config", args.config), ("--template", args.template), ("--lang", args.lang)):
            if value:
                cmd.extend([flag, value])
        if args.interactive_review:
            cmd.append("--interactive-review")
        if args.no_delivery_copy:
            cmd.append("--no-delivery-copy")
        log_path = log_root / f"{batch_id}_{project}.log"
        log_root.mkdir(parents=True, exist_ok=True)
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO
        captured = StringIO()
        with redirect_stdout(captured), redirect_stderr(captured):
            code = run_project_cli(cmd)
        output = captured.getvalue()
        print(output, end="")
        log_path.write_text(output, encoding="utf-8")
        if code != 0:
            failed += 1
            if args.stop_on_failure:
                break
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    command_args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="BIA-Brief report generation package")
    if not command_args or command_args[0] in {"-h", "--help"}:
        parser.epilog = "Commands: project, batch, doctor"
        parser.print_help()
        return 0
    command, rest = command_args[0], command_args[1:]
    if command == "project":
        return run_project_cli(rest)
    if command == "batch":
        return run_batch_cli(rest)
    if command == "doctor":
        from .doctor import main as doctor_main
        return doctor_main(rest)
    parser.error(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
