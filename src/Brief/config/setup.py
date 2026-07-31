"""Persistent model configuration and first-run setup helpers."""

from __future__ import annotations

import getpass
import os
from pathlib import Path
from typing import Callable

import yaml


def user_config_dir() -> Path:
    configured = os.environ.get("BIA_BRIEF_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".bia-brief"


DEFAULT_USER_CONFIG_PATH = user_config_dir() / "config.yaml"


def resolve_model_config_path(explicit: str | Path | None = None) -> Path | None:
    """Resolve model config in explicit, environment, user, then legacy order."""
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"Model config not found: {candidate}")
        return candidate.resolve()

    configured = os.environ.get("BIA_BRIEF_CONFIG")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            raise FileNotFoundError(f"Model config not found: {candidate}")
        return candidate.resolve()

    candidates = [
        user_config_dir() / "config.yaml",
        Path(__file__).resolve().parent / "config.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def write_model_config(
    *,
    path: str | Path,
    chat_api_key: str,
    chat_url: str,
    chat_model: str,
    mm_api_key: str | None = None,
    mm_url: str | None = None,
    mm_model: str | None = None,
) -> Path:
    """Write a complete two-model config and return its absolute path."""
    values = {
        "llm_config": {
            "CHAT_MODEL_API": {
                "api": chat_api_key,
                "url": chat_url,
                "model": chat_model,
                "type": "openai",
            },
            "MULTIMODAL_CHAT_MODEL_API": {
                "api": mm_api_key or chat_api_key,
                "url": mm_url or chat_url,
                "model": mm_model or chat_model,
                "type": "openai",
            },
            "ENABLE_THINKING": True,
            "ENABLE_SEARCH": False,
        },
        "brief_config": {
            "PROJECT_ID": "",
            "PROJECT_PATH": "",
            "REPORT_TEMPLATE": "templates/scRNA/report.md",
            "OUTPUT_DIR": "output",
        },
    }
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(values, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    if os.name != "nt":
        destination.chmod(0o600)
    return destination


def interactive_setup(
    *,
    output_path: str | Path | None = None,
    input_fn: Callable[[str], str] = input,
    secret_fn: Callable[[str], str] = getpass.getpass,
) -> Path:
    """Prompt once for provider settings and persist them for later runs."""
    destination = Path(output_path).expanduser() if output_path else user_config_dir() / "config.yaml"
    print("BIA-Brief first-run model setup")
    print("The API key is stored in the local config file and is never printed.")
    chat_url = input_fn("Chat model endpoint [https://api.openai.com/v1]: ").strip()
    chat_url = chat_url or "https://api.openai.com/v1"
    chat_model = input_fn("Chat model name: ").strip()
    chat_api_key = secret_fn("Chat model API key: ").strip()
    mm_url = input_fn(f"Vision model endpoint [{chat_url}]: ").strip() or chat_url
    mm_model = input_fn(f"Vision model name [{chat_model}]: ").strip() or chat_model
    mm_api_key = secret_fn("Vision model API key (press Enter to reuse chat key): ").strip()
    return write_model_config(
        path=destination,
        chat_api_key=chat_api_key,
        chat_url=chat_url,
        chat_model=chat_model,
        mm_api_key=mm_api_key or chat_api_key,
        mm_url=mm_url,
        mm_model=mm_model,
    )
