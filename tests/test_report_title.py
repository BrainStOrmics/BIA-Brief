from __future__ import annotations

from pathlib import Path

import pytest

from Brief.pipeline.project_info_background import parse_report_title, read_report_title


def _write_project_info(project: Path, body: str) -> Path:
    (project / "project_info.md").write_text(body, encoding="utf-8")
    return project


def test_report_title_is_read_verbatim() -> None:
    assert parse_report_title("报告名称：牛脂肪组织单细胞分析") == "牛脂肪组织单细胞分析"


def test_report_title_keeps_a_colon_inside_the_value() -> None:
    """A colon inside the title must not truncate it."""
    assert parse_report_title("报告名称：Project: Final Report") == "Project: Final Report"


def test_report_title_accepts_a_half_width_colon() -> None:
    assert parse_report_title("报告名称:单细胞分析报告") == "单细胞分析报告"


def test_report_title_is_empty_when_the_field_is_missing() -> None:
    assert parse_report_title("项目名称：示例项目") == ""


def test_report_title_is_empty_when_the_value_is_blank() -> None:
    assert parse_report_title("报告名称：") == ""


def test_report_title_reads_the_first_occurrence() -> None:
    text = "报告名称：第一个\n报告名称：第二个\n"
    assert parse_report_title(text) == "第一个"


def test_read_report_title_returns_empty_without_project_info(tmp_path: Path) -> None:
    assert read_report_title(tmp_path) == ""


def test_read_report_title_reads_the_project_file(tmp_path: Path) -> None:
    project = _write_project_info(tmp_path, "报告名称：示例报告\n")
    assert read_report_title(project) == "示例报告"


def test_agent_title_file_is_used_when_project_info_has_no_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The agent-written title only fills in when project_info.md has no name."""
    from Brief.core import _read_agent_title

    title_file = tmp_path / "report.md.title"
    title_file.write_text("Agent 生成的标题\n", encoding="utf-8")
    assert _read_agent_title(str(title_file)) == "Agent 生成的标题"


def test_agent_title_file_is_empty_when_missing(tmp_path: Path) -> None:
    from Brief.core import _read_agent_title

    assert _read_agent_title(str(tmp_path / "absent.title")) == ""

