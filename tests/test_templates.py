from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = REPO_ROOT / "templates"
PACKAGED_ROOT = REPO_ROOT / "src" / "Brief" / "resources" / "templates"

FAMILIES = ("scRNA", "spatial", "standard")

REQUIRED_PLACEHOLDERS = {
    "{{Cover_Report_Title}}",
    "{{Cover_Report_Date}}",
    "{{Cover_Image_Path}}",
    "{{Cover_Copyright_Text}}",
    "{{Table_Project_Info}}",
    "{{Table_QC}}",
    "{{Table_Mapping}}",
    "{{Table_Gene_Capture}}",
    "{{Body_Content}}",
}


def _templates() -> list[Path]:
    return [TEMPLATE_ROOT / family / "report.md" for family in FAMILIES]


@pytest.mark.parametrize("family", FAMILIES)
def test_template_exposes_every_placeholder(family: str) -> None:
    """Each family must expose the full placeholder set.

    A template that omits {{Body_Content}} silently drops the generated body:
    the report renders, but only shows whatever was hardcoded in the template.
    """
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")
    found = set(re.findall(r"\{\{[^}]+\}\}", text))

    assert REQUIRED_PLACEHOLDERS <= found, f"{family} is missing {sorted(REQUIRED_PLACEHOLDERS - found)}"


@pytest.mark.parametrize("family", FAMILIES)
def test_template_does_not_hardcode_the_report_body(family: str) -> None:
    """Sections 4-8 come from the model, so the template must not carry them."""
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")

    assert not re.search(r"^###\s+[4-8]\s", text, re.MULTILINE), (
        f"{family} hardcodes a body section instead of using {{{{Body_Content}}}}"
    )


@pytest.mark.parametrize("family", FAMILIES)
def test_template_has_only_one_primary_figure_one_caption(family: str) -> None:
    """The methods project-flow figure is supplementary, not a second 图1."""
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")

    assert text.count("<p align='center'>图1 ") == 1
    assert "附图1 项目流程图" in text


@pytest.mark.parametrize("family", FAMILIES)
def test_cover_does_not_render_a_project_id(family: str) -> None:
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")

    assert "{{Project_ID}}" not in text


@pytest.mark.parametrize("family", FAMILIES)
def test_template_caption_labels_are_unique(family: str) -> None:
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")
    labels = re.findall(r"<p align='center'>((?:图|附图)\d+) ", text)

    assert len(labels) == len(set(labels))


@pytest.mark.parametrize("family", FAMILIES)
def test_template_references_only_packaged_images(family: str) -> None:
    """Every image a template points at must exist in the packaged assets."""
    text = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")
    assets = TEMPLATE_ROOT / "assets"

    for src in sorted(set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text))):
        if src.startswith(("http://", "https://")):
            continue
        assert (assets / src.lstrip("./")).is_file(), f"{family} points at a missing image: {src}"


@pytest.mark.parametrize("family", FAMILIES)
def test_packaged_template_matches_the_source_copy(family: str) -> None:
    """The wheel ships a copy of each template; the two must not drift."""
    source = (TEMPLATE_ROOT / family / "report.md").read_text(encoding="utf-8")
    packaged = (PACKAGED_ROOT / family / "report.md").read_text(encoding="utf-8")

    assert source == packaged, f"the packaged {family} template differs from templates/{family}/report.md"


def test_legacy_template_archive_is_gone() -> None:
    """The legacy/ directory held a rendered sample, not a template."""
    assert not (TEMPLATE_ROOT / "legacy").exists()

