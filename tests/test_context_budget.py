import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from context_budget import parse_onpath_refs, measure  # noqa: E402


def test_parse_onpath_excludes_auxiliary():
    sample = (
        "读取: {skill_dir}/references/frameworks.md\n"
        "读取: {skill_dir}/references/onboard.md\n"
        "读取: {skill_dir}/references/writing-guide.md\n"
        "读取: {skill_dir}/references/commands.md\n"
    )
    refs = parse_onpath_refs(sample)
    assert "references/frameworks.md" in refs
    assert "references/writing-guide.md" in refs
    assert "references/onboard.md" not in refs
    assert "references/commands.md" not in refs


def test_parse_dedupes_and_preserves_order():
    sample = (
        "读取: {skill_dir}/references/seo-rules.md\n"
        "读取: {skill_dir}/references/seo-rules.md\n"
    )
    assert parse_onpath_refs(sample) == ["references/seo-rules.md"]


def test_measure_reports_peak_on_real_repo():
    repo = Path(__file__).resolve().parent.parent
    r = measure(repo)
    assert r["peak_tokens"] > 0
    assert any(e["name"] == "SKILL.md" for e in r["entries"])
