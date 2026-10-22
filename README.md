# BIA-Brief Report Skill

This directory packages the `bia-brief-report` Agent Skill. It teaches an
agent how to turn a bioinformatics project — a folder of analysis figures,
scripts, and metadata — into a finished report in Markdown, PDF, and LaTeX.

The Skill contains workflow instructions only. The report engine is the
`bia-brief` Python package, installed separately as the pinned 0.2.4 release.

There are two ways to use it:

- **Ask an agent.** Install this directory into your agent's skills directory,
  then say `$bia-brief-report generate a report for my project`. The agent
  reads `SKILL.md` and drives the CLI for you.
- **Run the commands yourself.** Install the runtime and call
  `bia-brief-project` directly. Nothing here requires an agent.

[中文版](README.zh-CN.md)

## What you need before you start

- Python 3.10 or newer
- An OpenAI-compatible endpoint and API key for a **chat** model and a
  **vision** model — the report engine reads your figures with the vision
  model to classify them and write captions
- Playwright's Chromium, which renders the PDF
- A project folder containing `figures/` or `pics/`
- Network access to the model endpoint. Each run makes several model calls
  and therefore consumes API quota.

## Install

Install this directory with an Agent Skills-compatible skill manager, or copy
it into your agent's skills directory. Then install the pinned runtime in the
environment that will generate reports:

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.4"
playwright install chromium
```

The runtime is not published to PyPI yet, so the immutable Git tag is the
install source. `pip install "bia-brief==0.2.4"` currently fails with
`No matching distribution found`. Once a release reaches PyPI, the shorter
form becomes available:

```powershell
python -m pip install "bia-brief==0.2.4"
```

## Configure your models once

Run the setup wizard once in the same environment:

```powershell
bia-brief-setup
```

It asks for six values — chat endpoint, chat model name, chat API key, vision
endpoint, vision model name, and vision API key. The vision values default to
the chat ones, so pressing Enter at the vision prompts is enough when one
model serves both roles. The API key is read without echo.

Settings are saved to `~/.bia-brief/config.yaml` and reused automatically by
later runs. Configuration lookup order:

1. Explicit `--config <path>`
2. `BIA_BRIEF_CONFIG`
3. `~/.bia-brief/config.yaml`
4. The legacy source-checkout config, when running directly from a checkout

**Keep the key out of chat.** Enter it through `bia-brief-setup`, keep the
generated user config outside Git, and pass `--config` only for an
intentional alternate file.

## Prepare your project

One folder per report:

```text
<project>/
|-- project_info.md        metadata; strongly recommended
|-- figures/ or pics/      analysis figures; required
|-- scripts/               analysis scripts; optional
|-- tables/                supporting tables; optional
`-- output/                generated artifacts
```

`figures/` and `pics/` are both accepted; the indexer looks for
`<project>/pics/figures/`, then `<project>/pics/`, then `<project>/figures/`.
`project_info.md` is what the report background is assembled from — without it
the report still runs, but the narrative context is thinner.

The `project` argument accepts either a path or an id. An id is resolved
against the `projects/` directory relative to your current working directory,
so `bia-brief-project my_project` looks for `./projects/my_project`. Passing
an existing path always wins, which is the safer option outside a checkout.

See [references/project-structure.md](references/project-structure.md) for the
input layout and template selection.

## Run your first report

Check the environment and the project layout first:

```powershell
bia-brief-doctor --project <project-path>
```

It verifies six Python dependencies, the packaged template, and that the
project has a `figures/` or `pics/` directory. Then generate the report:

```powershell
bia-brief-project <project-id-or-path>
```

The run takes a few minutes and goes through four stages:

1. The **indexer** scans the figures, reads the scripts, and writes
   `index.md` with captions and section summaries.
2. The agent drafts an outline. By default this is auto-approved and nothing
   waits for you; add `--interactive-review` to review the outline yourself.
3. The agent writes the report body to `output/report.md`.
4. Figures are embedded, the template is rendered, and the PDF and LaTeX are
   exported.

To check the background text before committing to a run, print it and stop:

```powershell
bia-brief-project <project-id-or-path> --print-background
```

## Read the results

Each successful run produces three files in the project's output directory:

```text
output/report.md     the report source
output/report.pdf    the finished report
output/report.tex    the LaTeX source
```

The PDF is also copied to the repository-level `deliverables/` directory,
named after the `报告名称` field in `project_info.md`. Pass
`--no-delivery-copy` to skip that.

Before reporting success, open the PDF and confirm the main sections, figures,
and table of contents are present. The detailed acceptance checks are in
[references/quality-checklist.md](references/quality-checklist.md).

## When something goes wrong

| Symptom | Likely cause |
|---|---|
| PDF export fails | Playwright Chromium not installed (`playwright install chromium`) |
| Doctor reports a missing project | Project lacks a `figures/` or `pics/` directory |
| `pip install "bia-brief==0.2.4"` fails | The release is not on PyPI yet — use the Git tag command above |
| Template not found | Wrong key or path — use `templates/scRNA/report.md`, `templates/spatial/report.md`, or `templates/standard/report.md` |
| Chinese text garbled in the PDF | Missing Chinese font — ensure the `ctex` LaTeX package or a system CJK font is available |
| Indexer returns nothing | Vision model unavailable — check the API key and base URL in `config.yaml` |
| GBK encoding error on Windows | Set `PYTHONIOENCODING=utf-8` or use a UTF-8 terminal |
| The agent does not offer the skill | The directory is not in the agent's skills directory, or the agent has no skill discovery |

More cases are in [references/troubleshooting.md](references/troubleshooting.md).

## Advanced options

| Option | Effect |
|---|---|
| `--template <key>` | Choose `scRNA` (default), `spatial`, or `standard` |
| `--print-background` | Print the assembled background and exit without generating |
| `--interactive-review` | Pause for outline review instead of auto-approving |
| `--no-delivery-copy` | Do not copy the PDF into `deliverables/` |
| `--config <path>` | Use a specific model configuration for this run |
| `--lang <code>` | Report language, default `zh-CN` |

Batch mode runs several projects in sequence:

```powershell
bia-brief-batch project_a project_b
bia-brief-batch --all
```

`--all` sweeps every project under the `projects/` directory. Confirm the
scope before using it. Add `--stop-on-failure` to halt at the first error.

## For skill integrators

The Skill is a documentation package; this section describes its internals.

```text
bia-brief-skill/
|-- SKILL.md                    # Agent instructions and report workflow
|-- agents/openai.yaml          # Optional Codex/OpenAI display metadata
|-- assets/config.yaml.example  # Example model configuration shape
|-- references/
|   |-- project-structure.md     # Input layout and template guidance
|   |-- quality-checklist.md     # Output acceptance checks
|   `-- troubleshooting.md       # Common failures and remedies
`-- scripts/check_bia_brief.py  # Local installation smoke check
```

The core `SKILL.md` follows the Agent Skills layout (`name`, `description`,
and Markdown instructions), so any agent that implements that convention can
load the workflow. It is not automatically available to every agent: the
agent must support skill discovery or be given this directory explicitly.

| Host type | Skill loading | Runtime requirements | Notes |
|---|---|---|---|
| Codex/OpenAI | Automatic from the skills directory | Python, package, Chromium, model config | `$bia-brief-report` and `agents/openai.yaml` are supported |
| Other Agent Skills-compatible agent | Usually automatic after installation | Same runtime requirements | Load `SKILL.md`; ignore `agents/openai.yaml` if unsupported |
| Plain agent without Skill support | Not automatic | Same runtime requirements | Provide this directory and explicitly instruct the agent to read `SKILL.md` |

The report runtime itself is portable across agents, but every host still
needs Python 3.10+, the pinned package, Playwright Chromium, filesystem access
to the project, and OpenAI-compatible chat and vision endpoints.

The examples use PowerShell because the maintained regression environment is
Windows. On POSIX systems, use the shell's equivalent activation and path
syntax; the Python package supports both Windows and POSIX approval timers.

The maintained Skill branch is `codex/bia-brief-skill`. The runtime release is
available from the immutable `v0.2.4` Git tag:

```text
https://github.com/BrainStOrmics/BIA-Brief/tree/codex/bia-brief-skill
https://github.com/BrainStOrmics/BIA-Brief/tree/v0.2.4
```

`v0.2.2` is the first release whose report pages use a pure-white sheet, so
figures no longer appear as white rectangles on a slightly darker page.
Install this release or newer; `v0.2.1` and earlier still carry the previous
page background.
