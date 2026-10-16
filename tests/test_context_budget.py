import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from context_budget import parse_onpath_refs, measure  # noqa: E402


def test_parse_onpath_excludes_auxiliary():
    sample = (
        "读取: {skill_dir}/references/pipeline/frameworks.md\n"
        "读取: {skill_dir}/references/guides/onboard.md\n"
        "读取: {skill_dir}/references/pipeline/writing-guide.md\n"
        "读取: {skill_dir}/references/guides/commands.md\n"
    )
    refs = parse_onpath_refs(sample)
    assert "references/pipeline/frameworks.md" in refs
    assert "references/pipeline/writing-guide.md" in refs
    assert "references/guides/onboard.md" not in refs
    assert "references/guides/commands.md" not in refs


def test_parse_dedupes_and_preserves_order():
    sample = (
        "读取: {skill_dir}/references/compliance/seo-rules.md\n"
        "读取: {skill_dir}/references/compliance/seo-rules.md\n"
    )
    assert parse_onpath_refs(sample) == ["references/compliance/seo-rules.md"]


def test_measure_reports_peak_on_real_repo():
    repo = Path(__file__).resolve().parent.parent
    r = measure(repo)
    assert r["peak_tokens"] > 0
    assert any(e["name"] == "SKILL.md" for e in r["entries"])
