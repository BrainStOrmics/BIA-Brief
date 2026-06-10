"""BIA-Brief CLI: single entry point for indexer, postprocessing, and export.

Usage:
    python brief_cli.py index <project_path> --config config.yaml [--background "..."] [--lang zh-CN]
    python brief_cli.py postprocess --input report.md --index index.md [--lang zh-CN]
    python brief_cli.py export --input report.md --template repo_temp.md [--title "..."] [--project-id p01]
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

# Auto-locate skill directory and add src/ to path
SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sub-command: index
# ---------------------------------------------------------------------------

def cmd_index(args):
    """Run the indexer to scan project files and generate captions."""
    import yaml
    from langchain_openai import ChatOpenAI
    from Brief.indexer import index_project

    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    mm_cfg = cfg.get("llm_config", {}).get("MULTIMODAL_CHAT_MODEL_API", {})
    enable_thinking = cfg.get("llm_config", {}).get("ENABLE_THINKING", True)
    enable_search = cfg.get("llm_config", {}).get("ENABLE_SEARCH", False)

    mmchat_model = ChatOpenAI(
        api_key=mm_cfg.get("api", ""),
        base_url=mm_cfg.get("url", ""),
        model=mm_cfg.get("model", ""),
        temperature=0,
        max_retries=3,
        extra_body={
            "enable_thinking": enable_thinking,
            "enable_search": enable_search,
        },
    )

    # Optional: use chat model for overview generation
    chat_model = None
    chat_cfg = cfg.get("llm_config", {}).get("CHAT_MODEL_API", {})
    if chat_cfg.get("api"):
        chat_model = ChatOpenAI(
            api_key=chat_cfg.get("api", ""),
            base_url=chat_cfg.get("url", ""),
            model=chat_cfg.get("model", ""),
            temperature=0,
            max_retries=3,
            extra_body={
                "enable_thinking": enable_thinking,
                "enable_search": enable_search,
            },
        )

    output_dir = cfg.get("brief_config", {}).get("OUTPUT_DIR", "output")
    project_path = Path(args.project_path).resolve()
    output_path = str(project_path / output_dir / "report.md")

    background = args.background or ""
    if not background:
        # Try to read from project's background file
        bg_file = project_path / "background.txt"
        if bg_file.exists():
            background = bg_file.read_text(encoding="utf-8").strip()
            logger.info("Loaded background from %s", bg_file)

    index_path = index_project(
        project_path=str(project_path),
        mmchat_model=mmchat_model,
        background=background,
        output_lang=args.lang,
        output_path=output_path,
        chat_model=chat_model,
    )
    logger.info("Index generated: %s", index_path)


# ---------------------------------------------------------------------------
# Sub-command: postprocess
# ---------------------------------------------------------------------------

def _build_figure_items(index_path: str, project_path: str, output_path: str) -> list[dict]:
    """Build figure items list from index.md for post-processing."""
    index_content = Path(index_path).read_text(encoding="utf-8")
    report_output_dir = Path(output_path).parent

    figure_items = []
    caption_pattern = re.compile(
        r"### Figure (\d+): (.+?)(?:\n(.*?))?(?=\n### Figure|\n## |\Z)",
        re.DOTALL,
    )

    # Get image paths from Images table
    image_paths = {}
    image_md_paths = {}
    in_images_section = False
    for line in index_content.splitlines():
        if line.strip() == "## Images":
            in_images_section = True
            continue
        if line.strip().startswith("## "):
            in_images_section = False
            continue
        if in_images_section:
            match = re.match(r"\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|", line)
            if match:
                idx = match.group(1)
                rel_path = match.group(3)
                abs_path = str((report_output_dir / rel_path).resolve())
                image_paths[idx] = abs_path
                image_md_paths[idx] = rel_path

    # Parse captions
    for match in caption_pattern.finditer(index_content):
        idx = match.group(1)
        caption_title = match.group(2).strip()
        body_and_summary = match.group(3).strip() if match.group(3) else ""

        caption_body = ""
        section_summary = ""
        if "**Section Summary:**" in body_and_summary:
            parts = body_and_summary.split("**Section Summary:**", 1)
            caption_body = parts[0].strip()
            section_summary = parts[1].strip()
        else:
            caption_body = body_and_summary

        image_path = image_paths.get(idx, "")
        image_md_path = image_md_paths.get(idx, "")

        figure_items.append({
            "index": idx,
            "image_path": image_path,
            "image_md_path": image_md_path,
            "caption_title": caption_title,
            "caption_body": caption_body,
            "caption": f"{caption_title} {caption_body}".strip(),
            "section_summary": section_summary,
        })

    return figure_items


def cmd_postprocess(args):
    """Run post-processing: embed figures, renumber, wrap paragraphs."""
    from Brief.utils.postprocess import (
        embed_figures_in_body,
        wrap_body_paragraphs,
    )

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    project_path = str(Path(args.input).parent.parent.resolve())
    figure_items = _build_figure_items(args.index, project_path, args.input)

    raw_md = input_path.read_text(encoding="utf-8")

    # Embed missing figures + renumber
    report_md = embed_figures_in_body(raw_md, figure_items, args.lang)
    # Wrap paragraphs with indentation
    report_md = wrap_body_paragraphs(report_md)

    input_path.write_text(report_md, encoding="utf-8")
    logger.info("Post-processed: %s", input_path)


# ---------------------------------------------------------------------------
# Sub-command: export
# ---------------------------------------------------------------------------

def cmd_export(args):
    """Run template rendering + PDF + LaTeX export."""
    from Brief.utils.postprocess import build_template_fields
    from Brief.utils.parse_md_template import render_report_markdown
    from Brief.utils.md_to_pdf import build_pdf_from_markdown
    from Brief.utils.md_to_latex import build_latex_from_markdown

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    report_md = input_path.read_text(encoding="utf-8")

    # Determine title
    title_path = input_path.with_suffix(input_path.suffix + ".title")
    if args.title:
        report_title = args.title
        title_path.write_text(report_title, encoding="utf-8")
    elif title_path.exists():
        report_title = title_path.read_text(encoding="utf-8").strip()
    else:
        report_title = "生物信息学分析报告"

    # Build template fields
    template_fields = build_template_fields({"body_md": report_md}, report_title=report_title)

    # Project path: parent of output dir
    project_path = str(input_path.parent.parent.resolve())
    output_path = str(input_path)

    # Render template
    report_md, report_dict = render_report_markdown(
        report_template=args.template,
        project_id=args.project_id,
        project_path=project_path,
        output_path=output_path,
        output_lang=args.lang,
        pic_abs_dirs=[],
        captions=[],
        section_summaries=[],
        conclusion="",
        discussion="",
        key_takeaways=[],
        template_fields=template_fields,
    )
    logger.info("Template rendered: %s", output_path)

    # PDF export
    pdf_path = str(input_path.with_suffix(".pdf"))
    try:
        build_pdf_from_markdown(input_path, Path(pdf_path))
        logger.info("PDF generated: %s", pdf_path)
    except Exception:
        logger.exception("PDF conversion failed")

    # LaTeX export
    tex_path = str(input_path.with_suffix(".tex"))
    try:
        build_latex_from_markdown(input_path, Path(tex_path))
        logger.info("LaTeX generated: %s", tex_path)
    except Exception:
        logger.exception("LaTeX conversion failed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BIA-Brief CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # index
    p_index = subparsers.add_parser("index", help="Run indexer")
    p_index.add_argument("project_path", help="Project directory path")
    p_index.add_argument("--config", required=True, help="Path to config.yaml")
    p_index.add_argument("--background", default="", help="Research background text")
    p_index.add_argument("--lang", default="zh-CN", help="Output language")
    p_index.set_defaults(func=cmd_index)

    # postprocess
    p_post = subparsers.add_parser("postprocess", help="Post-process report")
    p_post.add_argument("--input", required=True, help="Path to report.md")
    p_post.add_argument("--index", required=True, help="Path to index.md")
    p_post.add_argument("--lang", default="zh-CN", help="Output language")
    p_post.set_defaults(func=cmd_postprocess)

    # export
    p_export = subparsers.add_parser("export", help="Template render + PDF/LaTeX")
    p_export.add_argument("--input", required=True, help="Path to report.md")
    p_export.add_argument("--template", required=True, help="Path to report template")
    p_export.add_argument("--title", default="", help="Report title")
    p_export.add_argument("--project-id", default="p01", help="Project ID")
    p_export.add_argument("--lang", default="zh-CN", help="Output language")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
