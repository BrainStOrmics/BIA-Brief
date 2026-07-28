"""Brief: Main entry point for bioinformatics report generation.

Architecture: Indexer → ReAct Agent → Post-process → PDF + LaTeX
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Optional, Type

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Checkpointer, Command
from langgraph.store.base import BaseStore

from .pipeline.agent_runtime import build_report_agent, to_virtual_path
from .utils.postprocess import (
    build_template_fields,
    embed_figures_in_body,
    load_table_files,
    wrap_body_paragraphs,
)
from .utils.parse_md_template import render_report_markdown
from .utils.md_to_pdf import build_pdf_from_markdown
from .utils.md_to_latex import build_latex_from_markdown

try:
    from IPython.display import Image, display
except Exception:
    Image = None
    display = None

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


def _wait_for_human_review(prompt_msg: str, timeout: int = 300) -> str:
    """Print prompt, wait for user input with timeout.

    Uses signal.SIGALRM on Linux/macOS, threading.Timer on Windows.

    Args:
        prompt_msg: Message to display (from interrupt metadata).
        timeout: Seconds to wait before auto-resume.

    Returns:
        User feedback string. Timeout returns auto-resume message,
        EOFError returns approval message.

    Env bypass:
        Set BRIEF_AUTO_APPROVE=1 to skip the prompt entirely and return
        an empty approval string immediately. Used by parallel batch runs
        where interactive HITL is not feasible.
    """
    import os
    import sys

    if os.environ.get("BRIEF_AUTO_APPROVE") == "1":
        logger.info("HITL auto-approved (BRIEF_AUTO_APPROVE=1): %s", prompt_msg[:80])
        return ""

    print(f"\n{_GREEN}{'='*60}{_RESET}")
    print(f"{_GREEN}{prompt_msg}{_RESET}")
    print(f"{_YELLOW}编辑后按 Enter 继续...（{timeout}s 超时）{_RESET}")
    print(f"{_GREEN}{'='*60}{_RESET}")

    if sys.platform == "win32":
        return _wait_for_human_review_windows(timeout)
    else:
        return _wait_for_human_review_posix(timeout)


def _wait_for_human_review_windows(timeout: int) -> str:
    """Windows implementation using threading.Timer (no SIGALRM available)."""
    import threading

    timed_out = threading.Event()

    def _timeout_handler() -> None:
        timed_out.set()
        logger.info("Human review timed out, auto-resuming")

    timer = threading.Timer(timeout, _timeout_handler)
    timer.daemon = True
    timer.start()
    try:
        user_input = input()
        timer.cancel()
        if timed_out.is_set():
            return "审阅超时自动继续（未编辑）"
        return user_input
    except EOFError:
        timer.cancel()
        return "审阅通过"


def _wait_for_human_review_posix(timeout: int) -> str:
    """Linux/macOS implementation using signal.SIGALRM."""
    import signal

    def _timeout_handler(signum: int, frame: Any) -> None:
        raise TimeoutError("Human review timed out")

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(timeout)
    try:
        return input()
    except TimeoutError:
        logger.info("Human review timed out, auto-resuming")
        return "审阅超时自动继续（未编辑）"
    except EOFError:
        return "审阅通过"
    finally:
        signal.alarm(0)


def _stream_and_print(
    agent,
    stream_input: Any,
    config: dict,
    printer: AgentStepPrinter,
) -> None:
    """Stream agent events and print tool calls/results/AI text."""
    pending_tool_calls: dict[str, str] = {}

    for event in agent.stream(stream_input, config=config, stream_mode="updates"):
        if not isinstance(event, dict):
            continue
        for node_name, node_data in event.items():
            if not isinstance(node_data, dict):
                continue
            messages = node_data.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage):
                    for tc in msg.tool_calls or []:
                        tool_id = tc.get("id", tc.get("tool_call_id", ""))
                        pending_tool_calls[tool_id] = tc["name"]
                        printer.handle_tool_call(tc["name"], tc.get("args", {}))
                    if not msg.tool_calls and msg.content:
                        printer.handle_ai_text(msg.content)
                elif isinstance(msg, ToolMessage):
                    tool_id = msg.tool_call_id
                    tool_name = pending_tool_calls.pop(tool_id, "unknown")
                    printer.handle_tool_result(tool_name, str(msg.content))


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
        custom_title: str = "",
        *,
        project_path: str,
        report_template: str,
        output_dir: str,
        project_id: str,
    ) -> tuple[str, dict[str, Any]]:
        """Run the report generation pipeline.

        Args:
            background: Research background description.
            output_lang: Output language (e.g., "zh-CN", "en").
            custom_title: Optional custom report title. If provided, overrides the agent-generated title.
            project_path: Optional project root containing images/scripts/tables.
            report_template: Optional report template path.
            output_dir: Optional report output directory name.
            project_id: Optional project identifier.

        Returns:
            Tuple of (report_md, report_dict).
        """
        # Resolve output path
        output_path = str(Path(project_path) / output_dir / "report.md")
        index_path = str(Path(project_path) / "index.md")

        # DeepAgents owns filesystem, todo, and task tools. Business tools and
        # their post-action HITL interrupts are assembled in one runtime seam.
        logger.info("Creating DeepAgents report agent with HITL interrupt...")
        checkpointer = self.checkpointer or MemorySaver()
        repo_root = Path(__file__).resolve().parents[2]
        agent = build_report_agent(
            chat_model=self.chat_model,
            mmchat_model=self.mmchat_model,
            project_path=project_path,
            repo_root=repo_root,
            checkpointer=checkpointer,
            store=self.store,
            debug=self.debug,
        )

        # Build user message (agent will extract params and call run_indexer)
        report_guide_path = to_virtual_path(
            Path(__file__).resolve().parent / "prompts" / "report.md", repo_root
        )
        virtual_project_path = to_virtual_path(project_path, repo_root)
        virtual_output_path = to_virtual_path(output_path, repo_root)
        user_msg = (
            f"Generate a bioinformatics report.\n\n"
            f"Background: {background}\n"
            f"Output language: {output_lang}\n"
            f"Output path: {virtual_output_path}\n"
            f"Project path: {virtual_project_path}\n"
            f"Report guide path: {report_guide_path}\n"
        )

        config = {"configurable": {"thread_id": f"brief-{uuid.uuid4().hex[:8]}"}}
        printer = AgentStepPrinter()

        # Step A: Run agent until interrupt (after run_indexer completes)
        logger.info("Step A: Running indexer...")
        _stream_and_print(
            agent,
            {"messages": [{"role": "user", "content": user_msg}]},
            config,
            printer,
        )

        # Step B: Human-in-the-Loop loop — handle all interrupts (indexer, outline, ...)
        logger.info("Step B: Entering HITL interrupt loop...")
        while True:
            state = agent.get_state(config)
            if not state.interrupts:
                break

            for iv in state.interrupts:
                data = iv.value
                msg = data.get("message", "审阅完成，请继续。")
                user_feedback = _wait_for_human_review(msg, timeout=300)

            logger.info("Step C: Resuming agent with feedback...")
            _stream_and_print(
                agent,
                Command(resume=user_feedback),
                config,
                printer,
            )

        logger.info("Agent completed.")

        # Step 4: Post-processing
        logger.info("Step 4: Post-processing...")
        raw_md = Path(output_path).read_text(encoding="utf-8")

        # Build figure items from index for post-processing
        figure_items = self._build_figure_items(index_path, project_path, output_path)

        # Embed missing figures + renumber. start_index=2 because 图1 is the
        # static workflow figure in 技术简介 (provided by the template).
        report_md = embed_figures_in_body(raw_md, figure_items, output_lang, start_index=2)
        # Wrap paragraphs with indentation
        report_md = wrap_body_paragraphs(report_md)

        # Step 5: Template rendering
        logger.info("Step 5: Rendering template...")
        # Title source: custom_title > project_info.md > project_id
        if custom_title:
            report_title = custom_title
        else:
            project_info_path = Path(project_path) / "project_info.md"
            report_title = ""
            if project_info_path.exists():
                try:
                    for line in project_info_path.read_text(encoding="utf-8").splitlines():
                        if line.startswith("报告名称"):
                            report_title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                            break
                except Exception as e:
                    logger.warning("Failed to read project_info.md: %s", e)
            if not report_title:
                report_title = project_id

        template_fields_dict = build_template_fields({"body_md": report_md}, report_title=report_title)

        # Load project-specific table content (4 tables from <project_path>/table/)
        template_fields_dict.update(load_table_files(project_path))

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

        # Step 7: LaTeX export
        logger.info("Step 7: Converting to LaTeX...")
        tex_path = str(report_output_path.with_suffix(".tex"))
        try:
            build_latex_from_markdown(report_output_path, Path(tex_path))
            logger.info("LaTeX generated: %s", tex_path)
        except Exception:
            logger.exception("LaTeX conversion failed")
            tex_path = ""

        # Update report_dict
        report_dict["report_output_path"] = str(report_output_path)
        report_dict["report_pdf_path"] = pdf_path
        report_dict["report_tex_path"] = tex_path
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
