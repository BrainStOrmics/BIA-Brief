from __future__ import annotations

from pathlib import Path

from Brief.pipeline.template_spec import resolve_template_spec


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "Brief"
TEMPLATES = {
    "scRNA": "templates/scRNA/report.md",
    "dnbc4": "templates/standard/report.md",
    "spatial": "templates/spatial/report.md",
    "standard": "templates/standard/report.md",
}


def test_single_cell_template_uses_the_single_cell_guide() -> None:
    spec = resolve_template_spec(
        "scRNA",
        TEMPLATES,
        package_root=PACKAGE_ROOT,
        cwd=REPO_ROOT,
    )

    assert spec.body_profile == "single_cell"
    assert spec.guide_name == "report.md"
    assert spec.support_level == "stable"
    assert spec.dynamic_figure_start == 2


def test_standard_is_an_explicit_legacy_dnbc4_alias() -> None:
    spec = resolve_template_spec(
        "standard",
        TEMPLATES,
        package_root=PACKAGE_ROOT,
        cwd=REPO_ROOT,
    )

    assert spec.key == "standard"
    assert spec.body_profile == "single_cell"
    assert spec.support_level == "legacy"
    assert "DNBelab C4" in spec.display_name


def test_spatial_template_has_a_spatial_guide_and_is_marked_experimental() -> None:
    spec = resolve_template_spec(
        "spatial",
        TEMPLATES,
        package_root=PACKAGE_ROOT,
        cwd=REPO_ROOT,
    )

    assert spec.body_profile == "spatial"
    assert spec.guide_name == "report_spatial.md"
    assert spec.agent_prompt_name == "agent_spatial.md"
    assert spec.support_level == "experimental"


def test_custom_template_gets_the_generic_profile(tmp_path: Path) -> None:
    custom = tmp_path / "custom.md"
    custom.write_text("{{Body_Content}}", encoding="utf-8")

    spec = resolve_template_spec(
        str(custom),
        TEMPLATES,
        package_root=PACKAGE_ROOT,
        cwd=tmp_path,
    )

    assert spec.key == "custom"
    assert spec.body_profile == "generic"
    assert spec.dynamic_figure_start == 1


def test_explicit_builtin_path_keeps_its_body_profile() -> None:
    spec = resolve_template_spec(
        "templates/scRNA/report.md",
        TEMPLATES,
        package_root=PACKAGE_ROOT,
        cwd=REPO_ROOT,
    )

    assert spec.body_profile == "single_cell"
    assert spec.guide_name == "report.md"
