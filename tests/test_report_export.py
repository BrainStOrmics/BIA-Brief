from __future__ import annotations

from pathlib import Path

import pytest

from Brief.core import _write_report_exports


def test_required_exports_are_created_and_validated(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "report.md"
    report.write_text("report", encoding="utf-8")

    def write_pdf(_report: Path, output: Path) -> None:
        output.write_bytes(b"%PDF-1.4")

    def write_tex(_report: Path, output: Path) -> None:
        output.write_text("\\documentclass{article}", encoding="utf-8")

    monkeypatch.setattr("Brief.core.build_pdf_from_markdown", write_pdf)
    monkeypatch.setattr("Brief.core.build_latex_from_markdown", write_tex)
    monkeypatch.setattr("Brief.core._pdf_page_count", lambda _path: 1)

    exports = _write_report_exports(report)

    assert exports.pdf_path.is_file()
    assert exports.tex_path.is_file()


def test_pdf_failure_is_not_reported_as_success(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "report.md"
    report.write_text("report", encoding="utf-8")

    def fail_pdf(_report: Path, _output: Path) -> None:
        raise RuntimeError("Chromium missing")

    monkeypatch.setattr("Brief.core.build_pdf_from_markdown", fail_pdf)

    with pytest.raises(RuntimeError, match="Chromium missing"):
        _write_report_exports(report)


def test_empty_latex_output_fails(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "report.md"
    report.write_text("report", encoding="utf-8")

    def write_pdf(_report: Path, output: Path) -> None:
        output.write_bytes(b"%PDF-1.4")

    def write_empty_tex(_report: Path, output: Path) -> None:
        output.write_bytes(b"")

    monkeypatch.setattr("Brief.core.build_pdf_from_markdown", write_pdf)
    monkeypatch.setattr("Brief.core.build_latex_from_markdown", write_empty_tex)
    monkeypatch.setattr("Brief.core._pdf_page_count", lambda _path: 1)

    with pytest.raises(RuntimeError, match="LaTeX was not created"):
        _write_report_exports(report)
