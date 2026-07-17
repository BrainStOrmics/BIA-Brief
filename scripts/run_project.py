#!/usr/bin/env python3
"""Run the BIA-Brief pipeline for one project."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

from Brief.pipeline.runner_config import DEFAULT_CONFIG, DEFAULT_CONFIG_PATH, load_runner_config
from Brief.pipeline.project_info_background import build_project_background


def _resolve_project(project: str, projects_root: Path) -> Path:
    candidate = Path(project).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate.resolve()
    return (projects_root / project).resolve()


def _resolve_template(template: str, templates: dict[str, str]) -> Path:
    if template in templates:
        return (REPO_ROOT / templates[template]).resolve()
    candidate = Path(template).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (REPO_ROOT / candidate).resolve()


def _read_report_title(project_path: Path) -> str:
    info_path = project_path / "project_info.md"
    if info_path.is_file():
        for line in info_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("报告名称"):
                title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                if title:
                    return title
    return project_path.name


def _safe_pdf_name(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\r\n\t]+', "_", title).strip(" ._")
    return f"{cleaned or 'report'}.pdf"


def _copy_delivery_pdf(pdf_path: str, project_path: Path) -> Path | None:
    if not pdf_path:
        return None
    source = Path(pdf_path)
    if not source.exists():
        return None
    delivery_dir = REPO_ROOT / "deliverables"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    title = _read_report_title(project_path)
    destination = delivery_dir / _safe_pdf_name(title)
    shutil.copy2(source, destination)
    return destination


def _check_project_structure(project_path: Path, input_dirs: list[str]) -> bool:
    print("Project structure check:")
    has_input = False
    for name in input_dirs:
        exists = (project_path / name).is_dir()
        has_input = has_input or exists
        status = "OK" if exists else "MISS"
        print(f"  {status:4s} {name}/")

    for name in ("scripts", "tables"):
        exists = (project_path / name).is_dir()
        status = "OK" if exists else "WARN"
        suffix = "" if exists else " (recommended)"
        print(f"  {status:4s} {name}/{suffix}")

    project_info = project_path / "project_info.md"
    status = "OK" if project_info.is_file() else "WARN"
    suffix = "" if project_info.is_file() else " (recommended)"
    print(f"  {status:4s} project_info.md{suffix}")
    return has_input


def _fill_project_intro(project_path: Path, chat_model) -> None:
    """Generate 项目简介 via LLM if the field is empty in project_info.md."""
    info_path = project_path / "project_info.md"
    if not info_path.is_file():
        return

    text = info_path.read_text(encoding="utf-8")
    m = re.search(r"^项目简介\s*[:：]\s*(\S.*?)$", text, re.MULTILINE)
    if m and m.group(1).strip():
        return  # Already has content

    fields = {}
    for key in ("项目名称", "报告名称", "物种", "样本数量", "测序技术"):
        m2 = re.search(rf"^{re.escape(key)}\s*[:：]\s*(.*)$", text, re.MULTILINE)
        if m2 and m2.group(1).strip():
            fields[key] = m2.group(1).strip()

    prompt_parts = ["根据以下项目信息生成一段简洁的项目简介，说明研究目的和背景："]
    for k, v in fields.items():
        prompt_parts.append(f"{k}：{v}")
    prompt_parts.append("\n请直接输出一句话简介，不要前缀和引号。")
    prompt = "\n".join(prompt_parts)

    try:
        result = chat_model.invoke([{"role": "user", "content": prompt}])
        intro = result.content.strip().strip("\"'")
        text = re.sub(
            r"^(项目简介\s*[:：]).*$",
            f"\\1{intro}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        info_path.write_text(text, encoding="utf-8")
        print(f"  [auto] 项目简介已生成并写入 {info_path.name}")
    except Exception as exc:
        print(f"  [warn] 项目简介自动生成失败: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one BIA-Brief report.")
    parser.add_argument("project", help="Project id under projects/ or an explicit project path")
    parser.add_argument(
        "--template",
        default=None,
        help="Template key (scRNA/spatial) or template path. Default comes from run_config.yaml.",
    )
    parser.add_argument("--background", default="", help="Research background text")
    parser.add_argument(
        "--print-background",
        action="store_true",
        help="Print the background that would be sent to the report pipeline, then exit.",
    )
    parser.add_argument("--lang", default=None, help="Output language")
    parser.add_argument("--project-id", default="", help="Override project id")
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
        help="Do not copy the generated PDF to the repository root deliverables/ folder",
    )
    args = parser.parse_args()

    runtime_config = load_runner_config(args.config)
    runtime_cfg = runtime_config.get("runner", {})
    projects_root = (REPO_ROOT / runtime_cfg.get("projects_root", "projects")).resolve()
    input_dirs = runtime_cfg.get("project_input_dirs", ["figures", "pics"])
    templates = runtime_cfg.get("templates", DEFAULT_CONFIG["runner"]["templates"])
    template_name = args.template or runtime_cfg.get("default_template", "scRNA")
    output_lang = args.lang or runtime_cfg.get("default_lang", "zh-CN")

    project_path = _resolve_project(args.project, projects_root)
    project_id = args.project_id or project_path.name
    template_path = _resolve_template(template_name, templates)

    if not project_path.is_dir():
        print(f"Project directory not found: {project_path}", file=sys.stderr)
        return 1
    if not template_path.is_file():
        print(f"Template file not found: {template_path}", file=sys.stderr)
        return 1
    if not _check_project_structure(project_path, input_dirs):
        print(f"Project must contain one of {input_dirs}: {project_path}", file=sys.stderr)
        return 1

    auto_approve = bool(runtime_cfg.get("auto_approve", True))
    if auto_approve and not args.interactive_review:
        os.environ.setdefault("BRIEF_AUTO_APPROVE", "1")

    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(REPO_ROOT / "src"))

    from Brief.utils.setup import setup_brief
    setup_brief()

    from Brief.config.config import llm_config
    from langchain_openai import ChatOpenAI

    # Auto-fill 项目简介 via LLM if empty
    chat_model: ChatOpenAI = llm_config.MODELS["chat_model"]
    _fill_project_intro(project_path, chat_model)

    background = args.background or build_project_background(project_path, project_id)
    if args.print_background:
        print(background)
        return 0

    from Brief.core import Brief

    print("\n" + "=" * 60)
    print(f"Generating report: {project_id}")
    print(f"Project: {project_path}")
    print(f"Template: {template_path}")
    print("=" * 60 + "\n")

    start_time = time.time()
    try:
        brief = Brief(
            chat_model=llm_config.MODELS["chat_model"],
            mmchat_model=llm_config.MODELS["mmchat_model"],
        )
        _, report_dict = brief.Run(
            background=background,
            output_lang=output_lang,
            project_path=str(project_path),
            report_template=str(template_path),
            output_dir=str(runtime_cfg.get("project_output_dir", "output")),
            project_id=project_id,
        )
    except Exception as exc:
        elapsed = time.time() - start_time
        print(f"\nFailed ({elapsed:.1f}s): {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    report_md_path = Path(report_dict.get("report_output_path", ""))
    delivery_pdf = None
    if not args.no_delivery_copy:
        delivery_pdf = _copy_delivery_pdf(report_dict.get("report_pdf_path", ""), project_path)

    elapsed = time.time() - start_time
    print(f"\nDone ({elapsed:.1f}s)")
    print(f"  report.md: {report_dict.get('report_output_path', '')}")
    print(f"  report.pdf: {report_dict.get('report_pdf_path', '')}")
    print(f"  report.tex: {report_dict.get('report_tex_path', '')}")
    if delivery_pdf:
        print(f"  delivery.pdf: {delivery_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
