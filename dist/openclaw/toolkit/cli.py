#!/usr/bin/env python3
"""
CLI entry point for WeWrite.

Usage:
    python cli.py preview article.md --theme professional-clean
    python cli.py publish article.md --appid wx123 --secret abc123
    python cli.py themes
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from converter import WeChatConverter, preview_html
from theme import load_theme, list_themes
from wechat_api import get_access_token, upload_image, upload_thumb
from publisher import create_draft, create_image_post
from config import load_config


def cmd_preview(args):
    theme = load_theme(args.theme)
    converter = WeChatConverter(theme=theme)
    result = converter.convert_file(args.input)
    full_html = preview_html(result.html, theme)
    input_path = Path(args.input)
    output = args.output or str(input_path.with_suffix(".html"))
    Path(output).write_text(full_html, encoding="utf-8")
    print(f"Title: {result.title}")
    print(f"Digest: {result.digest}")
    print(f"Images: {len(result.images)}")
    print(f"Output: {output}")
    if not args.no_open:
        webbrowser.open(f"file://{Path(output).absolute()}")
        print("Opened in browser.")


def cmd_publish(args):
    cfg = load_config()
    wechat_cfg = cfg.get("wechat", {})
    appid = args.appid or wechat_cfg.get("appid")
    secret = args.secret or wechat_cfg.get("secret")
    theme_name = args.theme or cfg.get("theme", "professional-clean")
    author = args.author or wechat_cfg.get("author")
    if not appid or not secret:
        print("Error: --appid and --secret required (or set in config.yaml)", file=sys.stderr)
        sys.exit(1)
    theme = load_theme(theme_name)
    converter = WeChatConverter(theme=theme)
    result = converter.convert_file(args.input)
    print(f"Title: {result.title}")
    print(f"Digest: {result.digest}")
    print(f"Images found: {len(result.images)}")
    token = get_access_token(appid, secret)
    print("Access token obtained.")
    md_dir = Path(args.input).resolve().parent
    html = result.html
    for img_src in result.images:
        if img_src.startswith(("http://", "https://")):
            print(f"Skipping remote image: {img_src}")
            continue
        img_path = Path(img_src)
        if not img_path.is_absolute():
            if not img_path.exists():
                img_path = md_dir / img_src
        if img_path.exists():
            print(f"Uploading image: {img_src}")
            wechat_url = upload_image(token, str(img_path))
            html = html.replace(img_src, wechat_url)
            print(f"  -> {wechat_url}")
        else:
            print(f"Warning: image not found: {img_src} (searched {md_dir})")
    thumb_media_id = None
    if args.cover:
        print(f"Uploading cover: {args.cover}")
        thumb_media_id = upload_thumb(token, args.cover)
        print(f"  -> media_id: {thumb_media_id}")
    title = args.title or result.title or Path(args.input).stem
    digest = args.digest or result.digest
    draft = create_draft(
        access_token=token,
        title=title,
        html=html,
        digest=digest,
        thumb_media_id=thumb_media_id,
        author=author,
    )
    print(f"\nDraft created! media_id: {draft.media_id}")


def cmd_themes(args):
    names = list_themes()
    for name in names:
        theme = load_theme(name)
        print(f"  {name:24s} {theme.description}")


def cmd_image_post(args):
    cfg = load_config()
    wechat_cfg = cfg.get("wechat", {})
    appid = args.appid or wechat_cfg.get("appid")
    secret = args.secret or wechat_cfg.get("secret")
    if not appid or not secret:
        print("Error: --appid and --secret required (or set in config.yaml)", file=sys.stderr)
        sys.exit(1)
    images = args.images
    if not images:
        print("Error: at least 1 image required", file=sys.stderr)
        sys.exit(1)
    if len(images) > 20:
        print(f"Error: max 20 images, got {len(images)}", file=sys.stderr)
        sys.exit(1)
    token = get_access_token(appid, secret)
    print(f"Uploading {len(images)} images as permanent materials...")
    media_ids = []
    for img_path in images:
        p = Path(img_path)
        if not p.exists():
            print(f"Error: image not found: {img_path}", file=sys.stderr)
            sys.exit(1)
        print(f"  Uploading: {p.name}")
        mid = upload_thumb(token, str(p))
        media_ids.append(mid)
        print(f"    -> {mid}")
    title = args.title
    if len(title) > 32:
        print(f"Warning: title truncated to 32 chars (was {len(title)})")
        title = title[:32]
    content = args.content or ""
    result = create_image_post(
        access_token=token,
        title=title,
        image_media_ids=media_ids,
        content=content,
        open_comment=True,
    )
    print(f"\nImage post draft created!")
    print(f"  media_id: {result.media_id}")
    print(f"  images: {result.image_count}")
    print(f"  请到公众号后台草稿箱检查并发布")


def cmd_gallery(args):
    from concurrent.futures import ThreadPoolExecutor
    if args.input:
        md_text = Path(args.input).read_text(encoding="utf-8")
    else:
        md_text = "# Sample\n\nSample content for gallery."
    names = list_themes()
    results = {}
    def render_theme(name):
        theme = load_theme(name)
        converter = WeChatConverter(theme=theme)
        result = converter.convert(md_text)
        return name, theme.description, result.html
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, desc, html in pool.map(lambda n: render_theme(n), names):
            results[name] = (desc, html)
    output = args.output or "/tmp/wewrite-gallery.html"
    Path(output).write_text("Gallery HTML", encoding="utf-8")
    print(f"Gallery: {output} ({len(names)} themes)")
    if not args.no_open:
        webbrowser.open(f"file://{Path(output).absolute()}")


def main():
    parser = argparse.ArgumentParser(prog="wewrite", description="Markdown to WeChat HTML converter and publisher")
    sub = parser.add_subparsers(dest="command", required=True)
    p_preview = sub.add_parser("preview", help="Generate HTML and open in browser")
    p_preview.add_argument("input", help="Markdown file path")
    p_preview.add_argument("-t", "--theme", default="professional-clean", help="Theme name")
    p_preview.add_argument("-o", "--output", help="Output HTML file path")
    p_preview.add_argument("--no-open", action="store_true", help="Don't open browser")
    p_publish = sub.add_parser("publish", help="Convert and publish as WeChat draft")
    p_publish.add_argument("input", help="Markdown file path")
    p_publish.add_argument("-t", "--theme", default=None, help="Theme name")
    p_publish.add_argument("--appid", default=None, help="WeChat AppID")
    p_publish.add_argument("--secret", default=None, help="WeChat AppSecret")
    p_publish.add_argument("--cover", help="Cover image file path")
    p_publish.add_argument("--title", help="Override article title")
    p_publish.add_argument("--author", default=None, help="Article author")
    p_publish.add_argument("--digest", default=None, help="Override article digest")
    sub.add_parser("themes", help="List available themes")
    p_imgpost = sub.add_parser("image-post", help="Create WeChat image post")
    p_imgpost.add_argument("images", nargs="+", help="Image file paths")
    p_imgpost.add_argument("-t", "--title", required=True, help="Post title")
    p_imgpost.add_argument("-c", "--content", default="", help="Plain text description")
    p_imgpost.add_argument("--appid", default=None, help="WeChat AppID")
    p_imgpost.add_argument("--secret", default=None, help="WeChat AppSecret")
    p_gallery = sub.add_parser("gallery", help="Open theme gallery in browser")
    p_gallery.add_argument("input", nargs="?", default=None, help="Markdown file")
    p_gallery.add_argument("-o", "--output", help="Output HTML file path")
    p_gallery.add_argument("--no-open", action="store_true", help="Don't open browser")
    args = parser.parse_args()
    try:
        if args.command == "preview":
            cmd_preview(args)
        elif args.command == "publish":
            cmd_publish(args)
        elif args.command == "themes":
            cmd_themes(args)
        elif args.command == "image-post":
            cmd_image_post(args)
        elif args.command == "gallery":
            cmd_gallery(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()