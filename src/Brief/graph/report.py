import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Type, TypedDict

from ..prompts import load_prompt_template
from ..utils.md_to_pdf import build_pdf_from_markdown
from ..utils.prase_md_template import render_report_markdown

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# Regex patterns for content post-processing
REF_BODY_BOUNDARY = re.compile(r'(<div\s+class=[\'"]ref-title[\'"]\s*>)')
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\((?P<path>[^)]+)\)\s*(<p\s+align='center'>.*?</p>(?:\s*<p\s+align='center'>.*?</p>)?)")


def _get_cited_numbers(body_content: str) -> set[int]:
    """Extract citation numbers that are actually used in body content."""
    return {
        int(m.group(1))
        for m in re.finditer(r'<sup>\[(\d+)\]</sup>', body_content)
    }


def _filter_references_by_citation(references_block: str, cited_numbers: set[int]) -> str:
    """Keep only reference entries that are actually cited in the body."""
    if not references_block or not cited_numbers:
        return ""

    ref_pattern = re.compile(r'(<p[^>]*>\s*\[(\d+)\].*?</p>)', re.DOTALL)
    kept = [
        match.group(1)
        for match in ref_pattern.finditer(references_block)
        if int(match.group(2)) in cited_numbers
    ]

    return "\n\n".join(kept)


def _build_caption_html(caption_title: str, caption_body: str, caption: str, output_lang: str = "zh-CN") -> str:
    """Build caption HTML from title and body or fallback to caption."""
    title = caption_title.strip()
    body = caption_body.strip() if caption_body else ""

    # Normalize title format based on output language
    if output_lang.lower().startswith("zh") or "chinese" in output_lang.lower():
        # Chinese: use "图 X" format
        title = re.sub(r"Figure\s*\d+\s*\.?", f"图 ", title, flags=re.IGNORECASE)
    else:
        # English: use "Figure X" format
        title = re.sub(r"图\s*\d*\s*\.?", "Figure ", title)

    if title and body:
        return f"<p align='center'>{title}</p>\n\n<p align='center'>{body}</p>"
    return f"<p align='center'>{caption.strip()}</p>" if caption else ""


def _embed_figures_in_body(body_content: str, figure_items: list[dict[str, str]], output_lang: str) -> str:
    """Embed figures that are missing from body content.

    Strategy:
    1. Find which figures are already embedded in body
    2. For missing figures, append them at the end before references
    3. Renumber all figures based on final appearance order
    """
    if not body_content or not figure_items:
        return body_content

    # Find which figures are already embedded in body
    embedded_paths = set()
    for match in IMAGE_PATTERN.finditer(body_content):
        path = match.group("path").strip()
        if path:
            embedded_paths.add(path)

    # Find missing figures
    missing_items = [
        item for item in figure_items
        if str(item.get("image_md_path", "")).strip()
        and str(item.get("image_md_path", "")).strip() not in embedded_paths
    ]

    if not missing_items:
        # All figures embedded, just renumber them
        return _renumber_figures(body_content, figure_items)

    # Build figure blocks for missing items
    def build_figure_block(item: dict[str, str], index: int) -> str:
        image_md_path = str(item.get("image_md_path", "")).strip()
        caption_title = str(item.get("caption_title", "")).strip()
        caption_body = str(item.get("caption_body", "")).strip()
        caption = str(item.get("caption", "")).strip()

        # Update figure numbers in caption text
        def update_figure_num(text: str) -> str:
            text = re.sub(r"Figure\s+\d+", f"Figure {index}", text, flags=re.IGNORECASE)
            return re.sub(r"图\s*\d+", f"图 {index}", text)

        caption_title = update_figure_num(caption_title)
        caption_body = update_figure_num(caption_body)

        caption_html = _build_caption_html(caption_title, caption_body, caption, output_lang)
        # Use language-consistent figure format in Markdown
        figure_format = f"图 {index}" if output_lang.lower().startswith("zh") or "chinese" in output_lang.lower() else f"Figure {index}"
        return f"![{figure_format}]({image_md_path})\n\n{caption_html}"

    # Find references section and insert missing figures before it
    ref_match = REF_BODY_BOUNDARY.search(body_content)
    if ref_match:
        # Insert figures before references
        insert_pos = ref_match.start()
        figure_blocks = []
        for i, item in enumerate(missing_items, start=1):
            figure_blocks.append(build_figure_block(item, i))
        figures_text = "\n\n".join(figure_blocks)
        body_content = body_content[:insert_pos] + "\n\n" + figures_text + "\n\n" + body_content[insert_pos:]
    else:
        # No references, append at end
        for i, item in enumerate(missing_items, start=1):
            body_content += "\n\n" + build_figure_block(item, i)

    # Renumber all figures based on final appearance order
    return _renumber_figures(body_content, figure_items, output_lang)


def _renumber_figure_references(body_content: str, old_index_to_new_index: dict[str, str]) -> str:
    """Update figure references in body text to match final numbering.

    Matches patterns like "图 X", "Figure X", "见图 X", "如图 X 所示" and replaces
    the number using the old_index_to_new_index mapping.
    Does NOT match markdown image syntax ![图 X](...) or ![Figure X](...),
    and does NOT modify <p align='center'> caption blocks.
    """
    if not body_content or not old_index_to_new_index:
        return body_content

    # Temporarily remove <p align='center'> caption blocks to avoid modifying
    # figure numbers that were just corrected by _renumber_figures
    caption_blocks: list[str] = []
    def _extract_captions(m: re.Match[str]) -> str:
        placeholder = f"__CAPTION_BLOCK_{len(caption_blocks)}__"
        caption_blocks.append(m.group(0))
        return placeholder

    body = re.sub(
        r"<p\s+align='center'>.*?</p>(?:\s*<p\s+align='center'>.*?</p>)?",
        _extract_captions,
        body_content,
        flags=re.DOTALL,
    )

    # Pattern to match figure references in body text (NOT in markdown images)
    # Uses negative lookbehind (?<!\[) to exclude ![图 X] syntax
    ref_pattern = re.compile(r'(?<!\[)(图\s*|Figure\s+)(\d+)', re.IGNORECASE)

    def _replace_ref(match: re.Match[str]) -> str:
        prefix = match.group(1)
        old_num = match.group(2)
        new_num = old_index_to_new_index.get(old_num, old_num)
        return f"{prefix}{new_num}"

    body = ref_pattern.sub(_replace_ref, body)

    # Restore caption blocks
    for i, caption in enumerate(caption_blocks):
        body = body.replace(f"__CAPTION_BLOCK_{i}__", caption)

    return body


def _renumber_figures(body_content: str, figure_items: list[dict[str, str]], output_lang: str = "zh-CN") -> str:
    """Renumber figures based on appearance order and rebuild caption HTML."""
    if not body_content or not figure_items:
        return body_content

    path_to_item = {
        str(item.get("image_md_path", "")).strip(): item
        for item in figure_items
        if str(item.get("image_md_path", "")).strip()
    }

    # First pass: find all images and their order
    ordered_paths = [
        match.group("path").strip()
        for match in IMAGE_PATTERN.finditer(body_content)
        if match.group("path").strip() in path_to_item
    ]
    seen = set()
    ordered_paths = [p for p in ordered_paths if not (p in seen or seen.add(p))]

    path_to_new_index = {path: str(idx) for idx, path in enumerate(ordered_paths, start=1)}

    # Build old_index -> new_index mapping for updating body references
    old_index_to_new_index = {}
    for path, new_idx in path_to_new_index.items():
        item = path_to_item.get(path, {})
        old_idx = str(item.get("index", ""))
        if old_idx and old_idx != new_idx:
            old_index_to_new_index[old_idx] = new_idx

    def _swap(match: re.Match[str]) -> str:
        path = match.group("path").strip()
        if path not in path_to_new_index:
            return match.group(0)

        new_index = path_to_new_index[path]
        item = path_to_item.get(path, {})

        # Extract the actual caption HTML from the matched content (what LLM wrote)
        # IMAGE_PATTERN has groups: (1)=path (named), (2)=full caption HTML
        caption_html = match.group(2) if match.lastindex and match.lastindex >= 2 else ""

        if caption_html:
            def update_caption_nums(text: str) -> str:
                text = re.sub(r"Figure\s+\d+", f"Figure {new_index}", text, flags=re.IGNORECASE)
                return re.sub(r"图\s*\d+", f"图 {new_index}", text)

            para_pattern = re.compile(r"(<p\s+align='center'>.*?</p>)", re.DOTALL)
            paragraphs = para_pattern.findall(caption_html)

            if len(paragraphs) >= 2:
                updated_p1 = update_caption_nums(paragraphs[0])
                updated_p2 = update_caption_nums(paragraphs[1])
                caption_html = f"{updated_p1}\n\n{updated_p2}"
            elif len(paragraphs) == 1:
                caption_html = update_caption_nums(paragraphs[0])
        else:
            # Fallback: rebuild caption from item
            caption_title = str(item.get("caption_title", "")).strip()
            caption_body = str(item.get("caption_body", "")).strip()

            def update_figure_num(text: str) -> str:
                text = re.sub(r"Figure\s+\d+", f"Figure {new_index}", text, flags=re.IGNORECASE)
                return re.sub(r"图\s*\d+", f"图 {new_index}", text)

            caption_title = update_figure_num(caption_title)
            caption_body = update_figure_num(caption_body)
            caption_html = _build_caption_html(caption_title, caption_body, "", output_lang)

        # Use language-consistent figure format in Markdown
        figure_format = f"图 {new_index}" if output_lang.lower().startswith("zh") or "chinese" in output_lang.lower() else f"Figure {new_index}"
        return f"![{figure_format}]({path})\n\n{caption_html}"

    body_content = IMAGE_PATTERN.sub(_swap, body_content)

    # Update figure references in body text
    if old_index_to_new_index:
        body_content = _renumber_figure_references(body_content, old_index_to_new_index)

    return body_content



def _wrap_body_paragraphs(body_content: str) -> str:
    """Wrap plain text paragraphs in <p style='text-indent:18.20pt'> tags.

    Detects paragraphs that are plain text (not headings, images, HTML tags,
    lists, or tables) and wraps them with the indentation style.
    """
    if not body_content:
        return body_content

    blocks = re.split(r'\n\s*\n', body_content)
    result = []

    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue

        first_line = stripped.split('\n')[0].strip()

        # Skip: headings, images, HTML, lists, tables, code fences
        if (first_line.startswith('#')
                or first_line.startswith('!')
                or first_line.startswith('<')
                or first_line.startswith('- ')
                or first_line.startswith('* ')
                or first_line.startswith('|')
                or first_line.startswith('```')):
            result.append(block)
        else:
            # Plain text paragraph — wrap with indentation
            result.append(f"<p style='text-indent:18.20pt'>{stripped}</p>")

    return '\n\n'.join(result)


def _build_template_fields(report_output: dict[str, Any]) -> dict[str, Any]:
    """Build template fields dictionary from report output."""
    return {
        "Report_Title": str(report_output.get("report_title", "")),
        "Cover_Report_Title": str(report_output.get("cover_report_title") or report_output.get("report_title") or ""),
        "Cover_Copyright_Text": "©2026All Rights Reserved",
        "Body_Content": str(report_output.get("body_md", "")),
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
        output_path: str
        pic_abs_dirs: list[str]
        captions: list[dict[str, str]]
        section_summaries: list[dict[str, str]]
        conclusion: str
        discussion: str
        key_takeaways: list[str]
        report_md: str
        report_pdf_path: str
        report_dict: dict[str, Any]

    def node_report(state: State):
        logger.debug("START node_report")

        project_id = state.get("project_id", "")
        project_path = state["project_path"]
        background = state["background"]
        output_lang = state["output_lang"]
        report_template = state.get("report_template", "")
        pic_abs_dirs = state.get("pic_abs_dirs", [])
        captions = state.get("captions", [])
        section_summaries = state.get("section_summaries", [])
        conclusion = state.get("conclusion", "")
        discussion = state.get("discussion", "")
        key_takeaways = state.get("key_takeaways", [])
        project_root = Path(project_path).expanduser().resolve()
        output_path_raw = state.get("output_path", "")
        if output_path_raw and output_path_raw.startswith("/"):
            report_output_dir = Path(output_path_raw).parent
        elif output_path_raw:
            report_output_dir = project_root / Path(output_path_raw).parent
        else:
            report_output_dir = project_root / "local_tests" / "output"

        # Build figure items list
        caption_map = {item.get("image_path", ""): item for item in captions if isinstance(item, dict)}
        summary_map = {
            item.get("image_path", ""): item.get("section_summary", "")
            for item in section_summaries if isinstance(item, dict)
        }

        figure_items: list[dict[str, str]] = []
        for index, image_path in enumerate(pic_abs_dirs, start=1):
            caption_item = caption_map.get(image_path, {})
            image_md_path = os.path.relpath(
                Path(image_path).expanduser().resolve(), start=report_output_dir
            ).replace("\\", "/")

            figure_items.append({
                "index": str(index),
                "image_path": image_path,
                "image_md_path": str(image_md_path),
                "caption_title": str(caption_item.get("caption_title", "")),
                "caption_body": str(caption_item.get("caption_body", "")),
                "caption": str(caption_item.get("caption", "")),
                "caption_html": "",  # Filled after building caption
                "section_summary": str(summary_map.get(image_path, caption_item.get("section_summary", ""))),
            })

        # Build caption HTML for each figure item
        for item in figure_items:
            item["caption_html"] = _build_caption_html(
                item["caption_title"], item["caption_body"], item["caption"], output_lang
            )

        # Call LLM to generate report structure
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
            SystemMessage(content=prompt.format(
                background=background,
                output_lang=output_lang,
                report_template=report_template,
            )),
            HumanMessage(content=json.dumps(human_input, ensure_ascii=False)),
        ]

        chain = chat_model | JsonOutputParser()
        for attempt in range(max_retry):
            try:
                output = chain.invoke(message)
                if not isinstance(output, dict):
                    return {}

                # Normalize output with defaults
                normalized = {k: "" if v is None else str(v) for k, v in output.items() if k != "key_takeaways"}
                normalized["key_takeaways"] = output.get("key_takeaways", key_takeaways)
                normalized.setdefault("report_title", "")
                normalized.setdefault("cover_report_title", normalized.get("report_title", ""))
                normalized.setdefault("cover_copyright_text", "©2026All Rights Reserved")
                normalized.setdefault("body_md", "")

                # Post-process: embed missing figures, wrap paragraphs
                normalized["body_md"] = _embed_figures_in_body(
                    normalized.get("body_md", ""), figure_items, output_lang
                )
                normalized["body_md"] = _wrap_body_paragraphs(normalized.get("body_md", ""))

                # Build template fields and render final markdown
                template_fields = _build_template_fields(normalized)
                report_md, report_dict = render_report_markdown(
                    report_template=report_template,
                    project_id=project_id,
                    project_path=project_path,
                    output_path=output_path_raw,
                    output_lang=output_lang,
                    pic_abs_dirs=pic_abs_dirs,
                    captions=captions,
                    section_summaries=section_summaries,
                    conclusion=conclusion,
                    discussion=discussion,
                    key_takeaways=normalized["key_takeaways"],
                    template_fields=template_fields,
                )

                normalized["report_md"] = report_md
                normalized["report_dict"] = report_dict

                # Convert markdown to PDF
                md_path = report_dict.get("report_output_path", "")
                if md_path:
                    pdf_path = str(Path(md_path).with_suffix(".pdf"))
                    try:
                        build_pdf_from_markdown(Path(md_path), Path(pdf_path))
                        normalized["report_pdf_path"] = pdf_path
                        logger.info("PDF report generated: %s", pdf_path)
                    except Exception:
                        logger.exception("PDF conversion failed for: %s", md_path)
                        normalized["report_pdf_path"] = ""

                return normalized

            except Exception:
                if attempt >= max_retry - 1:
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
