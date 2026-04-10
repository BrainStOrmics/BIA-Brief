from __future__ import annotations

import re
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import load_report_template_file


def _relative_path_from_report(path_text: str, report_output_dir: Path) -> str:
    source = Path(path_text).expanduser().resolve()
    return os.path.relpath(source, start=report_output_dir).replace("\\", "/")


def _build_ordered_items(
    pic_abs_dirs: list[str],
    captions: list[dict[str, str]],
    section_summaries: list[dict[str, str]],
    report_output_dir: Path,
) -> list[dict[str, str]]:
    caption_map = {
        item.get("image_path", ""): item.get("caption", "")
        for item in captions
    }
    section_map = {
        item.get("image_path", ""): item.get("section_summary", "")
        for item in section_summaries
    }

    ordered_items: list[dict[str, str]] = []
    for image_path in pic_abs_dirs:
        ordered_items.append(
            {
                "image_path": image_path,
                "image_md_path": _relative_path_from_report(image_path, report_output_dir),
                "caption": caption_map.get(image_path, ""),
                "section_summary": section_map.get(image_path, ""),
            }
        )

    return ordered_items


def _build_template_context(
    *,
    project_id: str,
    output_lang: str,
    ordered_items: list[dict[str, str]],
    conclusion: str,
    discussion: str,
    key_takeaways: list[str],
    cover_image_md_path: str,
    template_fields: dict[str, Any] | None,
) -> dict[str, str]:
    key_takeaways_text = "\n".join(
        [f"- {item}" for item in key_takeaways if item]
    )

    auto_context: dict[str, str] = {
        "Cover_Contract_ID": project_id,
        "Cover_Report_Date": datetime.now().strftime("%Y-%m-%d"),
        "Cover_Image_Path": cover_image_md_path,
        "Cover_Report_Title": "",
        "Cover_Copyright_Text": f"©{datetime.now().year}All Rights Reserved",
        "Output_Lang": output_lang,
        "Discussion_Content": discussion,
        "Conclusion_Content": conclusion,
        "Key_Takeaways_Text": key_takeaways_text,
        "References_Block": "",
    }

    # Provide section/image placeholders based on discovered figures.
    for idx, item in enumerate(ordered_items, start=1):
        auto_context[f"Section_{idx:02d}_Image_Path"] = item.get("image_md_path", "")
        auto_context[f"Section_{idx:02d}_Caption"] = item.get("caption", "")
        auto_context[f"Section_{idx:02d}_Content"] = item.get("section_summary", "")

    # Backward compatibility with old placeholder names in templates.
    if ordered_items:
        auto_context["Pic_01_path"] = ordered_items[0].get("image_md_path", "")
        auto_context["Caption_01"] = ordered_items[0].get("caption", "")
    if len(ordered_items) > 1:
        auto_context["Pic_02_path"] = ordered_items[1].get("image_md_path", "")
        auto_context["Caption_02"] = ordered_items[1].get("caption", "")
    if len(ordered_items) > 2:
        auto_context["Pic_03_path"] = ordered_items[2].get("image_md_path", "")
        auto_context["Caption_03"] = ordered_items[2].get("caption", "")

    additional_blocks: list[str] = []
    for item in ordered_items:
        additional_blocks.append(
            "\n".join(
                [
                    f"![Image]({item.get('image_md_path', '')})" if item.get("image_md_path") else "",
                    item.get("caption", ""),
                    item.get("section_summary", ""),
                ]
            ).strip()
        )
    auto_context["Image_Summaries_Block"] = "\n\n".join([block for block in additional_blocks if block])

    user_context = {k: "" if v is None else str(v) for k, v in (template_fields or {}).items()}
    auto_context.update(user_context)

    if not auto_context.get("Cover_Report_Title"):
        auto_context["Cover_Report_Title"] = auto_context.get("report_title", project_id)
    if not auto_context.get("Cover_Copyright_Text"):
        auto_context["Cover_Copyright_Text"] = f"©{datetime.now().year}All Rights Reserved"
    if not auto_context.get("References_Block"):
        auto_context["References_Block"] = ""

    return auto_context


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
    output_filename: str = "auto_report.md",
) -> tuple[str, dict[str, Any]]:
    report_output_path = Path(project_path).expanduser().resolve() / "local_tests" / "output" / output_filename
    report_output_dir = report_output_path.parent

    report_template_text, resolved_template_path = load_report_template_file(
        report_template=report_template,
        project_path=project_path,
    )

    ordered_items = _build_ordered_items(
        pic_abs_dirs=pic_abs_dirs,
        captions=captions,
        section_summaries=section_summaries,
        report_output_dir=report_output_dir,
    )

    cover_image_path = Path(project_path).expanduser().resolve() / "template" / "BGI_SY" / "pics" / "cover.png"
    cover_image_md_path = _relative_path_from_report(cover_image_path, report_output_dir)

    template_context = _build_template_context(
        project_id=project_id,
        output_lang=output_lang,
        ordered_items=ordered_items,
        conclusion=conclusion,
        discussion=discussion,
        key_takeaways=key_takeaways,
        cover_image_md_path=cover_image_md_path,
        template_fields=template_fields,
    )

    report_md = re.sub(
        r"{{\s*([^{}]+?)\s*}}",
        lambda match: str(template_context.get(match.group(1), "")),
        report_template_text,
    )

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
    }

    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(report_md, encoding="utf-8")

    report_dict["report_output_path"] = str(report_output_path)
    report_dict["report_template_path"] = resolved_template_path

    return report_md, report_dict