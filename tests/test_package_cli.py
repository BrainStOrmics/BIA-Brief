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
