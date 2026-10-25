import os
import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
_SKILL_DIR_ENV = os.environ.get("BIA_BRIEF_SKILL_DIR")
SKILL_DIR = Path(_SKILL_DIR_ENV).resolve() if _SKILL_DIR_ENV else None


def _project_version() -> str:
    """Read the version the package actually publishes."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml does not declare a project version"
    return match.group(1)


def _skill_file(name: str) -> Path:
    if SKILL_DIR is None:
        pytest.skip("Set BIA_BRIEF_SKILL_DIR to verify the Skill contract")
    if not SKILL_DIR.is_dir():
        pytest.fail(f"Skill directory is not present: {SKILL_DIR}")
    path = SKILL_DIR / name
    if not path.is_file():
        pytest.fail(f"Skill file is not present: {path}")
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
        _skill_file("README.zh-CN.md"),
    ]

    for readme in readmes:
        text = readme.read_text(encoding="utf-8")
        assert f'bia-brief=={version}' in text, f"{readme} does not pin {version}"


def test_skill_troubleshooting_and_install_script_pin_the_current_release() -> None:
    version = _project_version()
    for name in ("references/troubleshooting.md", "scripts/check_bia_brief.py"):
        text = _skill_file(name).read_text(encoding="utf-8")
        assert version in text, f"{name} does not pin {version}"


def test_release_tag_exists() -> None:
    version = _project_version()
    result = subprocess.run(
        ["git", "tag", "--list", f"v{version}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == f"v{version}"
