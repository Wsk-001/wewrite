#!/usr/bin/env python3
"""
Pre-publish SEO check for WeWrite (搜一搜) articles.

Checks aligned with 2026 搜一搜 ranking factors:
  - title length (truncation in search results)
  - clickbait words (treated as cheating by the platform)
  - core keyword position: first 12 chars of title, first 100 chars of body
  - keyword density: 2-3% safe zone, >3% = keyword stuffing penalty
  - heading structure: >=3 subheadings for semantic extraction
  - body length and paragraph length for completion rate

Also suggests 1-2 internal links from history.yaml for end-of-article linking.

Exit codes: 0 = pass, 1 = at least one error.

Usage:
    python3 seo_check.py article.md --keywords "辅食,6个月宝宝"
    python3 seo_check.py article.md --keywords "失眠" --history history.yaml --json
"""

import argparse
import json
import re
import sys
from pathlib import Path

CLICKBAIT_PATTERNS = ["震惊", "惊呆", "必看", "速看", "竟然", "不看后悔", "绝了", "吓死", "99%的人不知道", "太可怕了"]

MAX_TITLE_LEN = 30
KEYWORD_DENSITY_MAX = 0.03
KEYWORD_DENSITY_MIN = 0.02
MIN_SUBHEADINGS = 3
MIN_BODY_CHARS = 1500
MAX_PARAGRAPH_CHARS = 150


def _parse_article(path: str):
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    title = ""
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    if m:
        title = m.group(1).strip()
    subheadings = re.findall(r"^#{2,3}\s+(.+)$", text, flags=re.M)
    body = re.sub(r"^#{1,3}\s+.*$", "", text, flags=re.M)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    return title, subheadings, body, paragraphs


def _keyword_density(keyword: str, body: str) -> float:
    if not keyword or not body:
        return 0.0
    hits = len(re.findall(re.escape(keyword), body))
    return hits * len(keyword) / max(len(body), 1)


def _suggest_links(history_path: str, title: str, keywords: list[str], max_links: int = 2):
    path = Path(history_path)
    if not path.exists():
        return []
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            history = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[warn] failed to read history: {e}", file=sys.stderr)
        return []

    scored = []
    tokens = set(keywords) | {w for w in re.split(r"[\s，。？！、：；,\.!\?]", title) if len(w) >= 2}
    for article in history.get("articles", []):
        hist_title = article.get("title", "")
        if not hist_title or hist_title == title:
            continue
        hist_topic = article.get("topic", "") or ""
        overlap = sum(1 for t in tokens if t and (t in hist_title or t in hist_topic))
        if overlap > 0:
            link = article.get("link") or article.get("url") or ""
            scored.append((overlap, hist_title, link, hist_topic))
    scored.sort(key=lambda x: -x[0])
    return [{"title": t, "topic": topic, "link": link, "relevance": o} for o, t, link, topic in scored[:max_links]]


def split_keywords(raw: str) -> list[str]:
    """核心词按空白、英文逗号、中文逗号、顿号统一切分。"""
    return [k for k in re.split(r"[\s,，、]+", raw or "") if k.strip()]


def check_article(path: str, keywords: list[str], history_path: str | None = None):
    title, subheadings, body, paragraphs = _parse_article(path)
    body_clean = re.sub(r"\s", "", body)
    issues = []
    infos = []

    if not title:
        issues.append({"level": "error", "check": "title", "detail": "未找到 H1 标题"})
    else:
        if len(title) > MAX_TITLE_LEN:
            issues.append({"level": "error", "check": "title_length", "detail": f"标题 {len(title)} 字，超过 {MAX_TITLE_LEN} 字搜索结果页会截断，建议 20-28 字"})
        elif len(title) < 12:
            infos.append({"check": "title_length", "detail": f"标题仅 {len(title)} 字，偏短，建议 20-28 字承载核心关键词"})
        for w in CLICKBAIT_PATTERNS:
            if w in title:
                issues.append({"level": "error", "check": "clickbait", "detail": f"标题含标题党词「{w}」，官方按作弊处理，改写标题"})

    if len(subheadings) < MIN_SUBHEADINGS:
        issues.append({"level": "error", "check": "subheadings", "detail": f"小标题仅 {len(subheadings)} 个，少于 {MIN_SUBHEADINGS} 个影响语义抽取和阅读完成率"})
    else:
        infos.append({"check": "subheadings", "detail": f"小标题 {len(subheadings)} 个，结构化达标"})

    if len(body_clean) < MIN_BODY_CHARS:
        issues.append({"level": "error", "check": "body_length", "detail": f"正文 {len(body_clean)} 字，低于 {MIN_BODY_CHARS} 字深度线，长尾竞争易被判低质"})

    long_paras = [p for p in paragraphs if len(p) > MAX_PARAGRAPH_CHARS]
    if long_paras:
        infos.append({"check": "paragraph_length", "detail": f"{len(long_paras)} 个段落超过 {MAX_PARAGRAPH_CHARS} 字，建议拆分（每段不超过 5 行）"})

    if keywords:
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if title and kw in title[:12]:
                infos.append({"check": "keyword_position", "detail": f"核心词「{kw}」已出现在标题前 12 字"})
            elif title:
                issues.append({"level": "warn", "check": "keyword_position", "detail": f"核心词「{kw}」未出现在标题前 12 字，搜一搜爬虫优先读取标题前部"})
            if kw in body_clean[:100]:
                infos.append({"check": "keyword_position_body", "detail": f"核心词「{kw}」已出现在正文前 100 字"})
            else:
                issues.append({"level": "warn", "check": "keyword_position_body", "detail": f"核心词「{kw}」未出现在正文前 100 字，语义对齐偏弱"})
            density = _keyword_density(kw, body_clean)
            if density > KEYWORD_DENSITY_MAX:
                issues.append({"level": "error", "check": "keyword_density", "detail": f"「{kw}」密度 {density:.1%} 超过 3%，有堆砌降权风险，建议 2%-3%"})
            elif density < KEYWORD_DENSITY_MIN and len(body_clean) >= MIN_BODY_CHARS:
                infos.append({"check": "keyword_density", "detail": f"「{kw}」密度 {density:.1%} 偏低，可自然补充 1-2 次"})

    links = _suggest_links(history_path, title, keywords) if history_path else []

    errors = sum(1 for i in issues if i["level"] == "error")
    warns = sum(1 for i in issues if i["level"] == "warn")
    return {"passed": errors == 0, "errors": errors, "warnings": warns, "issues": issues, "infos": infos, "title": title, "body_chars": len(body_clean), "subheading_count": len(subheadings), "suggested_links": links}


def main():
    parser = argparse.ArgumentParser(description="Pre-publish SEO check")
    parser.add_argument("input", help="Article markdown file")
    parser.add_argument("--keywords", default="", help="Core keywords, separated by comma or whitespace")
    parser.add_argument("--history", default=None, help="history.yaml path for internal link suggestions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    keywords = split_keywords(args.keywords)
    report = check_article(args.input, keywords, args.history)

    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(f"SEO 自检: {args.input}")
        print(f"  标题: {report['title']}（{len(report['title'])} 字）")
        print(f"  正文 {report['body_chars']} 字 / 小标题 {report['subheading_count']} 个")
        if report["errors"] == 0 and report["warnings"] == 0:
            print("  结构检查通过")
        for i in report["issues"]:
            marker = "ERROR" if i["level"] == "error" else "WARN "
            print(f"  {marker} [{i['check']}] {i['detail']}")
        for i in report["infos"]:
            print(f"  INFO  [{i['check']}] {i['detail']}")
        if report["suggested_links"]:
            print("  建议文末内链（提升账号整体收录）:")
            for l in report["suggested_links"]:
                print(f"    - {l['title']}（相关度 {l['relevance']}）{l['link']}")
        status = "不通过" if report["errors"] > 0 else "通过（含警告）" if report["warnings"] > 0 else "通过"
        print(f"\n结果: {status}（error {report['errors']} / warn {report['warnings']}）")

    sys.exit(1 if report["errors"] > 0 else 0)


if __name__ == "__main__":
    main()
