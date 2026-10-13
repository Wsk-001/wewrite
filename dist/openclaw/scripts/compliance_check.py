#!/usr/bin/env python3
"""
Health-content compliance scanner for WeWrite articles.

Static checks aligned with 2026 platform rules:
  - 《医疗广告认定指南》: no curative-effect claims, no medical institution promotion
  - 《医务人员互联网健康科普负面行为清单(试行)》: no fabricated cases, no "神医/神药"
  - 《广告法》: absolute terms (极限词)
  - WeChat 《运营规范》: no scare-mongering or diversion to external channels

Exit codes: 0 = pass (warnings allowed), 1 = at least one error.

Usage:
    python3 compliance_check.py article.md
    python3 compliance_check.py article.md --json
    python3 compliance_check.py article.md --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path

CURATIVE_PATTERNS = [
    ("保证根治", "error"), ("包治百病", "error"), ("药到病除", "error"),
    ("彻底治愈", "error"), ("永不复发", "error"), ("断根", "error"),
    ("根治", "warn"), ("治愈率100", "error"), ("百分百治愈", "error"),
    ("100%有效", "error"), ("有效率100", "error"), ("零风险", "error"),
    ("绝对安全", "error"), ("无任何副作用", "error"), ("立竿见影", "warn"),
    ("一针见效", "error"), ("三天见效", "warn"), ("数天痊愈", "error"),
]

ABSOLUTE_PATTERNS = [
    ("神医", "error"), ("神药", "error"), ("仙丹", "error"),
    ("祖传秘方", "error"), ("宫廷秘方", "error"), ("秘方", "warn"),
    ("最有效", "warn"), ("最好的医院", "error"), ("第一品牌", "error"),
    ("顶级专家", "warn"), ("国家级权威", "warn"), ("全球首创", "error"),
]

FABRICATED_CASE_REGEX = re.compile(
    r"(我妈|我爸|我姥|我奶|我爷|我姥姥|我外公|我外婆|我二姨|我三叔|"
    r"我大伯|我姑|我舅|我同事|我朋友|我同学|邻居|隔壁老王|我们村|老家亲戚|"
    r"网友小李|朋友老张)[^。！？\n]{0,40}"
    r"(?:得了|查出|确诊|做了|吃了|喝了|敷了|用了|贴了)[^。！？\n]{0,30}"
    r"(?:治好了|痊愈|康复了|好了|根治|消了|降下来了|恢复正常)"
)

DIVERSION_PATTERNS = [
    ("预约挂号", "warn"), ("挂号入口", "warn"), ("扫码进群", "error"),
    ("添加微信", "error"), ("加我微信", "error"), ("私信我", "warn"),
    ("私信咨询", "warn"), ("点击原文预约", "error"), ("后台回复挂号", "error"),
    ("电话咨询", "warn"), ("线下门店", "warn"), ("购买链接", "error"),
    ("点击购买", "error"), ("直播间抢购", "error"),
]

SCARE_PATTERNS = [
    ("再不.{0,6}就会死", "error"), ("再不.{0,8}就没救了", "error"),
    ("不转发.{0,10}出事", "error"), ("紧急通知", "warn"), ("速看救命", "error"),
    ("马上转发", "error"), ("转发给你最爱的人", "error"),
    ("家长必看否则", "error"), ("99%的人不知道", "warn"),
]

CLICKBAIT_PATTERNS = [
    ("震惊", "error"), ("惊呆", "error"), ("必看", "warn"), ("速看", "warn"),
    ("竟然", "warn"), ("不看后悔", "error"), ("绝了", "warn"),
    ("太可怕了", "warn"), ("吓死", "warn"),
]


def _load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _strip_markdown_noise(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text


def _find_all(patterns, text):
    hits = []
    for phrase, level in patterns:
        for m in re.finditer(re.escape(phrase), text):
            start = max(0, m.start() - 15)
            end = min(len(text), m.end() + 15)
            excerpt = text[start:end].replace("\n", " ").strip()
            hits.append({"rule": phrase, "level": level, "excerpt": excerpt})
    return hits


def _dedupe(hits):
    seen = set()
    out = []
    for h in hits:
        key = (h["rule"], h["excerpt"])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def check_article(text: str) -> dict:
    body = _strip_markdown_noise(text)
    results = []

    results.append({"check": "curative_claims", "hits": _dedupe(_find_all(CURATIVE_PATTERNS, body))})
    results.append({"check": "absolute_terms", "hits": _dedupe(_find_all(ABSOLUTE_PATTERNS, body))})

    fab_hits = []
    for m in FABRICATED_CASE_REGEX.finditer(body):
        excerpt = m.group(0).replace("\n", " ").strip()
        fab_hits.append({"rule": "fabricated_case", "level": "error", "excerpt": excerpt})
    results.append({"check": "fabricated_cases", "hits": _dedupe(fab_hits)})

    results.append({"check": "diversion", "hits": _dedupe(_find_all(DIVERSION_PATTERNS, body))})
    results.append({"check": "scare_tactics", "hits": _dedupe(_find_all(SCARE_PATTERNS, body))})
    results.append({"check": "clickbait_words", "hits": _dedupe(_find_all(CLICKBAIT_PATTERNS, body))})

    errors = sum(1 for r in results for h in r["hits"] if h["level"] == "error")
    warns = sum(1 for r in results for h in r["hits"] if h["level"] == "warn")
    return {"passed": errors == 0, "errors": errors, "warnings": warns, "results": results}


SUGGESTIONS = {
    "curative_claims": "改为描述研究结论或风险变化，删除断言式疗效表述",
    "absolute_terms": "删除极限词和'神医神药'类表述，用具体数据替代",
    "fabricated_cases": "虚构病例属于健康科普红线，改为泛化场景或引用真实报道并标注出处",
    "diversion": "删除引流导诊信息，健康科普内容不得植入预约/购买/加群入口",
    "scare_tactics": "恐吓式传播按违规处理，改为陈述风险事实并给出数据",
    "clickbait_words": "标题党词被官方按作弊处理，改写标题",
}


def main():
    parser = argparse.ArgumentParser(description="Health-content compliance scanner")
    parser.add_argument("input", help="Article markdown file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", action="store_true", help="Show all hits including warnings")
    args = parser.parse_args()

    text = _load_text(args.input)
    report = check_article(text)

    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(f"合规扫描: {args.input}")
        if report["errors"] == 0 and report["warnings"] == 0:
            print("  通过，未发现合规风险项")
        for r in report["results"]:
            if not r["hits"]:
                continue
            print(f"\n  [{r['check']}] {len(r['hits'])} 处命中")
            for h in r["hits"]:
                if h["level"] == "warn" and not args.verbose:
                    continue
                marker = "ERROR" if h["level"] == "error" else "WARN "
                print(f"    {marker} {h['excerpt']}")
            print(f"    建议: {SUGGESTIONS[r['check']]}")
        status = "不通过" if report["errors"] > 0 else "通过（含警告）" if report["warnings"] > 0 else "通过"
        print(f"\n结果: {status}（error {report['errors']} / warn {report['warnings']}）")

    sys.exit(1 if report["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
