import os
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = Path(
    os.environ.get(
        "BIA_BRIEF_SKILL_DIR",
        r"C:\Users\86139\.codex\skills\bia-brief-skill",
    )
)


def _project_version() -> str:
    """Read the version the package actually publishes."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml does not declare a project version"
    return match.group(1)


def _skill_file(name: str) -> Path:
    if not SKILL_DIR.is_dir():
        pytest.skip(f"Skill directory is not present: {SKILL_DIR}")
    path = SKILL_DIR / name
    if not path.is_file():
        pytest.skip(f"Skill file is not present: {path}")
    return path


def test_skill_documents_pinned_install_and_first_run_setup() -> None:
    version = _project_version()
    text = _skill_file("SKILL.md").read_text(encoding="utf-8")

    assert f'bia-brief=={version}' in text
    assert f'@v{version}' in text
    assert 'bia-brief-setup' in text
    assert '~/.bia-brief/config.yaml' in text
    assert 'BIA_BRIEF_CONFIG' in text


def test_readmes_pin_the_current_release() -> None:
    """Every install instruction must name the version in pyproject.toml."""
    version = _project_version()
    readmes = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "README.zh-CN.md",
        _skill_file("README.md"),
    ]

    for readme in readmes:
        text = readme.read_text(encoding="utf-8")
        assert f'bia-brief=={version}' in text, f"{readme} does not pin {version}"
