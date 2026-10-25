from pathlib import Path

import pytest

from Brief.cli import _Tee, _resolve_template, main, run_project_cli


def test_packaged_templates_are_available_from_any_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    template = _resolve_template(
        "scRNA",
        {"scRNA": "templates/scRNA/report.md"},
    )
    assert template.is_file()
    assert template.name == "report.md"


def test_dnbc4_alias_resolves_from_the_installed_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    template = _resolve_template(
        "dnbc4",
        {"dnbc4": "templates/standard/report.md"},
    )

    assert template.is_file()
    assert template.parent.name == "standard"


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
    monkeypatch.setattr(
        "Brief.cli.build_project_background",
        lambda *_args, **_kwargs: "background",
    )

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


def test_project_cli_returns_failure_when_report_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    (project / "pics").mkdir(parents=True)

    class DummyConfig:
        MODELS = {"chat_model": object(), "mmchat_model": object()}

    monkeypatch.setattr("Brief.cli._load_models", lambda _config: DummyConfig())
    monkeypatch.setattr(
        "Brief.cli.build_project_background",
        lambda *_args, **_kwargs: "background",
    )

    def fail_run(*_args, **_kwargs):
        raise RuntimeError("PDF export failed")

    monkeypatch.setattr("Brief.core.Brief.Run", fail_run)

    assert run_project_cli([str(project)]) == 1


def test_tee_keeps_interactive_prompts_visible_while_logging() -> None:
    console = []
    log = []

    class Stream:
        def __init__(self, target):
            self.target = target

        def write(self, text):
            self.target.append(text)

        def flush(self):
            pass

    tee = _Tee(Stream(console), Stream(log))
    tee.write("Review prompt")
    tee.flush()

    assert console == ["Review prompt"]
    assert log == ["Review prompt"]


def test_interactive_review_flag_overrides_environment_auto_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    (project / "pics").mkdir(parents=True)
    monkeypatch.setenv("BRIEF_AUTO_APPROVE", "1")

    class DummyConfig:
        MODELS = {"chat_model": object(), "mmchat_model": object()}

    captured: dict[str, object] = {}

    class DummyBrief:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def Run(self, **_kwargs):
            return "", {"report_output_path": "report.md"}

    monkeypatch.setattr("Brief.cli._load_models", lambda _config: DummyConfig())
    monkeypatch.setattr(
        "Brief.cli.build_project_background",
        lambda *_args, **_kwargs: "background",
    )
    monkeypatch.setattr("Brief.core.Brief", DummyBrief)

    assert run_project_cli(
        [str(project), "--interactive-review", "--no-delivery-copy"]
    ) == 0
    assert captured["review_gate"].auto_approve is False
