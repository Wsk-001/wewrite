#!/usr/bin/env python3
"""
Build a writing playbook from historical articles.

Reads all .md files in corpus/, analyzes writing patterns
in batches via LLM, and outputs a structured playbook.md.

Usage:
    python3 build_playbook.py
    python3 build_playbook.py --batch-size 10

Requires: ANTHROPIC_API_KEY or ARK API key in environment/config.
This script outputs analysis prompts to stdout for the Agent (LLM) to process.
The Agent reads the output and generates playbook.md.
"""

import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent


def load_corpus() -> list[dict]:
    corpus_dir = SKILL_DIR / "corpus"
    if not corpus_dir.exists():
        print(f"Error: corpus directory not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)
    articles = []
    for md_file in sorted(corpus_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        if not text.strip():
            continue
        title = ""
        for line in text.split("\n"):
            if line.strip().startswith("# ") and not line.strip().startswith("## "):
                title = line.strip()[2:].strip()
                break
        lines = [l for l in text.split("\n") if l.strip()]
        paragraphs = text.split("\n\n")
        h2_count = sum(1 for l in text.split("\n") if l.strip().startswith("## "))
        char_count = len(text.replace("\n", "").replace(" ", ""))
        articles.append({
            "filename": md_file.name,
            "title": title,
            "char_count": char_count,
            "paragraph_count": len([p for p in paragraphs if p.strip()]),
            "h2_count": h2_count,
            "text": text,
        })
    return articles


def compute_corpus_stats(articles: list[dict]) -> dict:
    if not articles:
        return {}
    titles = [a["title"] for a in articles if a["title"]]
    title_lengths = [len(t) for t in titles]
    char_counts = [a["char_count"] for a in articles]
    para_counts = [a["paragraph_count"] for a in articles]
    h2_counts = [a["h2_count"] for a in articles]
    return {
        "total_articles": len(articles),
        "avg_char_count": round(sum(char_counts) / len(char_counts)),
        "avg_title_length": round(sum(title_lengths) / len(title_lengths), 1) if title_lengths else 0,
        "title_length_range": f"{min(title_lengths)}-{max(title_lengths)}" if title_lengths else "N/A",
        "avg_paragraphs": round(sum(para_counts) / len(para_counts), 1),
        "avg_h2_count": round(sum(h2_counts) / len(h2_counts), 1),
    }


def build_analysis_batches(articles: list[dict], batch_size: int) -> list[list[dict]]:
    batches = []
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batches.append(batch)
    return batches


def output_analysis_prompt(articles: list[dict], stats: dict, batch_idx: int, total_batches: int):
    print(f"\n{'='*60}")
    print(f"BATCH {batch_idx + 1}/{total_batches} \u2014 {len(articles)} articles")
    print(f"{'='*60}\n")
    for i, article in enumerate(articles):
        print(f"--- Article {i+1}: {article['title']} ({article['char_count']}\u5b57) ---")
        text = article["text"]
        if len(text) > 3000:
            text = text[:3000] + "\n\n[...truncated...]"
        print(text)
        print()


def main():
    parser = argparse.ArgumentParser(description="Build writing playbook from corpus")
    parser.add_argument("--batch-size", type=int, default=10, help="Articles per batch")
    parser.add_argument("--stats-only", action="store_true", help="Only show corpus stats")
    args = parser.parse_args()
    articles = load_corpus()
    if not articles:
        print("Error: no articles found in corpus/", file=sys.stderr)
        sys.exit(1)
    stats = compute_corpus_stats(articles)
    print("=" * 60)
    print("CORPUS ANALYSIS")
    print("=" * 60)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.stats_only:
        return
    batches = build_analysis_batches(articles, args.batch_size)
    print(f"\nTotal: {stats['total_articles']} articles in {len(batches)} batch(es)")
    print(f"Average: {stats['avg_char_count']} chars, {stats['avg_title_length']} char titles, {stats['avg_h2_count']} H2s")
    print(f"""
{'='*60}
ANALYSIS INSTRUCTIONS FOR AGENT
{'='*60}

Read all articles below, then generate playbook.md with these sections:

## \u6807\u9898\u6a21\u5f0f
- \u5e73\u5747\u5b57\u6570\u548c\u8303\u56f4
- \u5e38\u7528\u7b56\u7565\u5206\u5e03\uff08\u6570\u5b57/\u53cd\u76f4\u89c9/\u75db\u70b9/\u7591\u95ee/\u9648\u8ff0\uff0c\u7ed9\u767e\u5206\u6bd4\uff09
- \u6807\u70b9\u4e60\u60ef\uff08\u9017\u53f7\u65ad\u53e5\uff1f\u95ee\u53f7\uff1f\u611f\u53f9\u53f7\uff1f\uff09
- \u793a\u4f8b\uff1a\u5217\u51fa 3 \u4e2a\u6700\u5178\u578b\u7684\u6807\u9898

## \u5f00\u5934\u6a21\u5f0f
- \u6700\u5e38\u7528\u7684\u5f00\u5934\u65b9\u5f0f\uff08\u573a\u666f/\u6570\u636e/\u53cd\u95ee/\u65b0\u95fb\u5f15\u8ff0/\u4e2a\u4eba\u7ecf\u5386\uff09
- \u7b2c\u4e00\u6bb5\u5e73\u5747\u957f\u5ea6
- \u4ece\u4e0d\u51fa\u73b0\u7684\u5f00\u5934\u65b9\u5f0f
- \u793a\u4f8b\uff1a\u5217\u51fa 3 \u4e2a\u5178\u578b\u5f00\u5934\u7684\u7b2c\u4e00\u6bb5

## \u6bb5\u843d\u8282\u594f
- \u5e73\u5747\u6bb5\u843d\u957f\u5ea6\uff08\u5b57\u6570\uff09
- \u77ed\u6bb5\uff08<30\u5b57\uff09\u5360\u6bd4
- \u6700\u957f\u6bb5\u843d\u4e0a\u9650
- \u957f\u77ed\u4ea4\u66ff\u89c4\u5f8b

## \u7528\u8bcd\u6307\u7eb9
- \u9ad8\u9891\u6807\u5fd7\u8bcd/\u53e3\u5934\u7985\uff08\u51fa\u73b0 3 \u6b21\u4ee5\u4e0a\u7684\u7279\u5f81\u6027\u8868\u8fbe\uff09
- \u7981\u7528\u8bcd\uff08\u4ece\u672a\u4f7f\u7528\u7684\u5e38\u89c1 AI \u7528\u8bed\uff09
- \u82f1\u6587/\u4e13\u4e1a\u672f\u8bed\u4f7f\u7528\u4e60\u60ef
- \u8bed\u6c14\u8bcd\u504f\u597d

## H2 \u547d\u540d\u4e60\u60ef
- \u7528\u95ee\u53e5\uff1f\u77ed\u8bed\uff1f\u6570\u5b57\u7f16\u53f7\uff1f
- \u5e73\u5747\u957f\u5ea6
- \u793a\u4f8b

## \u7ed3\u5c3e\u6a21\u5f0f
- \u6536\u5c3e\u65b9\u5f0f\uff08\u4e2a\u4eba\u89c2\u70b9/\u5f00\u653e\u63d0\u95ee/\u884c\u52a8\u5efa\u8bae/\u91d1\u53e5\uff09
- CTA \u98ce\u683c
- \u793a\u4f8b

## \u60c5\u7eea\u57fa\u8c03
- \u7406\u6027 vs \u611f\u6027\u7684\u6bd4\u4f8b
- \u5e7d\u9ed8\u9891\u7387
- \u6279\u5224\u6027\u5f3a\u5ea6

## \u914d\u56fe\u98ce\u683c\uff08\u5982\u679c\u5386\u53f2\u6587\u7ae0\u6709\u914d\u56fe\u63cf\u8ff0\uff09
- \u8272\u8c03\u504f\u597d
- \u98ce\u683c\u5173\u952e\u8bcd

\u8bf7\u7528\u91cf\u5316\u6570\u636e\uff08\u767e\u5206\u6bd4\u3001\u5e73\u5747\u503c\u3001\u8303\u56f4\uff09\u652f\u6491\u6bcf\u4e2a\u7ed3\u8bba\uff0c\u4e0d\u8981\u53ea\u505a\u5b9a\u6027\u63cf\u8ff0\u3002
""")
    for i, batch in enumerate(batches):
        output_analysis_prompt(batch, stats, i, len(batches))


if __name__ == "__main__":
    main()
