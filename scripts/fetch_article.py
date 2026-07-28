#!/usr/bin/env python3
"""fetch_article.py \u2014 extract WeChat article content as Markdown.

Four-level fetching strategy:
  Level 1: requests (fast, zero overhead, works for most articles)
  Level 2: Camoufox anti-detection browser (bypasses WeChat bot verification)
  Level 3: Playwright headless Chrome (fallback)
  Level 4: Prompt user to save HTML manually and pass via --file

Usage:
    python3 scripts/fetch_article.py <url>                    # auto fetch
    python3 scripts/fetch_article.py <url> -o article.md      # save to file
    python3 scripts/fetch_article.py --file saved.html        # from local HTML
    python3 scripts/fetch_article.py <url> --json             # JSON output for agent
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _fetch_requests(url: str, timeout: int = 20) -> str | None:
    try:
        resp = requests.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except requests.exceptions.RequestException:
        return None


def _fetch_camoufox(url: str) -> str | None:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        return None
    try:
        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_selector("#js_content", timeout=10000)
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
            return html
    except Exception:
        return None


def _fetch_playwright(url: str, timeout: int = 30000) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_BROWSER_UA)
            page.goto(url, wait_until="networkidle", timeout=timeout)
            page.wait_for_selector("#js_content", timeout=10000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return None


def fetch_html(url: str) -> str:
    html = _fetch_requests(url)
    if html and _has_content(html):
        return html
    print("requests \u672a\u83b7\u53d6\u5230\u6b63\u6587\uff0c\u5c1d\u8bd5 Camoufox...", file=sys.stderr)
    html = _fetch_camoufox(url)
    if html and _has_content(html):
        return html
    print("Camoufox \u672a\u83b7\u53d6\u5230\u6b63\u6587\uff0c\u5c1d\u8bd5 Playwright...", file=sys.stderr)
    html = _fetch_playwright(url)
    if html and _has_content(html):
        return html
    print("Error: \u65e0\u6cd5\u83b7\u53d6\u6587\u7ae0\u5185\u5bb9\u3002\u8bf7\u5728\u6d4f\u89c8\u5668\u4e2d\u6253\u5f00\u6587\u7ae0 \u2192 \u53f3\u952e\u53e6\u5b58\u4e3a HTML \u2192 \u4f7f\u7528 --file \u53c2\u6570\u4f20\u5165\u3002", file=sys.stderr)
    sys.exit(1)


def _has_content(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="js_content")
    if content is None:
        return False
    text = content.get_text(strip=True)
    return len(text) > 50


def _extract_metadata(soup: BeautifulSoup) -> dict:
    title_tag = soup.find("h1", class_="rich_media_title") or soup.find("h1", id="activity-name")
    title = title_tag.get_text(strip=True) if title_tag else ""
    author_tag = soup.find("a", id="js_name") or soup.find("span", class_="rich_media_meta_nickname")
    author = author_tag.get_text(strip=True) if author_tag else ""
    pub_tag = soup.find("em", id="publish_time")
    pub_time = pub_tag.get_text(strip=True) if pub_tag else ""
    return {"title": title, "author": author, "publish_time": pub_time}


def _elem_to_md(elem, depth: int = 0) -> str:
    tag = elem.name if hasattr(elem, "name") else None
    if isinstance(elem, NavigableString):
        text = str(elem).strip()
        return text if text else ""
    if tag is None:
        return ""
    style = elem.get("style", "")
    if "display:none" in style.replace(" ", "").lower():
        return ""
    if "visibility:hidden" in style.replace(" ", "").lower():
        return ""
    inner = ""
    for child in elem.children:
        inner += _elem_to_md(child, depth + 1)
    inner = inner.strip()
    if not inner:
        return ""
    if tag in ("h1", "h2", "h3", "h4"):
        level = int(tag[1])
        return f"\n\n{'#' * level} {inner}\n\n"
    if tag == "p":
        return f"\n\n{inner}\n\n"
    if tag == "br":
        return "\n"
    if tag in ("strong", "b"):
        return f"**{inner}**"
    if tag in ("em", "i"):
        return f"*{inner}*"
    if tag == "a":
        href = elem.get("href", "")
        if href and not href.startswith("javascript:"):
            return f"[{inner}]({href})"
        return inner
    if tag == "img":
        src = elem.get("data-src") or elem.get("src") or ""
        alt = elem.get("alt", "")
        if src:
            return f"\n\n![{alt}]({src})\n\n"
        return ""
    if tag == "blockquote":
        lines = inner.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines if line.strip())
        return f"\n\n{quoted}\n\n"
    if tag in ("ul", "ol"):
        return f"\n\n{inner}\n\n"
    if tag == "li":
        parent = elem.parent
        if parent and parent.name == "ol":
            return f"1. {inner}\n"
        return f"- {inner}\n"
    if tag == "code":
        if elem.parent and elem.parent.name == "pre":
            return inner
        return f"`{inner}`"
    if tag == "pre":
        return f"\n\n```\n{inner}\n```\n\n"
    if tag == "hr":
        return "\n\n---\n\n"
    if tag in ("section", "div", "span", "article", "main", "figure", "figcaption", "table", "thead", "tbody", "tr"):
        return inner
    if tag in ("td", "th"):
        return f" {inner} |"
    return inner


def html_to_markdown(soup: BeautifulSoup) -> str:
    content = soup.find(id="js_content")
    if content is None:
        return ""
    if content.get("style"):
        del content["style"]
    raw = _elem_to_md(content)
    md = re.sub(r"\n{3,}", "\n\n", raw)
    md = md.strip()
    return md


def fetch_article(url: str = None, file_path: str = None) -> dict:
    if file_path:
        html = Path(file_path).read_text(encoding="utf-8")
    elif url:
        html = fetch_html(url)
    else:
        raise ValueError("Either url or file_path must be provided")
    soup = BeautifulSoup(html, "html.parser")
    meta = _extract_metadata(soup)
    md = html_to_markdown(soup)
    return {"title": meta["title"], "author": meta["author"], "publish_time": meta["publish_time"], "markdown": md, "url": url or ""}


def main():
    ap = argparse.ArgumentParser(description="Extract WeChat article content as Markdown.")
    ap.add_argument("url", nargs="?", help="WeChat article URL")
    ap.add_argument("--file", dest="file_path", help="Local HTML file instead of URL")
    ap.add_argument("-o", "--output", help="Save Markdown to file")
    ap.add_argument("--json", dest="as_json", action="store_true", help="Output as JSON (for agent use)")
    args = ap.parse_args()
    if not args.url and not args.file_path:
        ap.error("Provide a URL or --file path")
    result = fetch_article(url=args.url, file_path=args.file_path)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.output:
        out = Path(args.output)
        frontmatter = f"---\ntitle: \"{result['title']}\"\nauthor: \"{result['author']}\"\n"
        if result["publish_time"]:
            frontmatter += f"date: \"{result['publish_time']}\"\n"
        if result["url"]:
            frontmatter += f"source: \"{result['url']}\"\n"
        frontmatter += "---\n\n"
        out.write_text(frontmatter + result["markdown"], encoding="utf-8")
        print(f"Saved: {out}")
    else:
        if result["title"]:
            print(f"# {result['title']}\n")
        if result["author"]:
            print(f"> {result['author']}")
        if result["publish_time"]:
            print(f"> {result['publish_time']}")
        if result["author"] or result["publish_time"]:
            print()
        print(result["markdown"])


if __name__ == "__main__":
    main()
