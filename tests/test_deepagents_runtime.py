from __future__ import annotations

import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from Brief.pipeline.agent_runtime import ReportFilesystemBackend, build_report_agent, to_virtual_path


def test_runtime_builds_with_deepagents() -> None:
    model = FakeListChatModel(responses=["ok"])
    agent = build_report_agent(
        chat_model=model,
        mmchat_model=model,
        project_path=REPO_ROOT / "projects" / "fudan_mouse_25",
        repo_root=REPO_ROOT,
    )

    assert agent is not None
    assert "model" in agent.get_graph().nodes


def test_virtual_path_is_repo_relative() -> None:
    path = to_virtual_path(
        REPO_ROOT / "projects" / "fudan_mouse_25" / "output" / "report.md",
        REPO_ROOT,
    )

    assert path == "/projects/fudan_mouse_25/output/report.md"


def test_virtual_path_rejects_outside_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside repository root"):
        to_virtual_path(tmp_path / "outside.md", REPO_ROOT)


def test_report_backend_overwrites_generated_artifacts(tmp_path: Path) -> None:
    backend = ReportFilesystemBackend(root_dir=tmp_path, virtual_mode=True)

    assert backend.write("/report.md", "old").error is None
    assert backend.write("/report.md", "new").error is None
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == "new"
