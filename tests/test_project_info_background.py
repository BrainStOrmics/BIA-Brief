from __future__ import annotations

from Brief.pipeline.project_info_background import (
    build_project_background,
    parse_project_info,
)


def test_project_intro_preserves_commas_and_semicolons() -> None:
    text = "项目简介：研究脂肪组织，比较不同处理组；解析细胞变化。\n"

    fields = parse_project_info(text)

    assert fields["项目简介"] == ["研究脂肪组织，比较不同处理组；解析细胞变化。"]


def test_project_intro_preserves_continuation_lines() -> None:
    text = "项目简介：第一行，保留逗号。\n第二行继续说明。\n样本ID:\nSAMPLE001\n"

    fields = parse_project_info(text)

    assert fields["项目简介"] == ["第一行，保留逗号。\n第二行继续说明。"]
    assert fields["样本ID"] == ["SAMPLE001"]


def test_free_text_notes_are_included_in_background(tmp_path) -> None:
    (tmp_path / "project_info.md").write_text(
        "项目名称：测试项目\n补充说明：批次信息见附表。\n",
        encoding="utf-8",
    )

    background = build_project_background(tmp_path)

    assert "批次信息见附表" in background


def test_project_intro_does_not_create_double_terminal_punctuation(tmp_path) -> None:
    (tmp_path / "project_info.md").write_text(
        "项目简介：第一句，第二句。\n",
        encoding="utf-8",
    )

    background = build_project_background(tmp_path)

    assert "第二句。。" not in background


def test_generic_background_does_not_claim_single_cell(tmp_path) -> None:
    (tmp_path / "project_info.md").write_text(
        "项目名称：测试项目\n测序技术：bulk RNA-seq\n",
        encoding="utf-8",
    )

    background = build_project_background(tmp_path, analysis_profile="generic")

    assert "单细胞转录组" not in background
    assert "项目数据分析" in background
