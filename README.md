# BIA-Brief

Automated bioinformatics report generation system. BIA-Brief takes figures, analysis scripts, and research background, then produces a professional-grade Markdown report (with optional PDF export) in English or Chinese.

Optimized for single-cell / single-nucleus transcriptomics projects, but adaptable to any bioinformatics domain.

## Architecture

```text
Indexer → ReAct Agent (w/ HITL interrupts) → Post-process → PDF
```

| Step | Model | Responsibility |
|------|-------|----------------|
| **Indexer** | Multimodal (vision) | Scans `pics/` and `scripts/`, classifies figures by analysis step, generates captions and section summaries in parallel |
| **ReAct Agent** | Text (reasoning) | Reads index, follows guides, assembles full report — with HITL interrupts for human review |
| **Post-process** | — (deterministic) | Paragraph wrapping, figure renumbering (fallback), template rendering |
| **PDF export** | — (Playwright) | Converts rendered Markdown to PDF with cover page, TOC, and page numbers |
| **LaTeX export** | — (stdlib) | Converts rendered Markdown to LaTeX with native `\tableofcontents` |

## Project Layout

```text
src/Brief/
  core.py              # Main entry point — Brief class, orchestrates full pipeline
  indexer.py           # Project scanner + analysis step classification + parallel caption/summary generation
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
  prompts/             # LLM prompt templates
    agent.md           #   Agent role and workflow steps
    synthesist.md      #   Used by indexer for multimodal caption generation
    thesis.md          #   Discussion/conclusion generation guide (agent reads at runtime)
    report.md          #   Report assembly guide with section structure and citation rules
    prompt_template.py #   Prompt loading utilities
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
  repo_temp.md         #   Minimal working template
  repo_temp_sc.md      #   scRNA-seq template (used in tests)
  scRNA_base.md        #   scRNA-seq base template
generate-BIA-brief/    # Claude Code Skill package (self-contained)
  SKILL.md             #   Skill definition — workflow steps for Claude Code
  brief_cli.py         #   CLI entry point (index, postprocess, export subcommands)
  config/              #   Skill-specific config (config.yaml.example)
  src/Brief/           #   Subset of core modules (indexer, prompts, utils)
  template/            #   Report templates
  requirements.txt     #   Minimal dependencies for skill mode
local_tests/           # Test scripts and logs (e.g. run_<project>_test.py, run_<project>_batch.py)
  logs/                #   Per-project log files from batch runs
run.py                 # Batch runner across all configured projects
<project_name>/        # Example project folder (e.g. fudan_mouse_25, imu_20)
  pics/                #   Figures
  scripts/             #   Analysis scripts
  tables/              #   Supplementary tables
  output/              #   Generated reports (report.md/.pdf/.tex, index.md)
output/                # Default output location when running from repo root
```

## Platform Support

BIA-Brief runs on both **Linux/macOS** and **Windows**.

The human-in-the-loop (HITL) review step uses platform-specific timeout mechanisms:
- **Linux/macOS**: `signal.SIGALRM` for interrupt-based timeout
- **Windows**: `threading.Timer` (since `SIGALRM` is not available on Windows)

Platform detection is automatic via `sys.platform` — no configuration needed.

### Bypassing HITL for batch runs

Set `BRIEF_AUTO_APPROVE=1` to skip interactive review prompts entirely. Used by `run_fudan_mouse_batch.py` to run multiple projects in parallel as independent subprocesses without blocking on stdin.

```bash
BRIEF_AUTO_APPROVE=1 python run.py
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
    custom_title="单细胞转录组分析报告",  # optional, overrides agent-generated title
)

print(report_md)
```

## generate-BIA-brief: Skill & CLI

The `generate-BIA-brief/` folder is a self-contained package that can be used in two ways:

### As a Claude Code Skill

Copy the folder into your project or register it as a skill, then invoke with `/brief` in Claude Code:

```bash
# Option A: Copy generate-BIA-brief/ into your project, then in Claude Code:
/brief

# Option B: Register as a global skill by symlinking to ~/.claude/skills/
ln -s /path/to/BIA-Brief/generate-BIA-brief ~/.claude/skills/generate-BIA-brief
```

The [SKILL.md](generate-BIA-brief/SKILL.md) defines a 9-step workflow that Claude Code orchestrates through its tool system — environment check, indexer, HITL review, report assembly, and export — all without writing Python code.

### As a standalone CLI

`brief_cli.py` is a standard Python CLI with three subcommands. No Claude Code required:

```bash
# 1. Run indexer — scan pics/scripts, generate captions via multimodal LLM
python brief_cli.py index ./my_project --config config/config.yaml --background "研究背景..." --lang zh-CN

# 2. Post-process — embed figures, renumber, wrap paragraphs
python brief_cli.py postprocess --input output/report.md --index index.md --lang zh-CN

# 3. Export — template rendering + PDF + LaTeX
python brief_cli.py export --input output/report.md --template template/repo_temp.md --title "报告标题" --lang zh-CN
```

Install dependencies first:

```bash
pip install -r generate-BIA-brief/requirements.txt
playwright install chromium   # for PDF export
```

## Input Folder Convention

The `PROJECT_PATH` is treated as the project root and is expected to contain:

```text
your_project/
  pics/               # Required — figures (.png/.jpg/.jpeg/.webp), optionally under pics/figures/
  scripts/            # Optional — analysis scripts (.py/.R)
  tables/             # Optional — supplementary tables referenced by the report
```

## Local Tests

Test scripts follow the naming pattern `run_<project>_test.py` (single-project) or `run_<project>_batch.py` (parallel batch). For example:

```bash
# Single-project end-to-end test
python local_tests/run_imu20_test.py

# Parallel batch run (auto-approves HITL via BRIEF_AUTO_APPROVE=1)
python local_tests/run_fudan_mouse_batch.py

# Batch run across all configured projects
python run.py
```

Each project writes output to its own `<project>/output/` directory:
- `report.md` — generated Markdown report
- `report.pdf` — PDF export
- `report.tex` — LaTeX export (compile with `xelatex report.tex`)
- `index.md` — indexer output with figure captions and analysis pipeline

Batch runs write per-project logs to `local_tests/logs/<project_id>.log`.

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

1. **Captions** — per-figure title, axes/panel descriptions, and analysis step classification
2. **Section summaries** — focused findings and biological interpretation per figure
3. **Discussion + Conclusion + Key Takeaways** — higher-level synthesis across all sections

Figures are automatically sorted by analysis pipeline order (QC → HVG → PCA → Clustering → Markers → Annotation → PAGA) rather than alphabetically, ensuring the report follows a logical analytical narrative.

The final report includes a two-level table of contents, inline figures, citations with a curated bibliography, and a required section structure covering data QC through functional enrichment analysis.

## Template System

Templates use `{{Placeholder}}` syntax. The engine at [parse_md_template.py](src/Brief/utils/parse_md_template.py) performs a single pass of regex substitution on the template file, replacing every `{{Placeholder}}` with its string value.

The body content with all figures, analysis text, discussion, conclusion, and references is generated by the LLM and injected wholesale into `{{Body_Content}}`. The cover area and front matter use dedicated placeholders:

| Placeholder | Source |
|-------------|--------|
| `{{Body_Content}}` | LLM-generated report body (full HTML) |
| `{{Cover_Report_Title}}` | Report title from agent's output (or `custom_title` arg) |
| `{{Cover_Report_Date}}` | Current date (`datetime.now().strftime("%Y-%m-%d")`) |
| `{{Cover_Image_Path}}` | Relative path to `template/BGI_SY/pics/cover.png` |
| `{{Cover_Copyright_Text}}` | Default: `©2026All Rights Reserved` |
| `{{Project_ID}}` | Left empty (present in template front matter, not auto-populated) |
| `{{Table_Project_Info}}` | Left empty (intended for manual project info) |
| `{{Table_QC}}` | Left empty (intended for QC statistics) |
| `{{Table_Mapping}}` | Left empty (intended for mapping statistics) |
| `{{Table_Gene_Capture}}` | Left empty (intended for gene capture statistics) |

Note: The `Project_ID` and `Table_*` placeholders are present in the template front matter but are not auto-populated by the current pipeline. They render as empty sections, intended for manual completion of sample-level statistics.

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
