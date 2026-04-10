import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Type, TypedDict

from ..prompts import load_prompt_template
from ..utils.prase_md_template import render_report_markdown

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)


SUMMARY_HEADING_PATTERN = re.compile(
    r"(?ms)^\s{0,3}#{1,6}\s*(?:摘要|Abstract)\s*$.*?(?=^\s{0,3}#{1,6}\s+|\Z)"
)

REFERENCE_HEADING_PATTERN = re.compile(
    r"(?m)^\s{0,3}#{1,6}\s*(?:\d+(?:\.\d+)*)?\s*(?:参考文献|References)\s*$"
)

FIGURE_CAPTION_IMAGE_PATTERN = re.compile(
    r"(?ms)(<p\s+align='center'>.*?</p>\s*<p\s+align='center'>.*?</p>\s*)!\[[^\]]*\]\((?P<path>[^)]+)\)"
)

REF_BLOCK_TITLE_PATTERN = re.compile(r"(?is)<h2 class='references-title'>\s*(?:参考文献|References)\s*</h2>\s*")


def _strip_summary_section(body_content: str) -> str:
    if not body_content:
        return ""
    cleaned = SUMMARY_HEADING_PATTERN.sub("", body_content)
    return cleaned.lstrip()


def _strip_reference_section(body_content: str) -> str:
    if not body_content:
        return ""
    parts = REFERENCE_HEADING_PATTERN.split(body_content, maxsplit=1)
    if len(parts) == 2:
        return parts[0].rstrip()
    return body_content.rstrip()


def _move_figure_images_below_captions(body_content: str, figure_items: list[dict[str, str]]) -> str:
    if not body_content or not figure_items:
        return body_content

    updated = body_content
    for item in figure_items:
        image_md_path = str(item.get("image_md_path", "")).strip()
        if not image_md_path:
            continue

        image_pattern = re.compile(
            rf"(?ms)(<p\s+align='center'>.*?</p>\s*<p\s+align='center'>.*?</p>\s*)!\[[^\]]*\]\({re.escape(image_md_path)}\)"
        )

        def _swap(match: re.Match[str]) -> str:
            caption_block = match.group(1).rstrip()
            figure_index = str(item.get("index", "Figure")).strip() or "Figure"
            return f"![Figure {figure_index}]({image_md_path})\n\n{caption_block}"

        updated = image_pattern.sub(_swap, updated, count=1)

    return updated


def _strip_summary_toc_entry(toc_block: str) -> str:
    if not toc_block:
        return ""

    line_pattern = re.compile(
        r"(?is)<div class='toc-line[^>]*>\s*"
        r"<span class='toc-item'>\s*(?:\d+(?:\.\d+)*)?\s*(?:摘要|Abstract)\s*</span>"
        r".*?</div>\s*"
    )
    return line_pattern.sub("", toc_block)


def _strip_reference_block_title(references_block: str) -> str:
    if not references_block:
        return ""
    return REF_BLOCK_TITLE_PATTERN.sub("", references_block).lstrip()


def _append_missing_figures(body_content: str, figure_items: list[dict[str, str]], output_lang: str) -> str:
    if not figure_items:
        return body_content

    missing_items: list[dict[str, str]] = []
    for item in figure_items:
        image_md_path = str(item.get("image_md_path", "")).strip()
        if not image_md_path:
            continue
        if image_md_path not in body_content:
            missing_items.append(item)

    if not missing_items:
        return body_content

    heading = "## 图像结果补充" if str(output_lang).lower().startswith("zh") else "## Supplementary Figure Panel"
    blocks: list[str] = [heading]
    for item in missing_items:
        image_md_path = str(item.get("image_md_path", "")).strip()
        caption_html = str(item.get("caption_html", "")).strip()
        if not image_md_path:
            continue
        blocks.append(f"![Figure {item.get('index', '')}]({image_md_path})")
        if caption_html:
            blocks.append(caption_html)

    extra_block = "\n\n".join([block for block in blocks if block]).strip()
    if not extra_block:
        return body_content

    body = body_content.rstrip()
    return f"{body}\n\n---\n\n{extra_block}\n"


def _compose_caption_html(caption_title: str, caption_body: str, caption: str) -> str:
    title = caption_title.strip()
    body = caption_body.strip()
    if title and body:
        return "\n\n".join(
            [
                f"<p align='center'>{title}</p>",
                f"<p align='center'>{body}</p>",
            ]
        )
    if caption:
        return f"<p align='center'>{caption.strip()}</p>"
    return ""


def _build_template_fields(report_output: dict[str, Any]) -> dict[str, Any]:
    cover_report_title = str(
        report_output.get("cover_report_title")
        or report_output.get("report_title")
        or ""
    )
    cover_copyright_text = str(
        report_output.get("cover_copyright_text")
        or f"©{datetime.now().year}All Rights Reserved"
    )

    return {
        "Report_Title": str(report_output.get("report_title", "")),
        "Cover_Report_Title": cover_report_title,
        "Cover_Copyright_Text": cover_copyright_text,
        "Toc_Block": str(report_output.get("toc_block", "")),
        "Body_Content": str(report_output.get("body_content", "")),
        "Discussion_Content": str(report_output.get("discussion_content", "")),
        "Conclusion_Content": str(report_output.get("conclusion_content", "")),
        "References_Block": str(report_output.get("references_block", "")),
    }


def create_report_agent(
    chat_model: LanguageModelLike,
    *,
    max_retry: int = 3,
    name: Optional[str] = "report_subgraph",
    config_schema: Optional[Type[Any]] = None,
    checkpointer: Optional[Checkpointer] = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[list[str]] = None,
    interrupt_after: Optional[list[str]] = None,
    debug: bool = False,
) -> CompiledStateGraph:

    class State(TypedDict):
        project_id: str
        project_path: str
        background: str
        output_lang: str
        report_template: str
        pic_abs_dirs: list[str]
        captions: list[dict[str, str]]
        section_summaries: list[dict[str, str]]
        conclusion: str
        discussion: str
        key_takeaways: list[str]
        report_md: str
        report_dict: dict[str, Any]

    def node_report(state: State):
        logger.debug("START node_report")

        background = state["background"]
        output_lang = state["output_lang"]
        project_id = state.get("project_id", "")
        project_path = state["project_path"]
        report_template = state.get("report_template", "")
        pic_abs_dirs = state.get("pic_abs_dirs", [])
        captions = state.get("captions", [])
        section_summaries = state.get("section_summaries", [])
        conclusion = state.get("conclusion", "")
        discussion = state.get("discussion", "")
        key_takeaways = state.get("key_takeaways", [])
        report_output_dir = Path(project_path).expanduser().resolve() / "local_tests" / "output"
        caption_map = {
            item.get("image_path", ""): item for item in captions if isinstance(item, dict)
        }
        summary_map = {
            item.get("image_path", ""): item.get("section_summary", "")
            for item in section_summaries
            if isinstance(item, dict)
        }

        figure_items: list[dict[str, str]] = []
        for index, image_path in enumerate(pic_abs_dirs, start=1):
            caption_item = caption_map.get(image_path, {})
            caption_title = str(caption_item.get("caption_title", ""))
            caption_body = str(caption_item.get("caption_body", ""))
            caption = str(caption_item.get("caption", ""))
            section_summary = str(summary_map.get(image_path, caption_item.get("section_summary", "")))
            image_md_path = os.path.relpath(
                Path(image_path).expanduser().resolve(),
                start=report_output_dir,
            ).replace("\\", "/")

            figure_items.append(
                {
                    "index": str(index),
                    "image_path": image_path,
                    "image_md_path": str(image_md_path),
                    "caption_title": caption_title,
                    "caption_body": caption_body,
                    "caption": caption,
                    "caption_html": _compose_caption_html(caption_title, caption_body, caption),
                    "section_summary": section_summary,
                }
            )

        prompt, _ = load_prompt_template("report")
        human_input = {
            "project_id": project_id,
            "background": background,
            "output_lang": output_lang,
            "report_template": report_template,
            "figure_items": figure_items,
            "discussion": discussion,
            "conclusion": conclusion,
            "key_takeaways": key_takeaways,
        }

        message = [
            SystemMessage(
                content=prompt.format(
                    background=background,
                    output_lang=output_lang,
                    report_template=report_template,
                )
            ),
            HumanMessage(content=json.dumps(human_input, ensure_ascii=False)),
        ]

        chain = chat_model | JsonOutputParser()
        attempts = 0
        while attempts < max_retry:
            try:
                output = chain.invoke(message)
                if not isinstance(output, dict):
                    return {}

                normalized = {k: "" if v is None else str(v) for k, v in output.items() if k != "key_takeaways"}
                normalized["key_takeaways"] = output.get("key_takeaways", key_takeaways)
                normalized.setdefault("report_title", "")
                normalized.setdefault("cover_report_title", normalized.get("report_title", ""))
                normalized.setdefault("cover_copyright_text", f"©{datetime.now().year}All Rights Reserved")
                normalized.setdefault("toc_block", "")
                normalized.setdefault("body_content", "")
                normalized.setdefault("discussion_content", discussion)
                normalized.setdefault("conclusion_content", conclusion)
                normalized.setdefault("references_block", str(output.get("references_block", "")))

                normalized["toc_block"] = _strip_summary_toc_entry(normalized.get("toc_block", ""))
                normalized["body_content"] = _strip_summary_section(normalized.get("body_content", ""))
                normalized["body_content"] = _strip_reference_section(normalized.get("body_content", ""))
                normalized["body_content"] = _move_figure_images_below_captions(
                    normalized.get("body_content", ""),
                    figure_items,
                )
                normalized["body_content"] = _append_missing_figures(
                    normalized.get("body_content", ""),
                    figure_items,
                    output_lang,
                )

                normalized["references_block"] = _strip_reference_block_title(
                    str(output.get("references_block", ""))
                )

                template_fields = _build_template_fields(normalized)
                report_md, report_dict = render_report_markdown(
                    report_template=report_template,
                    project_id=project_id,
                    project_path=project_path,
                    output_lang=output_lang,
                    pic_abs_dirs=pic_abs_dirs,
                    captions=captions,
                    section_summaries=section_summaries,
                    conclusion=normalized["conclusion_content"],
                    discussion=normalized["discussion_content"],
                    key_takeaways=normalized["key_takeaways"],
                    template_fields=template_fields,
                )

                normalized["report_md"] = report_md
                normalized["report_dict"] = report_dict
                return normalized
            except Exception:
                attempts += 1
                if attempts >= max_retry:
                    logger.exception("Failed to generate report after retries.")
                    raise

        return {}

    builder = StateGraph(State, config_schema=config_schema)
    builder.add_node("Report", node_report)
    builder.add_edge(START, "Report")
    builder.add_edge("Report", END)

    return builder.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
        name=name,
    )
