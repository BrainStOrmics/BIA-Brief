# BIA-Brief

Automated bioinformatics report generation system. BIA-Brief takes figures, analysis scripts, and research background, then produces a professional-grade Markdown report (with optional PDF export) in English or Chinese.

Optimized for single-cell / single-nucleus transcriptomics projects, but adaptable to any bioinformatics domain.

## Architecture

```text
Indexer → ReAct Agent (w/ HITL interrupts) → Post-process → PDF
```

| Step | Model | Responsibility |
|------|-------|----------------|
| **Indexer** | Multimodal (vision) | Scans `pics/` and `scripts/`, generates figure captions and section summaries in parallel |
| **ReAct Agent** | Text (reasoning) | Reads index, follows guides, assembles full report — with HITL interrupts for human review |
| **Post-process** | — (deterministic) | Paragraph wrapping, figure renumbering (fallback), template rendering |
| **PDF export** | — (Playwright) | Converts rendered Markdown to PDF with cover page, TOC, and page numbers |

## Project Layout

```text
src/Brief/
  core.py              # Main entry point — Brief class, orchestrates full pipeline
  indexer.py           # Project scanner + parallel caption/summary generation
  agent.py             # ReAct agent definition (langchain.agents.create_agent)
  config/              # Model and runtime configuration (YAML)
    config.py          #   Config class definitions
    config.yaml        #   Actual configuration (gitignored)
    config.yaml.example #   Template config
  tools/               # Generic tools available to the ReAct agent
    file_ops.py        #   read_file, write_file
    indexer_tool.py    #   run_indexer — calls index_project, triggers HITL interrupt
    outline_review.py  #   review_outline — triggers HITL interrupt for outline approval
    task_ops.py        #   create_task_list, mark_task_complete
  prompts/             # LLM prompt templates (English only)
    agent.md           #   Agent role and workflow steps
    synthesist.md      #   Used by indexer for multimodal caption generation
    thesis.md          #   Discussion/conclusion generation guide (agent reads at runtime)
    report.md          #   Report assembly guide (agent reads at runtime)
  utils/               # Helper utilities
    filemanager.py     #   Image/script discovery under project path
    io.py              #   File I/O utilities
    md_to_pdf.py       #   Markdown-to-PDF converter (Playwright)
    md_to_latex.py     #   Markdown-to-LaTeX converter (stdlib only)
    parse_md_template.py  # Template placeholder substitution engine
    postprocess.py     #   Figure embedding, renumbering, paragraph wrapping
    setup.py           #   System initialization
template/              # Report templates and cover assets
  BGI_SY/              #   Commercial template pack
    cover.md           #   Cover page template
    pics/              #   Cover background / watermark images
  repo.md              #   Commercial delivery template
  repo_temp.md         #   Minimal working template (used in tests)
  scRNA_base.md        #   scRNA-seq base template
pics/                  # Example figures
scripts/               # Example analysis scripts
local_tests/           # Test scripts and outputs
  fudan.py             #   End-to-end scRNA-seq report generation test
  generate_caption_test.py
  output/              #   Generated reports and test results
.harness/              # Agent constraint system (rules, runbooks, docs)
```

## Installation

Create a Python environment and install dependencies:

```bash
pip install -r requirements.txt

# If using Playwright for PDF export, install the browser:
playwright install chromium
```

If you use Conda, activate your environment first.

## Configuration

Model settings and project paths are in [src/Brief/config/config.yaml](src/Brief/config/config.yaml). Start from [config.yaml.example](src/Brief/config/config.yaml.example) if needed.

### LLM Configuration

- `CHAT_MODEL_API` — API key, base URL, and model name for the text/reasoning model
- `MULTIMODAL_CHAT_MODEL_API` — configuration for the vision-capable model
- `ENABLE_THINKING` — whether to enable model-side reasoning features
- `ENABLE_SEARCH` — whether to enable web search (requires Tavily API key)

### Brief Configuration

- `PROJECT_PATH` — Root directory containing `pics/` and optional `scripts/`
- `REPORT_TEMPLATE` — Path to the report template Markdown file
- `OUTPUT_DIR` — Output directory (relative to `PROJECT_PATH`)
- `PROJECT_ID` — Project identifier

## Quick Start

```python
from Brief.utils.setup import setup_brief
from Brief.config.config import llm_config, brief_config
from Brief.core import Brief

setup_brief()

# Set project config
brief_config.PROJECT_PATH = "/path/to/your_project"
brief_config.REPORT_TEMPLATE = "template/repo_temp.md"
brief_config.OUTPUT_DIR = "output"
brief_config.PROJECT_ID = "p01"

# Create and run
brief = Brief(
    chat_model=llm_config.MODELS["chat_model"],
    mmchat_model=llm_config.MODELS["mmchat_model"],
)

report_md, report_dict = brief.Run(
    background="Describe research background, analysis goals, and data context.",
    output_lang="zh-CN",
)

print(report_md)
```

## Input Folder Convention

The `PROJECT_PATH` is treated as the project root and is expected to contain:

```text
your_project/
  pics/               # Required — contains 
  scripts/            # Optional — analysis script (first found is used)
    scanpy_ppl.py
```

## Local Tests

```bash
# End-to-end scRNA-seq report generation (8 figures)
python local_tests/fudan.py

# Caption-only test (indexer only, uses cache on second run)
python local_tests/generate_caption_test.py
```

Outputs are written to `local_tests/output/`:
- `report.md` — generated Markdown report
- `report.pdf` — PDF export
- `report.tex` — LaTeX export (compile with `xelatex report.tex`)
- `*_result.json` — test summary with timing and status

## PDF Export

PDF conversion runs automatically as the final step of report generation — the `.pdf` file is created alongside the Markdown output (same path, `.pdf` extension).

The PDF pipeline:
1. Splits the Markdown at `<!-- __BODY_START__ -->` into cover and body sections
2. Renders cover page (without page numbers) as a separate PDF
3. Measures heading positions to update table of contents page numbers
4. Renders body content (with page numbers) and overlays a background watermark
5. Merges cover + TOC + body into a single PDF

## LaTeX Export

LaTeX conversion runs automatically alongside PDF export — the `.tex` file is created alongside the Markdown output (same path, `.tex` extension).

To compile the LaTeX file to PDF:
```bash
xelatex report.tex   # run twice for TOC generation
xelatex report.tex
```

The LaTeX pipeline:
1. Converts cover HTML to `\begin{titlepage}` environment
2. Uses LaTeX-native `\tableofcontents` (replaces HTML TOC block)
3. Converts headings, figures, citations, references, lists, and tables to LaTeX
4. Chinese text supported via `ctex` package
5. No Python dependencies added — uses stdlib only

## Output

The pipeline produces three layers of content:

1. **Captions** — per-figure title and concise axes/panel descriptions
2. **Section summaries** — integrated analysis combining image content, script context, and background
3. **Discussion + Conclusion + Key Takeaways** — higher-level synthesis across all sections

These are assembled into a structured Markdown report with table of contents, embedded figures, citations, and references.

## Template System

Templates use `{{Placeholder}}` syntax. The engine at [parse_md_template.py](src/Brief/utils/parse_md_template.py) performs a single pass of regex substitution on the template file, replacing every `{{Placeholder}}` with its string value.

The body content with all figures, analysis text, discussion, conclusion, and references is generated by the LLM and injected wholesale into `{{Body_Content}}`. The cover area has a few dedicated placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{Body_Content}}` | LLM-generated report body (full HTML) |
| `{{Cover_Report_Title}}` | Report title from agent's output |
| `{{Cover_Report_Date}}` | Current date (`datetime.now().strftime("%Y-%m-%d")`) |
| `{{Cover_Image_Path}}` | Relative path to `template/BGI_SY/pics/cover.png` |
| `{{Cover_Copyright_Text}}` | Default: `©2026All Rights Reserved` |

## Dependencies

Key dependencies:

- **LangChain / LangGraph** — ReAct agent orchestration
- **OpenAI-compatible API** — text and multimodal models
- **PyYAML** — configuration
- **markdown + pypdf + playwright** — PDF export
- **Pillow** — image handling

See [requirements.txt](requirements.txt) for the full list.

## Acknowledgements

Designed to automate bioinformatics report generation for early-stage project summaries, result organization, and manuscript drafting.
