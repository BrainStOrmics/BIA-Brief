"""Template resolution and the report-generation contract for each family."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class TemplateSpec:
    """Everything the pipeline needs to know about a report template."""

    key: str
    path: Path
    display_name: str
    body_profile: str
    guide_name: str
    agent_prompt_name: str
    support_level: str = "stable"
    dynamic_figure_start: int = 2


_BUILTIN_SPECS: dict[str, dict[str, str | int]] = {
    "scRNA": {
        "display_name": "scRNA-seq",
        "body_profile": "single_cell",
        "guide_name": "report.md",
        "agent_prompt_name": "agent.md",
        "support_level": "stable",
        "dynamic_figure_start": 2,
    },
    "dnbc4": {
        "display_name": "DNBelab C4 scRNA-seq",
        "body_profile": "single_cell",
        "guide_name": "report.md",
        "agent_prompt_name": "agent.md",
        "support_level": "legacy",
        "dynamic_figure_start": 2,
    },
    "standard": {
        "display_name": "DNBelab C4 scRNA-seq (legacy alias)",
        "body_profile": "single_cell",
        "guide_name": "report.md",
        "agent_prompt_name": "agent.md",
        "support_level": "legacy",
        "dynamic_figure_start": 2,
    },
    "spatial": {
        "display_name": "Stereo-seq spatial",
        "body_profile": "spatial",
        "guide_name": "report_spatial.md",
        "agent_prompt_name": "agent_spatial.md",
        "support_level": "experimental",
        "dynamic_figure_start": 2,
    },
}


def resolve_template_spec(
    value: str,
    templates: Mapping[str, str],
    *,
    package_root: Path,
    cwd: Path | None = None,
) -> TemplateSpec:
    """Resolve a template key or path and attach its report profile."""
    cwd = cwd or Path.cwd()
    configured = templates.get(value, value)
    candidate = Path(configured).expanduser()

    path: Path | None = None
    if candidate.is_absolute() and candidate.is_file():
        path = candidate.resolve()
    elif candidate.is_file():
        path = candidate.resolve()
    else:
        repo_candidate = cwd / candidate
        if repo_candidate.is_file():
            path = repo_candidate.resolve()
        else:
            packaged_candidates: list[Path] = []
            try:
                configured_relative = candidate.relative_to("templates")
            except ValueError:
                pass
            else:
                packaged_candidates.append(
                    package_root / "resources" / "templates" / configured_relative
                )
            packaged_candidates.append(
                package_root / "resources" / "templates" / value / "report.md"
            )
            for packaged in packaged_candidates:
                if packaged.is_file():
                    path = packaged.resolve()
                    break

    if path is None:
        raise FileNotFoundError(f"Template not found: {value}")

    if value in _BUILTIN_SPECS:
        key = value
    elif path.parent.name in _BUILTIN_SPECS:
        key = path.parent.name
    else:
        key = "custom"
        for configured_key, configured_path in templates.items():
            configured_candidate = Path(configured_path).expanduser()
            if configured_candidate.is_file() and configured_candidate.resolve() == path:
                key = configured_key
                break

    if key in _BUILTIN_SPECS:
        spec_data = _BUILTIN_SPECS[key]
    else:
        spec_data = {
            "display_name": "Custom template",
            "body_profile": "generic",
            "guide_name": "report_generic.md",
            "agent_prompt_name": "agent_generic.md",
            "support_level": "custom",
            "dynamic_figure_start": 1,
        }

    return TemplateSpec(
        key=key,
        path=path,
        display_name=str(spec_data["display_name"]),
        body_profile=str(spec_data["body_profile"]),
        guide_name=str(spec_data["guide_name"]),
        agent_prompt_name=str(spec_data["agent_prompt_name"]),
        support_level=str(spec_data["support_level"]),
        dynamic_figure_start=int(spec_data["dynamic_figure_start"]),
    )


def infer_template_spec(report_template: str | Path) -> TemplateSpec:
    """Infer a profile for callers using the library without a CLI spec."""
    path = Path(report_template).expanduser().resolve()
    parent = path.parent.name
    if parent in _BUILTIN_SPECS:
        key = parent
    else:
        key = "custom"
    data = _BUILTIN_SPECS.get(key)
    if data is None:
        data = {
            "display_name": "Custom template",
            "body_profile": "generic",
            "guide_name": "report_generic.md",
            "agent_prompt_name": "agent_generic.md",
            "support_level": "custom",
            "dynamic_figure_start": 1,
        }
    return TemplateSpec(
        key=key,
        path=path,
        display_name=str(data["display_name"]),
        body_profile=str(data["body_profile"]),
        guide_name=str(data["guide_name"]),
        agent_prompt_name=str(data["agent_prompt_name"]),
        support_level=str(data["support_level"]),
        dynamic_figure_start=int(data["dynamic_figure_start"]),
    )
