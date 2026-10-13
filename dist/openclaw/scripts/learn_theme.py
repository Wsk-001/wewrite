#!/usr/bin/env python3
"""learn_theme.py \u2014 extract a WeWrite-compatible theme from a WeChat article URL.

Usage:
    python3 scripts/learn_theme.py <url>          # fetch + analyse live article
    python3 scripts/learn_theme.py --file <path>  # analyse a saved HTML file
"""

import argparse
import colorsys
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


def rgb_to_hex(rgb_str: str) -> str:
    if not isinstance(rgb_str, str):
        return rgb_str
    s = rgb_str.strip()
    if re.match(r"^#[0-9a-fA-F]{3,8}$", s):
        return s.lower()
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,[\d.]+)?\s*\)", s, re.IGNORECASE)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
    return s


def lightness(hex_color: str) -> float:
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return 0.5
    try:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
    except ValueError:
        return 0.5
    _h, l, _s = colorsys.rgb_to_hls(r, g, b)
    return l


def is_gray(hex_color: str, threshold: int = 30) -> bool:
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return False
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
    except ValueError:
        return False
    return max(r, g, b) - min(r, g, b) <= threshold


def adjust_lightness(hex_color: str, target_l: float) -> str:
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return hex_color
    try:
        r = int(s[0:2], 16) / 255.0
        g = int(s[2:4], 16) / 255.0
        b = int(s[4:6], 16) / 255.0
    except ValueError:
        return hex_color
    h, _l, sat = colorsys.rgb_to_hls(r, g, b)
    nr, ng, nb = colorsys.hls_to_rgb(h, max(0.0, min(1.0, target_l)), sat)
    return "#{:02x}{:02x}{:02x}".format(int(nr * 255), int(ng * 255), int(nb * 255))


def derive_darkmode(colors: dict) -> dict:
    primary = colors.get("primary", "#2563eb")
    primary_l = lightness(primary)
    dm_primary = adjust_lightness(primary, min(primary_l + 0.15, 0.85))
    dm = {"background": "#1e1e1e", "text": adjust_lightness(colors.get("text", "#333333"), 0.80), "text_light": adjust_lightness(colors.get("text_light", "#666666"), 0.60), "primary": dm_primary, "code_bg": "#2d2d2d", "code_color": "#d4d4d4", "quote_bg": "#252525", "quote_border": dm_primary}
    return dm


_TARGET_TAGS = {"p", "section", "span", "strong", "em", "h1", "h2", "h3", "h4", "blockquote", "code", "pre", "img", "a"}

TEMPLATE_THEME = "professional-clean"
THEMES_DIR = Path(__file__).resolve().parent.parent / "toolkit" / "themes"


def _attach_title(soup, content) -> None:
    title_tag = soup.find("h1", class_="rich_media_title") or soup.find("h1", id="activity-name")
    content._wewrite_title = title_tag.get_text(strip=True) if title_tag else ""


def fetch_article(url: str, timeout: int = 20):
    from scripts.fetch_article import fetch_html
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="js_content")
    if content is None:
        print("Error: #js_content not found.", file=sys.stderr)
        sys.exit(1)
    _attach_title(soup, content)
    return content


def extract_styles(content) -> dict:
    grouped: dict[str, list[dict]] = {tag: [] for tag in _TARGET_TAGS}
    for elem in content.find_all(True):
        tag = elem.name
        if tag not in _TARGET_TAGS:
            continue
        raw_style = elem.get("style", "")
        if not raw_style:
            continue
        parsed = {}
        for declaration in raw_style.split(";"):
            declaration = declaration.strip()
            if ":" not in declaration:
                continue
            prop, _, val = declaration.partition(":")
            parsed[prop.strip().lower()] = val.strip()
        if parsed:
            grouped[tag].append(parsed)
    return grouped


DEFAULTS = {"primary": "#2563eb", "secondary": "#3b82f6", "text": "#333333", "text_light": "#666666", "background": "#ffffff", "code_bg": "#1e293b", "code_color": "#e2e8f0", "quote_border": "#2563eb", "quote_bg": "#eff6ff", "border_radius": "8px", "font_size": "16px", "line_height": "1.8", "letter_spacing": "0px", "font_family": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif', "p_margin": "0 0 16px 0"}


def most_common_value(style_list: list, prop: str):
    values = [d[prop] for d in style_list if prop in d and d[prop]]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _parse_px(value: str) -> float | None:
    if not value:
        return None
    m = re.match(r"([\d.]+)\s*px", value.strip(), re.IGNORECASE)
    return float(m.group(1)) if m else None


def analyze_styles(grouped: dict) -> dict:
    result = dict(DEFAULTS)
    p_styles = grouped.get("p", [])
    raw_text = most_common_value(p_styles, "color")
    if raw_text:
        result["text"] = rgb_to_hex(raw_text)
    all_colors = []
    for tag_styles in grouped.values():
        for d in tag_styles:
            val = d.get("color")
            if val:
                all_colors.append(rgb_to_hex(val))
    text_light_candidates = [c for c in all_colors if is_gray(c) and 0.15 < lightness(c) < 0.85 and c != result["text"]]
    if text_light_candidates:
        result["text_light"] = max(text_light_candidates, key=lightness)
    accent_tags = {"strong", "section", "h1", "h2", "h3", "span"}
    accent_counter: Counter = Counter()
    for tag in accent_tags:
        for d in grouped.get(tag, []):
            color_val = d.get("color")
            if not color_val:
                continue
            hex_c = rgb_to_hex(color_val)
            if is_gray(hex_c):
                continue
            if hex_c == result["text"]:
                continue
            fs = d.get("font-size")
            fs_px = _parse_px(fs) if fs else None
            weight = 5 if (fs_px is not None and fs_px >= 20) else 1
            accent_counter[hex_c] += weight
    if accent_counter:
        sorted_accents = accent_counter.most_common()
        result["primary"] = sorted_accents[0][0]
        if len(sorted_accents) >= 2:
            result["secondary"] = sorted_accents[1][0]
        else:
            primary_l = lightness(result["primary"])
            result["secondary"] = adjust_lightness(result["primary"], min(primary_l + 0.10, 0.90))
    else:
        primary_l = lightness(result["primary"])
        result["secondary"] = adjust_lightness(result["primary"], min(primary_l + 0.10, 0.90))
    for d in (grouped.get("section", []))[:10]:
        bg = d.get("background-color") or d.get("background")
        if bg:
            hex_bg = rgb_to_hex(bg)
            if lightness(hex_bg) > 0.85:
                result["background"] = hex_bg
                break
    if p_styles:
        fs = most_common_value(p_styles, "font-size")
        if fs:
            result["font_size"] = fs
        lh = most_common_value(p_styles, "line-height")
        if lh:
            result["line_height"] = lh
        ls = most_common_value(p_styles, "letter-spacing")
        if ls:
            result["letter_spacing"] = ls
        margin = most_common_value(p_styles, "margin")
        if margin:
            result["p_margin"] = margin
    span_styles = grouped.get("span", [])
    ff = most_common_value(span_styles, "font-family")
    if ff:
        result["font_family"] = ff
    bq_border = None
    bq_bg = None
    for d in grouped.get("blockquote", []):
        bl = d.get("border-left") or d.get("border-left-color")
        if bl and not bq_border:
            color_match = re.search(r"(rgb[a]?\([^)]+\)|#[0-9a-fA-F]{3,8})", bl)
            if color_match:
                bq_border = rgb_to_hex(color_match.group(1))
        bg = d.get("background-color") or d.get("background")
        if bg and not bq_bg:
            hex_bg = rgb_to_hex(bg)
            if hex_bg not in ("#ffffff", "#000000") and not is_gray(hex_bg, threshold=10):
                bq_bg = hex_bg
    if not bq_border:
        for tag in ("section", "p"):
            for d in grouped.get(tag, []):
                bl = d.get("border-left") or d.get("border-left-color")
                if bl:
                    color_match = re.search(r"(rgb[a]?\([^)]+\)|#[0-9a-fA-F]{3,8})", bl)
                    if color_match and not bq_border:
                        bq_border = rgb_to_hex(color_match.group(1))
                    bg = d.get("background-color") or d.get("background")
                    if bg and not bq_bg:
                        hex_bg = rgb_to_hex(bg)
                        if hex_bg not in ("#ffffff", "#000000") and not is_gray(hex_bg, threshold=10):
                            bq_bg = hex_bg
    if bq_border:
        result["quote_border"] = bq_border
    else:
        result["quote_border"] = result["primary"]
    if bq_bg:
        result["quote_bg"] = bq_bg
    else:
        primary_l = lightness(result["primary"])
        result["quote_bg"] = adjust_lightness(result["primary"], min(primary_l + 0.35, 0.95))
    for tag in ("pre", "code"):
        tag_styles = grouped.get(tag, [])
        bg = most_common_value(tag_styles, "background-color") or most_common_value(tag_styles, "background")
        if bg:
            result["code_bg"] = rgb_to_hex(bg)
        color = most_common_value(tag_styles, "color")
        if color:
            result["code_color"] = rgb_to_hex(color)
    all_radii = []
    for tag_styles in grouped.values():
        for d in tag_styles:
            br = d.get("border-radius")
            if br:
                all_radii.append(br)
    if all_radii:
        result["border_radius"] = Counter(all_radii).most_common(1)[0][0]
    return result


def _load_template_css() -> str:
    template_path = THEMES_DIR / f"{TEMPLATE_THEME}.yaml"
    with open(template_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["base_css"]


def generate_theme_yaml(name: str, title: str, analyzed: dict) -> str:
    css = _load_template_css()
    colors = {"primary": analyzed.get("primary", "#2563eb"), "secondary": analyzed.get("secondary", "#3b82f6"), "text": analyzed.get("text", "#333333"), "text_light": analyzed.get("text_light", "#666666"), "background": analyzed.get("background", "#ffffff"), "code_bg": analyzed.get("code_bg", "#1e293b"), "code_color": analyzed.get("code_color", "#e2e8f0"), "quote_border": analyzed.get("quote_border", "#2563eb"), "quote_bg": analyzed.get("quote_bg", "#eff6ff"), "border_radius": analyzed.get("border_radius", "8px")}
    css = css.replace("#2563eb", colors["primary"])
    css = css.replace("#3b82f6", colors["secondary"])
    css = css.replace("#333333", colors["text"])
    css = css.replace("#666666", colors["text_light"])
    css = css.replace("#1e293b", colors["code_bg"])
    css = css.replace("#e2e8f0", colors["code_color"])
    css = css.replace("#eff6ff", colors["quote_bg"])
    font_size = analyzed.get("font_size", "16px")
    line_height = analyzed.get("line_height", "1.8")
    font_family = analyzed.get("font_family", '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif')
    p_margin = analyzed.get("p_margin", "12px 0")
    border_radius = colors["border_radius"]
    css = re.sub(r"(body\s*\{[^}]*font-size:\s*)[\d.]+px", lambda m: m.group(1) + font_size, css, flags=re.DOTALL)
    css = re.sub(r"(body\s*\{[^}]*line-height:\s*)[\d.]+", lambda m: m.group(1) + line_height, css, flags=re.DOTALL)
    css = re.sub(r'(body\s*\{[^}]*font-family:\s*)[^;]+;', lambda m: m.group(1) + font_family + ";", css, flags=re.DOTALL)
    css = re.sub(r"(p\s*\{[^}]*line-height:\s*)[\d.]+", lambda m: m.group(1) + line_height, css, flags=re.DOTALL)
    css = re.sub(r"(p\s*\{[^}]*margin:\s*)[^;]+;", lambda m: m.group(1) + p_margin + ";", css, flags=re.DOTALL)
    css = re.sub(r"(li\s*\{[^}]*line-height:\s*)[\d.]+", lambda m: m.group(1) + line_height, css, flags=re.DOTALL)
    css = css.replace("border-radius: 8px", f"border-radius: {border_radius}")
    css = css.replace("border-radius: 4px", f"border-radius: {border_radius}")
    darkmode = derive_darkmode(colors)
    description = f"\u4ece\u300c{title}\u300d\u5b66\u4e60\u7684\u6392\u7248\u4e3b\u9898" if title else f"Learned theme: {name}"
    colors_with_dark = dict(colors)
    colors_with_dark["darkmode"] = darkmode
    theme_data = {"name": name, "description": description, "colors": colors_with_dark, "base_css": css}
    return yaml.dump(theme_data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Learn a WeChat formatting theme from an article URL.")
    parser.add_argument("url", help="WeChat article URL (https://mp.weixin.qq.com/s/...)")
    parser.add_argument("--name", required=True, help="Theme name (used as filename and reference)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: toolkit/themes/)")
    args = parser.parse_args()
    if not re.match(r"^[a-zA-Z0-9_-]+$", args.name):
        print("Error: --name must contain only letters, digits, hyphens, and underscores.", file=sys.stderr)
        raise SystemExit(1)
    output_dir = Path(args.output_dir) if args.output_dir else THEMES_DIR
    output_path = output_dir / f"{args.name}.yaml"
    if output_path.exists():
        print(f"Warning: {output_path} already exists, will be overwritten.", file=sys.stderr)
    print("Fetching article...")
    content = fetch_article(args.url)
    title = getattr(content, "_wewrite_title", "")
    if title:
        print(f"Title: {title}")
    grouped = extract_styles(content)
    styled_count = sum(len(v) for v in grouped.values())
    print(f"Extracted {styled_count} styled elements.")
    analyzed = analyze_styles(grouped)
    theme_yaml = generate_theme_yaml(args.name, title, analyzed)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(theme_yaml, encoding="utf-8")
    print()
    print(f"Learned theme from: {title or args.url}")
    print(f"  text:       {analyzed['text']}")
    print(f"  text_light: {analyzed['text_light']}")
    print(f"  primary:    {analyzed['primary']}")
    print(f"  secondary:  {analyzed['secondary']}")
    print(f"  background: {analyzed['background']}")
    print(f"  font:       {analyzed['font_family'][:50]}")
    print(f"  size:       {analyzed['font_size']} / line-height {analyzed['line_height']} / spacing {analyzed['letter_spacing']}")
    print()
    print(f"Theme saved \u2192 {output_path}")
    print(f"Use it:  python3 toolkit/cli.py preview article.md --theme {args.name}")
    print(f"Or set:  theme: {args.name}  in style.yaml")


if __name__ == "__main__":
    main()
