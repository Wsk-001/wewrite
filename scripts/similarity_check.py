#!/usr/bin/env python3
"""\u6587\u672c\u76f8\u4f3c\u5ea6\u95f8\u95e8\uff1a\u5b57\u7b26 3-gram Jaccard\uff0c\u7528\u4e8e\u8de8\u5e73\u53f0\u6539\u5199\u7684\u53bb\u91cd\u68c0\u6d4b\u3002

\u7528\u6cd5\uff1a
    python3 scripts/similarity_check.py a.md b.md [c.md ...]   # \u4e24\u4e24\u6700\u5927\u76f8\u4f3c\u5ea6
    python3 scripts/similarity_check.py a.md b.md --json       # agent \u89e3\u6790\u7528
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_NORM = re.compile(r"[^\w\u4e00-\u9fff]+")


def _normalize(text: str) -> str:
    return _NORM.sub("", text)


def char_ngrams(text: str, n: int = 3) -> set[str]:
    t = _normalize(text)
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def similarity(a: str, b: str, n: int = 3) -> float:
    A, B = char_ngrams(a, n), char_ngrams(b, n)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def max_pairwise(texts: list[str], n: int = 3) -> float:
    m = 0.0
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            m = max(m, similarity(texts[i], texts[j], n))
    return m


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="\u5b57\u7b26 n-gram Jaccard \u76f8\u4f3c\u5ea6\u95f8\u95e8")
    ap.add_argument("files", nargs="+", help="\u5f85\u6bd4\u8f83\u7684\u6587\u672c\u6587\u4ef6\uff08\u22652\uff09")
    ap.add_argument("--json", action="store_true", help="JSON \u8f93\u51fa\uff08agent \u7528\uff09")
    ap.add_argument("-n", type=int, default=3, help="n-gram \u957f\u5ea6\uff08\u9ed8\u8ba4 3\uff09")
    args = ap.parse_args(argv)
    texts = [Path(f).read_text(encoding="utf-8") for f in args.files]
    m = max_pairwise(texts, args.n) if len(texts) >= 2 else 0.0
    if args.json:
        print(json.dumps({"max_similarity": round(m, 4), "param": "similarity_threshold"}, ensure_ascii=False))
    else:
        print(f"max_similarity = {m:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
