# BIA-Brief

Multi-agent bioinformatics report generation system. BIA-Brief orchestrates a LangGraph workflow that takes figures, analysis scripts, and research background, then produces a professional-grade Markdown report (with optional PDF export) in English or Chinese.

The system is optimized for single-cell / single-nucleus transcriptomics projects, but can adapt to any bioinformatics domain where figures and analysis context are available.

## Architecture

The report generation pipeline consists of four sequential nodes in a LangGraph state graph:

```text
File manager → Summary sections → Generate thesis → Generate report
```

| Node | Model | Responsibility |
|------|-------|----------------|
| **File manager** | — (file system) | Discovers images under `pics/` and optional scripts under `scripts/` |
| **Summary sections** | Multimodal (vision) | Processes each image in parallel — generates figure captions (title + body) and section summaries |
| **Generate thesis** | Text (reasoning) | Synthesizes all section summaries into a coherent discussion, conclusion, and key takeaways |
| **Generate report** | Text (reasoning) | Assembles the full report from all inputs — writes structured body content, table of contents, and references |

## Features

- **Parallel image processing** — all figures analyzed concurrently via `ThreadPoolExecutor`
- **Figure embedding with renumbering** — figures placed near relevant analysis text and auto-renumbered
- **Discussion + Conclusion synthesis** — higher-level narrative generated from individual section summaries
- **Bilingual output** — Chinese and English with formal academic tone
- **Template-driven rendering** — `{{placeholder}}` substitution against customizable templates
- **Automatic PDF export** — PDF generated alongside Markdown

## Project Layout

```text
src/Brief/
  core.py              # Main entry point — Brief class
  config/              # Model and runtime configuration (YAML)
  graph/               # LangGraph state graph and subgraph nodes
    brief.py           #   Main graph: 4-node pipeline
    synthesist.py      #   Subgraph: multimodal caption + summary
    thesis.py          #   Subgraph: discussion/conclusion synthesis
    report.py          #   Subgraph: full report assembly + post-processing
  prompts/             # LLM prompt templates (Markdown)
    synthesist.md      #   Prompt for figure caption generation
    thesis.md          #   Prompt for discussion/conclusion synthesis
    report.md          #   Prompt for report structure and writing
  utils/               # Helpers
    filemanager.py     #   Image/script discovery under project path
    io.py              #   File I/O utilities
    md_to_pdf.py       #   Markdown-to-PDF converter (Playwright)
    prase_md_template.py  # Template placeholder substitution engine
    setup.py           #   System initialization
template/              # Report templates and cover assets
  BGI_SY/              #   Commercial template pack
    cover.md           #   Cover page template
    pics/              #   Cover background / watermark images
  repo.md              #   Commercial delivery template
  repo_temp.md         #   Minimal working template (used in tests)
pics/                  # Example figures
scripts/               # Example analysis scripts
local_tests/           # Test scripts and outputs
  fudan.py             #   End-to-end scRNA-seq report generation test
  generate_caption_test.py
  generate_report_test.py
  output/              #   Generated reports and test results
```

## Installation

Create a Python environment and install dependencies:

```bash
pip install -r requirements.txt

# If using Playwright for PDF export, install the browser:
playwright install chromium
```

If you use Conda, activate your environment first, then install requirements.

## Configuration

Model settings are in [src/Brief/config/config.yaml](src/Brief/config/config.yaml). Start from [config.yaml.example](src/Brief/config/config.yaml.example) if needed.

You need to configure:

- `CHAT_MODEL_API` — API key, base URL, and model name for the text/reasoning model (e.g., GPT-4o, Qwen, DeepSeek)
- `MULTIMODAL_CHAT_MODEL_API` — configuration for the vision-capable model
- `ENABLE_THINKING` — whether to enable model-side reasoning features
- `ENABLE_SEARCH` — whether to enable web search (requires Tavily API key)

## Input Folder Convention

The `project_path` is treated as the project root and is expected to contain:

```text
your_project/
  pics/               # Required — contains analysis figures
    figure_1.png
    figure_2.png
  scripts/            # Optional — analysis script (first found is used)
    scanpy_ppl.py
```

## Quick Start

```python
from Brief.utils.setup import setup_brief
from Brief.config.config import llm_config
from Brief.core import Brief

setup_brief()

brief = Brief(
    chat_model=llm_config.MODELS["chat_model"],
    mmchat_model=llm_config.MODELS["mmchat_model"],
)

report_md, report_dict = brief.Run(
    task="Generate project report",
    input_wrap={
        "project_path": "/path/to/your_project",
        "background": "Describe research background, analysis goals, and data context.",
        "output_lang": "zh-CN",
        "report_template": "template/repo_temp.md",
    },
    project_id="p01",
)

print(report_md)
```

## PDF Export

PDF conversion runs automatically as the final step of report generation — the `.pdf` file is created alongside the Markdown output (same path, `.pdf` extension).

The PDF pipeline:
1. Splits the Markdown at `<!-- __BODY_START__ -->` into cover and body sections
2. Renders cover page (without page numbers) as a separate PDF
3. Measures heading positions to update table of contents page numbers
4. Renders body content (with page numbers) and overlays a background watermark
5. Merges cover + TOC + body into a single PDF

## Local Tests

```bash
# End-to-end scRNA-seq report generation (8 figures)
python local_tests/fudan.py

# Caption-only test
python local_tests/generate_caption_test.py

# Report generation test
python local_tests/generate_report_test.py
```

Outputs are written to `local_tests/output/`:
- `auto_report.md` — generated Markdown report
- `*_result.json` — test summary with timing and status

## Output

The pipeline produces three layers of content:

1. **Captions** — per-figure title and concise axes/panel description
2. **Section summaries** — integrated analysis combining image content, script context, and background
3. **Discussion + Conclusion + Key Takeaways** — higher-level synthesis across all sections

These are assembled into a structured Markdown report with table of contents, embedded figures, citations, and references.

## Template System

Templates use `{{Placeholder}}` syntax. The engine at [prase_md_template.py](src/Brief/utils/prase_md_template.py) performs a single pass of regex substitution on the template file, replacing every `{{Placeholder}}` with its string value.

The body content with all figures, analysis text, discussion, conclusion, and references is generated by the LLM and injected wholesale into `{{Body_Content}}`. The cover area has a few dedicated placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{Body_Content}}` | LLM-generated report body (full HTML) |
| `{{Cover_Report_Title}}` | `cover_report_title` from report output, or falls back to `report_title` |
| `{{Cover_Report_Date}}` | Current date (`datetime.now().strftime("%Y-%m-%d")`) |
| `{{Cover_Image_Path}}` | Relative path to `template/BGI_SY/pics/cover.png` |
| `{{Cover_Copyright_Text}}` | Default: `©2026All Rights Reserved` |

Custom placeholders can be passed via `template_fields` in the `input_wrap` — they will be substituted into the template if defined, or replaced with an empty string if not.

## Dependencies

Key dependencies:

- **LangChain / LangGraph** — multi-agent orchestration
- **OpenAI-compatible API** — text and multimodal models
- **PyYAML** — configuration
- **markdown + pypdf + playwright** — PDF export
- **Pillow** — image handling

See [requirements.txt](requirements.txt) for the full list.

## Acknowledgements

Designed to automate bioinformatics report generation for early-stage project summaries, result organization, and manuscript drafting.
