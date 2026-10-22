# Troubleshooting

## Installation and configuration

| Symptom | Cause | Fix |
|---|---|---|
| `No matching distribution found` | The release is not on PyPI yet | Install from the immutable tag: `python -m pip install "bia-brief @ git+https://github.com/BrainStOrmics/BIA-Brief.git@v0.2.3"` |
| `Model config is required. Run bia-brief-setup once, or pass --config.` | No model configuration was found | Run `bia-brief-setup`, or pass `--config <path>` / set `BIA_BRIEF_CONFIG` |
| `Model config not found: <path>` | The given config path does not exist | Correct the path; the lookup order is `--config`, `BIA_BRIEF_CONFIG`, `~/.bia-brief/config.yaml`, then the legacy checkout config |
| `FAIL dependency: <module>` in `bia-brief-doctor` | A Python dependency is missing | Reinstall the runtime; the checked modules are `deepagents`, `langchain_core`, `langchain_openai`, `langgraph`, `yaml`, and `pypdf` |
| `FAIL resource: .../scRNA/report.md` | The package was installed without its template resources | Reinstall the runtime from the Git tag rather than copying files by hand |
| `bia-brief is not installed` from `scripts/check_bia_brief.py` | The runtime is not importable in this interpreter | Run the check with the same interpreter that will generate reports |

## Project input

| Symptom | Cause | Fix |
|---|---|---|
| `Could not find picture directory under <path> (looked for pics/, pics/figures/, figures/)` | The project has no figure directory | Add `figures/` or `pics/` under the project root |
| `No image files found in <dir>` | The figure directory is empty | Check that the analysis actually wrote image files into it |
| `Image file <path> does not exist` | `index.md` points at a figure that is gone | Re-run the indexer so the image table matches the files on disk |
| `Project path does not exist: <path>` | The project id resolved to nothing | Run from the directory that contains `projects/`, or pass an absolute path |
| `FAIL project inputs: <path>` in `bia-brief-doctor` | Neither `figures/` nor `pics/` exists | Same as the first row |

## Model and indexer

| Symptom | Cause | Fix |
|---|---|---|
| The indexer returns nothing, or captions stay empty | The vision model is unreachable or the key is wrong | Check the endpoint and key in `config.yaml`; the vision model must be able to read images |
| Figures are classified into the wrong analysis step | The captions in `index.md` are wrong | Edit `index.md` captions, or re-run the indexer with a better vision model |
| The report is generic and lacks project context | `project_info.md` is missing or empty | Add it — the background text is assembled from that file |
| The request fails with a `reasoning_content` or `400` error | The provider rejects a request shape the runtime sends | Use a different model endpoint, or one that accepts the OpenAI-compatible shape |

## PDF export

| Symptom | Cause | Fix |
|---|---|---|
| PDF export fails, or Chromium is reported missing | Playwright's browser is not installed | `playwright install chromium` |
| Chinese text is garbled in the PDF | No CJK font available to the renderer | Install a CJK font on the system |
| `GBK` codec error on Windows | The console codepage cannot encode the output | Set `PYTHONIOENCODING=utf-8` or use a UTF-8 terminal |
| The PDF has no page background or wave decoration | The packaged background asset is missing | Reinstall the runtime; `templates/assets/BGI_SY/pics/` must ship with the package |
| Figures appear as white rectangles on a slightly darker page | The runtime is older than 0.2.2 | Upgrade to `v0.2.2` or newer, which uses a pure-white sheet |

## Workflow

- Missing `bia-brief`: install the pinned release before retrying.
- Missing model config: request a local configuration path; never ask the user
  to paste an API key into chat.
- Missing figures: stop and ask for the correct project directory.
- Interactive review pause: retain the same process and follow the prompt, or
  use the configured automatic approval mode for unattended batch runs.
- `bia-brief-batch --all` covers every project under `projects/`; confirm the
  scope before running it, and use `--stop-on-failure` to halt at the first
  error.
