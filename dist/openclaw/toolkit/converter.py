import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import markdown
from bs4 import BeautifulSoup

from theme import Theme, load_theme, get_inline_css_rules


@dataclass
class ConvertResult:
    html: str
    title: str
    digest: str
    images: list[str] = field(default_factory=list)


class WeChatConverter:
    def __init__(self, theme: Optional[Theme] = None, theme_name: str = "professional-clean"):
        if theme is not None:
            self._theme = theme
        else:
            self._theme = load_theme(theme_name)
        self._css_rules = get_inline_css_rules(self._theme)

    def convert(self, markdown_text: str) -> ConvertResult:
        title = self._extract_title(markdown_text)
        markdown_text = self._strip_h1(markdown_text)

        markdown_text = self._preprocess_containers(markdown_text)
        markdown_text = self._fix_cjk_spacing(markdown_text)

        html = self._markdown_to_html(markdown_text)
        html = self._enhance_code_blocks(html)
        html, images = self._process_images(html)
        html = self._fix_cjk_bold_punctuation(html)
        html = self._convert_lists_to_sections(html)
        html = self._convert_links_to_footnotes(html)
        html = self._apply_inline_styles(html)
        html = self._apply_wechat_fixes(html)
        html = self._inject_darkmode(html)

        if self._theme.colors.get("css_randomize") or getattr(self._theme, '_raw_data', {}).get('css_randomize'):
            html = self._randomize_css(html)

        if self._theme.colors.get("aigc_footer") or getattr(self._theme, '_raw_data', {}).get('aigc_footer'):
            html = self._append_aigc_footer(html)

        digest = self._generate_digest(html)
        return ConvertResult(html=html, title=title, digest=digest, images=images)

    def convert_file(self, input_path: str) -> ConvertResult:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        text = path.read_text(encoding="utf-8")
        return self.convert(text)

    def _extract_title(self, text: str) -> str:
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return ""

    def _strip_h1(self, text: str) -> str:
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _markdown_to_html(self, text: str) -> str:
        extensions = [
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.sane_lists",
            "markdown.extensions.codehilite",
        ]
        extension_configs = {
            "codehilite": {
                "linenums": False,
                "guess_lang": True,
                "noclasses": True,
            }
        }
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        return md.convert(text)

    def _enhance_code_blocks(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if code:
                for cls in code.get("class", []):
                    if cls.startswith("language-"):
                        pre["data-lang"] = cls.replace("language-", "")
                        break
        return str(soup)

    def _process_images(self, html: str) -> tuple[str, list[str]]:
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                images.append(src)
            existing = img.get("style", "")
            if "max-width" not in existing:
                additions = "max-width: 100%; height: auto; display: block; margin: 24px auto"
                img["style"] = f"{existing}; {additions}" if existing else additions
        return str(soup), images

    def _apply_inline_styles(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for selector, styles in self._css_rules.items():
            if selector.strip() == "body":
                continue
            try:
                elements = soup.select(selector)
            except Exception:
                continue
            for elem in elements:
                existing = elem.get("style", "")
                style_dict = {}
                if existing:
                    for item in existing.split(";"):
                        if ":" in item:
                            key, val = item.split(":", 1)
                            style_dict[key.strip()] = val.strip()
                for prop, val in styles.items():
                    if prop not in style_dict:
                        style_dict[prop] = val
                elem["style"] = "; ".join(f"{k}: {v}" for k, v in style_dict.items())
        return str(soup)

    def _apply_wechat_fixes(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")
        for p in soup.find_all("p"):
            style = p.get("style", "")
            if "color" not in style:
                p["style"] = f"{style}; color: {text_color}" if style else f"color: {text_color}"
        for pre in soup.find_all("pre"):
            style = pre.get("style", "")
            if "white-space" not in style:
                pre["style"] = f"{style}; white-space: pre-wrap; word-wrap: break-word" if style else "white-space: pre-wrap; word-wrap: break-word"
        return str(soup)

    def _fix_cjk_spacing(self, text: str) -> str:
        cjk = r'[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef]'
        latin = r'[A-Za-z0-9]'
        lines = text.split('\n')
        result = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                result.append(line)
                continue
            if in_code_block:
                result.append(line)
                continue
            line = re.sub(f'({cjk})({latin})', r'\1 \2', line)
            line = re.sub(f'({latin})({cjk})', r'\1 \2', line)
            result.append(line)
        return '\n'.join(result)

    def _fix_cjk_bold_punctuation(self, html: str) -> str:
        pattern = r'(<strong>)(.*?)([\u3001\u3002\uff0c\uff01\uff1f\uff1b\uff1a\u3001]+)(</strong>)'
        return re.sub(pattern, r'\1\2\4\3', html)

    def _convert_lists_to_sections(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")
        primary = self._theme.colors.get("primary", "#2563eb")
        for ul in soup.find_all("ul"):
            section = soup.new_tag("section")
            for li in ul.find_all("li", recursive=False):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                bullet = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-size: 18px; line-height: 1.6")
                bullet.string = "\u2022"
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(bullet)
                item.append(content)
                section.append(item)
            ul.replace_with(section)
        for idx, ol in enumerate(soup.find_all("ol")):
            section = soup.new_tag("section")
            for num, li in enumerate(ol.find_all("li", recursive=False), 1):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                number = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-weight: 700; line-height: 1.8")
                number.string = f"{num}."
                content = soup.new_tag("span", style="flex: 1")
                for child in list(li.children):
                    content.append(child.extract() if hasattr(child, 'extract') else child)
                item.append(number)
                item.append(content)
                section.append(item)
            ol.replace_with(section)
        return str(soup)

    def _convert_links_to_footnotes(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        footnotes = []
        counter = 0
        primary = self._theme.colors.get("primary", "#2563eb")
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            counter += 1
            text = a.get_text()
            footnotes.append((counter, text, href))
            sup = soup.new_tag("sup")
            sup_link = soup.new_tag("span", style=f"color: {primary}; font-size: 12px")
            sup_link.string = f"[{counter}]"
            sup.append(sup_link)
            a.replace_with(text, sup)
        if footnotes:
            hr = soup.new_tag("hr", style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0 16px")
            soup.append(hr)
            ref_title = soup.new_tag("p", style="font-size: 13px; color: #999999; margin-bottom: 8px; font-weight: 700")
            ref_title.string = "\u53c2\u8003\u94fe\u63a5"
            soup.append(ref_title)
            for num, text, href in footnotes:
                ref = soup.new_tag("p", style="font-size: 12px; color: #999999; margin: 2px 0; word-break: break-all")
                ref.string = f"[{num}] {text}: {href}"
                soup.append(ref)
        return str(soup)

    def _inject_darkmode(self, html: str) -> str:
        darkmode = self._theme.colors.get("darkmode") or getattr(self._theme, "_raw_data", {}).get("darkmode", {})
        if not darkmode:
            return html
        soup = BeautifulSoup(html, "html.parser")
        dm_text = darkmode.get("text", "#c8c8c8")
        dm_bg = darkmode.get("background", "#1e1e1e")
        dm_primary = darkmode.get("primary", "#6aadff")
        for tag_name in ("p", "span", "section"):
            for elem in soup.find_all(tag_name):
                style = elem.get("style", "")
                if "color" in style:
                    elem["data-darkmode-color"] = dm_text
                    elem["data-darkmode-bgcolor"] = "transparent"
        dm_heading = darkmode.get("text", "#e0e0e0")
        for tag_name in ("h1", "h2", "h3", "h4"):
            for elem in soup.find_all(tag_name):
                elem["data-darkmode-color"] = dm_heading
                elem["data-darkmode-bgcolor"] = "transparent"
        dm_code_bg = darkmode.get("code_bg", "#2d2d2d")
        dm_code_color = darkmode.get("code_color", "#d4d4d4")
        for pre in soup.find_all("pre"):
            pre["data-darkmode-bgcolor"] = dm_code_bg
            pre["data-darkmode-color"] = dm_code_color
        for code in soup.find_all("code"):
            code["data-darkmode-color"] = dm_code_color
        dm_quote_bg = darkmode.get("quote_bg", "#2a2a2a")
        for bq in soup.find_all("blockquote"):
            bq["data-darkmode-bgcolor"] = dm_quote_bg
            bq["data-darkmode-color"] = dm_text
        for strong in soup.find_all("strong"):
            strong["data-darkmode-color"] = dm_primary
        return str(soup)

    def _preprocess_containers(self, text: str) -> str:
        text = self._process_dialogue(text)
        text = self._process_timeline(text)
        text = self._process_callout(text)
        text = self._process_quote_block(text)
        text = self._process_highlight(text)
        text = self._process_summary(text)
        return text

    def _process_dialogue(self, text: str) -> str:
        primary = self._theme.colors.get("primary", "#2563eb")
        def replace_dialogue(match):
            content = match.group(1).strip()
            bubbles = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('> '):
                    msg = line[2:].strip()
                    bubbles.append(f'<section style="display: flex; justify-content: flex-end; margin-bottom: 12px">'
                                   f'<section style="background: {primary}; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; max-width: 80%; font-size: 15px; line-height: 1.6">{msg}</section></section>')
                else:
                    bubbles.append(f'<section style="display: flex; justify-content: flex-start; margin-bottom: 12px">'
                                   f'<section style="background: #f3f4f6; color: #333; padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 80%; font-size: 15px; line-height: 1.6">{line}</section></section>')
            return '\n'.join(bubbles)
        return re.sub(r':::dialogue\n(.*?)\n:::', replace_dialogue, text, flags=re.DOTALL)

    def _process_timeline(self, text: str) -> str:
        primary = self._theme.colors.get("primary", "#2563eb")
        def replace_timeline(match):
            content = match.group(1).strip()
            items = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                items.append(
                    f'<section style="display: flex; margin-bottom: 16px">'
                    f'<section style="flex-shrink: 0; width: 12px; display: flex; flex-direction: column; align-items: center">'
                    f'<section style="width: 10px; height: 10px; border-radius: 50%; background: {primary}; margin-top: 6px"></section>'
                    f'<section style="width: 2px; flex: 1; background: #e5e7eb; margin-top: 4px"></section>'
                    f'</section>'
                    f'<section style="flex: 1; padding-left: 12px; padding-bottom: 8px; font-size: 15px; line-height: 1.7">{line}</section>'
                    f'</section>'
                )
            return '\n'.join(items)
        return re.sub(r':::timeline\n(.*?)\n:::', replace_timeline, text, flags=re.DOTALL)

    def _process_callout(self, text: str) -> str:
        colors_map = {
            "tip": ("#059669", "#ecfdf5", "\U0001f4a1"),
            "warning": ("#d97706", "#fffbeb", "\u26a0\ufe0f"),
            "info": ("#2563eb", "#eff6ff", "\u2139\ufe0f"),
            "danger": ("#dc2626", "#fef2f2", "\U0001f6a8"),
        }
        def replace_callout(match):
            ctype = match.group(1).strip().lower()
            content_raw = match.group(2).strip()
            if ctype in colors_map:
                color, bg, icon = colors_map[ctype]
                header = f'<section style="font-weight: 700; color: {color}; margin-bottom: 6px">{icon} {ctype.upper()}</section>'
            else:
                color = "#2563eb"
                bg = "#eff6ff"
                header = f'<section style="font-weight: 700; color: {color}; margin-bottom: 6px">{match.group(1).strip()}</section>'
            content_html = markdown.markdown(content_raw, extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.tables",
                "markdown.extensions.nl2br",
                "markdown.extensions.sane_lists",
            ])
            return (f'<section style="background: {bg}; border-left: 4px solid {color}; '
                    f'padding: 14px 16px; border-radius: 4px; margin: 16px 0; font-size: 15px; line-height: 1.7">'
                    f'{header}{content_html}</section>')
        return re.sub(r':::callout\s+([^\n]+)\n(.*?)\n:::', replace_callout, text, flags=re.DOTALL)

    def _process_quote_block(self, text: str) -> str:
        primary = self._theme.colors.get("primary", "#2563eb")
        def replace_quote(match):
            content_raw = match.group(1).strip()
            content_html = markdown.markdown(content_raw, extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.nl2br",
            ])
            return (f'<section style="margin: 24px 0; padding: 20px 24px; border-left: 4px solid {primary}; '
                    f'background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-radius: 0 8px 8px 0">'
                    f'<section style="font-size: 18px; line-height: 1.8; color: #333; font-style: italic">'
                    f'{content_html}</section></section>')
        return re.sub(r':::quote\n(.*?)\n:::', replace_quote, text, flags=re.DOTALL)

    def _append_aigc_footer(self, html: str) -> str:
        footer = ('<p style="text-align: center; font-size: 13px; color: #9ca3af; '
                  'margin-top: 48px; padding-top: 24px; border-top: 1px solid #e5e7eb;">'
                  '\u672c\u6587\u7531 AI \u8f85\u52a9\u521b\u4f5c\uff0c\u4f5c\u8005\u8fdb\u884c\u4e86\u5b9e\u6d4b\u9a8c\u8bc1\u548c\u7f16\u8f91\u4fee\u6539\u3002</p>')
        return html + '\n' + footer

    def _randomize_css(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        font_size_delta = random.choice([0, -1])
        line_height_delta = random.uniform(-0.1, 0.05)
        letter_spacing_delta = random.uniform(-0.1, 0.2)
        margin_delta = random.randint(-4, 4)
        for p in soup.find_all("p"):
            style = p.get("style", "")
            if not style:
                continue
            style = re.sub(
                r'margin:\s*0\s+0\s+(\d+)px\s+0',
                lambda m: f'margin: 0 0 {int(m.group(1)) + random.randint(-3, 3)}px 0',
                style
            )
            style = re.sub(
                r'font-size:\s*17px',
                f'font-size: {17 + font_size_delta}px',
                style
            )
            style = re.sub(
                r'line-height:\s*1\.9',
                f'line-height: {1.9 + line_height_delta:.2f}',
                style
            )
            p["style"] = style
        for h2 in soup.find_all("h2"):
            style = h2.get("style", "")
            style = re.sub(
                r'margin:\s*(\d+)px',
                lambda m: f'margin: {int(m.group(1)) + random.randint(-3, 3)}px',
                style
            )
            style = re.sub(
                r'font-size:\s*22px',
                f'font-size: {22 + random.choice([-1, 0, 1])}px',
                style
            )
            h2["style"] = style
        for section in soup.find_all("section", recursive=False):
            style = section.get("style", "")
            if "letter-spacing" in style:
                style = re.sub(
                    r'letter-spacing:\s*[\d.]+px',
                    f'letter-spacing: {0.3 + letter_spacing_delta:.1f}px',
                    style
                )
                section["style"] = style
        return str(soup)

    def _process_highlight(self, text: str) -> str:
        secondary = self._theme.colors.get("secondary", "#c4820e")
        highlight_bg = self._theme.colors.get("highlight_bg", "#fef7e8")
        highlight_border = self._theme.colors.get("highlight_border", "rgba(196,130,14,0.2)")
        def replace_highlight(match):
            content = match.group(1).strip()
            lines = content.split('\n', 1)
            title_raw = lines[0].strip() if lines else ""
            body_raw = lines[1].strip() if len(lines) > 1 else ""
            title_html = markdown.markdown(title_raw, extensions=[
                "markdown.extensions.nl2br",
            ]).strip() if title_raw else ""
            title_html = re.sub(r'^<p>(.*)</p>\n?$', r'\1', title_html) if title_html else ""
            body_html = markdown.markdown(body_raw, extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.nl2br",
            ]) if body_raw else ""
            html = (f'<section style="margin: 24px 0; padding: 20px 24px; background: {highlight_bg}; '
                    f'border: 1px solid {highlight_border}; border-radius: 6px;">')
            if title_html:
                html += f'<p style="margin: 0;"><strong style="color: {secondary};">{title_html}</strong></p>'
            if body_html:
                html += body_html
            html += '</section>'
            return html
        return re.sub(r':::highlight\n(.*?)\n:::', replace_highlight, text, flags=re.DOTALL)

    def _process_summary(self, text: str) -> str:
        primary = self._theme.colors.get("primary", "#1a6b5a")
        summary_bg = self._theme.colors.get("summary_bg", "#e8f5f0")
        summary_border = self._theme.colors.get("summary_border", "rgba(26,107,90,0.15)")
        def replace_summary(match):
            content = match.group(1).strip()
            lines = content.split('\n', 1)
            title_raw = lines[0].strip() if lines else "\u603b\u7ed3"
            body_raw = lines[1].strip() if len(lines) > 1 else ""
            title_html = markdown.markdown(title_raw, extensions=[
                "markdown.extensions.nl2br",
            ]).strip() if title_raw else "\u603b\u7ed3"
            title_html = re.sub(r'^<p>(.*)</p>\n?$', r'\1', title_html)
            body_html = markdown.markdown(body_raw, extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.nl2br",
            ]) if body_raw else ""
            html = (f'<section style="margin: 24px 0; padding: 20px 24px; background: {summary_bg}; '
                    f'border: 1px solid {summary_border}; border-radius: 6px;">')
            html += f'<p style="margin: 0;"><strong style="color: {primary};">{title_html}</strong></p>'
            if body_html:
                html += body_html
            html += '</section>'
            return html
        return re.sub(r':::summary\n(.*?)\n:::', replace_summary, text, flags=re.DOTALL)

    def _generate_digest(self, html: str, max_bytes: int = 120) -> str:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        ellipsis = "..."
        ellipsis_bytes = len(ellipsis.encode("utf-8"))
        target_bytes = max_bytes - ellipsis_bytes
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        truncated = encoded[:target_bytes].decode("utf-8", errors="ignore").rstrip()
        return truncated + ellipsis


def preview_html(body_html: str, theme: Theme) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview</title>
    <style>
{theme.base_css}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
