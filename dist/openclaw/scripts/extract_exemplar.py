#!/usr/bin/env python3
"""
Extract style exemplars from human-written articles for SICO-style few-shot injection.

Takes a markdown article, analyzes it for style fingerprints, extracts key
segments (opening hook, emotional peak, transition/self-correction, closing),
and saves structured exemplar files to references/exemplars/.

Usage:
    python3 scripts/extract_exemplar.py article.md
    python3 scripts/extract_exemplar.py article.md --category tech-opinion --source "\u516c\u4f17\u53f7\u540d"
    python3 scripts/extract_exemplar.py article1.md article2.md article3.md  # batch
    python3 scripts/extract_exemplar.py --list                                # list all exemplars
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import humanness_score as hs

SKILL_DIR = Path(__file__).parent.parent
EXEMPLARS_DIR = SKILL_DIR / "references" / "exemplars"
INDEX_FILE = EXEMPLARS_DIR / "index.yaml"

CATEGORIES = ["tech-opinion", "story-emotional", "list-practical", "hot-take", "general"]

STORY_MARKERS = ["\u6211", "\u6211\u4eec", "\u90a3\u5929", "\u90a3\u5e74", "\u8bb0\u5f97", "\u540e\u6765", "\u5f53\u65f6", "\u7b2c\u4e00\u6b21", "\u6700\u540e", "\u7a81\u7136", "\u7ec8\u4e8e"]


def extract_headings(text):
    return re.findall(r'^##\s+(.+)$', text, re.MULTILINE)


def extract_title(text):
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def extract_opening(paragraphs, max_chars=250):
    result = []
    total = 0
    for p in paragraphs:
        if total + len(p) > max_chars and result:
            break
        result.append(p)
        total += len(p)
    return "\n\n".join(result)


def extract_emotional_peak(paragraphs):
    best_para, best_density = "", -1.0
    for p in paragraphs:
        if len(p) < 20:
            continue
        count = sum(1 for m in hs.NEGATIVE_MARKERS if m in p)
        density = count / len(p) * 100
        if density > best_density:
            best_density = density
            best_para = p
    return best_para if best_density > 0 else ""


def extract_transition(paragraphs):
    transition_words = ["\u4f46\u662f", "\u4e0d\u8fc7", "\u7136\u800c", "\u8bdd\u8bf4\u56de\u6765", "\u6362\u4e2a\u89d2\u5ea6", "\u8bf4\u56de\u6765", "\u4f46\u8bdd\u53c8\u8bf4\u56de\u6765", "\u4e0d\u5bf9", "\u7b97\u4e86"]
    best_para, best_count = "", 0
    for p in paragraphs:
        if len(p) < 20:
            continue
        count = sum(len(re.findall(pat, p)) for pat in hs.SELF_CORRECTION_PATTERNS)
        count += sum(p.count(w) for w in transition_words)
        if count > best_count:
            best_count = count
            best_para = p
    return best_para if best_count > 0 else ""


def extract_closing(paragraphs, max_chars=250):
    result = []
    total = 0
    for p in reversed(paragraphs):
        if total + len(p) > max_chars and result:
            break
        result.insert(0, p)
        total += len(p)
    return "\n\n".join(result)


def detect_category(text, paragraphs, headings):
    data_count = sum(len(re.findall(p, text)) for p in hs.REAL_SOURCE_PATTERNS)
    story_count = sum(text.count(m) for m in STORY_MARKERS)
    h2_count = len(headings)
    neg_count = sum(1 for m in hs.NEGATIVE_MARKERS if m in text)
    scores = {
        "tech-opinion": data_count * 2,
        "story-emotional": story_count * 1.5,
        "list-practical": h2_count * 3 if h2_count >= 5 else 0,
        "hot-take": neg_count * 2 + data_count if len(text) < 2000 else 0,
        "general": 5,
    }
    return max(scores, key=scores.get)


def compute_vocab_temperature(text):
    counts = {
        "cold": sum(text.count(w) for w in hs.COLD_WORDS),
        "warm": sum(text.count(w) for w in hs.WARM_WORDS),
        "hot": sum(text.count(w) for w in hs.HOT_WORDS),
        "wild": sum(text.count(w) for w in hs.WILD_WORDS),
    }
    total = sum(counts.values())
    if total == 0:
        return {k: 0.25 for k in counts}
    return {k: round(v / total, 2) for k, v in counts.items()}


def compute_paragraph_cv(paragraphs):
    if len(paragraphs) < 3:
        return 0.0
    lengths = [len(p) for p in paragraphs]
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    return round((variance ** 0.5) / mean, 2)


def count_short_paragraphs(text):
    return sum(1 for l in text.split('\n') if l.strip() and 1 <= len(l.strip()) <= 10 and not l.strip().startswith('#'))


def extract_exemplar(text, category=None, source=None):
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()
    paragraphs = hs._split_paragraphs(text)
    sentences = hs._split_sentences(clean)
    headings = extract_headings(text)
    title = extract_title(text) or source or ""
    if not category:
        category = detect_category(clean, paragraphs, headings)
    score_result = hs.score_article(text)
    lengths = [len(s) for s in sentences]
    if len(lengths) >= 2:
        mean = sum(lengths) / len(lengths)
        variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
        sentence_stddev = round(variance ** 0.5, 1)
    else:
        sentence_stddev = 0.0
    neg_count = sum(1 for s in sentences if any(m in s for m in hs.NEGATIVE_MARKERS))
    negative_ratio = round(neg_count / len(sentences), 2) if sentences else 0.0
    return {
        "title": title,
        "source": source or title,
        "category": category,
        "humanness_score": score_result["composite_score"],
        "fingerprint": {
            "sentence_stddev": sentence_stddev,
            "vocab_temperature": compute_vocab_temperature(clean),
            "negative_ratio": negative_ratio,
            "paragraph_cv": compute_paragraph_cv(paragraphs),
            "short_paragraphs": count_short_paragraphs(text),
        },
        "segments": {
            "opening": extract_opening(paragraphs),
            "emotional_peak": extract_emotional_peak(paragraphs),
            "transition": extract_transition(paragraphs),
            "closing": extract_closing(paragraphs),
        },
        "extracted_at": datetime.now().strftime("%Y-%m-%d"),
        "char_count": len(clean),
    }


def save_exemplar(exemplar):
    EXEMPLARS_DIR.mkdir(parents=True, exist_ok=True)
    category = exemplar["category"]
    num = 1
    while (EXEMPLARS_DIR / f"{category}-{num:03d}.md").exists():
        num += 1
    filename = f"{category}-{num:03d}.md"
    filepath = EXEMPLARS_DIR / filename
    fp = exemplar["fingerprint"]
    seg = exemplar["segments"]
    frontmatter = {
        "source": exemplar["source"],
        "category": category,
        "humanness_score": exemplar["humanness_score"],
        "sentence_stddev": fp["sentence_stddev"],
        "vocab_temperature": fp["vocab_temperature"],
        "negative_ratio": fp["negative_ratio"],
        "paragraph_cv": fp["paragraph_cv"],
        "short_paragraphs": fp["short_paragraphs"],
        "extracted_at": exemplar["extracted_at"],
    }
    content = "---\n" + yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False) + "---\n\n"
    section_map = [("opening", "\u5f00\u5934\u94a9\u5b50"), ("emotional_peak", "\u60c5\u7eea\u9ad8\u5cf0"), ("transition", "\u8f6c\u6298/\u81ea\u7ea0"), ("closing", "\u6536\u5c3e")]
    for key, label in section_map:
        if seg.get(key):
            content += f"## {label}\n\n{seg[key]}\n\n"
    filepath.write_text(content, encoding="utf-8")
    _update_index(filename, exemplar)
    return filepath


def _update_index(filename, exemplar):
    index = []
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index = yaml.safe_load(f) or []
    entry = {"file": filename, "source": exemplar["source"], "category": exemplar["category"], "humanness_score": exemplar["humanness_score"], "extracted_at": exemplar["extracted_at"]}
    index = [e for e in index if e.get("file") != filename]
    index.append(entry)
    index.sort(key=lambda x: (x["category"], x["humanness_score"]))
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        yaml.dump(index, f, allow_unicode=True, default_flow_style=False)


def list_exemplars():
    if not INDEX_FILE.exists():
        print("\u8303\u6587\u5e93\u4e3a\u7a7a\u3002\u7528\u6cd5: python3 scripts/extract_exemplar.py article.md")
        return
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = yaml.safe_load(f) or []
    if not index:
        print("\u8303\u6587\u5e93\u4e3a\u7a7a\u3002")
        return
    print(f"\n{'=' * 60}")
    print(f"\u8303\u6587\u5e93 ({len(index)} \u7bc7)")
    print(f"{'=' * 60}")
    by_cat = {}
    for e in index:
        by_cat.setdefault(e["category"], []).append(e)
    for cat, entries in sorted(by_cat.items()):
        print(f"\n  [{cat}] ({len(entries)} \u7bc7)")
        for e in entries:
            score = e["humanness_score"]
            bar = "\u2588" * int((100 - score) / 10) + "\u2591" * (10 - int((100 - score) / 10))
            print(f"    {bar} {score:5.1f}  {e['source'][:40]}")


def main():
    parser = argparse.ArgumentParser(description="Extract style exemplars from articles")
    parser.add_argument("inputs", nargs="*", help="Markdown article file(s)")
    parser.add_argument("--category", "-c", choices=CATEGORIES, help="Article category (auto-detected if omitted)")
    parser.add_argument("--source", "-s", help="Source name (e.g. account name)")
    parser.add_argument("--list", "-l", action="store_true", help="List all exemplars")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    if args.list:
        list_exemplars()
        return
    if not args.inputs:
        parser.print_help()
        sys.exit(1)
    for input_path in args.inputs:
        path = Path(input_path)
        if not path.exists():
            print(f"Error: {input_path} not found", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        source = args.source or path.stem
        exemplar = extract_exemplar(text, category=args.category, source=source)
        filepath = save_exemplar(exemplar)
        if args.json:
            print(json.dumps(exemplar, ensure_ascii=False, indent=2))
        else:
            print(f"\u2713 {path.name}")
            print(f"  Category:  {exemplar['category']}")
            print(f"  Score:     {exemplar['humanness_score']:.1f}/100")
            print(f"  Segments:  {sum(1 for v in exemplar['segments'].values() if v)}/4")
            fp = exemplar["fingerprint"]
            print(f"  Stddev:    {fp['sentence_stddev']}")
            print(f"  Neg ratio: {fp['negative_ratio']:.0%}")
            print(f"  Para CV:   {fp['paragraph_cv']}")
            temp = fp["vocab_temperature"]
            print(f"  Temp:      cold={temp['cold']} warm={temp['warm']} hot={temp['hot']} wild={temp['wild']}")
            print(f"  Saved to:  {filepath}")
            print()


if __name__ == "__main__":
    main()
