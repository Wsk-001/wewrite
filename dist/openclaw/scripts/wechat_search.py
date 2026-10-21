#!/usr/bin/env python3
"""wechat_search.py — 搜狗微信搜索：按关键词检索公众号文章。

用途（主管道 Step 2 选题）：公众号生态里的同行怎么写、哪些题在爆，
WebSearch 搜不到，热搜榜也没有——这是目前公开可用、无需登录、无需浏览器
的直接途径。

Usage:
    python3 scripts/wechat_search.py "睡眠债" --limit 10
    python3 scripts/wechat_search.py "睡眠债" --days 90 --json
    python3 scripts/wechat_search.py "睡眠债" --resolve     # 追出真实 mp.weixin.qq.com 链接

Exit codes:
    0 成功（可能 0 条结果）
    2 参数/网络错误
    3 命中搜狗反爬（验证码），需退化为 WebSearch
"""

import argparse
import html as html_lib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BASE = "https://weixin.sogou.com"
SEARCH_URL = BASE + "/weixin"
TIMEOUT = (10, 20)
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": BASE + "/",
}

BLOCK_MARKERS = ("antispider", "请输入验证码", "请输入图片中的验证码", "访问过于频繁")
TZ = timezone(timedelta(hours=8))


def detect_block(html: str) -> str:
    """Return a reason string when Sogou serves its anti-spider page."""
    for marker in BLOCK_MARKERS:
        if marker in html:
            return marker
    if "news-list" not in html and "no-result" not in html:
        return "unexpected page (no result list)"
    return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html_lib.unescape(text or "")).strip()


def _epoch_from(block) -> int | None:
    m = re.search(r"timeConvert\('(\d+)'\)", block.decode() if hasattr(block, "decode") else str(block))
    return int(m.group(1)) if m else None


def parse_results(html: str, base: str = BASE) -> list[dict]:
    """Parse one Sogou WeChat result page into a flat list of articles."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    seen: set[str] = set()

    container = soup.select_one("ul.news-list") or soup
    for li in container.select("li"):
        title_a = li.select_one("h3 a")
        if not title_a:
            continue
        title = _clean(title_a.get_text())
        if not title or title in seen:
            continue
        seen.add(title)

        href = (title_a.get("href") or "").strip()
        if href.startswith("/"):
            href = base + href

        summary_el = li.select_one("p.txt-info")
        account_el = li.select_one("span.all-time-y2")

        epoch = None
        script_el = li.find("script")
        if script_el and script_el.string:
            m = re.search(r"timeConvert\('(\d+)'\)", script_el.string)
            if m:
                epoch = int(m.group(1))

        item = {
            "title": title,
            "account": _clean(account_el.get_text()) if account_el else "",
            "summary": _clean(summary_el.get_text())[:120] if summary_el else "",
            "url": html_lib.unescape(href),
        }
        if epoch:
            dt = datetime.fromtimestamp(epoch, TZ)
            item["date"] = dt.strftime("%Y-%m-%d")
            item["days_ago"] = (datetime.now(TZ).date() - dt.date()).days
        items.append(item)
    return items


def join_redirect_parts(parts: list[str]) -> str:
    """Sogou's /link page assembles the target URL from `url += '...'` chunks."""
    return "".join(parts).replace("@", "")


def filter_items(items: list[dict], days: int | None = None, limit: int | None = None) -> list[dict]:
    """Apply recency and count filters to parsed results."""
    out = items
    if days is not None:
        out = [i for i in out if i.get("days_ago") is None or i["days_ago"] <= days]
    if limit is not None:
        out = out[:limit]
    return out


def resolve_url(session: requests.Session, sogou_url: str) -> str | None:
    """Follow a Sogou /link redirect and return the real article URL."""
    try:
        resp = session.get(sogou_url, headers={**HEADERS, "Referer": BASE + "/"}, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    parts = re.findall(r"url \+= '([^']*)'", resp.text)
    if not parts:
        return None
    url = join_redirect_parts(parts)
    return url if url.startswith("http") else None


def fetch(query: str, page: int = 1, session: requests.Session | None = None) -> tuple[str, requests.Session]:
    sess = session or requests.Session()
    params = {"type": "2", "query": query, "ie": "utf8"}
    if page > 1:
        params["page"] = page
    resp = sess.get(SEARCH_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text, sess


def search(query: str, limit: int = 10, days: int | None = None,
           resolve: bool = False, pages: int = 1) -> dict:
    """Search Sogou WeChat; scan up to `pages` result pages.

    搜狗按相关度排序、混着老文，所以 --days 过滤需要多翻几页才捞得到近文。
    """
    sess = requests.Session()
    collected: list[dict] = []
    seen: set[str] = set()

    for page in range(1, max(1, pages) + 1):
        try:
            html, sess = fetch(query, page=page, session=sess)
        except requests.RequestException as e:
            if page == 1:
                raise
            print(f"[warn] page {page} failed: {e}", file=sys.stderr)
            break

        blocked = detect_block(html)
        if blocked:
            if page == 1:
                return {
                    "timestamp": datetime.now(TZ).isoformat(),
                    "query": query,
                    "blocked": True,
                    "error": f"Sogou anti-spider hit: {blocked}. Fall back to WebSearch.",
                    "count": 0,
                    "items": [],
                }
            print(f"[warn] anti-spider on page {page}, stopping", file=sys.stderr)
            break

        page_items = parse_results(html)
        if not page_items:
            break
        for item in page_items:
            if item["title"] in seen:
                continue
            seen.add(item["title"])
            collected.append(item)

        if days is not None:
            recent = [i for i in collected if i.get("days_ago") is None or i["days_ago"] <= days]
            if len(recent) >= limit:
                break

    items = filter_items(collected, days=days, limit=limit)

    if resolve:
        for item in items:
            real = resolve_url(sess, item["url"])
            if real:
                item["resolved_url"] = real

    return {
        "timestamp": datetime.now(TZ).isoformat(),
        "query": query,
        "source": "sogou_wechat",
        "blocked": False,
        "count": len(items),
        "items": items,
    }


def _print_table(result: dict) -> None:
    if result.get("blocked"):
        print(f"[blocked] {result['error']}", file=sys.stderr)
        return
    print(f"查询「{result['query']}」命中 {result['count']} 篇（搜狗微信搜索）")
    if not result["items"]:
        print("（无结果：换更宽的关键词或加大 --days）")
        return
    for idx, item in enumerate(result["items"], 1):
        date = item.get("date", "?")
        ago = item.get("days_ago")
        ago_s = f"{ago}天前" if isinstance(ago, int) else ""
        print(f"{idx}. [{date} {ago_s}] {item['title']}")
        print(f"   公众号：{item['account'] or '?'}")
        if item["summary"]:
            print(f"   摘要：{item['summary']}")
        print(f"   链接：{item.get('resolved_url') or item['url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="搜狗微信搜索：按关键词检索公众号文章")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=10, help="最多返回条数（默认 10）")
    parser.add_argument("--days", type=int, default=None, help="只保留最近 N 天的文章（会多翻几页）")
    parser.add_argument("--pages", type=int, default=1, help="最多翻几页结果（默认 1，配合 --days 用 3-5）")
    parser.add_argument("--resolve", action="store_true", help="追出真实 mp.weixin.qq.com 链接（慢）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if args.limit < 1:
        print("Error: --limit 必须 ≥ 1", file=sys.stderr)
        return 2

    try:
        result = search(
            args.query,
            limit=args.limit,
            days=args.days,
            resolve=args.resolve,
            pages=args.pages,
        )
    except requests.RequestException as e:
        print(f"Error: 请求搜狗失败：{e}", file=sys.stderr)
        return 2

    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_table(result)

    if result.get("blocked"):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
