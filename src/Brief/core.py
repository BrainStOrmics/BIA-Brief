"""Brief: Main entry point for bioinformatics report generation.

Architecture: Indexer → ReAct Agent → Post-process → PDF
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Type

from langchain_core.language_models import LanguageModelLike

from .config.config import brief_config
from .indexer import index_project
from .agent import create_brief_agent, load_agent_prompt
from .tools import create_tools
from .utils.postprocess import (
    build_template_fields,
    embed_figures_in_body,
    wrap_body_paragraphs,
)
from .utils.parse_md_template import render_report_markdown
from .utils.md_to_pdf import build_pdf_from_markdown

try:
    from IPython.display import Image, display
except Exception:
    Image = None
    display = None

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Checkpointer
from langgraph.store.base import BaseStore

logger = logging.getLogger(__name__)

# ANSI colors for terminal output
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GRAY = "\033[90m"
_RESET = "\033[0m"


class AgentStepPrinter:
    """Print agent execution steps to terminal in a readable format."""

    def __init__(self):
        self._step = 0

    def handle_tool_call(self, name: str, args: dict) -> None:
        self._step += 1
        args_str = ""
        for k, v in args.items():
            val = str(v)
            if len(val) > 80:
                val = val[:77] + "..."
            args_str += f"{k}={val!r}, "
        if args_str:
            args_str = args_str.rstrip(", ")
        print(f"  {_YELLOW}[{self._step}]{_RESET} {_CYAN}{name}{_RESET}({args_str})", flush=True)

    def handle_tool_result(self, name: str, result: str) -> None:
        r = result[:60].replace("\n", " ")
        suffix = "..." if len(result) > 60 else ""
        print(f"     {_GREEN}→{_RESET} {_GRAY}{r}{suffix}{_RESET}", flush=True)

    def handle_ai_text(self, text: str) -> None:
        preview = text[:120].replace("\n", " ")
        suffix = "..." if len(text) > 120 else ""
        print(f"  {_GREEN}→ AI:{_RESET} {_GRAY}{preview}{suffix}{_RESET}", flush=True)


class Brief:
    """Bioinformatics report generation agent.

    Uses Indexer + ReAct Agent architecture:
    1. Indexer scans project files and generates captions/summaries → index.md
    2. ReAct Agent reads index.md, generates thesis and assembles report
    3. Post-processing handles figure embedding, paragraph wrapping, template rendering
    4. PDF conversion
    """

    def __init__(
        self,
        chat_model: LanguageModelLike,
        mmchat_model: LanguageModelLike,
        *,
        max_retry: int = 3,
        name: Optional[str] = "brief",
        config_schema: Optional[Type[Any]] = None,
        checkpointer: Optional[Checkpointer] = None,
        store: Optional[BaseStore] = None,
        interrupt_before: Optional[list[str]] = None,
        interrupt_after: Optional[list[str]] = None,
        debug: bool = False,
    ):
        self.chat_model = chat_model
        self.mmchat_model = mmchat_model
        self.max_retry = max_retry
        self.name = name
        self.config_schema = config_schema
        self.checkpointer = checkpointer
        self.store = store
        self.interrupt_before = interrupt_before
        self.interrupt_after = interrupt_after
        self.debug = debug

    def Run(
        self,
        background: str,
        output_lang: str,
    ) -> tuple[str, dict[str, Any]]:
        """Run the report generation pipeline.

        Args:
            background: Research background description.
            output_lang: Output language (e.g., "zh-CN", "en").

        Returns:
            Tuple of (report_md, report_dict).
        """
        project_path = brief_config.PROJECT_PATH
        report_template = brief_config.REPORT_TEMPLATE
        output_dir = brief_config.OUTPUT_DIR
        project_id = brief_config.PROJECT_ID

        # Resolve output path
        output_path = str(Path(project_path) / output_dir / "report.md")

        # Step 1: Indexer (scan + parallel caption/summary → write index.md)
        logger.info("Step 1: Indexing project...")
        index_path = index_project(
            project_path=project_path,
            mmchat_model=self.mmchat_model,
            background=background,
            output_lang=output_lang,
            max_retry=self.max_retry,
            output_path=output_path,
            chat_model=self.chat_model,
        )
        logger.info("Index written to: %s", index_path)

        # Step 2: Create agent
        logger.info("Step 2: Creating ReAct agent...")
        prompts_dir = Path(__file__).parent / "prompts"
        thesis_guide_path = str(prompts_dir / "thesis.md")
        report_guide_path = str(prompts_dir / "report.md")

        tools = create_tools()
        agent = create_brief_agent(
            chat_model=self.chat_model,
            system_prompt=load_agent_prompt(),
            tools=tools,
            checkpointer=self.checkpointer,
            store=self.store,
        )

        # Step 3: Invoke agent with streaming visualization
        user_msg = (
            f"Generate a bioinformatics report.\n\n"
            f"Project index path: {index_path}\n"
            f"Thesis guide path: {thesis_guide_path}\n"
            f"Report guide path: {report_guide_path}\n"
            f"Project path: {project_path}\n"
            f"Background: {background}\n"
            f"Output language: {output_lang}\n"
            f"Output path: {output_path}\n"
        )

        # Step 3: Stream agent execution with terminal visualization
        logger.info("Step 3: Invoking ReAct agent...")
        printer = AgentStepPrinter()
        pending_tool_calls: dict[str, str] = {}  # tool_id -> tool_name

        for event in agent.stream(
            {"messages": [{"role": "user", "content": user_msg}]},
            stream_mode="updates",
        ):
            # event is a dict like {'model': {'messages': [...]}} or {'tools': {'messages': [...]}}
            for node_name, node_data in event.items():
                messages = node_data.get("messages", [])

                if node_name == "model":
                    for msg in messages:
                        if not isinstance(msg, AIMessage):
                            continue
                        # Handle tool calls from AI
                        for tc in msg.tool_calls or []:
                            tool_id = tc.get("id", tc.get("tool_call_id", ""))
                            pending_tool_calls[tool_id] = tc["name"]
                            printer.handle_tool_call(tc["name"], tc.get("args", {}))
                        # Handle plain text from AI
                        if not msg.tool_calls and msg.content:
                            printer.handle_ai_text(msg.content)

                elif node_name == "tools":
                    for msg in messages:
                        if not isinstance(msg, ToolMessage):
                            continue
                        tool_id = msg.tool_call_id
                        tool_name = pending_tool_calls.pop(tool_id, "unknown")
                        printer.handle_tool_result(tool_name, msg.content)

        logger.info("Agent completed.")

        # Step 4: Post-processing
        logger.info("Step 4: Post-processing...")
        raw_md = Path(output_path).read_text(encoding="utf-8")

        # Build figure items from index for post-processing
        figure_items = self._build_figure_items(index_path, project_path, output_path)

        # Embed missing figures + renumber
        report_md = embed_figures_in_body(raw_md, figure_items, output_lang)
        # Wrap paragraphs with indentation
        report_md = wrap_body_paragraphs(report_md)

        # Step 5: Template rendering
        logger.info("Step 5: Rendering template...")
        # Read title from agent's output (written to output_path.title)
        title_path = Path(output_path + ".title")
        report_title = title_path.read_text(encoding="utf-8").strip() if title_path.exists() else ""
        if not report_title:
            # Fallback: derive from background
            report_title = "生物信息学分析报告"

        template_fields_dict = build_template_fields({"body_md": report_md}, report_title=report_title)

        project_root = Path(project_path).expanduser().resolve()
        report_output_path = Path(output_path)
        report_output_dir = report_output_path.parent

        # Get image paths for template rendering
        pic_abs_dirs = [item.get("image_path", "") for item in figure_items if item.get("image_path")]

        report_md, report_dict = render_report_markdown(
            report_template=report_template,
            project_id=project_id,
            project_path=project_path,
            output_path=output_path,
            output_lang=output_lang,
            pic_abs_dirs=pic_abs_dirs,
            captions=[],  # Captions already embedded in report_md
            section_summaries=[],  # Summaries already embedded
            conclusion="",  # Already in report_md
            discussion="",  # Already in report_md
            key_takeaways=[],  # Already in report_md
            template_fields=template_fields_dict,
        )

        # Step 6: PDF conversion
        logger.info("Step 6: Converting to PDF...")
        pdf_path = str(report_output_path.with_suffix(".pdf"))
        try:
            build_pdf_from_markdown(report_output_path, Path(pdf_path))
            logger.info("PDF generated: %s", pdf_path)
        except Exception:
            logger.exception("PDF conversion failed")
            pdf_path = ""

        # Update report_dict
        report_dict["report_output_path"] = str(report_output_path)
        report_dict["report_pdf_path"] = pdf_path
        report_dict["report_md"] = report_md

        logger.info("Report generation complete: %s", report_output_path)
        return report_md, report_dict

    def _build_figure_items(
        self, index_path: str, project_path: str, output_path: str
    ) -> list[dict[str, str]]:
        """Build figure items list from index.md for post-processing."""
        import re

        index_content = Path(index_path).read_text(encoding="utf-8")
        project_root = Path(project_path).expanduser().resolve()
        report_output_dir = Path(output_path).parent

        # Parse figure captions section
        figure_items = []
        caption_pattern = re.compile(
            r"### Figure (\d+): (.+?)(?:\n(.*?))?(?=\n### Figure|\n## |\Z)",
            re.DOTALL,
        )

        # Get image paths from Images table only (not Scripts table)
        # Path column is now already relative to report output directory
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

    def draw_graph(self):
        """Not supported in new architecture."""
        print("draw_graph is not available in the ReAct agent architecture.")
