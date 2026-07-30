from pathlib import Path


SKILL_PATH = Path(r"C:\Users\86139\.codex\skills\bia-brief-skill\SKILL.md")


def test_skill_documents_pinned_install_and_first_run_setup() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")

    assert 'bia-brief==0.2.1' in text
    assert 'bia-brief-setup' in text
    assert '~/.bia-brief/config.yaml' in text
    assert 'BIA_BRIEF_CONFIG' in text
