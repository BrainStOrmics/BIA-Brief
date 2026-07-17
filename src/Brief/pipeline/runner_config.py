from __future__ import annotations

from pathlib import Path
from typing import Any
from copy import deepcopy

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "run_config.yaml"
DEFAULT_CONFIG: dict[str, Any] = {
    "runner": {
        "projects_root": "projects",
        "project_output_dir": "output",
        "deliverables_dir": "deliverables",
        "batch_log_dir": "logs/batch",
        "default_template": "scRNA",
        "default_lang": "zh-CN",
        "auto_approve": True,
        "project_input_dirs": ["figures", "pics"],
        "templates": {
            "scRNA": "templates/scRNA/report.md",
            "spatial": "templates/spatial/report.md",
            "standard": "templates/standard/report.md",
        },
    }
}


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


def load_runner_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH
    config = deepcopy(DEFAULT_CONFIG)
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Runner config must be a mapping: {path}")
        config = _deep_update(config, loaded)
    return config
