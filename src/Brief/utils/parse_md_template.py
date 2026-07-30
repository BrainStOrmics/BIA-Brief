from __future__ import annotations

import re
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import load_report_template_file


def _template_assets_root() -> Path:
    """Find template assets in a source checkout or an installed wheel."""
    source_assets = Path(__file__).resolve().parents[3] / "templates" / "assets"
    package_assets = Path(__file__).resolve().parents[1] / "resources" / "templates" / "assets"
    for candidate in (source_assets, package_assets):
        if candidate.exists():
            return candidate
    return source_assets


def _relative_path_from_report(path_text: str, report_output_dir: Path) -> str:
    source = Path(path_text).expanduser().resolve()
    return os.path.relpath(source, start=report_output_dir).replace("\\", "/")


def _build_template_context(
    cover_image_md_path: str,
    template_fields: dict[str, Any] | None = None,
) -> dict[str, str]:
    context = {
        "Cover_Report_Date": datetime.now().strftime("%Y-%m-%d"),
        "Cover_Image_Path": cover_image_md_path,
        "Cover_Report_Title": "",
        "Cover_Copyright_Text": "©2026All Rights Reserved",
    }
    if template_fields:
        for k, v in template_fields.items():
            context[k] = "" if v is None else str(v)
    if not context["Cover_Report_Title"]:
        context["Cover_Report_Title"] = context.get("report_title", "")
    return context


def render_report_markdown(
    *,
    report_template: str,
    project_id: str,
    project_path: str,
    output_lang: str,
    pic_abs_dirs: list[str],
    captions: list[dict[str, str]],
    section_summaries: list[dict[str, str]],
    conclusion: str,
    discussion: str,
    key_takeaways: list[str],
    template_fields: dict[str, Any] | None = None,
    output_path: str = "",
    output_filename: str = "auto_report.md",
) -> tuple[str, dict[str, Any]]:
    project_root = Path(project_path).expanduser().resolve()
    if output_path and output_path.startswith("/"):
        report_output_path = Path(output_path)
    elif output_path:
        report_output_path = project_root / output_path
    else:
        report_output_path = project_root / "local_tests" / "output" / output_filename
    report_output_dir = report_output_path.parent

    report_template_text, resolved_template_path = load_report_template_file(
        report_template=report_template,
        project_path=project_path,
    )

    # Build ordered items for report metadata
    caption_map = {item.get("image_path", ""): item.get("caption", "") for item in captions}
    section_map = {item.get("image_path", ""): item.get("section_summary", "") for item in section_summaries}
    ordered_items = [
        {
            "image_path": path,
            "image_md_path": _relative_path_from_report(path, report_output_dir),
            "caption": caption_map.get(path, ""),
            "section_summary": section_map.get(path, ""),
        }
        for path in pic_abs_dirs
    ]

    assets_root = _template_assets_root()
    cover_image_path = assets_root / "BGI_SY" / "pics" / "cover.png"
    cover_image_md_path = _relative_path_from_report(cover_image_path, report_output_dir)

    template_context = _build_template_context(
        cover_image_md_path=cover_image_md_path,
        template_fields=template_fields,
    )

    report_md = re.sub(
        r"{{\s*([^{}]+?)\s*}}",
        lambda match: str(template_context.get(match.group(1), "")),
        report_template_text,
    )

    # Rewrite template-relative static image paths (./BGI_SY/...) to output-relative
    # paths so they resolve correctly from the rendered report's location.
    # In the template file itself, ./BGI_SY/ works (relative to templates/).
    # After rendering to <project>/output/report.md, ./BGI_SY/ would break, so
    # we rewrite it to the correct relative path from the output directory.
    bgi_sy_rel = _relative_path_from_report(str(assets_root / "BGI_SY"), report_output_dir)
    report_md = report_md.replace("./BGI_SY/", f"{bgi_sy_rel}/")


    report_dict: dict[str, Any] = {
        "project_id": project_id,
        "project_path": project_path,
        "output_lang": output_lang,
        "template_path": resolved_template_path,
        "images": ordered_items,
        "discussion": discussion,
        "conclusion": conclusion,
        "key_takeaways": key_takeaways,
        "template_context": template_context,
        "report_output_path": str(report_output_path),
        "report_template_path": resolved_template_path,
    }

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(report_md, encoding="utf-8")

    return report_md, report_dict
