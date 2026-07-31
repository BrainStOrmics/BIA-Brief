# BIA-Brief Report Skill

This directory packages the `bia-brief-report` Agent Skill. It teaches an
agent how to inspect a bioinformatics project and use the installed BIA-Brief
runtime to produce and verify Markdown, PDF, and LaTeX reports.

The Skill contains workflow instructions; the report engine is installed
separately as the pinned `bia-brief==0.2.1` Python package.

## Quick Start

```powershell
python -m pip install "bia-brief==0.2.1"
playwright install chromium
bia-brief-setup
bia-brief-project <project-id-or-path>
```

Run `bia-brief-setup` only for the first model configuration, or when changing
providers. Subsequent project and batch commands reuse the saved configuration.

## Directory Layout

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

## Installation

Install this directory with an Agent Skills-compatible skill manager, or copy
it into the agent's skills directory. Then install the pinned runtime in the
environment that will generate reports:

```powershell
python -m pip install "bia-brief==0.2.1"
playwright install chromium
```

If PyPI does not contain the release, use the immutable Git tag:

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.1"
```

## One-Time Model Setup

Run the setup wizard once in the same environment:

```powershell
bia-brief-setup
```

It saves chat and vision model settings to `~/.bia-brief/config.yaml` and
does not echo API keys. Later report commands discover this file automatically.
Use `BIA_BRIEF_CONFIG` or `--config` only to select a different configuration.

Configuration lookup order is:

1. Explicit `--config <path>`
2. `BIA_BRIEF_CONFIG`
3. `~/.bia-brief/config.yaml`
4. The legacy source-checkout config, when running directly from a checkout

## Usage

```powershell
bia-brief-doctor --project <project-path>
bia-brief-project <project-id-or-path>
bia-brief-batch project_a project_b
```

The project should contain `figures/` or `pics/`; `project_info.md`,
`scripts/`, and `tables/` improve report context but are optional.

Each successful run produces `report.md`, `report.pdf`, and `report.tex` in the
project output directory. Unless `--no-delivery-copy` is used, the PDF is also
copied to the repository-level `deliverables/` directory.

Before reporting success, inspect the generated PDF and confirm that the main
sections, figures, and table of contents are present. The detailed acceptance
checks are in `references/quality-checklist.md`.

## Agent Compatibility

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

## Release Source

The maintained Skill branch is `codex/bia-brief-skill`. The runtime release is
available from the immutable `v0.2.1` Git tag when PyPI is unavailable:

```text
https://github.com/BrainStOrmics/BIA-Brief/tree/codex/bia-brief-skill
https://github.com/BrainStOrmics/BIA-Brief/tree/v0.2.1
```

## Security Boundary

Do not paste API keys into agent messages. Enter them through
`bia-brief-setup`, keep the generated user config outside Git, and use
`--config` only for an intentional alternate file.
