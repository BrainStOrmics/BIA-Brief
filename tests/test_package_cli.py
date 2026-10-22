from pathlib import Path

import pytest

from Brief.cli import _resolve_template, main, run_project_cli


def test_packaged_templates_are_available_from_any_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    template = _resolve_template(
        "scRNA",
        {"scRNA": "templates/scRNA/report.md"},
    )
    assert template.is_file()
    assert template.name == "report.md"


def test_product_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        run_project_cli(["--help"])
    assert error.value.code == 0
    assert "Generate one BIA-Brief report" in capsys.readouterr().out


def test_top_level_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "BIA-Brief report generation package" in capsys.readouterr().out


def test_project_cli_passes_no_config_for_saved_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "project"
    (project / "pics").mkdir(parents=True)
    seen: list[str | None] = []

    monkeypatch.setattr("Brief.cli._load_models", lambda config: seen.append(config) or object())
    monkeypatch.setattr("Brief.cli.build_project_background", lambda *_args: "background")

    assert run_project_cli([str(project), "--print-background"]) == 0
    assert seen == [None]
    assert "background" in capsys.readouterr().out


def test_delivery_pdf_name_uses_the_resolved_report_title(tmp_path: Path) -> None:
    """The delivery PDF is named from the same title the cover shows."""
    from Brief.cli import _copy_delivery_pdf, _safe_pdf_name

    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    delivery = tmp_path / "deliverables"

    copied = _copy_delivery_pdf(str(pdf), "牛脂肪组织单细胞分析", delivery)

    assert copied is not None
    assert copied.name == "牛脂肪组织单细胞分析.pdf"
    assert _safe_pdf_name("牛脂肪组织单细胞分析") == "牛脂肪组织单细胞分析.pdf"


def test_delivery_pdf_name_sanitizes_path_separators(tmp_path: Path) -> None:
    from Brief.cli import _copy_delivery_pdf

    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    copied = _copy_delivery_pdf(str(pdf), "a/b:c", tmp_path / "deliverables")

    assert copied is not None
    assert copied.name == "a_b_c.pdf"
