"""
Markdown to WeChat-compatible HTML converter.

Forked from wechat_article_skills/scripts/markdown_to_html.py,
adapted for YAML-driven themes and agent integration.
"""

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
    """Result of a Markdown → WeChat HTML conversion."""

    html: str  # WeChat-compatible inline-style HTML (body content only)
    title: str  # Extracted H1 title
    digest: str  # Auto-generated summary (first 120 chars)
    images: list[str] = field(default_factory=list)  # Image references found


class WeChatConverter:
    """Convert Markdown to WeChat-compatible inline-style HTML."""

    def __init__(self, theme: Optional[Theme] = None, theme_name: str = "professional-clean"):
        if theme is not None:
            self._theme = theme
        else:
            self._theme = load_theme(theme_name)
        self._css_rules = get_inline_css_rules(self._theme)

    def convert(self, markdown_text: str) -> ConvertResult:
        """
        Convert Markdown text to WeChat-compatible HTML.

        Returns ConvertResult with:
          - html: inline-style HTML (body content only, no <html>/<head> wrapper)
          - title: extracted H1 title (or empty string)
          - digest: first 120 characters of plain text
          - images: list of image src references
        """
        title = self._extract_title(markdown_text)
        markdown_text = self._strip_h1(markdown_text)

        # Pre-process container blocks (:::dialogue, :::timeline, etc.)
        markdown_text = self._preprocess_containers(markdown_text)

        # CJK fix: auto-space between CJK and Latin characters
        markdown_text = self._fix_cjk_spacing(markdown_text)

        # Parse Markdown → HTML
        html = self._markdown_to_html(markdown_text)

        # Enhance code blocks (add data-lang attribute)
        html = self._enhance_code_blocks(html)

        # Process images (ensure responsive styling)
        html, images = self._process_images(html)

        # CJK fix: move punctuation outside bold tags
        html = self._fix_cjk_bold_punctuation(html)

        # CJK fix: convert ul/ol to section-based lists (WeChat renders native lists unreliably)
        html = self._convert_lists_to_sections(html)

        # Convert external links to footnotes (WeChat blocks external links)
        html = self._convert_links_to_footnotes(html)

        # Apply inline CSS from theme
        html = self._apply_inline_styles(html)

        # Apply WeChat compatibility fixes
        html = self._apply_wechat_fixes(html)

        # Inject dark mode attributes
        html = self._inject_darkmode(html)

        # Apply CSS randomization if enabled (anti-fingerprint for WeChat low-creativity detection)
        if self._theme.colors.get("css_randomize") or getattr(self._theme, '_raw_data', {}).get('css_randomize'):
            html = self._randomize_css(html)

        # Append AIGC declaration if theme enables it
        if self._theme.colors.get("aigc_footer") or getattr(self._theme, '_raw_data', {}).get('aigc_footer'):
            html = self._append_aigc_footer(html)

        # Generate digest from plain text
        digest = self._generate_digest(html)

        return ConvertResult(html=html, title=title, digest=digest, images=images)

    def convert_file(self, input_path: str) -> ConvertResult:
        """Convert a Markdown file."""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        text = path.read_text(encoding="utf-8")
        return self.convert(text)

    # -- internal methods --

    def _extract_title(self, text: str) -> str:
        """Extract the first H1 title from Markdown text."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                return stripped[2:].strip()
        return ""

    def _strip_h1(self, text: str) -> str:
        """Remove H1 lines — WeChat has a separate title field."""
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# ") and not stripped.startswith("## "):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _markdown_to_html(self, text: str) -> str:
        """Parse Markdown to HTML using python-markdown with extensions."""
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
                "noclasses": True,  # Inline syntax highlight styles
            }
        }
        md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
        return md.convert(text)

    def _enhance_code_blocks(self, html: str) -> str:
        """Add data-lang attribute to <pre> elements for language labeling."""
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
        """Extract image references and ensure responsive styling."""
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                images.append(src)
            # Ensure responsive image styles
            existing = img.get("style", "")
            if "max-width" not in existing:
                additions = "max-width: 100%; height: auto; display: block; margin: 24px auto"
                img["style"] = f"{existing}; {additions}" if existing else additions
        return str(soup), images

    def _apply_inline_styles(self, html: str) -> str:
        """Apply theme CSS rules as inline styles on matching elements."""
        soup = BeautifulSoup(html, "html.parser")

        for selector, styles in self._css_rules.items():
            # Skip body — we don't wrap in body tag
            if selector.strip() == "body":
                continue

            try:
                elements = soup.select(selector)
            except Exception:
                continue

            for elem in elements:
                existing = elem.get("style", "")
                style_dict = {}

                # Parse existing inline styles
                if existing:
                    for item in existing.split(";"):
                        if ":" in item:
                            key, val = item.split(":", 1)
                            style_dict[key.strip()] = val.strip()

                # Add theme styles (existing styles take precedence)
                for prop, val in styles.items():
                    if prop not in style_dict:
                        style_dict[prop] = val

                elem["style"] = "; ".join(f"{k}: {v}" for k, v in style_dict.items())

        return str(soup)

    def _apply_wechat_fixes(self, html: str) -> str:
        """
        Apply WeChat-specific compatibility fixes:
        1. Force explicit color on every <p> tag
        2. Ensure code blocks preserve whitespace
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")

        # Fix 1: Ensure all <p> tags have explicit color
        for p in soup.find_all("p"):
            style = p.get("style", "")
            if "color" not in style:
                p["style"] = f"{style}; color: {text_color}" if style else f"color: {text_color}"

        # Fix 2: Ensure <pre> has whitespace preservation
        for pre in soup.find_all("pre"):
            style = pre.get("style", "")
            if "white-space" not in style:
                pre["style"] = f"{style}; white-space: pre-wrap; word-wrap: break-word" if style else "white-space: pre-wrap; word-wrap: break-word"

        return str(soup)

    # -- CJK compatibility fixes --

    def _fix_cjk_spacing(self, text: str) -> str:
        """Auto-insert thin space between CJK and Latin/digit characters.

        WeChat renders CJK-Latin without spacing, making mixed text hard to read.
        This inserts a thin space (U+200A) at CJK↔Latin boundaries.
        Runs on raw Markdown before parsing, skipping code blocks and links.
        """
        # CJK unicode ranges
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

            # CJK followed by Latin
            line = re.sub(f'({cjk})({latin})', r'\1 \2', line)
            # Latin followed by CJK
            line = re.sub(f'({latin})({cjk})', r'\1 \2', line)
            result.append(line)

        return '\n'.join(result)

    def _fix_cjk_bold_punctuation(self, html: str) -> str:
        """Move Chinese punctuation outside bold/strong tags.

        WeChat renders bold CJK punctuation with ugly spacing.
        Move trailing punctuation (，。！？；：、） outside </strong>.
        """
        # Match: <strong>内容+中文标点</strong> → <strong>内容</strong>标点
        pattern = r'(<strong>)(.*?)([，。！？；：、]+)(</strong>)'
        return re.sub(pattern, r'\1\2\4\3', html)

    def _convert_lists_to_sections(self, html: str) -> str:
        """Convert <ul>/<ol> to styled <section> elements.

        WeChat's native list rendering is unreliable (inconsistent bullet
        style, broken indentation on some devices). Using section+span
        for bullets/numbers gives full control over appearance.
        """
        soup = BeautifulSoup(html, "html.parser")
        text_color = self._theme.colors.get("text", "#333333")
        primary = self._theme.colors.get("primary", "#2563eb")

        for ul in soup.find_all("ul"):
            section = soup.new_tag("section")
            for li in ul.find_all("li", recursive=False):
                item = soup.new_tag("section", style=f"display: flex; align-items: flex-start; margin-bottom: 8px; color: {text_color}")
                bullet = soup.new_tag("span", style=f"color: {primary}; margin-right: 8px; flex-shrink: 0; font-size: 18px; line-height: 1.6")
                bullet.string = "•"
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

    # -- External link → footnote conversion --

    def _convert_links_to_footnotes(self, html: str) -> str:
        """Convert external <a> links to superscript footnote numbers.

        WeChat blocks external links — readers see dead text. This converts
        each external link to a superscript number with the URL collected
        into a reference list appended at the end.
        """
        soup = BeautifulSoup(html, "html.parser")
        footnotes = []
        counter = 0
        primary = self._theme.colors.get("primary", "#2563eb")

        for a in soup.find_all("a"):
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue  # skip anchors

            counter += 1
            text = a.get_text()
            footnotes.append((counter, text, href))

            # Replace <a> with text + superscript number
            sup = soup.new_tag("sup")
            sup_link = soup.new_tag("span", style=f"color: {primary}; font-size: 12px")
            sup_link.string = f"[{counter}]"
            sup.append(sup_link)
            a.replace_with(text, sup)

        if footnotes:
            # Append reference section
            hr = soup.new_tag("hr", style="border: none; border-top: 1px solid #e5e5e5; margin: 32px 0 16px")
            soup.append(hr)
            ref_title = soup.new_tag("p", style="font-size: 13px; color: #999999; margin-bottom: 8px; font-weight: 700")
            ref_title.string = "参考链接"
            soup.append(ref_title)
            for num, text, href in footnotes:
                ref = soup.new_tag("p", style="font-size: 12px; color: #999999; margin: 2px 0; word-break: break-all")
                ref.string = f"[{num}] {text}: {href}"
                soup.append(ref)

        return str(soup)

    # -- Dark mode --

    def _inject_darkmode(self, html: str) -> str:
        """Inject data-darkmode-* attributes for WeChat dark mode.

        WeChat auto-inverts colors in dark mode, which often breaks
        designed color schemes. Explicit darkmode attributes tell WeChat
        exactly what colors to use instead of guessing.
        """
        darkmode = self._theme.colors.get("darkmode", {})
        if not darkmode:
            return html

        soup = BeautifulSoup(html, "html.parser")
        dm_text = darkmode.get("text", "#c8c8c8")
        dm_bg = darkmode.get("background", "#1e1e1e")
        dm_primary = darkmode.get("primary", "#6aadff")

        # Body-level elements (p, li, section, span)
        for tag_name in ("p", "span", "section"):
            for elem in soup.find_all(tag_name):
                style = elem.get("style", "")
                # Only set if element has a color
                if "color" in style:
                    elem["data-darkmode-color"] = dm_text
                    elem["data-darkmode-bgcolor"] = "transparent"

        # Headings
        dm_heading = darkmode.get("text", "#e0e0e0")
        for tag_name in ("h1", "h2", "h3", "h4"):
            for elem in soup.find_all(tag_name):
                elem["data-darkmode-color"] = dm_heading
                elem["data-darkmode-bgcolor"] = "transparent"

        # Code blocks
        dm_code_bg = darkmode.get("code_bg", "#2d2d2d")
        dm_code_color = darkmode.get("code_color", "#d4d4d4")
        for pre in soup.find_all("pre"):
            pre["data-darkmode-bgcolor"] = dm_code_bg
            pre["data-darkmode-color"] = dm_code_color
        for code in soup.find_all("code"):
            code["data-darkmode-color"] = dm_code_color

        # Blockquotes
        dm_quote_bg = darkmode.get("quote_bg", "#2a2a2a")
        for bq in soup.find_all("blockquote"):
            bq["data-darkmode-bgcolor"] = dm_quote_bg
            bq["data-darkmode-color"] = dm_text

        # Strong/em with primary color
        for strong in soup.find_all("strong"):
            strong["data-darkmode-color"] = dm_primary

        return str(soup)

    # -- Container block syntax --

    def _preprocess_containers(self, text: str) -> str:
        """Pre-process :::container blocks into styled HTML before Markdown parsing.

        Supports:
          :::dialogue   — chat bubble layout
          :::timeline   — vertical timeline with dots
          :::callout    — Obsidian-style callout (tip/warning/info/danger)
          :::quote      — styled pull quote
        """
        text = self._process_dialogue(text)
        text = self._process_timeline(text)
        text = self._process_callout(text)
        text = self._process_quote_block(text)
        text = self._process_highlight(text)
        text = self._process_summary(text)
        return text

    def _process_dialogue(self, text: str) -> str:
        """Convert :::dialogue blocks to chat bubble HTML."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_dialogue(match):
            content = match.group(1).strip()
            bubbles = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('> '):
                    # Right-aligned (reply) bubble
                    msg = line[2:].strip()
                    bubbles.append(f'<section style="display: flex; justify-content: flex-end; margin-bottom: 12px">'
                                   f'<section style="background: {primary}; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; max-width: 80%; font-size: 15px; line-height: 1.6">{msg}</section></section>')
                else:
                    # Left-aligned bubble
                    bubbles.append(f'<section style="display: flex; justify-content: flex-start; margin-bottom: 12px">'
                                   f'<section style="background: #f3f4f6; color: #333; padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 80%; font-size: 15px; line-height: 1.6">{line}</section></section>')
            return '\n'.join(bubbles)

        return re.sub(r':::dialogue\n(.*?)\n:::', replace_dialogue, text, flags=re.DOTALL)

    def _process_timeline(self, text: str) -> str:
        """Convert :::timeline blocks to vertical timeline HTML."""
        primary = self._theme.colors.get("primary", "#2563eb")

        def replace_timeline(match):
            content = match.group(1).strip()
            items = []
            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Format: "**title** description" or just "description"
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
        """Convert :::callout blocks to styled callout boxes.

        Syntax: :::callout tip/warning/info/danger
        Content markdown is converted to HTML before embedding.
        """
        colors_map = {
            "tip": ("#059669", "#ecfdf5","h4\"):\n            for elem in soup.find_all(tag_name):\n                elem[\"data-darkmode-color\"] = dm_heading\n                elem[\"data-darkmode-bgcolor\"] = \"transparent\"\n\n        # Code blocks\n        dm_code_bg = darkmode.get(\"code_bg\", \"#2d2d2d\")\n        dm_code_color = darkmode.get(\"code_color\", \"#d4d4d4\")\n        for pre in soup.find_all(\"pre\"):\n            pre[\"data-darkmode-bgcolor\"] = dm_code_bg\n            pre[\"data-darkmode-color\"] = dm_code_color\n        for code in soup.find_all(\"code\"):\n            code[\"data-darkmode-color\"] = dm_code_color\n\n        # Blockquotes\n        dm_quote_bg = darkmode.get(\"quote_bg\", \"#2a2a2a\")\n        for bq in soup.find_all(\"blockquote\"):\n            bq[\"data-darkmode-bgcolor\"] = dm_quote_bg\n            bq[\"data-darkmode-color\"] = dm_text\n\n        # Strong/em with primary color\n        for strong in soup.find_all(\"strong\"):\n            strong[\"data-darkmode-color\"] = dm_primary\n\n        return str(soup)\n\n    # -- Container block syntax --\n\n    def _preprocess_containers(self, text: str) -> str:\n        \"\"\"Pre-process :::container blocks into styled HTML before Markdown parsing.\n\n        Supports:\n          :::dialogue   \u2014 chat bubble layout\n          :::timeline   \u2014 vertical timeline with dots\n          :::callout    \u2014 Obsidian-style callout (tip/warning/info/danger)\n          :::quote      \u2014 styled pull quote\n        \"\"\"\n        text = self._process_dialogue(text)\n        text = self._process_timeline(text)\n        text = self._process_callout(text)\n        text = self._process_quote_block(text)\n        text = self._process_highlight(text)\n        text = self._process_summary(text)\n        return text\n\n    def _process_dialogue(self, text: str) -> str:\n        \"\"\"Convert :::dialogue blocks to chat bubble HTML.\"\"\"\n        primary = self._theme.colors.get(\"primary\", \"#2563eb\")\n\n        def replace_dialogue(match):\n            content = match.group(1).strip()\n            bubbles = []\n            for line in content.split('\\n'):\n                line = line.strip()\n                if not line:\n                    continue\n                if line.startswith('> '):\n                    # Right-aligned (reply) bubble\n                    msg = line[2:].strip()\n                    bubbles.append(f'<section style=\"display: flex; justify-content: flex-end; margin-bottom: 12px\">'\n                                   f'<section style=\"background: {primary}; color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; max-width: 80%; font-size: 15px; line-height: 1.6\">{msg}</section></section>')\n                else:\n                    # Left-aligned bubble\n                    bubbles.append(f'<section style=\"display: flex; justify-content: flex-start; margin-bottom: 12px\">'\n                                   f'<section style=\"background: #f3f4f6; color: #333; padding: 10px 14px; border-radius: 12px 12px 12px 2px; max-width: 80%; font-size: 15px; line-height: 1.6\">{line}</section></section>')\n            return '\\n'.join(bubbles)\n\n        return re.sub(r':::dialogue\\n(.*?)\\n:::', replace_dialogue, text, flags=re.DOTALL)\n\n    def _process_timeline(self, text: str) -> str:\n        \"\"\"Convert :::timeline blocks to vertical timeline HTML.\"\"\"\n        primary = self._theme.colors.get(\"primary\", \"#2563eb\")\n\n        def replace_timeline(match):\n            content = match.group(1).strip()\n            items = []\n            for line in content.split('\\n'):\n                line = line.strip()\n                if not line:\n                    continue\n                # Format: \"**title** description\" or just \"description\"\n                items.append(\n                    f'<section style=\"display: flex; margin-bottom: 16px\">'\n                    f'<section style=\"flex-shrink: 0; width: 12px; display: flex; flex-direction: column; align-items: center\">'\n                    f'<section style=\"width: 10px; height: 10px; border-radius: 50%; background: {primary}; margin-top: 6px\"></section>'\n                    f'<section style=\"width: 2px; flex: 1; background: #e5e7eb; margin-top: 4px\"></section>'\n                    f'</section>'\n                    f'<section style=\"flex: 1; padding-left: 12px; padding-bottom: 8px; font-size: 15px; line-height: 1.7\">{line}</section>'\n                    f'</section>'\n                )\n            return '\\n'.join(items)\n\n        return re.sub(r':::timeline\\n(.*?)\\n:::', replace_timeline, text, flags=re.DOTALL)\n\n    def _process_callout(self, text: str) -> str:\n        \"\"\"Convert :::callout blocks to styled callout boxes.\n\n        Syntax: :::callout tip/warning/info/danger\n        Content markdown is converted to HTML before embedding.\n        \"\"\"\n        colors_map = {\n            \"tip\": (\"#059669\", \"#ecfdf5\", \"\U0001f4a1\"),\n            \"warning\": (\"#d97706\", \"#fffbeb\", \"\u26a0\ufe0f\"),\n            \"info\": (\"#2563eb\", \"#eff6ff\", \"\u2139\ufe0f\"),\n            \"danger\": (\"#dc2626\", \"#fef2f2\", \"\U0001f6a8\"),\n        }\n\n        def replace_callout(match):\n            ctype = match.group(1).strip().lower()\n            content_raw = match.group(2).strip()\n            if ctype in colors_map:\n                color, bg, icon = colors_map[ctype]\n                header = f'<section style=\"font-weight: 700; color: {color}; margin-bottom: 6px\">{icon} {ctype.upper()}</section>'\n            else:\n                # Custom title (e.g. Chinese text like \"\u6b63\u786e\u505a\u6cd5\")\n                color = \"#2563eb\"\n                bg = \"#eff6ff\"\n                header = f'<section style=\"font-weight: 700; color: {color}; margin-bottom: 6px\">{match.group(1).strip()}</section>'\n            # Convert content markdown to HTML\n            content_html = markdown.markdown(content_raw, extensions=[\n                \"markdown.extensions.fenced_code\",\n                \"markdown.extensions.tables\",\n                \"markdown.extensions.nl2br\",\n                \"markdown.extensions.sane_lists\",\n            ])\n            return (f'<section style=\"background: {bg}; border-left: 4px solid {color}; '\n                    f'padding: 14px 16px; border-radius: 4px; margin: 16px 0; font-size: 15px; line-height: 1.7\">'\n                    f'{header}{content_html}</section>')\n\n        return re.sub(r':::callout\\s+([^\\n]+)\\n(.*?)\\n:::', replace_callout, text, flags=re.DOTALL)\n\n    def _process_quote_block(self, text: str) -> str:\n        \"\"\"Convert :::quote blocks to styled pull quotes.\n\n        Content markdown is converted to HTML before embedding.\n        \"\"\"\n        primary = self._theme.colors.get(\"primary\", \"#2563eb\")\n\n        def replace_quote(match):\n            content_raw = match.group(1).strip()\n            content_html = markdown.markdown(content_raw, extensions=[\n                \"markdown.extensions.fenced_code\",\n                \"markdown.extensions.nl2br\",\n            ])\n            return (f'<section style=\"margin: 24px 0; padding: 20px 24px; border-left: 4px solid {primary}; '\n                    f'background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-radius: 0 8px 8px 0\">'\n                    f'<section style=\"font-size: 18px; line-height: 1.8; color: #333; font-style: italic\">'\n                    f'{content_html}</section></section>')\n\n        return re.sub(r':::quote\\n(.*?)\\n:::', replace_quote, text, flags=re.DOTALL)\n\n    # -- AIGC footer --\n\n    def _append_aigc_footer(self, html: str) -> str:\n        \"\"\"Append AIGC declaration footer as required by WeChat platform rules.\"\"\"\n        footer = ('<p style=\"text-align: center; font-size: 13px; color: #9ca3af; '\n                  'margin-top: 48px; padding-top: 24px; border-top: 1px solid #e5e7eb;\">'\n                  '\u672c\u6587\u7531 AI \u8f85\u52a9\u521b\u4f5c\uff0c\u4f5c\u8005\u8fdb\u884c\u4e86\u5b9e\u6d4b\u9a8c\u8bc1\u548c\u7f16\u8f91\u4fee\u6539\u3002</p>')\n        return html + '\\n' + footer\n\n    # -- CSS randomization (anti-fingerprint) --\n\n    def _randomize_css(self, html: str) -> str:\n        \"\"\"Apply random CSS perturbations to defeat WeChat low-creativity fingerprinting.\n\n        Slightly varies font-size, line-height, letter-spacing, margins etc.\n        so each article has a unique HTML fingerprint instead of identical templates.\n        \"\"\"\n        soup = BeautifulSoup(html, \"html.parser\")\n\n        # Randomize body-level wrapper (first section or all p tags)\n        font_size_delta = random.choice([0, -1])  # 16 or 17\n        line_height_delta = random.uniform(-0.1, 0.05)\n        letter_spacing_delta = random.uniform(-0.1, 0.2)\n        margin_delta = random.randint(-4, 4)\n\n        for p in soup.find_all(\"p\"):\n            style = p.get(\"style\", \"\")\n            if not style:\n                continue\n            # Randomize margin-bottom\n            style = re.sub(\n                r'margin:\\s*0\\s+0\\s+(\\d+)px\\s+0',\n                lambda m: f'margin: 0 0 {int(m.group(1)) + random.randint(-3, 3)}px 0',\n                style\n            )\n            # Randomize font-size if present\n            style = re.sub(\n                r'font-size:\\s*17px',\n                f'font-size: {17 + font_size_delta}px',\n                style\n            )\n            # Randomize line-height if present\n            style = re.sub(\n                r'line-height:\\s*1\\.9',\n                f'line-height: {1.9 + line_height_delta:.2f}',\n                style\n            )\n            p[\"style\"] = style\n\n        # Randomize h2 margins\n        for h2 in soup.find_all(\"h2\"):\n            style = h2.get(\"style\", \"\")\n            style = re.sub(\n                r'margin:\\s*(\\d+)px',\n                lambda m: f'margin: {int(m.group(1)) + random.randint(-3, 3)}px',\n                style\n            )\n            style = re.sub(\n                r'font-size:\\s*22px',\n                f'font-size: {22 + random.choice([-1, 0, 1])}px',\n                style\n            )\n            h2[\"style\"] = style\n\n        # Randomize letter-spacing on body-level container\n        for section in soup.find_all(\"section\", recursive=False):\n            style = section.get(\"style\", \"\")\n            if \"letter-spacing\" in style:\n                style = re.sub(\n                    r'letter-spacing:\\s*[\\d.]+px',\n                    f'letter-spacing: {0.3 + letter_spacing_delta:.1f}px',\n                    style\n                )\n                section[\"style\"] = style\n\n        return str(soup)\n\n    def _process_highlight(self, text: str) -> str:\n        \"\"\"Convert :::highlight blocks to amber highlight info boxes (Impeccable style).\n\n        Content markdown is converted to HTML before embedding.\n        \"\"\"\n        secondary = self._theme.colors.get(\"secondary\", \"#c4820e\")\n        highlight_bg = self._theme.colors.get(\"highlight_bg\", \"#fef7e8\")\n        highlight_border = self._theme.colors.get(\"highlight_border\", \"rgba(196,130,14,0.2)\")\n\n        def replace_highlight(match):\n            content = match.group(1).strip()\n            lines = content.split('\\n', 1)\n            title_raw = lines[0].strip() if lines else \"\"\n            body_raw = lines[1].strip() if len(lines) > 1 else \"\"\n            # Convert title markdown (e.g. **bold**) to HTML\n            title_html = markdown.markdown(title_raw, extensions=[\n                \"markdown.extensions.nl2br\",\n            ]).strip() if title_raw else \"\"\n            title_html = re.sub(r'^<p>(.*)</p>\\n?$', r'\\1', title_html) if title_html else \"\"\n            body_html = markdown.markdown(body_raw, extensions=[\n                \"markdown.extensions.fenced_code\",\n                \"markdown.extensions.nl2br\",\n            ]) if body_raw else \"\"\n            html = (f'<section style=\"margin: 24px 0; padding: 20px 24px; background: {highlight_bg}; '\n                    f'border: 1px solid {highlight_border}; border-radius: 6px;\">')\n            if title_html:\n                html += f'<p style=\"margin: 0;\"><strong style=\"color: {secondary};\">{title_html}</strong></p>'\n            if body_html:\n                html += body_html\n            html += '</section>'\n            return html\n\n        return re.sub(r':::highlight\\n(.*?)\\n:::', replace_highlight, text, flags=re.DOTALL)\n\n    def _process_summary(self, text: str) -> str:\n        \"\"\"Convert :::summary blocks to teal summary boxes (Impeccable style).\n\n        Content markdown is converted to HTML before embedding.\n        \"\"\"\n        primary = self._theme.colors.get(\"primary\", \"#1a6b5a\")\n        summary_bg = self._theme.colors.get(\"summary_bg\", \"#e8f5f0\")\n        summary_border = self._theme.colors.get(\"summary_border\", \"rgba(26,107,90,0.15)\")\n\n        def replace_summary(match):\n            content = match.group(1).strip()\n            lines = content.split('\\n', 1)\n            title_raw = lines[0].strip() if lines else \"\u603b\u7ed3\"\n            body_raw = lines[1].strip() if len(lines) > 1 else \"\"\n            # Convert title markdown (e.g. **bold**) to HTML\n            title_html = markdown.markdown(title_raw, extensions=[\n                \"markdown.extensions.nl2br\",\n            ]).strip() if title_raw else \"\u603b\u7ed3\"\n            title_html = re.sub(r'^<p>(.*)</p>\\n?$', r'\\1', title_html)\n            body_html = markdown.markdown(body_raw, extensions=[\n                \"markdown.extensions.fenced_code\",\n                \"markdown.extensions.nl2br\",\n            ]) if body_raw else \"\"\n            html = (f'<section style=\"margin: 24px 0; padding: 20px 24px; background: {summary_bg}; '\n                    f'border: 1px solid {summary_border}; border-radius: 6px;\">')\n            html += f'<p style=\"margin: 0;\"><strong style=\"color: {primary};\">{title_html}</strong></p>'\n            if body_html:\n                html += body_html\n            html += '</section>'\n            return html\n\n        return re.sub(r':::summary\\n(.*?)\\n:::', replace_summary, text, flags=re.DOTALL)\n\n    # -- Digest generation --\n\n    def _generate_digest(self, html: str, max_bytes: int = 120) -> str:\n        \"\"\"Generate a digest that fits within WeChat's byte limit (120 bytes UTF-8).\"\"\"\n        soup = BeautifulSoup(html, \"html.parser\")\n        text = soup.get_text(separator=\" \", strip=True)\n        text = re.sub(r\"\\s+\", \" \", text).strip()\n\n        # Truncate to fit within max_bytes (UTF-8)\n        ellipsis = \"...\"\n        ellipsis_bytes = len(ellipsis.encode(\"utf-8\"))\n        target_bytes = max_bytes - ellipsis_bytes\n\n        encoded = text.encode(\"utf-8\")\n        if len(encoded) <= max_bytes:\n            return text\n\n        # Truncate at valid UTF-8 boundary\n        truncated = encoded[:target_bytes].decode(\"utf-8\", errors=\"ignore\").rstrip()\n        return truncated + ellipsis\n\n\ndef preview_html(body_html: str, theme: Theme) -> str:\n    \"\"\"\n    Wrap body content in a full HTML document for browser preview.\n    This is only for local preview \u2014 NOT for WeChat publishing.\n    \"\"\"\n    return f\"\"\"<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Preview</title>\n    <style>\n{theme.base_css}\n    </style>\n</head>\n<body>\n    {body_html}\n</body>\n</html>\"\"\"\n"}, {"path": "toolkit/publisher.py", "content": "import json\n\nimport requests\nfrom dataclasses import dataclass\nfrom typing import Optional\n\n\n@dataclass\nclass DraftResult:\n    media_id: str\n\n\n@dataclass\nclass ImagePostResult:\n    media_id: str\n    image_count: int\n\n\ndef create_draft(\n    access_token: str,\n    title: str,\n    html: str,\n    digest: str,\n    thumb_media_id: Optional[str] = None,\n    author: Optional[str] = None,\n) -> DraftResult:\n    \"\"\"\n    Create a draft in WeChat.\n    API: POST https://api.weixin.qq.com/cgi-bin/draft/add\n    Returns DraftResult.\n    Raise ValueError on error (errcode present and != 0).\n    \"\"\"\n    article = {\n        \"title\": title,\n        \"author\": author or \"\",\n        \"digest\": digest,\n        \"content\": html,\n        \"show_cover_pic\": 0,\n    }\n\n    # thumb_media_id is required by WeChat API \u2014 if not provided,\n    # upload a default 1x1 white pixel, or skip if truly empty\n    if thumb_media_id:\n        article[\"thumb_media_id\"] = thumb_media_id\n\n    body = {\"articles\": [article]}\n\n    # MUST use ensure_ascii=False \u2014 otherwise Chinese becomes \\uXXXX\n    # and WeChat stores the escape sequences literally, causing title\n    # length overflow and garbled content.\n    resp = requests.post(\n        \"https://api.weixin.qq.com/cgi-bin/draft/add\",\n        params={\"access_token\": access_token},\n        data=json.dumps(body, ensure_ascii=False).encode(\"utf-8\"),\n        headers={\"Content-Type\": \"application/json; charset=utf-8\"},\n    )\n\n    data = resp.json()\n\n    errcode = data.get(\"errcode\", 0)\n    if errcode != 0:\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat create_draft error: errcode={errcode}, errmsg={errmsg}\")\n\n    if \"media_id\" not in data:\n        raise ValueError(f\"WeChat create_draft error: missing media_id in response: {data}\")\n\n    return DraftResult(media_id=data[\"media_id\"])\n\n\ndef get_draft(access_token: str, media_id: str) -> str:\n    \"\"\"\n    Get draft content from WeChat by media_id.\n    API: POST https://api.weixin.qq.com/cgi-bin/draft/get\n    Returns the HTML content of the first article.\n    \"\"\"\n    resp = requests.post(\n        \"https://api.weixin.qq.com/cgi-bin/draft/get\",\n        params={\"access_token\": access_token},\n        json={\"media_id\": media_id},\n    )\n    resp.encoding = \"utf-8\"\n    data = resp.json()\n\n    errcode = data.get(\"errcode\", 0)\n    if errcode != 0:\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat get_draft error: errcode={errcode}, errmsg={errmsg}\")\n\n    articles = data.get(\"news_item\", [])\n    if not articles:\n        raise ValueError(f\"WeChat get_draft: no articles in draft {media_id}\")\n\n    return articles[0].get(\"content\", \"\")\n\n\ndef html_to_plaintext(html: str) -> str:\n    \"\"\"Extract plain text from WeChat HTML, stripping all tags and styles.\"\"\"\n    import re\n    # Remove script/style blocks\n    text = re.sub(r\"<(script|style)[^>]*>.*?</\\1>\", \"\", html, flags=re.DOTALL | re.IGNORECASE)\n    # Replace block-level tags with newlines\n    text = re.sub(r\"<(br|p|div|section|h[1-6])[^>]*>\", \"\\n\", text, flags=re.IGNORECASE)\n    # Remove all remaining tags\n    text = re.sub(r\"<[^>]+>\", \"\", text)\n    # Decode HTML entities\n    import html as html_module\n    text = html_module.unescape(text)\n    # Collapse whitespace\n    text = re.sub(r\"[ \\t]+\", \" \", text)\n    text = re.sub(r\"\\n{3,}\", \"\\n\\n\", text)\n    return text.strip()\n\n\ndef create_image_post(\n    access_token: str,\n    title: str,\n    image_media_ids: list[str],\n    content: str = \"\",\n    open_comment: bool = False,\n    fans_only_comment: bool = False,\n) -> ImagePostResult:\n    \"\"\"\n    Create a WeChat image post (\u5c0f\u7eff\u4e66/\u56fe\u7247\u5e16) draft.\n\n    This uses article_type=\"newspic\" which displays as a horizontal\n    swipe carousel (3:4 ratio), similar to Xiaohongshu.\n\n    Args:\n        access_token: WeChat access token.\n        title: Post title, max 32 characters.\n        image_media_ids: List of permanent media_ids from upload_thumb().\n                        Min 1, max 20. First image becomes the cover.\n        content: Plain text description, max ~1000 chars. No HTML.\n        open_comment: Allow comments.\n        fans_only_comment: Only followers can comment.\n\n    Returns ImagePostResult with media_id of created draft.\n    \"\"\"\n    if not image_media_ids:\n        raise ValueError(\"At least 1 image is required for image post\")\n    if len(image_media_ids) > 20:\n        raise ValueError(f\"Max 20 images allowed, got {len(image_media_ids)}\")\n    if len(title) > 32:\n        raise ValueError(f\"Title max 32 chars for image post, got {len(title)}\")\n\n    article = {\n        \"article_type\": \"newspic\",\n        \"title\": title,\n        \"content\": content,\n        \"image_info\": {\n            \"image_list\": [\n                {\"image_media_id\": mid} for mid in image_media_ids\n            ]\n        },\n        \"need_open_comment\": 1 if open_comment else 0,\n        \"only_fans_can_comment\": 1 if fans_only_comment else 0,\n    }\n\n    body = {\"articles\": [article]}\n\n    resp = requests.post(\n        \"https://api.weixin.qq.com/cgi-bin/draft/add\",\n        params={\"access_token\": access_token},\n        data=json.dumps(body, ensure_ascii=False).encode(\"utf-8\"),\n        headers={\"Content-Type\": \"application/json; charset=utf-8\"},\n    )\n\n    data = resp.json()\n\n    errcode = data.get(\"errcode\", 0)\n    if errcode != 0:\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat create_image_post error: errcode={errcode}, errmsg={errmsg}\")\n\n    if \"media_id\" not in data:\n        raise ValueError(f\"WeChat create_image_post: missing media_id in response: {data}\")\n\n    return ImagePostResult(\n        media_id=data[\"media_id\"],\n        image_count=len(image_media_ids),\n    )\n"}, {"path": "toolkit/wechat_api.py", "content": "import time\nimport mimetypes\nimport requests\nfrom pathlib import Path\nfrom dataclasses import dataclass\n\n# Token cache\n_token_cache: dict = {}\n\n# Unified timeout for WeChat API calls\nAPI_TIMEOUT = 30\n\n\n@dataclass\nclass TokenResult:\n    access_token: str\n    expires_at: float  # unix timestamp\n    appid: str\n    secret: str\n\n\ndef get_access_token(appid: str, secret: str, force_refresh: bool = False) -> str:\n    \"\"\"\n    Get access_token with caching and auto-refresh.\n    Cache key: appid\n    API: GET https://api.weixin.qq.com/cgi-bin/token\n    Cache until expires_in - 300 seconds (5 min buffer).\n    Raise ValueError on API error.\n    \"\"\"\n    now = time.time()\n\n    if not force_refresh and appid in _token_cache:\n        cached: TokenResult = _token_cache[appid]\n        if now < cached.expires_at:\n            return cached.access_token\n\n    resp = requests.get(\n        \"https://api.weixin.qq.com/cgi-bin/token\",\n        params={\n            \"grant_type\": \"client_credential\",\n            \"appid\": appid,\n            \"secret\": secret,\n        },\n        timeout=API_TIMEOUT,\n    )\n    data = resp.json()\n\n    if \"access_token\" not in data:\n        errcode = data.get(\"errcode\", \"unknown\")\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat API error: errcode={errcode}, errmsg={errmsg}\")\n\n    access_token = data[\"access_token\"]\n    expires_in = data.get(\"expires_in\", 7200)\n\n    _token_cache[appid] = TokenResult(\n        access_token=access_token,\n        expires_at=now + expires_in - 300,\n        appid=appid,\n        secret=secret,\n    )\n\n    return access_token\n\n\ndef ensure_valid_token(appid: str, secret: str) -> str:\n    \"\"\"Get a valid token, force-refreshing if near expiry.\n\n    Use this instead of get_access_token for long-running operations\n    where the token may have expired since initial acquisition.\n    \"\"\"\n    now = time.time()\n    if appid in _token_cache:\n        cached = _token_cache[appid]\n        if now >= cached.expires_at:\n            return get_access_token(appid, secret, force_refresh=True)\n        return cached.access_token\n    return get_access_token(appid, secret)\n\n\ndef _guess_content_type(file_path: str) -> str:\n    \"\"\"Detect content type from file extension.\"\"\"\n    content_type, _ = mimetypes.guess_type(file_path)\n    return content_type or \"application/octet-stream\"\n\n\ndef upload_image(access_token: str, image_path: str) -> str:\n    \"\"\"\n    Upload image for use inside article content.\n    API: POST https://api.weixin.qq.com/cgi-bin/media/uploadimg\n    Returns the url string.\n    Raise ValueError on error.\n    \"\"\"\n    path = Path(image_path)\n    content_type = _guess_content_type(image_path)\n\n    with open(path, \"rb\") as f:\n        resp = requests.post(\n            \"https://api.weixin.qq.com/cgi-bin/media/uploadimg\",\n            params={\"access_token\": access_token},\n            files={\"media\": (path.name, f, content_type)},\n            timeout=API_TIMEOUT,\n        )\n\n    data = resp.json()\n\n    if \"url\" not in data:\n        errcode = data.get(\"errcode\", \"unknown\")\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat upload_image error: errcode={errcode}, errmsg={errmsg}\")\n\n    return data[\"url\"]\n\n\ndef upload_thumb(access_token: str, image_path: str) -> str:\n    \"\"\"\n    Upload cover image as permanent material.\n    API: POST https://api.weixin.qq.com/cgi-bin/material/add_material\n    Returns media_id string.\n    Raise ValueError on error.\n    \"\"\"\n    path = Path(image_path)\n    content_type = _guess_content_type(image_path)\n\n    with open(path, \"rb\") as f:\n        resp = requests.post(\n            \"https://api.weixin.qq.com/cgi-bin/material/add_material\",\n            params={\"access_token\": access_token, \"type\": \"image\"},\n            files={\"media\": (path.name, f, content_type)},\n            timeout=API_TIMEOUT,\n        )\n\n    data = resp.json()\n\n    if \"media_id\" not in data:\n        errcode = data.get(\"errcode\", \"unknown\")\n        errmsg = data.get(\"errmsg\", \"unknown error\")\n        raise ValueError(f\"WeChat upload_thumb error: errcode={errcode}, errmsg={errmsg}\")\n\n    return data[\"media_id\"]\n"}, {"path": "toolkit/theme.py", "content": "\"\"\"\nTheme system for WeWrite.\n\nLoads YAML theme definitions and provides CSS parsing utilities\nfor the inline style converter.\n\"\"\"\n\nimport logging\nimport os\nimport re\nfrom dataclasses import dataclass, field\nfrom pathlib import Path\nfrom typing import Optional\n\nimport cssutils\nimport yaml\n\n# Suppress cssutils warnings (it's very noisy about non-standard properties)\ncssutils.log.setLevel(logging.CRITICAL)\n\n\n@dataclass\nclass Theme:\n    \"\"\"A theme definition with colors and base CSS.\"\"\"\n\n    name: str\n    description: str\n    base_css: str\n    colors: dict = field(default_factory=dict)\n\n\ndef _default_themes_dir() -> str:\n    \"\"\"Return the themes/ directory relative to this file.\"\"\"\n    return str(Path(__file__).parent / \"themes\")\n\n\ndef load_theme(name: str, themes_dir: str = None) -> Theme:\n    \"\"\"\n    Load a theme by name from a YAML file.\n\n    Args:\n        name: Theme name (without .yaml extension).\n        themes_dir: Directory containing theme YAML files.\n                    Defaults to themes/ relative to this file.\n\n    Returns:\n        A Theme object.\n\n    Raises:\n        FileNotFoundError: If the theme YAML file does not exist.\n        ValueError: If the YAML is malformed or missing required fields.\n    \"\"\"\n    if themes_dir is None:\n        themes_dir = _default_themes_dir()\n\n    theme_path = os.path.join(themes_dir, f\"{name}.yaml\")\n    if not os.path.exists(theme_path):\n        raise FileNotFoundError(f\"Theme file not found: {theme_path}\")\n\n    with open(theme_path, \"r\", encoding=\"utf-8\") as f:\n        data = yaml.safe_load(f)\n\n    if not isinstance(data, dict):\n        raise ValueError(f\"Invalid theme file: {theme_path}\")\n\n    required = (\"name\", \"description\", \"base_css\", \"colors\")\n    for key in required:\n        if key not in data:\n            raise ValueError(f\"Theme file missing required field '{key}': {theme_path}\")\n\n    theme = Theme(\n        name=data[\"name\"],\n        description=data[\"description\"],\n        base_css=data[\"base_css\"],\n        colors=data.get(\"colors\", {}),\n    )\n    # Attach raw data for extra fields (aigc_footer, css_randomize, etc.)\n    theme._raw_data = data\n    return theme\n\n\ndef list_themes(themes_dir: str = None) -> list[str]:\n    \"\"\"\n    List available theme names.\n\n    Args:\n        themes_dir: Directory containing theme YAML files.\n                    Defaults to themes/ relative to this file.\n\n    Returns:\n        Sorted list of theme names (without .yaml extension).\n    \"\"\"\n    if themes_dir is None:\n        themes_dir = _default_themes_dir()\n\n    if not os.path.isdir(themes_dir):\n        return []\n\n    names = []\n    for filename in os.listdir(themes_dir):\n        if filename.endswith(\".yaml\") or filename.endswith(\".yml\"):\n            names.append(filename.rsplit(\".\", 1)[0])\n\n    return sorted(names)\n\n\ndef _resolve_css_variables(css_text: str, colors: dict) -> str:\n    \"\"\"\n    Replace var(--xxx) references in CSS with actual color values.\n\n    Supports var(--primary), var(--secondary), etc. based on the\n    colors dict keys. The CSS variable name is mapped by stripping\n    the leading --.\n    \"\"\"\n    def replacer(match: re.Match) -> str:\n        var_name = match.group(1).strip()\n        # Strip leading -- prefix\n        key = var_name.lstrip(\"-\")\n        # Also try with hyphens converted to underscores\n        key_underscore = key.replace(\"-\", \"_\")\n        if key in colors:\n            return str(colors[key])\n        if key_underscore in colors:\n            return str(colors[key_underscore])\n        # Return original if not found\n        return match.group(0)\n\n    return re.sub(r\"var\\(\\s*--([a-zA-Z0-9_-]+)\\s*\\)\", replacer, css_text)\n\n\ndef _is_simple_selector(selector: str) -> bool:\n    \"\"\"\n    Check if a selector is simple enough for inline styling.\n\n    Rejects pseudo-classes, pseudo-elements, media queries,\n    and complex combinators.\n    \"\"\"\n    selector = selector.strip()\n\n    # Reject if contains any of these characters\n    reject_chars = (\":\", \"@\", \">\", \"+\", \"~\", \"[\", \"*\")\n    for ch in reject_chars:\n        if ch in selector:\n            return False\n\n    return True\n\n\ndef get_inline_css_rules(theme: Theme) -> dict[str, dict[str, str]]:\n    \"\"\"\n    Parse a theme's base_css into a selector -> {property: value} dict.\n\n    This resolves CSS variable references using theme.colors, then\n    parses the CSS with cssutils. Only simple selectors are included\n    (no pseudo-classes, pseudo-elements, media queries, or complex\n    combinators).\n\n    Args:\n        theme: A Theme object with base_css and colors.\n\n    Returns:\n        Dict mapping CSS selectors to dicts of {property: value}.\n        Example: {\"h1\": {\"color\": \"#333\", \"font-size\": \"28px\"}, ...}\n    \"\"\"\n    # Resolve CSS variables first\n    resolved_css = _resolve_css_variables(theme.base_css, theme.colors)\n\n    # Parse with cssutils\n    sheet = cssutils.parseString(resolved_css, validate=False)\n\n    rules: dict[str, dict[str, str]] = {}\n\n    for rule in sheet:\n        if rule.type != rule.STYLE_RULE:\n            continue\n\n        selector_text = rule.selectorText\n\n        # A rule can have multiple comma-separated selectors\n        selectors = [s.strip() for s in selector_text.split(\",\")]\n\n        # Build property dict for this rule\n        props: dict[str, str] = {}\n        for prop in rule.style:\n            props[prop.name] = prop.value\n\n        if not props:\n            continue\n\n        for selector in selectors:\n            if not _is_simple_selector(selector):\n                continue\n\n            if selector in rules:\n                # Merge (later rules override)\n                rules[selector].update(props)\n            else:\n                rules[selector] = dict(props)\n\n    return rules\n"}]}