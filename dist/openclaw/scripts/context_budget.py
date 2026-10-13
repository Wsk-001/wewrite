#!/usr/bin/env python3
"""
Measure the doc-context load of a normal full WeWrite pipeline run (issue #16).

Parses SKILL.md for happy-path `\u8bfb\u53d6:` directives, sums the sizes of the
reference docs a normal generate-an-article run loads, and reports
lines / chars / estimated tokens. Doubles as a CI regression guard so
SKILL.md cannot silently re-bloat (e.g. re-adding wechat-constraints.md).

Usage:
    python3 scripts/context_budget.py                      # human table
    python3 scripts/context_budget.py --json               # machine output
    python3 scripts/context_budget.py --budget-tokens 12000  # exit 1 if over
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

AUXILIARY = {
    "onboard.md",
    "learn-edits.md",
    "effect-review.md",
    "style-template.md",
    "exemplar-seeds.yaml",
    "commands.md",
    "compliance-seo.md",
    "cover-prompts.md",
    "wechat-constraints.md",
}

DEFAULT_PERSONA = "personas/midnight-friend.yaml"

LOAD_RE = re.compile(r"\u8bfb\u53d6:\s*\{skill_dir\}/(references/[\w./-]+\.(?:md|yaml))")


def parse_onpath_refs(skill_md_text: str) -> list:
    seen = []
    for m in LOAD_RE.finditer(skill_md_text):
        rel = m.group(1)
        base = rel.split("/")[-1]
        if base in AUXILIARY:
            continue
        if rel not in seen:
            seen.append(rel)
    return seen


def _stats(path: Path) -> tuple:
    text = path.read_text(encoding="utf-8")
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return lines, len(text)


def measure(skill_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    entries = []
    l, c = _stats(skill_md)
    entries.append({"name": "SKILL.md", "lines": l, "chars": c})
    for rel in parse_onpath_refs(skill_md.read_text(encoding="utf-8")):
        p = skill_dir / rel
        if p.exists():
            l, c = _stats(p)
            entries.append({"name": rel, "lines": l, "chars": c})
    persona = skill_dir / DEFAULT_PERSONA
    if persona.exists():
        l, c = _stats(persona)
        entries.append({"name": DEFAULT_PERSONA, "lines": l, "chars": c})
    total_lines = sum(e["lines"] for e in entries)
    total_chars = sum(e["chars"] for e in entries)
    return {
        "entries": entries,
        "peak_lines": total_lines,
        "peak_chars": total_chars,
        "peak_tokens": round(total_chars / 3.5),
    }


def main():
    ap = argparse.ArgumentParser(description="Measure WeWrite pipeline context load")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--budget-tokens", type=int, default=None)
    args = ap.parse_args()
    r = measure(REPO_ROOT)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"{'file':<45}{'lines':>7}{'chars':>8}{'~tok':>7}")
        print("-" * 67)
        for e in r["entries"]:
            print(f"{e['name']:<45}{e['lines']:>7}{e['chars']:>8}{round(e['chars']/3.5):>7}")
        print("-" * 67)
        print(f"{'PEAK (normal run)':<45}{r['peak_lines']:>7}{r['peak_chars']:>8}{r['peak_tokens']:>7}")
    if args.budget_tokens is not None and r["peak_tokens"] > args.budget_tokens:
        print(f"\n\u2717 context budget exceeded: {r['peak_tokens']} > {args.budget_tokens}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
