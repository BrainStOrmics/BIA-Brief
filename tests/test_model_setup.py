from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from Brief.config.setup import (
    DEFAULT_USER_CONFIG_PATH,
    interactive_setup,
    resolve_model_config_path,
    write_model_config,
)


def test_user_config_is_used_when_no_explicit_config_is_given(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("llm_config: {}\n", encoding="utf-8")
    monkeypatch.setenv("BIA_BRIEF_HOME", str(tmp_path))

    assert resolve_model_config_path() == config_path
    assert DEFAULT_USER_CONFIG_PATH.name == "config.yaml"


def test_missing_explicit_config_does_not_fall_back_to_user_config(tmp_path: Path, monkeypatch) -> None:
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "config.yaml").write_text("llm_config: {}\n", encoding="utf-8")
    monkeypatch.setenv("BIA_BRIEF_HOME", str(user_dir))

    with pytest.raises(FileNotFoundError, match="Model config not found"):
        resolve_model_config_path(tmp_path / "missing.yaml")


def test_setup_writes_chat_and_multimodal_config_without_printing_secret(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    output = write_model_config(
        path=config_path,
        chat_api_key="chat-secret",
        chat_url="https://chat.example/v1",
        chat_model="chat-model",
        mm_api_key="vision-secret",
        mm_url="https://vision.example/v1",
        mm_model="vision-model",
    )

    content = config_path.read_text(encoding="utf-8")
    assert output == config_path
    assert "chat-model" in content
    assert "vision-model" in content
    assert "chat-secret" in content
    assert "vision-secret" in content


def test_interactive_setup_does_not_echo_api_keys(tmp_path: Path, capsys) -> None:
    answers = iter(["https://chat.example/v1", "chat-model", "", "", ""])
    secrets = iter(["chat-secret", ""])

    output = interactive_setup(
        output_path=tmp_path / "config.yaml",
        input_fn=lambda _prompt: next(answers),
        secret_fn=lambda _prompt: next(secrets),
    )

    assert output.is_file()
    assert "chat-secret" not in capsys.readouterr().out
