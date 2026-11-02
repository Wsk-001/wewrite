#!/usr/bin/env python3
"""
Comic tietu (小绿书 / image post) pipeline.

Takes a storyboard.json, builds an image-generation batch, renders the
AI base images into captioned 3:4 panels with a recap card, and writes a
local preview. The companion CLI commands are `comic-plan`,
`comic-render`, and `comic-post` (see toolkit/cli.py).

Storyboard schema (see references/pipeline/comic-tietu.md):

{
  "article": "output/foo.md",
  "article_title": "...",
  "post_title": "...",              # <= 32 chars (editor caps at 20), used by comic-post
  "post_body": "...",               # <= 1000 chars
  "style_anchor": "...",
  "size": "1152x1536",              # generation size, 16-multiples
  "palette": "...",
  "avoid": ["文字", "..."],
  "recap_title": "...", "recap_sub": "...", "recap_note": "...", "recap_tail": "...",
  "panels": [
    {"no": 1, "beat": "hook", "scene": "...", "caption": "...", "render": "ai"},
    {"no": 2, ..., "brief": {...}}   # optional full image_prompt_builder brief
  ]
}
"""

import html
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1440
DEFAULT_GEN_SIZE = "1152x1536"
MAX_PANELS = 20
RECOMMENDED_PANELS = 9

BASE_W, BASE_H = 1080, 1440
INK = (24, 32, 34)
CREAM = (247, 243, 233)
ORANGE = (198, 90, 50)
GRAY = (92, 96, 96)

_FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ],
    "bold": [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ],
}


class ComicError(ValueError):
    """Invalid storyboard or render input."""


def _find_font_path(kind):
    for path in _FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return path
    raise ComicError(
        "No CJK font found. Install one (e.g. `apt install fonts-noto-cjk` on "
        "Debian/Ubuntu) or set WEWRITE_FONT_REGULAR / WEWRITE_FONT_BOLD."
    )


def _env_font(kind):
    import os

    key = f"WEWRITE_FONT_{kind.upper()}"
    path = os.environ.get(key)
    if path:
        if not Path(path).exists():
            raise ComicError(f"{key} points to a missing file: {path}")
        return path
    return _find_font_path(kind)


def _font(kind, size):
    path = _env_font(kind)
    indexes = (2, 0) if path.lower().endswith((".ttc", ".otc")) else (0,)
    last_error = None
    for index in indexes:
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError as exc:  # pragma: no cover - font-specific
            last_error = exc
    raise ComicError(f"Cannot load font {path}: {last_error}")


def load_storyboard(path):
    """Load and validate a storyboard JSON file."""
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ComicError(f"storyboard not found: {p}")
    except json.JSONDecodeError as exc:
        raise ComicError(f"storyboard is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise ComicError("storyboard must be a JSON object")
    validate_storyboard(data)
    return data


def validate_storyboard(sb):
    """Return a list of warnings; raise ComicError on hard errors."""
    warnings = []
    panels = sb.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ComicError("storyboard.panels must be a non-empty array")
    if len(panels) > MAX_PANELS:
        raise ComicError(f"storyboard supports at most {MAX_PANELS} panels")
    if len(panels) > RECOMMENDED_PANELS:
        warnings.append(
            f"{len(panels)} panels exceeds the {RECOMMENDED_PANELS}-image limit "
            "of the WeChat image-post editor; split into two posts if needed"
        )

    seen = set()
    for i, panel in enumerate(panels, start=1):
        if not isinstance(panel, dict):
            raise ComicError(f"panels[{i - 1}] must be an object")
        no = panel.get("no", i)
        if not isinstance(no, int) or no < 1:
            raise ComicError(f"panels[{i - 1}].no must be a positive integer")
        if no in seen:
            raise ComicError(f"duplicate panel no: {no}")
        seen.add(no)
        if not (panel.get("caption") or "").strip():
            raise ComicError(f"panel {no} needs a caption")
        render = panel.get("render", "ai")
        if render not in {"ai", "recap"}:
            raise ComicError(f"panel {no} has unsupported render: {render}")
        if render == "ai" and not (panel.get("scene") or panel.get("brief")):
            raise ComicError(f"panel {no} needs scene or brief for AI generation")
        brief = panel.get("brief")
        if brief is not None and not isinstance(brief, dict):
            raise ComicError(f"panel {no}.brief must be an object")

    title = sb.get("post_title")
    if title is not None:
        if len(title) > 32:
            raise ComicError("storyboard.post_title must be <= 32 chars")
        if len(title) > 20:
            warnings.append(
                "post_title is "
                f"{len(title)} chars; the WeChat image-post editor caps titles at "
                "20 chars, so shorten it before publishing from the web UI"
            )
    body = sb.get("post_body") or ""
    if len(body) > 1000:
        raise ComicError("storyboard.post_body must be <= 1000 chars")
    return warnings


DEFAULT_AVOID = ["文字", "字母", "数字", "标签", "logo", "水印", "二维码", "伪文字"]


def _subject_from_scene(scene):
    for sep in ("；", ";", "，", ",", "。"):
        if sep in scene:
            scene = scene.split(sep, 1)[0]
            break
    return scene.strip()[:30]


def _panel_brief(sb, panel):
    if isinstance(panel.get("brief"), dict):
        brief = dict(panel["brief"])
        brief.setdefault("template", "scene")
        return brief
    scene = (panel.get("scene") or "").strip()
    brief = {
        "template": "scene",
        "subject": (panel.get("subject") or _subject_from_scene(scene)).strip(),
        "action": scene,
        "environment": sb.get("environment", "干净、生活化的室内场景，背景虚化"),
    }
    for key in ("camera", "lighting", "style", "palette", "avoid", "aspect"):
        value = panel.get(key, sb.get(key))
        if value:
            brief[key] = value
    if "style" not in brief and sb.get("style_anchor"):
        brief["style"] = sb["style_anchor"]
    brief.setdefault("avoid", list(DEFAULT_AVOID))
    brief.setdefault("aspect", "3:4")
    return brief


def build_batch(storyboard, raw_dir):
    """Build an image_gen --batch task list from the AI panels."""
    raw_dir = Path(raw_dir)
    tasks = []
    for panel in storyboard["panels"]:
        if panel.get("render", "ai") != "ai":
            continue
        tasks.append(
            {
                "output": str(raw_dir / f"raw-{panel['no']}.jpg"),
                "size": panel.get("size") or storyboard.get("size") or DEFAULT_GEN_SIZE,
                "brief": _panel_brief(storyboard, panel),
            }
        )
    return tasks


def _base_image(raw_path):
    img = Image.open(raw_path).convert("RGB")
    return ImageOps.fit(img, (BASE_W, BASE_H), method=Image.LANCZOS, centering=(0.5, 0.45))


def _top_gradient(img, height=260, alpha=160):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(height):
        a = int(alpha * (1 - y / height) ** 1.4)
        d.line((0, y, BASE_W, y), fill=(8, 12, 14, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _top_marks(img, no, total):
    img = _top_gradient(img)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(
        (56, 48),
        f"{no:02d} / {total:02d}",
        font=_font("bold", 32),
        fill=(255, 255, 255, 235),
    )
    return Image.alpha_composite(img, layer)


def _caption_box(img, caption, max_size=76):
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((48, 1090, 1032, 1334), radius=22, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        (54, 1080, 1026, 1324),
        radius=22,
        fill=CREAM + (244,),
        outline=(30, 38, 40, 55),
        width=2,
    )
    d.rounded_rectangle((82, 1148, 92, 1256), radius=5, fill=ORANGE + (255,))

    f = _fit_font(d, caption, 820, max_size)
    box = d.textbbox((0, 0), caption, font=f)
    th = box[3] - box[1]
    d.text((124, 1202 - th / 2 - box[1]), caption, font=f, fill=INK)

    return Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), shadow), layer)


def _fit_font(draw, text, max_width, max_size, min_size=44):
    for size in range(max_size, min_size - 1, -2):
        f = _font("bold", size)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_width:
            return f
    return _font("bold", min_size)


def render_panel(panel, total, raw_path, out_path):
    img = _base_image(raw_path)
    img = _top_marks(img, panel["no"], total)
    max_size = 80 if panel["no"] == 1 else 72
    img = _caption_box(img, panel["caption"], max_size=max_size)
    img.convert("RGB").save(out_path, quality=90, optimize=True)
    return out_path


def _rounded_thumb(path, size):
    img = Image.open(path).convert("RGB")
    img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.4))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=14, fill=255
    )
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def render_recap(storyboard, thumb_paths, out_path):
    bg = Image.open(thumb_paths[0]).convert("RGB")
    bg = ImageOps.fit(bg, (BASE_W, BASE_H), method=Image.LANCZOS, centering=(0.5, 0.4))
    bg = bg.filter(ImageFilter.GaussianBlur(16))
    bg = Image.alpha_composite(
        bg.convert("RGBA"), Image.new("RGBA", (BASE_W, BASE_H), (10, 16, 18, 155))
    )
    bg = _top_gradient(bg, height=200, alpha=180)

    shadow = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((58, 168, 1022, 1272), radius=36, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    bg = Image.alpha_composite(bg, shadow)

    card = Image.new("RGBA", (BASE_W, BASE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle(
        (70, 156, 1010, 1260),
        radius=36,
        fill=CREAM + (252,),
        outline=(30, 38, 40, 45),
        width=2,
    )

    label = storyboard.get("recap_label", "贴图回顾")
    f = _font("bold", 26)
    box = d.textbbox((0, 0), label, font=f)
    d.text(((BASE_W - (box[2] - box[0])) / 2, 204), label, font=f, fill=ORANGE)

    title = storyboard.get("recap_title", "一张图记住要点")
    f = _fit_font(d, title, 860, 82)
    box = d.textbbox((0, 0), title, font=f)
    d.text(((BASE_W - (box[2] - box[0])) / 2, 260), title, font=f, fill=INK)

    sub = storyboard.get("recap_sub") or ""
    if sub:
        f = _font("regular", 30)
        box = d.textbbox((0, 0), sub, font=f)
        d.text(((BASE_W - (box[2] - box[0])) / 2, 372), sub, font=f, fill=GRAY)

    count = min(len(thumb_paths), 5)
    tw, th, gap = 150, 200, 18
    total = count * tw + (count - 1) * gap
    x0 = (BASE_W - total) // 2
    y0 = 500
    for i, p in enumerate(thumb_paths[:count], start=1):
        x = x0 + (i - 1) * (tw + gap)
        thumb = _rounded_thumb(p, (tw, th))
        border = Image.new("RGBA", (tw + 8, th + 8), (255, 255, 255, 255))
        border.paste(thumb, (4, 4), thumb)
        card.alpha_composite(border, (x - 4, y0 - 4))
        d.ellipse((x + 8, y0 + 8, x + 42, y0 + 42), fill=ORANGE + (255,))
        nf = _font("bold", 20)
        nb = d.textbbox((0, 0), str(i), font=nf)
        d.text(
            (x + 25 - (nb[2] - nb[0]) / 2, y0 + 25 - (nb[3] - nb[1]) / 2 - 1),
            str(i),
            font=nf,
            fill=(255, 255, 255, 255),
        )

    d.rounded_rectangle((300, 820, 780, 920), radius=50, fill=ORANGE + (255,))
    cta = storyboard.get("recap_cta", "见公众号文章")
    f = _fit_font(d, cta, 400, 44, min_size=36)
    box = d.textbbox((0, 0), cta, font=f)
    d.text(
        ((BASE_W - (box[2] - box[0])) / 2, 870 - (box[3] - box[1]) / 2 - box[1]),
        cta,
        font=f,
        fill=(255, 255, 255, 255),
    )

    note = storyboard.get("recap_note") or ""
    if note:
        f = _font("regular", 26)
        box = d.textbbox((0, 0), note, font=f)
        d.text(((BASE_W - (box[2] - box[0])) / 2, 980), note, font=f, fill=GRAY)

    tail = storyboard.get("recap_tail") or ""
    if tail:
        f = _font("regular", 26)
        box = d.textbbox((0, 0), tail, font=f)
        d.text(((BASE_W - (box[2] - box[0])) / 2, 1040), tail, font=f, fill=GRAY)

    bg = Image.alpha_composite(bg, card)
    bg.convert("RGB").save(out_path, quality=90, optimize=True)
    return out_path


def contact_sheet(paths, out_path, cols=3, cell=(340, 453)):
    tw, th = cell
    rows = (len(paths) + cols - 1) // cols
    gap, margin = 20, 20
    sheet = Image.new(
        "RGB",
        (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap),
        (238, 234, 224),
    )
    for i, p in enumerate(paths):
        img = ImageOps.fit(Image.open(p).convert("RGB"), (tw, th), method=Image.LANCZOS)
        x = gap + (i % cols) * (tw + gap)
        y = gap + (i // cols) * (th + gap)
        sheet.paste(img, (x, y))
    sheet.save(out_path, quality=90, optimize=True)
    return out_path


def render(storyboard, raw_dir, out_dir, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Render all panels, recap, contact sheet, and preview.html."""
    raw_dir = Path(raw_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    panels = sorted(storyboard["panels"], key=lambda p: p["no"])
    total = len(panels)

    ai_panels = [p for p in panels if p.get("render", "ai") == "ai"]
    missing = [str(raw_dir / f"raw-{p['no']}.jpg") for p in ai_panels
               if not (raw_dir / f"raw-{p['no']}.jpg").exists()]
    if missing:
        raise ComicError("missing raw images: " + ", ".join(missing))

    thumbs = [raw_dir / f"raw-{p['no']}.jpg" for p in ai_panels]
    rendered = []
    for panel in panels:
        out_path = out_dir / f"tietu-{panel['no']}.jpg"
        if panel.get("render", "ai") == "recap":
            if not thumbs:
                raise ComicError("recap panel needs at least one AI panel")
            path = render_recap(storyboard, thumbs, out_path)
        else:
            path = render_panel(panel, total, raw_dir / f"raw-{panel['no']}.jpg", out_path)
        rendered.append(path)

    if (width, height) != (BASE_W, BASE_H):
        for path in rendered:
            img = Image.open(path).convert("RGB")
            ImageOps.fit(img, (width, height), method=Image.LANCZOS).save(
                path, quality=90, optimize=True
            )

    preview = contact_sheet(rendered, out_dir / "preview.jpg")
    preview_html = write_preview_html(storyboard, rendered, out_dir / "preview.html")
    (out_dir / "title.txt").write_text(
        (storyboard.get("post_title") or "") + "\n", encoding="utf-8"
    )
    (out_dir / "body.txt").write_text(
        (storyboard.get("post_body") or "") + "\n", encoding="utf-8"
    )
    return {
        "panels": [str(p) for p in rendered],
        "preview": str(preview),
        "preview_html": str(preview_html),
        "sizes": [list(Image.open(p).size) for p in rendered],
    }


def write_preview_html(storyboard, panel_paths, out_path):
    title = html.escape(storyboard.get("post_title") or "贴图预览")
    body = html.escape(storyboard.get("post_body") or "")
    figures = []
    for panel, path in zip(
        sorted(storyboard["panels"], key=lambda p: p["no"]), panel_paths
    ):
        figures.append(
            '<figure><img src="{src}" alt="{alt}">'
            "<figcaption>{no:02d} {cap}</figcaption></figure>".format(
                src=html.escape(Path(path).name),
                alt=html.escape(panel["caption"]),
                no=panel["no"],
                cap=html.escape(panel["caption"]),
            )
        )
    count = len(panel_paths)
    doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 贴图预览</title>
<style>
  body {{ margin:0; padding:24px; background:#f6f4ef; color:#2b2b2b;
         font-family:-apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif; }}
  h1 {{ font-size:20px; margin:0 0 6px; }}
  .meta {{ font-size:13px; color:#8a857c; margin-bottom:20px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:18px; }}
  figure {{ margin:0; background:#fff; border-radius:10px; padding:10px;
           box-shadow:0 1px 4px rgba(0,0,0,.07); }}
  img {{ width:100%; display:block; border-radius:6px; }}
  figcaption {{ font-size:12px; color:#8a857c; margin-top:8px; text-align:center; }}
  .body {{ margin-top:26px; max-width:640px; background:#fff; border-radius:10px;
          padding:18px 20px; font-size:14px; line-height:1.8; white-space:pre-line;
          box-shadow:0 1px 4px rgba(0,0,0,.07); }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">贴图草稿预览 · {count} 张 · 首图为封面</div>
  <div class="grid">
{figures}
  </div>
  <div class="body">{body}</div>
</body>
</html>
""".format(
        title=title, count=count, figures="\n    ".join(figures), body=body
    )
    Path(out_path).write_text(doc, encoding="utf-8")
    return out_path


def image_paths(storyboard, out_dir):
    return [
        Path(out_dir) / f"tietu-{p['no']}.jpg"
        for p in sorted(storyboard["panels"], key=lambda p: p["no"])
    ]
