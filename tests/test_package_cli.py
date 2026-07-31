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
