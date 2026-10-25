"""Public command-line interface for the installable BIA-Brief package."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from .pipeline.project_info_background import build_project_background
from .pipeline.review_gate import ReviewGate
from .pipeline.runner_config import DEFAULT_CONFIG, load_runner_config
from .pipeline.template_spec import TemplateSpec, resolve_template_spec
from .config.setup import interactive_setup, resolve_model_config_path


class _Tee:
    """Write to the live console and the batch log at the same time."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_project(value: str, projects_root: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (projects_root / value).resolve()


def _resolve_template(value: str, templates: dict[str, str]) -> Path:
    return _resolve_template_spec(value, templates).path


def _resolve_template_spec(value: str, templates: dict[str, str]) -> TemplateSpec:
    return resolve_template_spec(
        value,
        templates,
        package_root=_package_root(),
    )


def _safe_pdf_name(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', "_", title).strip(" ._")
    return f"{cleaned or 'report'}.pdf"


def _copy_delivery_pdf(pdf_path: str, title: str, delivery_dir: Path) -> Path | None:
    source = Path(pdf_path)
    if not source.is_file():
        return None
    delivery_dir.mkdir(parents=True, exist_ok=True)
    destination = delivery_dir / _safe_pdf_name(title)
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

    path = resolve_model_config_path(config_path)
    if path is None:
        raise FileNotFoundError(
            "Model config is required. Run bia-brief-setup once, or pass --config."
        )
    load_yaml_config(str(path))
    setup_LLMs()
    return llm_config


def setup_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Configure BIA-Brief models for future runs.")
    parser.add_argument("--output", default=None, help="Config path (default: ~/.bia-brief/config.yaml)")
    args = parser.parse_args(argv)
    path = interactive_setup(output_path=args.output)
    print(f"Saved model config: {path}")
    print("Future runs can omit --config and reuse this file.")
    return 0


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
    template_spec = _resolve_template_spec(
        template,
        runtime.get("templates", DEFAULT_CONFIG["runner"]["templates"]),
    )
    if template_spec.support_level in {"legacy", "experimental"}:
        print(
            f"Template note: {template_spec.key} is {template_spec.support_level} "
            f"({template_spec.display_name}).",
            file=sys.stderr,
        )
    project_id = args.project_id or project_path.name
    auto_approve = bool(runtime.get("auto_approve", True)) and not args.interactive_review

    try:
        llm_config = _load_models(args.config)
        background = args.background or build_project_background(
            project_path,
            project_id,
            analysis_profile=template_spec.body_profile,
        )
        if args.print_background:
            print(background)
            return 0

        from .core import Brief

        started = time.time()
        brief = Brief(
            chat_model=llm_config.MODELS["chat_model"],
            mmchat_model=llm_config.MODELS["mmchat_model"],
            review_gate=ReviewGate(
                auto_approve=auto_approve,
                timeout=int(runtime.get("review_timeout", 300)),
            ),
        )
        _, report = brief.Run(
            background=background,
            output_lang=args.lang or runtime.get("default_lang", "zh-CN"),
            project_path=str(project_path),
            report_template=str(template_spec.path),
            template_spec=template_spec,
            output_dir=str(runtime.get("project_output_dir", "output")),
            project_id=project_id,
        )
        if not args.no_delivery_copy:
            delivery_root = Path(runtime.get("deliverables_dir", "deliverables"))
            if not delivery_root.is_absolute():
                delivery_root = Path.cwd() / delivery_root
            copied = _copy_delivery_pdf(
                report.get("report_pdf_path", ""),
                report.get("report_title", "") or project_id,
                delivery_root,
            )
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
        console_stdout = _Tee(sys.stdout, captured) if args.interactive_review else captured
        console_stderr = _Tee(sys.stderr, captured) if args.interactive_review else captured
        with redirect_stdout(console_stdout), redirect_stderr(console_stderr):
            code = run_project_cli(cmd)
        output = captured.getvalue()
        if not args.interactive_review:
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
        parser.epilog = "Commands: setup, project, batch, doctor"
        parser.print_help()
        return 0
    command, rest = command_args[0], command_args[1:]
    if command == "setup":
        return setup_cli(rest)
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
