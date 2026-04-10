#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strictly render Markdown to PDF and update table of contents page numbers according to actual pagination.

Usage:
    python md_to_pdf.py auto_report/Auto_Report.md -o auto_report/Auto_Report.pdf

Description:
- Core rendering: Markdown -> HTML -> Playwright PDF.
- If <!-- __BODY_START__ --> is present in the Markdown, the document is split into cover/body; the cover does not show page numbers.
- Table of contents page numbers are updated according to the actual pagination of the final PDF, ensuring consistency.
"""
from __future__ import annotations

import argparse
import html
import io
import re
from pathlib import Path

try:
    from markdown import markdown
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit("请先安装依赖: pip install -r requirements.txt") from exc

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:  # pragma: no cover - handled at runtime with clear message
    PdfReader = None
    PdfWriter = None

from playwright.sync_api import sync_playwright


BODY_START_MARKER = "<!-- __BODY_START__ -->"
A4_HEIGHT_MM = 297.0
A4_WIDTH_MM = 210.0
BOTTOM_MARGIN_MM = 30.0
FOOTER_SAFE_SPACE_MM = 42.0
MM_TO_PX = 96.0 / 25.4
PAGE_CONTENT_HEIGHT_PX = (A4_HEIGHT_MM - BOTTOM_MARGIN_MM) * MM_TO_PX
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = REPO_ROOT.parent.parent
FALLBACK_BACKGROUND_PATH = PROJECT_ROOT / "template" / "BGI_SY" / "pics" / "background.png"
INSTALL_REQUIREMENTS_HINT = "请先安装依赖: pip install -r requirements.txt"
INSTALL_PYPDF_HINT = "缺少 pypdf 依赖，请先安装：pip install pypdf"
CHROMIUM_LAUNCH_ERROR_HINT = "PDF 转换失败，请确保 Playwright 已安装其自带的 Chromium。"


def _launch_chromium_browser(playwright_context):
    try:
        return playwright_context.chromium.launch()
    except Exception as exc:
        raise RuntimeError(f"{CHROMIUM_LAUNCH_ERROR_HINT} 详情: {exc}") from exc


def resolve_path(path_text: str, must_exist: bool = False) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path

    candidates = [
        Path.cwd() / path,
        SCRIPT_DIR / path,
        REPO_ROOT / path,
    ]

    if must_exist:
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    for candidate in candidates:
        if candidate.exists() or candidate.parent.exists():
            return candidate
    return candidates[0]


def read_md(path: Path) -> str:
    encodings = ["utf-8", "gbk", "cp1252"]
    for encoding in encodings:
        try:
            with io.open(path, "r", encoding=encoding) as f:
                return f.read()
        except Exception:
            continue
    raise RuntimeError(f"无法读取文件，尝试不同编码均失败: {path}")


def normalize_headings(md_text: str) -> str:
    lines = md_text.splitlines()
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
                text = html.escape(heading_match.group(2).strip())
                result.append(f"<h{level}>{text}</h{level}>")
                continue

        result.append(line)

    return "\n".join(result)


def convert(md_text: str) -> str:
    return markdown(md_text, extensions=["extra", "tables", "toc", "nl2br"])


def build_html_document(
    body_html: str,
    background_image_uri: str,
    title: str = "自动化报告",
    base_href: str | None = None,
) -> str:
    base_tag = f'    <base href="{html.escape(base_href)}" />\n' if base_href else ""
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"utf-8\" />
    <title>{html.escape(title)}</title>
{base_tag}    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <style>
        @page {{
            size: A4;
            margin: 0;
        }}
        html, body {{
            width: 100%;
            height: 100%;
        }}
        body {{
            font-family: "Arial", "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
            font-size: 15pt;
            line-height: 1.7;
            color: #222;
            margin: 0;
        }}
        .page-bg {{
            position: fixed;
            right: 0;
            bottom: 0;
            width: {A4_WIDTH_MM}mm;
            height: {A4_HEIGHT_MM}mm;
            background-image: url('{background_image_uri}');
            background-size: 100% 100%;
            background-position: right bottom;
            background-repeat: no-repeat;
            opacity: 1;
            z-index: 0;
            pointer-events: none;
        }}
        .layout-table {{
            width: 100%;
            border: none;
            border-collapse: collapse;
            position: relative;
            z-index: 2;
            background: transparent;
            margin: 0;
        }}
        .layout-table th, .layout-table td {{
            border: none;
            padding: 0;
            background: transparent;
        }}
        .header-space {{
            height: 14mm;
        }}
        .footer-space {{
            height: {FOOTER_SAFE_SPACE_MM}mm;
        }}
        .content {{
            width: 100%;
            box-sizing: border-box;
            padding: 0 16mm 16mm;
        }}
        .cover-wrapper {{
            text-align: center;
            padding-top: 15mm;
            min-height: auto;
            page-break-inside: avoid;
        }}
        .cover-wrapper h2 {{
            font-size: 26pt;
            font-weight: bold;
            margin: 15mm 0;
            color: #222;
        }}
        .toc-block {{
            page-break-inside: avoid;
            break-inside: avoid-page;
            margin: 0 auto;
            padding: 2mm 1mm 0;
            width: 100%;
            max-width: 170mm;
            background: transparent;
            border: none;
        }}
        .toc-title {{
            text-align: center;
            font-size: 14pt;
            font-weight: 700;
            margin: 0 0 5mm;
            letter-spacing: 1px;
            color: #1f2d3d;
        }}
        .toc-line {{
            display: flex;
            align-items: baseline;
            gap: 6px;
            font-size: 11.5pt;
            line-height: 1.35;
            margin: 1.2mm 0;
            color: #1d2a39;
        }}
        .toc-item {{
            white-space: nowrap;
        }}
        .toc-dots {{
            flex: 1;
            border-bottom: 1px dotted #2f4256;
            transform: translateY(-1px);
        }}
        .toc-page {{
            min-width: 10mm;
            text-align: right;
            white-space: nowrap;
        }}
        .content > :last-child {{
            margin-bottom: 0;
        }}
        .textbox-block {{
            margin: 8px 0 10px;
            padding: 6px 10px;
            border: 1px solid #bdbdbd;
            background: #f3f3f3;
        }}
        .textbox-block pre {{
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: "Microsoft YaHei", "PingFang SC", "SimSun", sans-serif;
            font-size: 10.5pt;
            line-height: 1.5;
        }}
        table.report-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            background: #ffffff;
            font-size: 10.5pt;
            border-top: 1px solid #2a5da8;
            border-bottom: 1px solid #8aa3c7;
        }}
        table.report-table th, table.report-table td {{
            border: none;
            padding: 4px 8px;
            vertical-align: top;
        }}
        table.report-table th {{
            background: #1f5aa6;
            color: #ffffff;
            font-weight: 400;
            text-align: left;
        }}
        table.report-table p {{
            margin: 0.2em 0;
        }}
        h1, h2, h3 {{
            color: #1f2d3d;
            margin-top: 0.9em;
            margin-bottom: 0.5em;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 8px auto;
        }}
        p {{
            margin: 0.45em 0;
        }}
    </style>
</head>
<body>
    <div class=\"page-bg\"></div>

    <table class=\"layout-table\">
        <thead>
            <tr><td><div class=\"header-space\"></div></td></tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    <main class=\"content\">{body_html}</main>
                </td>
            </tr>
        </tbody>
        <tfoot>
            <tr><td><div class=\"footer-space\"></div></td></tr>
        </tfoot>
    </table>
</body>
</html>
"""


def split_cover_and_body(md_text: str) -> tuple[str, str]:
    sections = md_text.split(BODY_START_MARKER, maxsplit=1)
    if len(sections) == 2:
        return sections[0].strip(), sections[1].strip()
    return "", md_text.strip()


def collect_heading_pages(html_path: Path) -> list[dict[str, int | str]]:
    if not html_path.exists():
        raise FileNotFoundError(f"临时 HTML 不存在: {html_path}")

    with sync_playwright() as p:
        browser = _launch_chromium_browser(p)

        page = browser.new_page(viewport={"width": 794, "height": 1122}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.wait_for_timeout(100)

        heading_data = page.evaluate(
            f"""() => {{
                const pageHeight = {PAGE_CONTENT_HEIGHT_PX};
                const headings = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
                    .filter(el => !el.closest('.toc-block') && !el.closest('.cover-wrapper'))
                    .map(el => {{
                        const text = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                        const rect = el.getBoundingClientRect();
                        return {{
                            text,
                            top: rect.top,
                            page: Math.floor(rect.top / pageHeight) + 1,
                        }};
                    }})
                    .filter(item => item.text);
                return headings;
            }}"""
        )
        browser.close()

    return heading_data


def replace_toc_page_numbers(body_html: str, page_numbers: list[int]) -> str:
    toc_page_pattern = re.compile(r"<span class='toc-page'>(.*?)</span>")
    page_iter = iter(page_numbers)

    def repl(match: re.Match[str]) -> str:
        try:
            page_number = next(page_iter)
        except StopIteration:
            return match.group(0)
        return f"<span class='toc-page'>{page_number}</span>"

    return toc_page_pattern.sub(repl, body_html)


def collect_heading_pages_from_pdf(pdf_path: Path, heading_texts: list[str]) -> list[int]:
    if PdfReader is None:
        raise RuntimeError(INSTALL_PYPDF_HINT)

    reader = PdfReader(str(pdf_path))
    pages_text: list[str] = []
    toc_last_page_index = -1

    for page in reader.pages:
        text = page.extract_text() or ""
        normalized = re.sub(r"\s+", "", text)
        pages_text.append(normalized)
        if normalized.startswith("目录"):
            toc_last_page_index = len(pages_text) - 1

    page_numbers: list[int] = []
    search_start_page = max(1, toc_last_page_index + 2)

    for heading in heading_texts:
        heading_normalized = re.sub(r"\s+", "", heading)
        if not heading_normalized:
            continue

        page_number = None
        for page_index in range(search_start_page - 1, len(pages_text)):
            if heading_normalized in pages_text[page_index]:
                page_number = page_index + 1
                break

        if page_number is None:
            page_number = search_start_page

        page_numbers.append(page_number)
        search_start_page = page_number

    return page_numbers


def _render_html_to_pdf(html_path: Path, output_pdf: Path, show_page_numbers: bool) -> None:
    with sync_playwright() as p:
        browser = _launch_chromium_browser(p)

        page = browser.new_page(viewport={"width": 794, "height": 1122}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(output_pdf),
            format="A4",
            print_background=True,
            display_header_footer=show_page_numbers,
            header_template="<span></span>",
            footer_template=(
                '<div style="font-size: 10pt; text-align: center; width: 100%; '
                'margin-bottom: 4mm; color: #444;">'
                '<span class="pageNumber"></span> / <span class="totalPages"></span></div>'
                if show_page_numbers
                else "<span></span>"
            ),
            margin={
                "top": "0mm",
                "right": "0mm",
                "bottom": f"{BOTTOM_MARGIN_MM}mm",
                "left": "0mm",
            },
        )
        browser.close()


def _merge_pdfs(cover_pdf: Path, body_pdf: Path, merged_pdf: Path) -> None:
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError(INSTALL_PYPDF_HINT)

    writer = PdfWriter()
    for src in (cover_pdf, body_pdf):
        reader = PdfReader(str(src))
        for page in reader.pages:
            writer.add_page(page)

    with merged_pdf.open("wb") as f:
        writer.write(f)


def _get_pdf_page_count(pdf_path: Path) -> int:
    if PdfReader is None:
        raise RuntimeError(INSTALL_PYPDF_HINT)

    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


def build_pdf_from_markdown(md_path: Path, output_pdf: Path) -> None:
    md_path = md_path.resolve()
    output_pdf = output_pdf.resolve()

    if not md_path.exists():
        raise FileNotFoundError(f"找不到输入文件: {md_path}")

    md_text = read_md(md_path)
    md_text = normalize_headings(md_text)
    cover_md, body_md = split_cover_and_body(md_text)
    base_href = md_path.parent.as_uri().rstrip("/") + "/"

    background_image_path = md_path.parent / "images" / "pdf_bg.png"
    if not background_image_path.exists():
        fallback_background = FALLBACK_BACKGROUND_PATH
        if fallback_background.exists():
            background_image_path = fallback_background
        else:
            raise FileNotFoundError(f"背景图片不存在: {background_image_path}")

    body_html = convert(body_md)

    temp_html = output_pdf.parent / f"_{output_pdf.stem}_body_temp.html"
    body_pdf = output_pdf.parent / f"_{output_pdf.stem}_body.pdf"
    cover_pdf = output_pdf.parent / f"_{output_pdf.stem}_cover.pdf"
    measure_pdf = output_pdf.parent / f"_{output_pdf.stem}_measure.pdf"
    cover_page_offset = 0

    try:
        if cover_md:
            cover_html = convert(cover_md)
            cover_html_doc = build_html_document(
                cover_html,
                background_image_path.as_uri(),
                title=md_path.stem,
                base_href=base_href,
            )
            temp_cover_html = output_pdf.parent / f"_{output_pdf.stem}_cover_temp.html"
            try:
                temp_cover_html.write_text(cover_html_doc, encoding="utf-8")
                _render_html_to_pdf(temp_cover_html, cover_pdf, show_page_numbers=False)
            finally:
                if temp_cover_html.exists():
                    temp_cover_html.unlink()

            cover_page_offset = _get_pdf_page_count(cover_pdf)

        temp_html.write_text(
            build_html_document(
                body_html,
                background_image_path.as_uri(),
                title=md_path.stem,
                base_href=base_href,
            ),
            encoding="utf-8",
        )

        heading_data = collect_heading_pages(temp_html)
        heading_texts = [str(item["text"]) for item in heading_data]

        _render_html_to_pdf(temp_html, measure_pdf, show_page_numbers=True)
        toc_pages = [page + cover_page_offset for page in collect_heading_pages_from_pdf(measure_pdf, heading_texts)]

        if toc_pages:
            body_html = replace_toc_page_numbers(body_html, toc_pages)
            temp_html.write_text(
                build_html_document(
                    body_html,
                    background_image_path.as_uri(),
                    title=md_path.stem,
                    base_href=base_href,
                ),
                encoding="utf-8",
            )

        if cover_md:
            _render_html_to_pdf(temp_html, body_pdf, show_page_numbers=True)
            _merge_pdfs(cover_pdf, body_pdf, output_pdf)
        else:
            _render_html_to_pdf(temp_html, output_pdf, show_page_numbers=True)
    finally:
        for temp_file in (temp_html, body_pdf, cover_pdf, measure_pdf):
            if temp_file.exists():
                temp_file.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("md", help="输入 Markdown 文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出 PDF 文件路径")
    args = parser.parse_args()

    md_path = resolve_path(args.md, must_exist=True)
    output_pdf = resolve_path(args.output, must_exist=False)

    build_pdf_from_markdown(md_path, output_pdf)
    print(f"PDF 报告已生成：{output_pdf}")


if __name__ == "__main__":
    main()
