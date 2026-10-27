#!/usr/bin/env python3
"""
CLI entry point for WeWrite.

Usage:
    python cli.py preview article.md --theme moyu-green
    python cli.py publish article.md --appid wx123 --secret abc123
    python cli.py themes
"""

import argparse
import os
import re
import sys
import traceback
import webbrowser
from pathlib import Path
from urllib.parse import unquote

from wechat_api import get_access_token, upload_image, upload_thumb
from publisher import create_draft, create_image_post
from config import load_config
from gzh_converter import GzhConverter, ConvertResult
from theme_configs import THEMES as GZH_THEMES, generate_adaptive_theme


def _is_gzh_theme(theme_name: str) -> bool:
    """Check whether a theme name belongs to the gzh-design theme set."""
    return theme_name in GZH_THEMES or theme_name == "adaptive"


def _resolve_theme(theme_name: str, article_path, cover_path=None) -> str:
    """Resolve `auto` theme by generating adaptive design from content; pass through otherwise."""
    if theme_name != "auto":
        return theme_name
    
    text = Path(article_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((l.lstrip("# ").strip() for l in lines if l.startswith("# ")), "")
    
    # 查找封面图（优先使用显式传入的，否则查找同目录 cover-* 文件）
    if cover_path is None:
        article_dir = Path(article_path).parent
        covers = list(article_dir.glob("cover-*.jpg")) + list(article_dir.glob("cover-*.png"))
        cover_path = covers[0] if covers else None
    
    theme, design_report = generate_adaptive_theme(title, text, cover_path)
    print(design_report)
    
    # 注册到全局 THEMES 以便 GzhConverter.get_theme 查找
    GZH_THEMES["adaptive"] = theme
    return "adaptive"


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _local_image_refs(md_text: str):
    """Return image sources in the markdown that point to local files."""
    refs = []
    for m in MD_IMAGE_RE.finditer(md_text):
        src = unquote(m.group(1).strip())
        if src.startswith(("http://", "https://", "data:", "//")):
            continue
        refs.append(src)
    return refs


def _image_files_in_dir(directory: Path):
    return sorted(
        p.name for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def _resolve_image_path(src: str, md_path: Path) -> Path:
    """Resolve a markdown image source for both validation and upload.

    Tried in order: absolute path, cwd-relative, article-dir-relative, and a
    filename-only fallback (so `output/x.jpg` works when the article itself
    already lives in `output/`). Validation and upload MUST share this, or
    pre-flight passes while the real upload silently skips the image.
    """
    p = Path(src)
    if p.is_absolute():
        return p
    for candidate in (p, md_path.parent / p, md_path.parent / p.name):
        if candidate.is_file():
            return candidate
    return p


def _validate_publish_inputs(args) -> None:
    """Fail fast before any network call when publish inputs are incomplete."""
    md_path = Path(args.input).resolve()
    if not md_path.is_file():
        print(f"Error: 文章文件不存在: {args.input}", file=sys.stderr)
        sys.exit(2)

    no_cover = getattr(args, "no_cover", False)
    if no_cover and args.cover:
        print("Error: --cover 与 --no-cover 不能同时使用。", file=sys.stderr)
        sys.exit(2)
    if not no_cover:
        if not args.cover:
            print(
                "Error: publish 需要封面图，请传 --cover <路径>；"
                "确无封面请在命令中显式加 --no-cover。",
                file=sys.stderr,
            )
            sys.exit(2)
        if not Path(args.cover).is_file():
            print(f"Error: 封面文件不存在: {args.cover}", file=sys.stderr)
            sys.exit(2)

    if getattr(args, "force", False):
        return

    md_text = md_path.read_text(encoding="utf-8")
    refs = _local_image_refs(md_text)
    missing = []
    for src in refs:
        if not _resolve_image_path(src, md_path).is_file():
            missing.append(src)
    if missing:
        print("Error: 正文引用了不存在的图片文件:", file=sys.stderr)
        for src in missing:
            print(f"  - {src}", file=sys.stderr)
        print("请修正路径，或加 --force 跳过本检查。", file=sys.stderr)
        sys.exit(2)

    expect = getattr(args, "expect_images", None)
    if expect is not None and len(refs) != expect:
        print(
            f"Error: 期望 {expect} 张内文图，正文实际引用 {len(refs)} 张。",
            file=sys.stderr,
        )
        print("请补全 ![](路径) 引用，或加 --force 跳过本检查。", file=sys.stderr)
        sys.exit(2)

    if not refs:
        prefix = md_path.stem.split("-")[0]
        candidates = [
            n for n in _image_files_in_dir(md_path.parent)
            if not n.lower().startswith("cover") and n.startswith(prefix)
        ]
        print("Error: 正文没有任何本地图片引用，草稿将不含内文图。", file=sys.stderr)
        if candidates:
            print(f"疑似本文配图: {candidates}", file=sys.stderr)
        print(
            "请在正文合适位置插入 ![](output/<文件名>)，或加 --force 跳过本检查。",
            file=sys.stderr,
        )
        sys.exit(2)


def cmd_preview(args):
    """Generate HTML preview and open in browser."""
    theme_name = _resolve_theme(args.theme, args.input, cover_path=args.cover)
    if not _is_gzh_theme(theme_name):
        print(f"Error: unknown gzh theme: {theme_name}", file=sys.stderr)
        print(f"Available themes: {', '.join(GZH_THEMES)} (or 'auto')", file=sys.stderr)
        sys.exit(1)

    skill_root = Path(__file__).parent.parent / ".ai-ready" / "skills" / "gzh-design"
    converter = GzhConverter(theme_identifier=theme_name, skill_root=skill_root if skill_root.exists() else None)
    cfg = load_config()
    author = cfg.get("wechat", {}).get("author") or cfg.get("author")
    result = converter.convert_file(Path(args.input), author=author)
    print(f"[GZH Design] Using {theme_name} theme")
    full_html = _wrap_gzh_preview(result.html, theme_name)

    # Write to temp file
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


def _wrap_gzh_preview(content_html: str, theme_name: str) -> str:
    """Wrap GZH content in preview HTML shell."""
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Preview - {theme_name}</title>
  <style>
    body {{ margin: 0; padding: 20px; background: #f5f5f5; font-family: sans-serif; }}
    .phone {{ max-width: 375px; margin: 0 auto; background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    .phone-content {{ padding: 0; }}
  </style>
</head>
<body>
  <div class="phone">
    <div class="phone-content">{content_html}</div>
  </div>
</body>
</html>"""


def cmd_publish(args):
    """Convert, upload images, and create WeChat draft."""
    _validate_publish_inputs(args)

    cfg = load_config()
    wechat_cfg = cfg.get("wechat", {})

    appid = args.appid or wechat_cfg.get("appid")
    secret = args.secret or wechat_cfg.get("secret")
    theme_name = _resolve_theme(
        args.theme or cfg.get("theme", "moyu-green"), 
        args.input, 
        cover_path=args.cover
    )
    author = args.author or wechat_cfg.get("author") or cfg.get("author")

    if not appid or not secret:
        print("Error: --appid and --secret required (or set in config.yaml)", file=sys.stderr)
        sys.exit(1)

    if not _is_gzh_theme(theme_name):
        print(f"Error: unknown gzh theme: {theme_name}", file=sys.stderr)
        print(f"Available themes: {', '.join(GZH_THEMES)} (or 'auto')", file=sys.stderr)
        sys.exit(1)

    skill_root = Path(__file__).parent.parent / ".ai-ready" / "skills" / "gzh-design"
    converter = GzhConverter(theme_identifier=theme_name, skill_root=skill_root if skill_root.exists() else None)
    result = converter.convert_file(Path(args.input), author=author)
    print(f"[GZH Design] Using {theme_name} theme")

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

        img_path = _resolve_image_path(unquote(img_src), Path(args.input).resolve())

        if img_path.is_file():
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
    """List available themes."""
    print("GZH Design Themes:")
    for ident, theme in GZH_THEMES.items():
        print(f"  {ident:24s} {theme.display_name} - {theme.suitable_for}")
    print("\nSpecial:")
    print(f"  {'auto':24s} 自适应生成 - 根据内容语义和封面图自动设计配色")


def cmd_image_post(args):
    """Create a WeChat image post (\u5c0f\u7eff\u4e66) from image files."""
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

    print("\nImage post draft created!")
    print(f"  media_id: {result.media_id}")
    print(f"  images: {result.image_count}")
    print(f"  title: {title}")
    print("  \u8bf7\u5230\u516c\u4f17\u53f7\u540e\u53f0\u8349\u7a3f\u7bb1\u68c0\u67e5\u5e76\u53d1\u5e03")


def cmd_gallery(args):
    """Render all gzh themes side by side in a browser gallery."""
    from concurrent.futures import ThreadPoolExecutor

    if args.input:
        md_text = Path(args.input).read_text(encoding="utf-8")
    else:
        md_text = _gallery_sample_markdown()

    names = list(GZH_THEMES.keys())
    results = {}

    def render_theme(name):
        converter = GzhConverter(theme_identifier=name)
        result = converter.convert(md_text)
        return name, GZH_THEMES[name].display_name, result.html

    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, desc, html in pool.map(lambda n: render_theme(n), names):
            results[name] = (desc, html)

    gallery_html = _build_gallery_html(results, names)
    output = args.output or "/tmp/wewrite-gallery.html"
    Path(output).write_text(gallery_html, encoding="utf-8")
    print(f"Gallery: {output} ({len(names)} themes)")

    if not args.no_open:
        webbrowser.open(f"file://{Path(output).absolute()}")


def _gallery_sample_markdown():
    return """# \u793a\u4f8b\u6587\u7ae0\u6807\u9898

## \u7b2c\u4e00\u90e8\u5206

\u8fd9\u662f\u4e00\u6bb5\u6b63\u5e38\u7684\u6587\u7ae0\u5185\u5bb9\uff0c\u7528\u6765\u5c55\u793a\u4e0d\u540c\u4e3b\u9898\u7684\u6392\u7248\u6548\u679c\u3002WeWrite \u652f\u6301\u591a\u79cd\u6392\u7248\u4e3b\u9898\uff0c\u6bcf\u79cd\u90fd\u6709\u72ec\u7279\u7684\u89c6\u89c9\u98ce\u683c\u3002

\u8bf4\u5b9e\u8bdd\uff0c\u9009\u4e3b\u9898\u8fd9\u4ef6\u4e8b\u2014\u2014\u770b\u622a\u56fe\u6c38\u8fdc\u4e0d\u5982\u770b\u5b9e\u9645\u6e32\u67d3\u6548\u679c\u3002

## \u5173\u952e\u6570\u636e

| \u6307\u6807 | \u6570\u503c | \u53d8\u5316 |
|------|------|------|
| \u9605\u8bfb\u91cf | 12,580 | +23% |
| \u5206\u4eab\u7387 | 4.7% | +0.8% |
| \u5b8c\u8bfb\u7387 | 68% | -2% |

## \u4ee3\u7801\u793a\u4f8b

```python
def hello():
    print("Hello, WeWrite!")
```

> \u597d\u7684\u6392\u7248\u4e0d\u662f\u8ba9\u8bfb\u8005\u6ce8\u610f\u5230\u8bbe\u8ba1\uff0c\u800c\u662f\u8ba9\u8bfb\u8005\u5fd8\u8bb0\u8bbe\u8ba1\uff0c\u53ea\u8bb0\u4f4f\u5185\u5bb9\u3002

## \u5217\u8868\u5c55\u793a

- \u7b2c\u4e00\u4e2a\u8981\u70b9\uff1a\u7b80\u6d01\u662f\u8bbe\u8ba1\u7684\u7075\u9b42
- \u7b2c\u4e8c\u4e2a\u8981\u70b9\uff1a\u4e00\u81f4\u6027\u6bd4\u521b\u610f\u66f4\u91cd\u8981
- \u7b2c\u4e09\u4e2a\u8981\u70b9\uff1a\u79fb\u52a8\u7aef\u4f53\u9a8c\u4f18\u5148

**\u52a0\u7c97\u6587\u672c**\u548c*\u659c\u4f53\u6587\u672c*\u7684\u6837\u5f0f\u4e5f\u9700\u8981\u5173\u6ce8\u3002

\u6700\u540e\u8fd9\u6bb5\u7528\u6765\u5c55\u793a\u6587\u7ae0\u7ed3\u5c3e\u7684\u7559\u767d\u548c\u95f4\u8ddd\u6548\u679c\u3002\u4e00\u7bc7\u597d\u6587\u7ae0\u7684\u7ed3\u5c3e\uff0c\u5e94\u8be5\u50cf\u4e00\u9996\u597d\u6b4c\u7684\u6700\u540e\u4e00\u4e2a\u97f3\u7b26\u2014\u2014\u6070\u5230\u597d\u5904\u5730\u6536\u675f\u3002
"""


def _join_newline(items):
    return ",\n".join(items)


def _build_gallery_html(results, names):
    cards = []
    for name in names:
        desc, html = results[name]
        cards.append(f"""
        <div class="theme-card" onclick="selectTheme('{name}')">
          <div class="theme-name">{name}</div>
          <div class="theme-desc">{desc}</div>
          <div class="phone-frame">
            <div class="phone-content" id="preview-{name}">{html}</div>
          </div>
          <button class="copy-btn" onclick="event.stopPropagation(); copyHTML('{name}')">\u590d\u5236 HTML</button>
        </div>""")

    data_entries = []
    for name in names:
        desc, html = results[name]
        safe = html.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        data_entries.append(f"  '{name}': '{safe}'")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WeWrite \u4e3b\u9898\u753b\u5eca</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f0f0f; color: #fff; }}
.header {{ text-align: center; padding: 40px 20px 20px; }}
.header h1 {{ font-size: 28px; font-weight: 700; }}
.header p {{ color: #888; margin-top: 8px; font-size: 15px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px; padding: 24px; max-width: 1440px; margin: 0 auto; }}
.theme-card {{ background: #1a1a1a; border-radius: 12px; padding: 16px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
.theme-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
.theme-name {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; }}
.theme-desc {{ font-size: 13px; color: #888; margin-bottom: 12px; }}
.phone-frame {{ background: #fff; border-radius: 8px; overflow: hidden; max-height: 480px; overflow-y: auto; }}
.phone-content {{ padding: 16px; font-size: 14px; transform: scale(0.85); transform-origin: top left; width: 118%; }}
.copy-btn {{ margin-top: 12px; width: 100%; padding: 8px; background: #333; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }}
.copy-btn:hover {{ background: #555; }}
.toast {{ position: fixed; bottom: 40px; left: 50%; transform: translateX(-50%); background: #333; color: #fff; padding: 10px 24px; border-radius: 8px; font-size: 14px; display: none; z-index: 999; }}
</style>
</head>
<body>
<div class="header">
  <h1>WeWrite \u4e3b\u9898\u753b\u5eca</h1>
  <p>{len(names)} \u4e2a\u4e3b\u9898 \u00b7 \u70b9\u51fb\u5361\u7247\u67e5\u770b\u5927\u56fe \u00b7 \u70b9\u51fb\u300c\u590d\u5236 HTML\u300d\u76f4\u63a5\u7c98\u8d34\u5230\u516c\u4f17\u53f7\u7f16\u8f91\u5668</p>
</div>
<div class="grid">
{''.join(cards)}
</div>
<div class="toast" id="toast">\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f</div>
<script>
const themeData = {{
{_join_newline(data_entries)}
}};
function copyHTML(name) {{
  const html = themeData[name];
  if (html) {{
    navigator.clipboard.writeText(html).then(() => {{
      const t = document.getElementById('toast');
      t.style.display = 'block';
      setTimeout(() => t.style.display = 'none', 1500);
    }});
  }}
}}
function selectTheme(name) {{
  localStorage.setItem('wewrite-theme', name);
  const el = document.getElementById('preview-' + name);
  if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
}}
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        prog="wewrite",
        description="Markdown to WeChat HTML converter and publisher",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_preview = sub.add_parser("preview", help="Generate HTML and open in browser")
    p_preview.add_argument("input", help="Markdown file path")
    p_preview.add_argument("-t", "--theme", default="moyu-green", help="GZH theme name, or 'auto' to match content")
    p_preview.add_argument("-o", "--output", help="Output HTML file path")
    p_preview.add_argument("--cover", help="Cover image path (used by 'auto' theme for color extraction)")
    p_preview.add_argument("--no-open", action="store_true", help="Don't open browser")

    p_publish = sub.add_parser("publish", help="Convert and publish as WeChat draft")
    p_publish.add_argument("input", help="Markdown file path")
    p_publish.add_argument("-t", "--theme", default=None,
        help="GZH theme. Options: moyu-green (摸鱼绿), red-white (红白), graphite-minimal (石墨), zen-whitespace (禅意), moyu-ticket (票据), olive-journal (手记), hotpot-warm (汤底暖橙), or 'auto' to match content")
    p_publish.add_argument("--appid", default=None, help="WeChat AppID (or set in config.yaml)")
    p_publish.add_argument("--secret", default=None, help="WeChat AppSecret (or set in config.yaml)")
    p_publish.add_argument("--cover", help="Cover image file path")
    p_publish.add_argument(
        "--no-cover",
        action="store_true",
        help="Explicitly publish without a cover image",
    )
    p_publish.add_argument(
        "--expect-images",
        type=int,
        default=None,
        help="Fail if the number of local inline image references differs",
    )
    p_publish.add_argument(
        "--force",
        action="store_true",
        help="Skip inline-image reference validation",
    )
    p_publish.add_argument("--title", help="Override article title")
    p_publish.add_argument("--author", default=None, help="Article author")
    p_publish.add_argument("--digest", default=None, help="Override article digest (≤120 UTF-8 bytes)")

    sub.add_parser("themes", help="List available themes")

    p_imgpost = sub.add_parser("image-post", help="Create WeChat image post (小绿书)")
    p_imgpost.add_argument("images", nargs="+", help="Image file paths (1-20, first = cover)")
    p_imgpost.add_argument("-t", "--title", required=True, help="Post title (max 32 chars)")
    p_imgpost.add_argument("-c", "--content", default="", help="Plain text description (max ~1000 chars)")
    p_imgpost.add_argument("--appid", default=None, help="WeChat AppID")
    p_imgpost.add_argument("--secret", default=None, help="WeChat AppSecret")

    p_gallery = sub.add_parser("gallery", help="Open theme gallery in browser")
    p_gallery.add_argument("input", nargs="?", default=None, help="Markdown file (optional, uses sample if omitted)")
    p_gallery.add_argument("-o", "--output", help="Output HTML file path")
    p_gallery.add_argument("--no-open", action="store_true", help="Don't open browser")

    args = parser.parse_args()

    try:
        # 在执行命令前，加载配置并验证
        from config_manager import load_config, get_config_path, validate_config, check_startup
        
        cfg = load_config()
        cfg_path = get_config_path()
        
        # 输出配置加载信息
        if cfg_path:
            print(f"[Config] Loaded from: {cfg_path}", file=sys.stderr)
        else:
            print("[Config] No config file found, using defaults", file=sys.stderr)
        
        # 验证配置
        is_valid = validate_config()
        if not is_valid:
            print(f"[Config] ⚠ Configuration has issues", file=sys.stderr)
        else:
            print("[Config] ✓ Configuration valid", file=sys.stderr)
        
        # 检查启动状态
        check_startup()
        
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
        if os.environ.get("WEWRITE_DEBUG"):
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
