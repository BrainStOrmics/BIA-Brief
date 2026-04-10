# BIA-Brief

Multi-modal report generation prototype for bioinformatics projects. BIA-Brief uses LangGraph to orchestrate a workflow that combines figures, analysis scripts, and background context to produce publication-style captions, section summaries, discussions, and conclusions in English or Chinese.

The project is currently optimized for single-cell and single-nucleus transcriptomics workflows, where a project folder already contains figures and supporting scripts that need to be turned into structured report text.

## Highlights

- Automatically discovers images under `pics/` and optional scripts under `scripts/`.
- Uses a multimodal model to generate figure captions and section summaries.
- Uses a text model to synthesize multiple section summaries into discussion and conclusion sections.
- Includes Markdown-to-PDF utilities for final report formatting.
- Supports custom model configuration, output language, and report templates.

## Project Layout

```text
src/Brief/
  core.py            # Main entry point and Brief class
  config/            # Model and runtime configuration
  graph/             # LangGraph workflows and subgraphs
  prompts/           # Prompt templates
  utils/             # File, I/O, and PDF helpers
template/            # Report templates and cover assets
pics/                # Example figures
scripts/             # Example analysis scripts
local_tests/         # Local test scripts and outputs
```

## Installation

Create a dedicated Python environment and install the dependencies:

```bash
pip install -r requirements.txt
```

If you use Conda, activate your environment first and then install the requirements.

## Configuration

Model settings live in [src/Brief/config/config.yaml](src/Brief/config/config.yaml).
If you prefer a template first, start from [src/Brief/config/config.yaml.example](src/Brief/config/config.yaml.example).

You will need to fill in:

- `CHAT_MODEL_API`: API key, base URL, and model name for the text model.
- `MULTIMODAL_CHAT_MODEL_API`: configuration for the vision-capable model.
- `ENABLE_THINKING`: whether to enable model-side reasoning features.
- `ENABLE_SEARCH`: whether to enable web search capabilities.

## Input Folder Convention

By default, the project treats the provided `project_path` as the project root and reads content in the following way:

- `pics/`: required, and must contain at least one image.
- `scripts/`: optional; if present, the first script found will be used as contextual input.

Your project folder should therefore look something like this:

```text
your_project/
  pics/
    figure_1.png
    figure_2.png
  scripts/
    analysis.py
```

## Quick Start

Minimal example:

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
        "background": "Describe the research background, analysis goal, and data context here.",
        "output_lang": "en-US",
        "report_template": "template/repo.md",
    },
    project_id="p01",
)

print(report_md)
print(report_dict)
```

## Local Test

The repository includes a batch caption test script that checks whether the multimodal subgraph can process images under `pics/`:

```bash
python local_tests/generate_caption_test.py
```

The script writes structured output to [local_tests/output/generate_caption_result.json](local_tests/output/generate_caption_result.json).

## Output

The current workflow produces three main layers of content:

- Captions: descriptive titles and figure legends for individual images.
- Section summaries: integrated summaries that combine image, script, and background context.
- Discussion and conclusion: higher-level narrative generated from multiple section summaries.

In the intended workflow, these outputs are then assembled into a Markdown report template and exported to PDF.

## Use Cases

- Organizing single-cell or single-nucleus transcriptomics reports.
- Archiving figures and analysis results from bioinformatics projects.
- Turning analysis plots, scripts, and context into writing-ready draft text for reports or papers.

## Current Status

BIA-Brief is a prototype. The figure-caption and section-summary chain is in place, but the full report assembly and PDF export pipeline is still being completed. If you plan to use it in a production workflow, validate your own templates and model settings end-to-end first.

## Dependencies

Key dependencies include:

- LangChain / LangGraph
- OpenAI-compatible text and multimodal models
- PyYAML
- markdown, pypdf, and playwright

See [requirements.txt](requirements.txt) for the full dependency list.

## Acknowledgements

This project is designed to help automate bioinformatics reporting during the early stages of project summaries, result organization, and manuscript drafting.
