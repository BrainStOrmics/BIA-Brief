from __future__ import annotations

import re
from pathlib import Path

import pytest

from Brief.utils.postprocess import build_template_fields
from Brief.utils.parse_md_template import render_report_markdown


def _render(tmp_path: Path, template_text: str) -> str:
    template = tmp_path / "custom-template.md"
    template.write_text(template_text, encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()

    report, _ = render_report_markdown(
        report_template=str(template),
        project_id="PROJECT-42",
        project_path=str(project),
        output_lang="zh-CN",
        pic_abs_dirs=[],
        captions=[],
        section_summaries=[],
        conclusion="",
        discussion="",
        key_takeaways=[],
        template_fields={"Body_Content": "body"},
        output_path=str(project / "output" / "report.md"),
    )
    return report


def test_project_id_is_rendered(tmp_path: Path) -> None:
    report = _render(tmp_path, "{{Project_ID}}\n\n{{Body_Content}}")

    assert "PROJECT-42" in report
    assert "{{Project_ID}}" not in report


def test_unknown_placeholder_fails_instead_of_rendering_empty(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unfilled"):
        _render(tmp_path, "{{Body_Content}}\n{{Unknown_Field}}")


@pytest.mark.parametrize("family", ["scRNA", "spatial", "standard"])
def test_builtin_templates_render_all_required_fields(
    tmp_path: Path,
    family: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    template = Path(__file__).resolve().parents[1] / "templates" / family / "report.md"
    fields = build_template_fields(
        {"body_md": "body"},
        report_title="Title",
        project_id="PROJECT-42",
    )
    fields.update(
        {
            "Table_Project_Info": "",
            "Table_QC": "",
            "Table_Mapping": "",
            "Table_Gene_Capture": "",
        }
    )

    report, _ = render_report_markdown(
        report_template=str(template),
        project_id="PROJECT-42",
        project_path=str(project),
        output_lang="zh-CN",
        pic_abs_dirs=[],
        captions=[],
        section_summaries=[],
        conclusion="",
        discussion="",
        key_takeaways=[],
        template_fields=fields,
        output_path=str(project / "output" / "report.md"),
    )

    assert "PROJECT-42" in report
    assert "body" in report
    assert not re.findall(r"{{\s*[^{}]+\s*}}", report)
