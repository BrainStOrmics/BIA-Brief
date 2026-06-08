"""Convert Markdown report to compilable LaTeX (.tex) file.

Usage:
    python md_to_latex.py auto_report/Auto_Report.md -o auto_report/Auto_Report.tex

Description:
- Custom regex-based conversion: Markdown -> LaTeX
- Handles Chinese text via ctex package (compile with xelatex)
- Produces single .tex file with cover page, TOC, body, and bibliography
- Zero new Python dependencies (stdlib only)

Pipeline order (critical to avoid double-escaping):
    1. Split cover/body
    2. Extract code blocks (protect from all processing)
    3. Extract citations (protect [N] from escaping)
    4. Escape LaTeX special chars in plain text
    5. Block-level conversions (headings, figures, etc.) — produce LaTeX on escaped text
    6. Inline conversions (bold, italic, HTML stripping)
    7. Restore citations and code blocks
"""
from __future__ import annotations

import argparse
import io
import re
from pathlib import Path


# Shared with md_to_pdf.py
BODY_START_MARKER = "<!-- __BODY_START__ -->"

# Image file extensions
PIC_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


# ============================================================================
# Utility
# ============================================================================


def read_md(path: Path) -> str:
    """Read markdown file with encoding fallback."""
    for encoding in ["utf-8", "gbk", "cp1252"]:
        try:
            with io.open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            continue
    raise RuntimeError(f"Cannot read file with any encoding: {path}")


# Common Greek letters that appear in scientific text
_GREEK_MAP = {
    "α": "\\ensuremath{\\alpha}",
    "β": "\\ensuremath{\\beta}",
    "γ": "\\ensuremath{\\gamma}",
    "δ": "\\ensuremath{\\delta}",
    "ε": "\\ensuremath{\\epsilon}",
    "θ": "\\ensuremath{\\theta}",
    "λ": "\\ensuremath{\\lambda}",
    "μ": "\\ensuremath{\\mu}",
    "π": "\\ensuremath{\\pi}",
    "σ": "\\ensuremath{\\sigma}",
    "φ": "\\ensuremath{\\phi}",
    "ω": "\\ensuremath{\\omega}",
    "Α": "\\ensuremath{\\Alpha}",
    "Β": "\\ensuremath{\\Beta}",
    "Γ": "\\ensuremath{\\Gamma}",
    "Δ": "\\ensuremath{\\Delta}",
    "Σ": "\\ensuremath{\\Sigma}",
    "Φ": "\\ensuremath{\\Phi}",
    "Ω": "\\ensuremath{\\Omega}",
}


def _escape_latex(text: str) -> str:
    """Escape LaTeX special characters in plain text content.

    Order matters: backslash must be escaped first to avoid double-escaping.
    Also converts common Greek letters to \\ensuremath{} commands.
    """
    replacements = [
        ("\\", "\\textbackslash{}"),
        ("&", "\\&"),
        ("%", "\\%"),
        ("$", "\\$"),
        ("#", "\\#"),
        ("_", "\\_"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("~", "\\textasciitilde{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    # Convert Greek letters (after escaping, so backslashes in \ensuremath are safe)
    for greek, latex_cmd in _GREEK_MAP.items():
        text = text.replace(greek, latex_cmd)
    return text


def _strip_html_tags(text: str) -> str:
    """Remove all HTML tags from text, converting <br> to newline."""
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


# ============================================================================
# Preamble
# ============================================================================


def _build_preamble(title: str, date: str) -> str:
    """Build LaTeX document preamble with packages and formatting."""
    return rf"""\documentclass[a4paper,11pt]{{article}}
\usepackage[UTF8]{{ctex}}
\usepackage{{graphicx}}
\usepackage{{hyperref}}
\usepackage[top=15mm,right=16mm,bottom=30mm,left=16mm]{{geometry}}
\usepackage{{float}}
\usepackage{{xcolor}}
\usepackage{{titlesec}}
\usepackage{{fancyhdr}}
\usepackage{{placeins}}

\definecolor{{headingblue}}{{HTML}}{{0D63B8}}

\titleformat{{\section}}
  {{\normalfont\Large\bfseries\color{{headingblue}}}}{{\thesection}}{{1em}}{{}}
\titleformat{{\subsection}}
  {{\normalfont\large\bfseries\color{{headingblue}}}}{{\thesubsection}}{{1em}}{{}}

\hypersetup{{
  colorlinks=true,
  linkcolor=black,
  citecolor=black,
  urlcolor=blue,
  pdfinfo={{
    Title={{{title}}},
  }}
}}

\pagestyle{{fancy}}
\fancyhf{{}}
\fancyfoot[C]{{\thepage}}
\renewcommand{{\headrulewidth}}{{0pt}}

\setcounter{{tocdepth}}{{2}}
\setlength{{\parindent}}{{18pt}}

\title{{\textbf{{{title}}}}}
\date{{{date}}}

\begin{{document}}"""


# ============================================================================
# Cover page
# ============================================================================


def _parse_cover_html(cover_html: str) -> dict[str, str]:
    """Extract title, date, image path, and copyright from cover HTML."""
    info: dict[str, str] = {"title": "", "date": "", "image": "", "copyright": ""}

    h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', cover_html, re.DOTALL)
    if h2s:
        info["title"] = _strip_html_tags(h2s[0]).replace('\n', ' ').strip()
    if len(h2s) > 1:
        info["date"] = _strip_html_tags(h2s[1]).strip()

    img_match = re.search(r'<img\s+[^>]*src=["\']([^"\']+)["\']', cover_html)
    if img_match:
        info["image"] = img_match.group(1)

    for p_match in re.finditer(r'<p[^>]*>(.*?)</p>', cover_html, re.DOTALL):
        text = _strip_html_tags(p_match.group(1))
        if '©' in text or 'Copyright' in text.lower() or 'rights' in text.lower():
            info["copyright"] = text
            break

    # Fallback: look for copyright in a div
    if not info["copyright"]:
        for div_match in re.finditer(r'<div[^>]*>(.*?)</div>', cover_html, re.DOTALL):
            text = _strip_html_tags(div_match.group(1))
            if '©' in text:
                info["copyright"] = text
                break

    return info


def _convert_cover(cover_html: str) -> str:
    """Convert cover HTML to LaTeX titlepage environment."""
    info = _parse_cover_html(cover_html)

    lines = ["\\begin{titlepage}", "\\centering"]

    lines.append("\\vspace*{2cm}")
    if info["title"]:
        lines.append(
            f"{{\\Huge\\bfseries {_escape_latex(info['title'])}\\par}}"
        )
        lines.append("\\vspace{1.5cm}")
    if info["date"]:
        lines.append(f"{{\\large {_escape_latex(info['date'])}\\par}}")
        lines.append("\\vspace{2cm}")
    if info["image"]:
        lines.append(
            f"\\includegraphics[width=0.7\\textwidth]{{{info['image']}}}"
        )
        lines.append("\\vspace{2cm}")

    if info["copyright"]:
        lines.append("\\vfill")
        lines.append(
            f"{{\\small\\textcolor{{gray}}{{{_escape_latex(info['copyright'])}}}}}"
        )

    lines.append("\\end{titlepage}")
    return "\n".join(lines)


# ============================================================================
# Code blocks (extract/restore — protect from all processing)
# ============================================================================


def _extract_code_blocks(text: str) -> tuple[str, list[str]]:
    """Extract fenced code blocks, replace with placeholders."""
    blocks: list[str] = []

    def _save(m: re.Match[str]) -> str:
        blocks.append(m.group(1))
        return f"\n__CODEBLOCK_{len(blocks) - 1}__\n"

    text = re.sub(r'```[^\n]*\n(.*?)```', _save, text, flags=re.DOTALL)
    return text, blocks


def _restore_code_blocks(text: str, blocks: list[str]) -> str:
    """Restore code blocks as LaTeX verbatim environments."""
    for i, block in enumerate(blocks):
        # Code content is NOT escaped — verbatim handles raw text
        latex = f"\\begin{{verbatim}}\n{block}\\end{{verbatim}}"
        text = text.replace(f"__CODEBLOCK_{i}__", latex)
    return text


# ============================================================================
# Citation extraction (protect from escaping)
# ============================================================================


def _extract_citations(text: str) -> tuple[str, list[str]]:
    """Extract <sup>[N]</sup> citations, replace with placeholders.

    Must run BEFORE _escape_text to preserve [N] brackets.
    Uses §CITEN§ format to avoid conflict with __text__ bold markdown.
    Returns (text, list of LaTeX citation commands).
    """
    citations: list[str] = []

    def _save(m: re.Match[str]) -> str:
        nums = re.findall(r'\d+', m.group(1))
        cite_cmds = ",".join(f"\\cite{{ref{n}}}" for n in nums)
        idx = len(citations)
        citations.append(f"\\textsuperscript{{{cite_cmds}}}")
        return f"§CITE{idx}§"

    text = re.sub(r'<sup>\s*(\[.*?\])\s*</sup>', _save, text)
    return text, citations


def _restore_citations(text: str, citations: list[str]) -> str:
    """Restore citation placeholders with LaTeX commands."""
    for i, cite in enumerate(citations):
        text = text.replace(f"§CITE{i}§", cite)
    return text


# ============================================================================
# Escape plain text (runs BEFORE block/inline conversions)
# ============================================================================


def _escape_text(text: str) -> str:
    """Escape LaTeX special chars in plain text content.

    Runs after block-level conversions (headings, figures, etc.).
    Skips already-generated LaTeX commands and HTML tags.
    Escapes only plain text portions.
    """

    def _escape_segment(segment: str) -> str:
        """Escape a plain text segment, preserving citation placeholders."""
        parts = re.split(r'(§CITE\d+§)', segment)
        escaped_parts = []
        for part in parts:
            if re.match(r'^§CITE\d+§$', part):
                escaped_parts.append(part)
            else:
                escaped_parts.append(_escape_latex(part))
        return "".join(escaped_parts)

    lines = text.split('\n')
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip already-generated LaTeX commands
        if stripped.startswith('\\'):
            result.append(line)
            continue

        # Skip code block placeholders
        if re.match(r'^__CODEBLOCK_\d+__$', stripped):
            result.append(line)
            continue

        # For HTML block lines, escape text inside tags
        if stripped.startswith('<'):
            # Split by HTML tags, escape text between them
            parts = re.split(r'(<[^>]+>)', line)
            escaped_line: list[str] = []
            for part in parts:
                if part.startswith('<') and part.endswith('>'):
                    escaped_line.append(part)
                else:
                    escaped_line.append(_escape_segment(part))
            result.append("".join(escaped_line))
            continue

        # Plain text line — escape it
        result.append(_escape_segment(line))

    return '\n'.join(result)


# ============================================================================
# Block-level conversions (run on escaped text)
# ============================================================================


def _convert_headings(text: str) -> str:
    """Convert markdown headings to LaTeX section commands.

    Input text is already escaped, so heading_text is safe to embed.
    Skips headings inside fenced code blocks.
    """
    heading_map = {
        1: "section",
        2: "section",
        3: "subsection",
        4: "subsubsection",
    }
    lines = text.splitlines()
    result: list[str] = []
    in_fence = False
    fence_token: str | None = None

    for line in lines:
        fence_match = re.match(r"^([`~]{3,})", line)
        if fence_match:
            token = fence_match.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_token = token
            elif fence_token == token:
                in_fence = False
                fence_token = None
            result.append(line)
            continue

        if not in_fence:
            heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                # Strip leading auto-number (e.g. "1 ", "1.1 ", "1.1.2 ")
                # since LaTeX \section{} adds its own numbering
                heading_text = re.sub(r'^[\d]+(\.\d+)*\s+', '', heading_text)
                cmd = heading_map.get(min(level, 4), "subsubsection")
                # heading_text is already escaped
                result.append(f"\\{cmd}{{{heading_text}}}")
                continue

        result.append(line)

    return "\n".join(result)


def _remove_toc_block(text: str) -> str:
    """Remove HTML TOC block (replaced by LaTeX native \\tableofcontents)."""
    return re.sub(
        r"<section\s+class=['\"]toc-block['\"]>.*?</section>",
        "",
        text,
        flags=re.DOTALL,
    )


def _convert_page_breaks(text: str) -> str:
    """Convert HTML page break divs to \\clearpage."""
    return re.sub(
        r"<div\s+style=['\"][^'\"]*page-break-after:\s*always[^'\"]*['\"]>\s*</div>",
        lambda m: "\\clearpage",
        text,
        flags=re.IGNORECASE,
    )


def _convert_ref_title(text: str) -> str:
    """Convert <div class='ref-title'> to unnumbered section."""
    return re.sub(
        r"<div\s+class=['\"]ref-title['\"][^>]*>.*?</div>",
        lambda m: "\\section*{参考文献}\n\\addcontentsline{toc}{section}{参考文献}",
        text,
        flags=re.DOTALL,
    )


def _convert_figures(text: str) -> str:
    """Convert markdown image + caption to LaTeX figure environment.

    Handles: ![alt](path) followed by one or two <p align='center'> captions.
    Figures are numbered sequentially based on appearance order.
    Caption text is already escaped from _escape_text pass on <p> content.
    """
    ordered_paths: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        path = m.group(1).strip()
        if path and path not in seen and Path(path).suffix.lower() in PIC_EXTS:
            ordered_paths.append(path)
            seen.add(path)
    path_to_index = {path: i for i, path in enumerate(ordered_paths, start=1)}

    def _replace_figure(m: re.Match[str]) -> str:
        img_path = m.group(1).strip()
        caption_html = m.group(2)

        if img_path not in path_to_index:
            return m.group(0)

        fig_num = path_to_index[img_path]

        # Parse caption: may be one or two <p> tags
        p_tags = re.findall(
            r"<p\s+align='center'>(.*?)</p>", caption_html, re.DOTALL
        )
        if len(p_tags) >= 2:
            title_text = _strip_html_tags(p_tags[0])
            body_text = _strip_html_tags(p_tags[1])
            caption_text = f"{title_text} {body_text}".strip()
        elif p_tags:
            caption_text = _strip_html_tags(p_tags[0])
        else:
            caption_text = _strip_html_tags(caption_html)

        # Caption was NOT escaped by _escape_text (it's inside <p> tags)
        # so we need to escape it here
        caption_latex = _escape_latex(caption_text)

        return (
            f"\\begin{{figure}}[htbp]\n"
            f"\\centering\n"
            f"\\includegraphics[width=0.85\\textwidth]{{{img_path}}}\n"
            f"\\caption{{{caption_latex}}}\n"
            f"\\label{{fig:{fig_num}}}\n"
            f"\\end{{figure}}"
        )

    pattern = re.compile(
        r"!\[[^\]]*\]\(([^)]+)\)\s*\n*\s*"
        r"(<p\s+align='center'>.*?</p>(?:\s*\n*\s*<p\s+align='center'>.*?</p>)?)",
        re.DOTALL,
    )
    return pattern.sub(_replace_figure, text)


def _convert_tables(text: str) -> str:
    """Convert markdown tables to LaTeX tabular environments."""

    def _replace_table(m: re.Match[str]) -> str:
        table_text = m.group(0).strip()
        rows = [
            r.strip()
            for r in table_text.split("\n")
            if r.strip() and not re.match(r'^\|?\s*[-:]+', r.strip())
        ]
        if not rows:
            return table_text

        header_cells = [
            c.strip() for c in rows[0].strip("|").split("|") if c.strip()
        ]
        num_cols = len(header_cells)
        if num_cols == 0:
            return table_text

        col_spec = "|" + "|".join(["c"] * num_cols) + "|"
        lines = [
            "\\begin{table}[htbp]",
            "\\centering",
            f"\\begin{{tabular}}{{{col_spec}}}",
            "\\hline",
        ]

        # Header row (cells already escaped by _escape_text)
        header_latex = [f"\\textbf{{{c}}}" for c in header_cells]
        lines.append(" & ".join(header_latex) + " \\\\")
        lines.append("\\hline")

        # Data rows (cells already escaped)
        for row in rows[1:]:
            cells = [c.strip() for c in row.strip("|").split("|")]
            cells = cells[:num_cols]
            while len(cells) < num_cols:
                cells.append("")
            lines.append(" & ".join(cells) + " \\\\")

        lines.extend(["\\hline", "\\end{tabular}", "\\end{table}"])
        return "\n".join(lines)

    return re.sub(
        r"(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)",
        _replace_table,
        text,
    )


def _convert_lists(text: str) -> str:
    """Convert markdown lists to LaTeX list environments.

    List item text is already escaped by _escape_text.
    """
    lines = text.split("\n")
    result: list[str] = []
    current_list: str | None = None

    for line in lines:
        ul_match = re.match(r'^(\s*)[*-]\s+(.+)$', line)
        ol_match = re.match(r'^(\s*)\d+\.\s+(.+)$', line)

        if ul_match:
            if current_list != "itemize":
                if current_list:
                    result.append(f"\\end{{{current_list}}}")
                result.append("\\begin{itemize}")
                current_list = "itemize"
            # Item text already escaped
            result.append(f"  \\item {ul_match.group(2)}")
        elif ol_match:
            if current_list != "enumerate":
                if current_list:
                    result.append(f"\\end{{{current_list}}}")
                result.append("\\begin{enumerate}")
                current_list = "enumerate"
            result.append(f"  \\item {ol_match.group(2)}")
        else:
            if current_list:
                result.append(f"\\end{{{current_list}}}")
                current_list = None
            result.append(line)

    if current_list:
        result.append(f"\\end{{{current_list}}}")

    return "\n".join(result)


# ============================================================================
# Inline conversions (run on escaped text, after block conversions)
# ============================================================================


def _convert_inline(text: str) -> str:
    """Convert inline markdown and strip remaining HTML tags.

    Text is already escaped. Block-level LaTeX commands are already in place.
    This function:
    1. Converts **bold** -> \\textbf{} (wraps already-escaped text)
    2. Converts *italic* -> \\textit{} (wraps already-escaped text)
    3. Strips <p style='text-indent:...'> wrappers
    4. Converts remaining <sup>text</sup> -> ^{text}
    5. Removes <style> and <script> blocks
    6. Strips remaining HTML tags
    """
    # --- Bold: **text** or __text__ ---
    # Content is already escaped, just wrap in \textbf
    def _bold_cb(m: re.Match[str]) -> str:
        return f"\\textbf{{{m.group(1)}}}"

    text = re.sub(r'\*\*(.+?)\*\*', _bold_cb, text)
    text = re.sub(r'__(.+?)__', _bold_cb, text)

    # --- Italic: *text* only ---
    # NOTE: _text_ italic is intentionally disabled — underscores are far more
    # common in bioinformatics identifiers (n_genes_by_counts, pct_counts_mt)
    # and image filenames (violin_1_qc.png) than as italic markers.
    def _italic_cb(m: re.Match[str]) -> str:
        return f"\\textit{{{m.group(1)}}}"

    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', _italic_cb, text)

    # --- Strip <p style='text-indent:...'> wrapper (LaTeX handles indent) ---
    text = re.sub(r"<p\s+style=['\"]text-indent:[^'\"]*['\"]>\s*", "", text)
    text = re.sub(r"\s*</p>", "", text)

    # --- <p align='center'> (standalone, not part of figure caption) ---
    text = re.sub(
        r"<p\s+align=['\"]center['\"]>\s*(.*?)\s*</p>",
        lambda m: f"\\begin{{center}}{_strip_html_tags(m.group(1))}\\end{{center}}",
        text,
        flags=re.DOTALL,
    )

    # --- Remaining <sup>text</sup> -> ^{text} ---
    def _sup_cb(m: re.Match[str]) -> str:
        inner = _strip_html_tags(m.group(1))
        return f"^{{{inner}}}"

    text = re.sub(r'<sup>(.*?)</sup>', _sup_cb, text, flags=re.DOTALL)

    # --- Remove <style> and <script> blocks ---
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

    # --- Strip remaining HTML tags ---
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)

    return text


# ============================================================================
# References
# ============================================================================


def _convert_references(text: str) -> str:
    """Convert reference entries to LaTeX thebibliography environment.

    Input:  <p ...>[N] Author. Title. Journal. Year;Vol:Pages.</p>
    Output: \\bibitem{refN} Author. Title. Journal. Year;Vol:Pages.

    Reference text inside <p> was NOT escaped by _escape_text (it starts with <),
    so we escape it here.
    """
    ref_entries = re.findall(
        r"<p[^>]*>\s*\[(\d+)\]\s*(.*?)</p>", text, re.DOTALL
    )
    if not ref_entries:
        return text

    # Remove reference entries from text
    text = re.sub(
        r"<p[^>]*>\s*\[\d+\]\s*.*?</p>", "", text, flags=re.DOTALL
    )

    # Build thebibliography
    bib_lines = ["\\begin{thebibliography}{99}"]
    for num, ref_text in ref_entries:
        clean = _escape_latex(_strip_html_tags(ref_text))
        bib_lines.append(f"\\bibitem{{ref{num}}} {clean}")
    bib_lines.append("\\end{thebibliography}")

    return text.rstrip() + "\n\n" + "\n".join(bib_lines)


# ============================================================================
# Main conversion
# ============================================================================


def convert_md_to_latex(
    md_text: str, *, title: str = "", date: str = ""
) -> str:
    """Convert markdown report text to a complete LaTeX document string."""

    # Split cover and body
    if BODY_START_MARKER in md_text:
        parts = md_text.split(BODY_START_MARKER, 1)
        cover_html = parts[0].strip()
        body = parts[1].strip()
    else:
        cover_html = ""
        body = md_text.strip()

    # Parse cover info (extract title/date if not provided)
    cover_info = _parse_cover_html(cover_html) if cover_html else {}
    final_title = title or cover_info.get("title", "") or "Report"
    final_date = date or cover_info.get("date", "")

    # Build preamble
    preamble = _build_preamble(final_title, final_date)

    # Build cover titlepage
    cover_latex = _convert_cover(cover_html) if cover_html else ""

    # Process body — order is critical:
    # 1. Extract code blocks (protect from all processing)
    body, code_blocks = _extract_code_blocks(body)
    # 2. Extract citations (protect [N] from escaping)
    body, citations = _extract_citations(body)
    # 3. Block-level conversions (on raw markdown, each converter escapes its own text)
    body = _remove_toc_block(body)
    body = _convert_page_breaks(body)
    body = _convert_ref_title(body)
    body = _convert_headings(body)
    body = _convert_figures(body)
    body = _convert_tables(body)
    body = _convert_lists(body)
    # 4. Escape remaining plain text (paragraphs, loose text not yet processed)
    body = _escape_text(body)
    # 5. References (parse <p> entries before inline HTML stripping)
    body = _convert_references(body)
    # 6. Inline conversions (bold, italic, HTML stripping)
    body = _convert_inline(body)
    # 7. Restore protected elements
    body = _restore_citations(body, citations)
    body = _restore_code_blocks(body, code_blocks)

    # Assemble document
    sections = [preamble, ""]
    if cover_latex:
        sections.extend([cover_latex, ""])
    sections.extend([
        "\\tableofcontents",
        "\\clearpage",
        "",
        body,
        "",
        "\\end{document}",
    ])
    return "\n".join(sections)


# ============================================================================
# File I/O
# ============================================================================


def build_latex_from_markdown(md_path: Path, output_tex: Path) -> None:
    """Read markdown file and write converted LaTeX file."""
    md_text = read_md(md_path)
    latex_text = convert_md_to_latex(md_text)
    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex_text, encoding="utf-8")


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Markdown report to LaTeX (.tex) file"
    )
    parser.add_argument("md", help="Input Markdown file path")
    parser.add_argument(
        "-o", "--output", help="Output .tex file path (default: same name as input)"
    )
    parser.add_argument("--title", default="", help="Document title override")
    parser.add_argument("--date", default="", help="Document date override")
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        raise SystemExit(f"File not found: {md_path}")

    output_tex = Path(args.output) if args.output else md_path.with_suffix(".tex")

    md_text = read_md(md_path)
    latex_text = convert_md_to_latex(md_text, title=args.title, date=args.date)

    output_tex.parent.mkdir(parents=True, exist_ok=True)
    output_tex.write_text(latex_text, encoding="utf-8")
    print(f"LaTeX generated: {output_tex}")


if __name__ == "__main__":
    main()
