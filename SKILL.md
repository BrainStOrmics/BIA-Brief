---
name: bia-brief-report
description: Use when a user asks to generate, review, or batch-produce a BIA-Brief bioinformatics report from project metadata, figures, scripts, or tables.
---

# BIA-Brief Report

Use the installed `bia-brief` package as the only report runtime. Do not copy
or modify its source code into the project being reported.

## Install and First Run

Install the Skill through the Codex Skill installer, then install the pinned
runtime and its PDF browser in the active environment:

```powershell
python -m pip install "bia-brief==0.2.1"
playwright install chromium
```

Run `bia-brief-doctor` once. If no model configuration exists, run the
interactive setup wizard:

```powershell
bia-brief-setup
```

The wizard stores the configuration at `~/.bia-brief/config.yaml`. The API
keys are entered interactively and are never printed by the Skill. After this
one-time setup, omit `--config`; the CLI reuses that file automatically. Set
`BIA_BRIEF_CONFIG` only when a different configuration is needed.

If the pinned release is not yet on PyPI, install the immutable Git tag:

```powershell
python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.1"
```

## Run a report

1. Locate the project directory and read `project_info.md` when present.
2. Check that the project contains `figures/` or `pics/`; note missing
   `scripts/` and `tables/` as warnings rather than creating placeholder data.
3. Run the installation check:

   ```powershell
   bia-brief-doctor --project <project-path>
   ```

4. If `bia-brief` is missing, install the pinned `0.2.1` release and Chromium
   as described above.
5. If report generation reports that model configuration is missing, ask the
   user to complete `bia-brief-setup` once. Do not read, print, or echo API
   keys. Do not start report generation until setup succeeds.
6. Preview the assembled background when the user asks to review it:

   ```powershell
   bia-brief-project <project-id-or-path> --print-background
   ```

7. Generate the report. Keep interactive review only when the user requests it;
   otherwise use the configured auto-approval behavior.

   ```powershell
   bia-brief-project <project-id-or-path>
   ```

8. Verify `report.md`, `report.pdf`, and `report.tex` exist in the project
   output directory. Report their absolute paths and the delivery PDF path when
   it was created.

## Batch mode

Use explicit project IDs or `--all` only after confirming the intended scope:

```powershell
bia-brief-batch project_a project_b
bia-brief-batch --all
```

Pass `--config <model-config.yaml>` only when intentionally overriding the
saved user configuration.

Use `--stop-on-failure` when later reports should not run after an error.

## Quality checks

Read [references/quality-checklist.md](references/quality-checklist.md) before
declaring a report complete. Read
[references/project-structure.md](references/project-structure.md) if input
layout or template selection is unclear. Read
[references/troubleshooting.md](references/troubleshooting.md) only when a
command fails.
