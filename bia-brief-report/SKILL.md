---
name: bia-brief-report
description: Generate, review, or batch-produce BIA-Brief bioinformatics reports from project metadata, figures, scripts, and tables. Use when the user asks to create a Markdown, PDF, or LaTeX bioinformatics report with BIA-Brief, inspect report readiness, or run reports for one or more projects.
---

# BIA-Brief Report

Use the installed `bia-brief` package as the only report runtime. Do not copy
or modify its source code into the project being reported.

## Run a report

1. Locate the project directory and read `project_info.md` when present.
2. Check that the project contains `figures/` or `pics/`; note missing
   `scripts/` and `tables/` as warnings rather than creating placeholder data.
3. Run the installation check:

   ```powershell
   bia-brief-doctor --project <project-path>
   ```

4. If `bia-brief` is missing, install a released version:

   ```powershell
   python -m pip install "bia-brief>=0.2,<0.3"
   ```

   For a GitHub release before PyPI publication, install the immutable tag:

   ```powershell
   python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.0"
   ```

5. Require a model configuration file without reading or exposing its API key.
   Pass its path with `--config`, or let the user set `BIA_BRIEF_CONFIG`.
6. Preview the assembled background when the user asks to review it:

   ```powershell
   bia-brief-project <project-id-or-path> --config <model-config.yaml> --print-background
   ```

7. Generate the report. Keep interactive review only when the user requests it;
   otherwise use the configured auto-approval behavior.

   ```powershell
   bia-brief-project <project-id-or-path> --config <model-config.yaml>
   ```

8. Verify `report.md`, `report.pdf`, and `report.tex` exist in the project
   output directory. Report their absolute paths and the delivery PDF path when
   it was created.

## Batch mode

Use explicit project IDs or `--all` only after confirming the intended scope:

```powershell
bia-brief-batch project_a project_b --config <model-config.yaml>
bia-brief-batch --all --config <model-config.yaml>
```

Use `--stop-on-failure` when later reports should not run after an error.

## Quality checks

Read [references/quality-checklist.md](references/quality-checklist.md) before
declaring a report complete. Read
[references/project-structure.md](references/project-structure.md) if input
layout or template selection is unclear. Read
[references/troubleshooting.md](references/troubleshooting.md) only when a
command fails.
