#!/usr/bin/env python3
"""
Learn from human edits by diffing AI draft vs published final.

Compares the original AI-generated article with the human-edited version,
computes structured diffs, and saves typed lessons to lessons/.

Each lesson has:
  - type: word_sub / para_delete / para_add / structure / title / tone
  - occurrences: how many times this pattern has been seen across all lessons
  - first_seen / last_seen: timestamps for confidence decay
  - confidence: auto-computed from occurrences + recency

When summarizing, outputs all patterns with aggregated confidence scores.
The Agent uses this to write structured playbook.md rules.

Usage:
    python3 learn_edits.py --draft path/to/draft.md --final path/to/final.md
    python3 learn_edits.py --from-wechat         # auto-sync from WeChat draft box
    python3 learn_edits.py --summarize           # all lessons with confidence
    python3 learn_edits.py --summarize --json    # JSON output for agent
"""

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).parent.parent

PATTERN_TYPES = {"word_sub": "\u7528\u8bcd\u66ff\u6362", "para_delete": "\u6bb5\u843d\u5220\u9664", "para_add": "\u6bb5\u843d\u65b0\u589e", "structure": "\u7ed3\u6784\u8c03\u6574", "title": "\u6807\u9898\u4fee\u6539", "tone": "\u8bed\u6c14\u8c03\u6574", "expression": "\u8868\u8fbe\u504f\u597d"}


def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def markdown_to_plaintext(md: str) -> str:
    text = md
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _find_config_file(name: str) -> "Path | None":
    from pathlib import Path as _P
    for p in (SKILL_DIR / "config" / name, SKILL_DIR / name):
        if p.exists():
            return p
    return None


def fetch_wechat_draft() -> tuple[str, str, str]:
    config_path = _find_config_file("config.yaml")
    if config_path is None:
        raise FileNotFoundError("config.yaml not found \u2014 need WeChat API credentials")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    wechat = config.get("wechat", {})
    appid = wechat.get("appid", "")
    secret = wechat.get("secret", "")
    if not appid or not secret:
        raise ValueError("config.yaml missing wechat.appid or wechat.secret")
    history_path = SKILL_DIR / "history.yaml"
    if not history_path.exists():
        raise FileNotFoundError("history.yaml not found \u2014 no articles to compare")
    with open(history_path) as f:
        history = yaml.safe_load(f) or []
    latest = None
    for article in reversed(history):
        if article.get("media_id"):
            latest = article
            break
    if not latest:
        raise ValueError("No article with media_id found in history.yaml")
    media_id = latest["media_id"]
    title = latest.get("title", "")
    date = latest.get("date", "")
    output_dir = SKILL_DIR / "output"
    draft_path = None
    output_file = latest.get("output_file", "")
    if output_file:
        candidate = SKILL_DIR / output_file if not Path(output_file).is_absolute() else Path(output_file)
        if candidate.exists():
            draft_path = candidate
    if not draft_path and date:
        candidates = sorted(output_dir.glob(f"{date}-*.md"))
        if len(candidates) == 1:
            draft_path = candidates[0]
        elif len(candidates) > 1:
            title_lower = title.lower()
            for c in candidates:
                slug = c.stem.replace(date + "-", "").replace("-", " ")
                if any(w in title_lower for w in slug.split() if len(w) > 1):
                    draft_path = c
                    break
            if not draft_path:
                draft_path = max(candidates, key=lambda p: p.stat().st_size)
    if not draft_path or not draft_path.exists():
        raise FileNotFoundError(f"Cannot find local draft for '{title}' (date={date}) in output/")
    sys.path.insert(0, str(SKILL_DIR / "toolkit"))
    from wechat_api import get_access_token
    from publisher import get_draft, html_to_plaintext
    token = get_access_token(appid, secret)
    html = get_draft(token, media_id)
    wechat_text = html_to_plaintext(html)
    local_md = load_text(str(draft_path))
    local_text = markdown_to_plaintext(local_md)
    print(f"\u672c\u5730\u6587\u4ef6: {draft_path}")
    print(f"\u5fae\u4fe1\u8349\u7a3f: media_id={media_id}")
    print(f"\u6587\u7ae0\u6807\u9898: {title}")
    print(f"\u672c\u5730\u5b57\u6570: {len(local_text)}, \u5fae\u4fe1\u5b57\u6570: {len(wechat_text)}")
    return local_text, wechat_text, str(draft_path)


def split_sections(text: str) -> list[dict]:
    sections = []
    current = {"header": "(intro)", "lines": []}
    for line in text.split("\n"):
        if line.strip().startswith("## "):
            if current["lines"] or current["header"] != "(intro)":
                sections.append(current)
            current = {"header": line.strip(), "lines": []}
        else:
            current["lines"].append(line)
    sections.append(current)
    return sections


def extract_title(text: str) -> str:
    for line in text.split("\n"):
        if line.strip().startswith("# ") and not line.strip().startswith("## "):
            return line.strip()[2:].strip()
    return ""


def compute_diff(draft: str, final: str) -> dict:
    draft_lines = draft.split("\n")
    final_lines = final.split("\n")
    differ = difflib.unified_diff(draft_lines, final_lines, lineterm="")
    diff_lines = list(differ)
    additions = [l[1:].strip() for l in diff_lines if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
    deletions = [l[1:].strip() for l in diff_lines if l.startswith("-") and not l.startswith("---") and l[1:].strip()]
    draft_title = extract_title(draft)
    final_title = extract_title(final)
    draft_sections = split_sections(draft)
    final_sections = split_sections(final)
    draft_h2s = [s["header"] for s in draft_sections if s["header"] != "(intro)"]
    final_h2s = [s["header"] for s in final_sections if s["header"] != "(intro)"]
    draft_chars = len(draft.replace("\n", "").replace(" ", ""))
    final_chars = len(final.replace("\n", "").replace(" ", ""))
    return {"title_changed": draft_title != final_title, "draft_title": draft_title, "final_title": final_title, "structure_changed": draft_h2s != final_h2s, "draft_h2s": draft_h2s, "final_h2s": final_h2s, "lines_added": len(additions), "lines_deleted": len(deletions), "draft_chars": draft_chars, "final_chars": final_chars, "char_diff": final_chars - draft_chars, "additions_sample": additions[:20], "deletions_sample": deletions[:20]}


def save_lesson(diff_result: dict, draft_path: str, final_path: str) -> Path:
    lessons_dir = SKILL_DIR / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    lesson_file = lessons_dir / f"{date_str}-diff.yaml"
    counter = 1
    while lesson_file.exists():
        lesson_file = lessons_dir / f"{date_str}-diff-{counter}.yaml"
        counter += 1
    data = {"date": date_str, "timestamp": datetime.now().isoformat(), "draft_file": str(draft_path), "final_file": str(final_path), "diff_summary": {"title_changed": diff_result["title_changed"], "draft_title": diff_result["draft_title"], "final_title": diff_result["final_title"], "structure_changed": diff_result["structure_changed"], "lines_added": diff_result["lines_added"], "lines_deleted": diff_result["lines_deleted"], "char_diff": diff_result["char_diff"]}, "patterns": []}
    with open(lesson_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    return lesson_file


def load_all_lessons() -> list[dict]:
    lessons_dir = SKILL_DIR / "lessons"
    if not lessons_dir.exists():
        return []
    lessons = []
    for f in sorted(lessons_dir.glob("*-diff*.yaml")):
        with open(f, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if data:
                lessons.append(data)
    return lessons


def compute_confidence(occurrences: int, first_seen: str, last_seen: str) -> float:
    base = min(8, 2 + occurrences * 2)
    try:
        last = datetime.fromisoformat(last_seen)
        days_since = (datetime.now() - last).days
    except (ValueError, TypeError):
        days_since = 0
    recency_bonus = 1.0 if days_since <= 7 else 0.0
    age_decay = max(0, days_since // 30)
    return max(1.0, min(10.0, base + recency_bonus - age_decay))


def aggregate_patterns(lessons: list[dict]) -> list[dict]:
    pattern_map = {}
    for lesson in lessons:
        date = lesson.get("date", "")
        timestamp = lesson.get("timestamp", date)
        for p in lesson.get("patterns", []):
            key = p.get("key", "")
            if not key:
                continue
            if key not in pattern_map:
                pattern_map[key] = {"key": key, "type": p.get("type", "expression"), "description": p.get("description", ""), "rule": p.get("rule", ""), "occurrences": 0, "first_seen": timestamp, "last_seen": timestamp}
            entry = pattern_map[key]
            entry["occurrences"] += 1
            if p.get("description"):
                entry["description"] = p["description"]
            if p.get("rule"):
                entry["rule"] = p["rule"]
            if timestamp < entry["first_seen"]:
                entry["first_seen"] = timestamp
            if timestamp > entry["last_seen"]:
                entry["last_seen"] = timestamp
    results = []
    for entry in pattern_map.values():
        entry["confidence"] = round(compute_confidence(entry["occurrences"], entry["first_seen"], entry["last_seen"]), 1)
        results.append(entry)
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def summarize_lessons(as_json: bool = False):
    lessons = load_all_lessons()
    if not lessons:
        print("No lessons found.")
        return
    patterns = aggregate_patterns(lessons)
    if as_json:
        print(json.dumps({"total_lessons": len(lessons), "total_patterns": len(patterns), "patterns": patterns}, ensure_ascii=False, indent=2))
        return
    print(f"Total lessons: {len(lessons)}")
    print(f"Unique patterns: {len(patterns)}")
    print()
    for p in patterns:
        type_label = PATTERN_TYPES.get(p["type"], p["type"])
        conf_bar = "\u2588" * int(p["confidence"]) + "\u2591" * (10 - int(p["confidence"]))
        print(f"  {conf_bar} {p['confidence']:4.1f}  [{type_label}] {p['key']}")
        print(f"         {p['description']}")
        if p["rule"]:
            print(f"         \u2192 {p['rule']}")
        print(f"         seen {p['occurrences']}x, first {p['first_seen'][:10]}, last {p['last_seen'][:10]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Learn from human edits")
    parser.add_argument("--draft", help="Path to AI draft")
    parser.add_argument("--final", help="Path to human-edited final")
    parser.add_argument("--from-wechat", action="store_true", help="Auto-fetch edited version from WeChat draft box")
    parser.add_argument("--summarize", action="store_true", help="Summarize all lessons")
    parser.add_argument("--json", action="store_true", help="JSON output (with --summarize)")
    args = parser.parse_args()
    if args.summarize:
        summarize_lessons(as_json=args.json)
        return
    if args.from_wechat:
        local_text, wechat_text, draft_path = fetch_wechat_draft()
        if local_text == wechat_text:
            print("\n\u5fae\u4fe1\u8349\u7a3f\u4e0e\u672c\u5730\u6587\u4ef6\u5185\u5bb9\u4e00\u81f4\uff0c\u6ca1\u6709\u4fee\u6539\u3002")
            return
        diff_result = compute_diff(local_text, wechat_text)
        lesson_file = save_lesson(diff_result, draft_path, f"wechat:{draft_path}")
        print(f"\nLesson saved to: {lesson_file}")
        print(f"\n\u68c0\u6d4b\u5230 {diff_result['lines_added']} \u5904\u65b0\u589e, {diff_result['lines_deleted']} \u5904\u5220\u9664")
        print(f"\u5b57\u6570\u53d8\u5316: {diff_result['char_diff']:+d}")
        print(f"\nAgent \u63a5\u4e0b\u6765\u8bfb\u53d6 {draft_path} \u548c\u5fae\u4fe1\u8349\u7a3f\u5185\u5bb9\uff0c\u5206\u6790\u4fee\u6539\u6a21\u5f0f\u5e76\u5199\u5165 {lesson_file}")
        return
    if not args.draft or not args.final:
        print("Error: --draft and --final required (or use --from-wechat)", file=sys.stderr)
        sys.exit(1)
    draft = load_text(args.draft)
    final = load_text(args.final)
    diff_result = compute_diff(draft, final)
    print("=" * 60)
    print("EDIT ANALYSIS")
    print("=" * 60)
    if diff_result["title_changed"]:
        print(f"\n\u6807\u9898\u4fee\u6539:")
        print(f"  AI:   {diff_result['draft_title']}")
        print(f"  \u4eba\u5de5: {diff_result['final_title']}")
    if diff_result["structure_changed"]:
        print(f"\n\u7ed3\u6784\u4fee\u6539:")
        print(f"  AI H2:   {diff_result['draft_h2s']}")
        print(f"  \u4eba\u5de5 H2: {diff_result['final_h2s']}")
    print(f"\n\u6570\u91cf\u53d8\u5316:")
    print(f"  \u65b0\u589e {diff_result['lines_added']} \u884c, \u5220\u9664 {diff_result['lines_deleted']} \u884c")
    print(f"  \u5b57\u6570\u53d8\u5316: {diff_result['char_diff']:+d} ({diff_result['draft_chars']} \u2192 {diff_result['final_chars']})")
    if diff_result["deletions_sample"]:
        print(f"\n\u88ab\u5220\u9664\u7684\u5185\u5bb9\uff08\u91c7\u6837\uff09:")
        for line in diff_result["deletions_sample"][:10]:
            print(f"  - {line[:80]}")
    if diff_result["additions_sample"]:
        print(f"\n\u65b0\u589e\u7684\u5185\u5bb9\uff08\u91c7\u6837\uff09:")
        for line in diff_result["additions_sample"][:10]:
            print(f"  + {line[:80]}")
    lesson_file = save_lesson(diff_result, args.draft, args.final)
    print(f"\nLesson saved to: {lesson_file}")
    final_title = extract_title(final)
    try:
        import extract_exemplar
        exemplar = extract_exemplar.extract_exemplar(final, source=final_title or "user-edited")
        if exemplar["humanness_score"] <= 50:
            exemplar_path = extract_exemplar.save_exemplar(exemplar)
            print(f"\n\u2713 \u7ec8\u7a3f\u5df2\u52a0\u5165\u8303\u6587\u5e93: {exemplar_path}")
            print(f"  Score: {exemplar['humanness_score']:.1f}/100, Category: {exemplar['category']}")
        else:
            print(f"\n\u26a0 \u7ec8\u7a3f humanness_score={exemplar['humanness_score']:.1f} > 50\uff0c\u672a\u52a0\u5165\u8303\u6587\u5e93")
    except Exception as e:
        print(f"\n\u26a0 \u8303\u6587\u63d0\u53d6\u8df3\u8fc7: {e}")
    lesson_count = len(load_all_lessons())
    print(f"Total lessons: {lesson_count}")
    if lesson_count >= 5 and lesson_count % 5 == 0:
        print(f"\n{'=' * 60}")
        print("PLAYBOOK UPDATE TRIGGERED")
        print(f"{'=' * 60}")
        print(f"{lesson_count} lessons. Agent should run:")
        print(f"  python3 scripts/learn_edits.py --summarize --json")
        print(f"Then update playbook.md with high-confidence patterns.")
    print(f"""
{'=' * 60}
INSTRUCTIONS FOR AGENT
{'=' * 60}

Read the draft and final versions, then for each meaningful edit:

1. Read: {args.draft}
2. Read: {args.final}
3. For each edit, add a pattern entry to {lesson_file}:

   patterns:
     - type: "word_sub"           # {' / '.join(PATTERN_TYPES.keys())}
       key: "short_unique_id"     # e.g. "avoid_jiangzhen", "shorter_paragraphs"
       description: "\u628a'\u8bb2\u771f'\u66ff\u6362\u4e3a'\u5766\u767d\u8bf4'"
       rule: "\u4e0d\u8981\u4f7f\u7528'\u8bb2\u771f'\uff0c\u7528'\u5766\u767d\u8bf4'\u4ee3\u66ff"  # imperative, executable

4. Rules must be imperative (\u53ef\u6267\u884c\u7684\u6307\u4ee4), not descriptive.
   BAD:  "\u7528\u6237\u504f\u597d\u7b80\u77ed\u6bb5\u843d"
   GOOD: "\u6bb5\u843d\u4e0d\u8d85\u8fc7 80 \u5b57\uff0c\u957f\u6bb5\u5fc5\u987b\u5728 3 \u53e5\u5185\u6362\u884c"

5. If pattern already exists in previous lessons (same key),
   confidence will auto-increase on next --summarize.
""")


if __name__ == "__main__":
    main()
