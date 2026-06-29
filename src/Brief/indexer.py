"""Project indexer: scan files, generate captions/summaries, write index.md."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from .prompts import load_prompt_template
from .utils.io import (
    check_file_exists,
    check_image_exists,
    image_to_base64_for_llm,
)

logger = logging.getLogger(__name__)

# Supported file extensions
PIC_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SCRIPT_EXTS = {".py", ".r", ".R", ".ipynb", ".sh", ".jl", ".m"}


def _compute_cache_key(background: str, output_lang: str, output_path: str = "") -> str:
    """Compute SHA256 hash of background + output_lang + output_dir for caching."""
    from pathlib import Path
    output_dir = str(Path(output_path).parent) if output_path else ""
    content = f"{background}\x00{output_lang}\x00{output_dir}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _find_pics_search_dir(project_path: Path) -> Path | None:
    """Locate the directory containing analysis figures for a project.

    Searches in priority order:
      1. <project>/pics/figures/
      2. <project>/pics/
      3. <project>/figures/

    Returns None if no candidate directory exists.
    """
    pics_dir = project_path / "pics"
    if pics_dir.exists():
        figures_sub = pics_dir / "figures"
        if figures_sub.exists() and figures_sub.is_dir():
            return figures_sub
        return pics_dir
    figures_dir = project_path / "figures"
    if figures_dir.exists() and figures_dir.is_dir():
        return figures_dir
    return None


def _get_source_mtime(project_path: Path) -> float:
    """Get the maximum modification time of all source files (pics + scripts)."""
    max_mtime = 0.0

    search_dir = _find_pics_search_dir(project_path)
    if search_dir is not None:
        for f in search_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in PIC_EXTS:
                max_mtime = max(max_mtime, f.stat().st_mtime)

    scripts_dir = project_path / "scripts"
    if scripts_dir.exists():
        for f in scripts_dir.rglob("*"):
            if f.is_file() and f.suffix in SCRIPT_EXTS:
                max_mtime = max(max_mtime, f.stat().st_mtime)

    return max_mtime


def _check_cache(index_path: Path, cache_key: str, source_mtime: float) -> bool:
    """Check if index.md exists and is still valid. Returns True if cache hit."""
    if not index_path.exists():
        return False

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            # Read first 5 lines to find cache metadata
            header_lines = []
            for _ in range(5):
                line = f.readline()
                if not line:
                    break
                header_lines.append(line)

        header = "\n".join(header_lines)

        # Parse cache_key from comment
        if f"cache_key: {cache_key}" not in header:
            logger.debug("Cache miss: cache_key mismatch")
            return False

        # Parse source_mtime from comment
        import re
        mtime_match = re.search(r"source_mtime:\s*([\d.]+)", header)
        if not mtime_match:
            logger.debug("Cache miss: source_mtime not found")
            return False

        recorded_mtime = float(mtime_match.group(1))
        if source_mtime > recorded_mtime + 1.0:  # 1s tolerance
            logger.debug("Cache miss: source files changed")
            return False

        logger.info("Cache hit: index.md is up to date")
        return True

    except Exception as e:
        logger.debug("Cache check failed: %s", e)
        return False


# Mapping from filename patterns to (analysis_step, sort_order)
# IMPORTANT: More specific patterns must come before general ones.
# e.g., "rank_genes" before "leiden" (since rank_genes files may contain "leiden" in name),
# and "leiden_search" before "leiden".
ANALYSIS_STEP_MAP = {
    "violin": ("数据质量控制", 1),
    "scatter": ("数据质量控制", 2),
    "qc": ("数据质量控制", 2),
    "filter_genes": ("高变基因筛选", 3),
    "hvg": ("高变基因筛选", 3),
    "pca": ("PCA降维分析", 4),
    "rank_genes": ("标记基因鉴定", 7),
    "markers": ("标记基因鉴定", 8),
    "leiden_search": ("细胞聚类分析", 5),
    "leiden": ("细胞聚类分析", 6),
    "annotation": ("细胞类型注释", 9),
    "paga": ("细胞间通讯网络分析", 10),
    "pseudotime": ("拟时序分析", 11),
    "go_kegg": ("GO与Pathway功能分析", 12),
    "enrichment": ("GO与Pathway功能分析", 12),
}


def _get_analysis_step(filename: str) -> tuple[str, int]:
    """Determine analysis step and sort order from filename."""
    name_lower = filename.lower()
    for pattern, (step, order) in ANALYSIS_STEP_MAP.items():
        if pattern.lower() in name_lower:
            return step, order
    return "其他分析", 99


def _discover_project_files(project_path: Path) -> tuple[list[str], list[str]]:
    """Discover image and script files. Returns (pic_abs_dirs, script_abs_dirs).

    Images are sorted by analysis workflow order (QC → HVG → PCA → Clustering →
    Markers → Annotation → PAGA), not alphabetically.
    """
    pic_search_dir = _find_pics_search_dir(project_path)
    if pic_search_dir is None or not pic_search_dir.exists():
        raise FileNotFoundError(
            f"Could not find picture directory under {project_path} "
            f"(looked for pics/, pics/figures/, figures/)"
        )

    all_pics = [
        p for p in pic_search_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in PIC_EXTS
    ]
    # Sort by analysis workflow order
    all_pics.sort(key=lambda p: _get_analysis_step(p.name))
    pic_abs_dirs = [str(p.resolve()) for p in all_pics]

    if not pic_abs_dirs:
        raise FileNotFoundError(f"No image files found in {pic_search_dir}")

    script_dir = project_path / "scripts"
    script_abs_dirs: list[str] = []
    if script_dir.exists() and script_dir.is_dir():
        script_files = sorted(
            p for p in script_dir.rglob("*")
            if p.is_file() and p.suffix in SCRIPT_EXTS
        )
        script_abs_dirs = [str(p.resolve()) for p in script_files]

    logger.info(
        "Discovered %d images, %d scripts: %s",
        len(pic_abs_dirs), len(script_abs_dirs),
        ", ".join(Path(s).name for s in script_abs_dirs) if script_abs_dirs else "<none>",
    )
    return pic_abs_dirs, script_abs_dirs


def _get_image_dimensions(image_path: str) -> tuple[int, int]:
    """Get image dimensions (width, height)."""
    from PIL import Image
    with Image.open(image_path) as img:
        return img.size


def _get_file_size_str(path: str) -> str:
    """Get human-readable file size."""
    size = os.path.getsize(path)
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.0f}KB"
    else:
        return f"{size / (1024 * 1024):.1f}MB"


def _get_script_summary(script_path: str, max_lines: int = 30) -> tuple[str, int, str]:
    """Get script language, line count, and key analysis steps as summary.

    Extracts import statements and key function calls (sc.tl.*, sc.pp.*, etc.)
    to provide meaningful analysis context rather than just the first N lines.
    """
    path = Path(script_path)
    lang = path.suffix.lstrip(".")
    if lang.lower() == "r":
        lang = "R"

    with open(script_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    line_count = len(lines)

    # Extract key analysis steps: imports + function calls
    summary_parts = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue
        # Keep imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            summary_parts.append(stripped)
        # Keep key scanpy/anndata function calls
        elif any(kw in stripped for kw in [
            "sc.pp.", "sc.tl.", "sc.pl.", "sc.get.",
            "adata.", "celltypist.", "scvi.",
            "resolution=", "n_comps=", "n_pcs=",
        ]):
            summary_parts.append(stripped)

    # Limit to max_lines
    if len(summary_parts) > max_lines:
        summary_parts = summary_parts[:max_lines]
        summary_parts.append("...")

    summary = "\n".join(summary_parts) if summary_parts else "".join(lines[:5]).strip() + "\n..."

    return lang, line_count, summary


def _generate_overview(
    background: str,
    script_summaries: list[tuple[str, str, int, str]],
    pic_filenames: list[str],
    chat_model: LanguageModelLike,
) -> str:
    """Generate a high-level project overview from background, scripts, and images."""
    scripts_info = "\n".join(
        f"- {path} ({lang}, {lines} lines)\n  ```\n{first_n}\n  ```"
        for path, lang, lines, first_n in script_summaries
    )
    # Include analysis step for each image
    images_info = "\n".join(
        f"- {name} ({_get_analysis_step(name)[0]})"
        for name in pic_filenames
    )

    system_prompt = (
        "You are a senior bioinformatics analyst. Based on the research background, "
        "analysis scripts, and output figures provided, write a concise project overview "
        "as plain text paragraphs. Include: the research goal, analytical methods used, "
        "and a brief summary of what the figures show. For each analysis step found in the "
        "figures, mention the specific tools/software used (e.g., scanpy, Seurat, dnbc4tools) "
        "and key parameters if visible in the scripts. Do NOT repeat all details — "
        "synthesize into a high-level narrative. "
        "Output plain text only — NO headings, NO code fences, NO titles."
    )

    human_content = (
        f"Research Background:\n{background}\n\n"
        f"Analysis Scripts:\n{scripts_info if scripts_info else '(none)'}\n\n"
        f"Output Figures (sorted by analysis pipeline order):\n{images_info if images_info else '(none)'}"
    )

    message = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_content),
    ]

    try:
        response = chat_model.invoke(message)
        text = response.content if hasattr(response, "content") else str(response)
        # Strip any leading heading lines (# or ##) that the LLM may add
        lines = text.split("\n")
        while lines and lines[0].strip().startswith("#"):
            lines.pop(0)
        return "\n".join(lines).strip()
    except Exception as e:
        logger.warning("Failed to generate project overview: %s", e)
        return ""


def _process_single_image(
    index: int,
    total: int,
    pic_abs_dir: str,
    script_paths: list[str],
    background: str,
    output_lang: str,
    mmchat_model: LanguageModelLike,
    max_retry: int,
) -> dict[str, str] | None:
    """Process a single image: generate caption and section summary."""
    figure_id = f"Figure {index}"
    logger.info("[%d/%d] Processing %s", index, total, pic_abs_dir)

    try:
        if not check_image_exists(pic_abs_dir):
            raise FileNotFoundError(f"Image file {pic_abs_dir} does not exist")

        pic_64, pic_mime_type = image_to_base64_for_llm(pic_abs_dir)

        script_parts: list[str] = []
        for sp in script_paths:
            if sp and check_file_exists(sp):
                _, line_count, summary = _get_script_summary(sp)
                script_parts.append(f"### {Path(sp).name} ({line_count} lines)\n{summary}")
        script_content = "\n\n".join(script_parts) if script_parts else ""

        prompt, _ = load_prompt_template("synthesist")

        human_input = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        f"Write a figure title and explanation for the following image. "
                        f"Use identifier '{figure_id}' in the title. " + script_content
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{pic_mime_type};base64,{pic_64}"},
                },
            ]
        )

        message = [
            SystemMessage(content=prompt.format(
                background=background,
                output_lang=output_lang,
                figure_id=figure_id,
            )),
            human_input,
        ]

        chain = mmchat_model | JsonOutputParser()
        for attempt in range(max_retry):
            try:
                json_output = chain.invoke(message)
                caption_title = json_output.get("caption_title", "")
                caption_body = json_output.get("caption_body", "")
                caption = json_output.get("caption", "")
                section_summary = json_output.get("section_summary", "")
                analysis_step = json_output.get("analysis_step", "")

                if not caption and (caption_title or caption_body):
                    caption = " ".join(part for part in [caption_title, caption_body] if part)

                logger.info("[%d/%d] Completed %s", index, total, pic_abs_dir)
                return {
                    "image_path": pic_abs_dir,
                    "caption_title": caption_title,
                    "caption_body": caption_body,
                    "caption": caption,
                    "section_summary": section_summary,
                    "analysis_step": analysis_step,
                }
            except Exception as e:
                if attempt >= max_retry - 1:
                    raise
                logger.debug("Retry %d/%d for %s: %s", attempt + 1, max_retry, figure_id, e)

    except Exception:
        logger.exception("[%d/%d] Failed %s", index, total, pic_abs_dir)
        raise

    return None


def _build_index_md(
    project_path: Path,
    pic_abs_dirs: list[str],
    script_abs_dirs: list[str],
    captions: list[dict[str, str]],
    cache_key: str,
    source_mtime: float,
    output_path: str = "",
    overview: str = "",
) -> str:
    """Build the index.md content."""
    lines = []

    # Cache metadata header
    lines.append(f"<!--")
    lines.append(f"  cache_key: {cache_key}")
    lines.append(f"  source_mtime: {source_mtime}")
    lines.append(f"  generated_at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"-->")
    lines.append("")
    lines.append("# Project Index")
    lines.append("")

    if overview:
        lines.append("## Project Overview")
        lines.append("")
        lines.append(overview)
        lines.append("")

    # Images table
    lines.append("## Images")
    lines.append("")
    lines.append("| # | File | Analysis Step | Path | Dimensions | Size |")
    lines.append("|---|------|---------------|------|------------|------|")

    for i, pic_path in enumerate(pic_abs_dirs, start=1):
        p = Path(pic_path)
        report_dir = Path(output_path).parent if output_path else project_path
        rel_path = os.path.relpath(p, start=report_dir).replace("\\", "/")
        step, _ = _get_analysis_step(p.name)
        try:
            w, h = _get_image_dimensions(pic_path)
            dims = f"{w}x{h}"
        except Exception:
            dims = "N/A"
        size = _get_file_size_str(pic_path)
        lines.append(f"| {i} | {p.name} | {step} | {rel_path} | {dims} | {size} |")

    lines.append("")

    # Analysis Pipeline
    lines.append("## Analysis Pipeline")
    lines.append("")
    pipeline_steps: dict[str, list[str]] = {}
    for i, pic_path in enumerate(pic_abs_dirs, start=1):
        p = Path(pic_path)
        step, _ = _get_analysis_step(p.name)
        pipeline_steps.setdefault(step, []).append(f"图 {i} ({p.name})")
    for step_name in dict.fromkeys(_get_analysis_step(p)[0] for p in pic_abs_dirs):
        figs = pipeline_steps.get(step_name, [])
        lines.append(f"- **{step_name}**: {', '.join(figs)}")
    lines.append("")

    # Scripts table
    lines.append("## Scripts")
    lines.append("")
    lines.append("| # | File | Path | Language | Lines | Key Analysis Steps |")
    lines.append("|---|------|------|----------|-------|-------------------|")

    if script_abs_dirs:
        for i, script_path in enumerate(script_abs_dirs, start=1):
            p = Path(script_path)
            report_dir = Path(output_path).parent if output_path else project_path
            rel_path = os.path.relpath(p, start=report_dir).replace("\\", "/")
            lang, line_count, summary = _get_script_summary(script_path)
            summary = summary.replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {i} | {p.name} | {rel_path} | {lang} | {line_count} | {summary} |")
    else:
        lines.append("| - | - | - | - | - | No scripts found |")

    lines.append("")

    # Figure Captions
    lines.append("## Figure Captions")
    lines.append("")

    for i, cap in enumerate(captions, start=1):
        analysis_step = cap.get("analysis_step", "")
        step_label = f" [{analysis_step}]" if analysis_step else ""
        lines.append(f"### Figure {i}: {cap.get('caption_title', '')}{step_label}")
        lines.append("")
        if cap.get("caption_body"):
            lines.append(cap["caption_body"])
            lines.append("")
        lines.append(f"**Section Summary:** {cap.get('section_summary', '')}")
        lines.append("")

    return "\n".join(lines)


def index_project(
    project_path: str,
    mmchat_model: LanguageModelLike,
    background: str,
    output_lang: str,
    max_retry: int = 3,
    output_path: str = "",
    chat_model: LanguageModelLike | None = None,
) -> str:
    """Scan project, generate captions/summaries for each image in parallel, write to index.md.

    Returns the path to index.md.
    All information is written to index.md — agent reads it directly.
    Supports caching: skips regeneration if index.md is up to date.
    """
    project_root = Path(project_path).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise FileNotFoundError(f"Project path does not exist: {project_root}")

    # Defensive: if output_path is a directory or empty, default to report.md
    if not output_path or Path(output_path).is_dir():
        output_path = str(Path(output_path or project_root) / "report.md")

    index_path = project_root / "index.md"
    cache_key = _compute_cache_key(background, output_lang, output_path)
    source_mtime = _get_source_mtime(project_root)

    # Check cache
    if _check_cache(index_path, cache_key, source_mtime):
        logger.info("Using cached index.md: %s", index_path)
        return str(index_path)

    # Discover files
    pic_abs_dirs, script_abs_dirs = _discover_project_files(project_root)

    # Generate project overview
    logger.info("Generating project overview...")
    pic_filenames = [Path(p).name for p in pic_abs_dirs]
    script_summaries: list[tuple[str, str, int, str]] = []
    for sp in script_abs_dirs:
        p = Path(sp)
        lang, lines_count, summary = _get_script_summary(sp)
        script_summaries.append((str(p), lang, lines_count, summary))

    overview = _generate_overview(
        background=background,
        script_summaries=script_summaries,
        pic_filenames=pic_filenames,
        chat_model=chat_model or mmchat_model,
    )

    # Process images in parallel
    logger.info("Processing %d images in parallel...", len(pic_abs_dirs))
    captions: list[dict[str, str]] = [{} for _ in pic_abs_dirs]

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _process_single_image,
                index=i,
                total=len(pic_abs_dirs),
                pic_abs_dir=pic_path,
                script_paths=script_abs_dirs,
                background=background,
                output_lang=output_lang,
                mmchat_model=mmchat_model,
                max_retry=max_retry,
            ): i
            for i, pic_path in enumerate(pic_abs_dirs)
        }
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            if result:
                captions[idx] = result

    # Build and write index.md
    index_content = _build_index_md(
        project_path=project_root,
        pic_abs_dirs=pic_abs_dirs,
        script_abs_dirs=script_abs_dirs,
        captions=captions,
        cache_key=cache_key,
        source_mtime=source_mtime,
        output_path=output_path,
        overview=overview,
    )

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index_content, encoding="utf-8")
    logger.info("Index written to: %s", index_path)

    return str(index_path)
