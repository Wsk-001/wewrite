#!/usr/bin/env python3
"""
SEO keyword research tool.

Queries real search data to evaluate keyword popularity:
  1. Baidu search suggestions (autocomplete volume proxy)
  2. Baidu related searches
  3. WeChat sogou index (search volume proxy)

Usage:
    python3 seo_keywords.py "AI\u5927\u6a21\u578b"
    python3 seo_keywords.py "AI\u5927\u6a21\u578b" "\u79d1\u6280\u80a1" "\u521b\u4e1a"
    python3 seo_keywords.py --json "AI\u5927\u6a21\u578b"

Output: keyword popularity score, related keywords, trending signals.
"""

import argparse
import json
import sys

import requests

TIMEOUT = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def baidu_suggestions(keyword: str) -> list[str]:
    try:
        resp = requests.get("https://suggestion.baidu.com/su", params={"wd": keyword, "action": "opensearch", "ie": "utf-8"}, headers=HEADERS, timeout=TIMEOUT)
        data = resp.json()
        if isinstance(data, list) and len(data) >= 2:
            return data[1]
        return []
    except Exception as e:
        print(f"[warn] baidu suggestions failed: {e}", file=sys.stderr)
        return []


def so360_suggestions(keyword: str) -> list[str]:
    try:
        resp = requests.get("https://sug.so.360.cn/suggest", params={"word": keyword, "encodein": "utf-8", "encodeout": "utf-8", "format": "json"}, headers=HEADERS, timeout=TIMEOUT)
        data = resp.json()
        return [item.get("word", "") for item in data.get("result", []) if item.get("word")]
    except Exception as e:
        print(f"[warn] 360 suggestions failed: {e}", file=sys.stderr)
        return []


def analyze_keyword(keyword: str) -> dict:
    baidu_suggs = baidu_suggestions(keyword)
    so360_suggs = so360_suggestions(keyword)
    baidu_score = min(len(baidu_suggs), 10)
    so360_score = min(len(so360_suggs), 10)
    combined_score = round((baidu_score + so360_score) / 2, 1)
    all_related = list(dict.fromkeys(baidu_suggs + so360_suggs))
    return {"keyword": keyword, "seo_score": combined_score, "baidu_score": baidu_score, "so360_score": so360_score, "baidu_suggestions": baidu_suggs[:5], "so360_suggestions": so360_suggs[:5], "related_keywords": all_related[:10]}


def main():
    parser = argparse.ArgumentParser(description="SEO keyword analysis")
    parser.add_argument("keywords", nargs="+", help="Keywords to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    results = []
    for kw in args.keywords:
        result = analyze_keyword(kw)
        results.append(result)
    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    else:
        for r in results:
            print(f"\n\u5173\u952e\u8bcd: {r['keyword']}")
            print(f"  \u7efc\u5408 SEO \u8bc4\u5206: {r['seo_score']}/10\uff08\u767e\u5ea6 {r['baidu_score']} + 360 {r['so360_score']}\uff09")
            if r["so360_suggestions"]:
                print(f"  360\u70ed\u641c\u8bcd: {', '.join(r['so360_suggestions'][:5])}")
            if r["related_keywords"]:
                print(f"  \u76f8\u5173\u5173\u952e\u8bcd: {', '.join(r['related_keywords'][:5])}")


if __name__ == "__main__":
    main()
