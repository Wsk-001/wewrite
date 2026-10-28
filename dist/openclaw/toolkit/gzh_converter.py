#!/usr/bin/env python3
"""
GZH Design Converter - Automated WeChat article formatting.
Implements gzh-design skill's core capabilities programmatically.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from html import unescape as _unescape
import jieba
import jieba.analyse

from theme_configs import get_theme, ThemeConfig


@dataclass
class ConvertResult:
    """Conversion result shared by all converters."""
    html: str
    title: str
    digest: str
    images: list = field(default_factory=list)
    residues: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# 版式变体：决定封面 / 章节标题 / 分隔线 / 正文的结构化排版（而非仅换色）
# 每个变体是一套真正不同的 HTML 结构。WeChat 会剥离伪元素，故一律用真实元素实现。
# ---------------------------------------------------------------------------
LAYOUT_PROFILES = {
    # 圆角渐变徽章卡（原有风格）
    "classic": dict(cover="card", section="badge", divider="ornament",
                    radius=20, shadow=True, indent=False, para_size=14, serif_titles=False),
    # 杂志编辑：居中报头 + 大号衬线数字章节号 + 细线
    "editorial": dict(cover="masthead", section="numeral", divider="rule",
                      radius=0, shadow=False, indent=True, para_size=15, serif_titles=True),
    # 临床科技：直角描边 + 等宽方框编号 + 全宽细线
    "clinical": dict(cover="boxed", section="monobox", divider="rule",
                     radius=0, shadow=False, indent=False, para_size=14, serif_titles=False),
    # 杂志封面：顶部色块刊头 + 通栏色条章节标题
    "magazine": dict(cover="kicker", section="bar", divider="thinrule",
                     radius=0, shadow=False, indent=True, para_size=15, serif_titles=False),
    # 极简：无卡片，左侧竖条章节标题，大留白
    "minimal": dict(cover="plain", section="rule", divider="none",
                    radius=0, shadow=False, indent=False, para_size=15, serif_titles=False),
    # 报纸：双线报头 + 上划线衬线章节标题
    "newspaper": dict(cover="masthead_serif", section="ruleserif", divider="doublerule",
                      radius=0, shadow=False, indent=True, para_size=15, serif_titles=True),
    # 海报：超大堆叠标题 + 色块编号
    "poster": dict(cover="poster", section="block", divider="none",
                   radius=0, shadow=False, indent=False, para_size=16, serif_titles=False),
    # 书页侧栏：左侧窄栏放编号，右侧正文，中线分隔
    "sidebar": dict(cover="card", section="sidebarnum", divider="rule",
                    radius=12, shadow=False, indent=False, para_size=14, serif_titles=False),
}


class GzhConverter:
    """Convert Markdown to WeChat HTML using gzh-design themes."""
    
    def __init__(self, theme_identifier: str = "moyu-green", skill_root: Optional[Path] = None):
        """
        Initialize converter with specified theme.
        
        Args:
            theme_identifier: Theme identifier (moyu-green, red-white, etc.)
            skill_root: Path to gzh-design skill root (for validation script)
        """
        self.theme_cfg = get_theme(theme_identifier)
        if not self.theme_cfg:
            raise ValueError(f"Unknown theme: {theme_identifier}")
        
        self.skill_root = skill_root
        self.validate_script = skill_root / "scripts" / "validate_gzh_html.py" if skill_root else None
        
        # Extract colors from theme config
        self.PRIMARY = self.theme_cfg.primary_color
        self.PRIMARY_LIGHT = self.theme_cfg.accent_color or self.theme_cfg.primary_light
        self.TEXT_MAIN = self.theme_cfg.text_color
        self.TEXT_GRAY = self.theme_cfg.secondary_color
        self.UNDERLINE_CSS = self.theme_cfg.underline_css
        
        # Extract layout parameters from theme config
        self.SECTION_MARGIN = self.theme_cfg.section_margin
        self.LINE_HEIGHT = self.theme_cfg.line_height
        self.TITLE_WEIGHT = self.theme_cfg.title_weight
        self.BODY_WEIGHT = self.theme_cfg.body_weight

        # Typography: font stack / page background / letter spacing
        self.FONT_FAMILY = self.theme_cfg.font_family or ThemeConfig.DEFAULT_SANS
        self.PAGE_BG = self.theme_cfg.page_bg
        self.LETTER_SPACING = self.theme_cfg.letter_spacing

        # Layout variant (结构性排版，非仅配色)
        self.VARIANT = (getattr(self.theme_cfg, "style_variant", "") or "classic").strip() or "classic"
        self.LAYOUT = LAYOUT_PROFILES.get(self.VARIANT, LAYOUT_PROFILES["classic"])
        self.TITLE_FONT = ThemeConfig.SERIF_STACK if self.LAYOUT["serif_titles"] else self.FONT_FAMILY

    def _rgba(self, alpha: float) -> str:
        """Derive rgba() string from the theme primary color."""
        h = self.PRIMARY.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
        
    def convert_file(self, md_path: Path, author: Optional[str] = None, author_intro: Optional[str] = None) -> ConvertResult:
        """Convert markdown file to WeChat HTML."""
        md_text = md_path.read_text(encoding="utf-8")
        return self.convert(md_text, author, author_intro)
    
    def convert(self, md_text: str, author: Optional[str] = None, author_intro: Optional[str] = None) -> ConvertResult:
        """Convert markdown text to WeChat HTML."""
        # Parse structure
        structure = self._parse_markdown(md_text)

        # Generate HTML
        html = self._generate_html(structure, author, author_intro)

        # Extract metadata
        return ConvertResult(
            html=html,
            title=structure["title"],
            digest=self._extract_digest(structure),
            images=structure["images"],
            residues=self._check_markdown_residue(html)
        )
    
    def _parse_markdown(self, md_text: str) -> Dict:
        """Parse markdown structure."""
        lines = md_text.split("\n")
        
        structure = {
            "title": "",
            "intro_paragraphs": [],
            "sections": [],
            "images": [],
            "summary": None
        }
        
        current_section = None
        intro_done = False
        current_paragraph_lines = []
        in_container = None  # Track ::: container type (e.g., "summary")
        container_lines = []
        skip_until = -1  # Table blocks consumed by lookahead

        for line_idx, line in enumerate(lines):
            if line_idx <= skip_until:
                continue
            stripped = line.strip()

            # Table block (consecutive lines starting with "|")
            if stripped.startswith("|"):
                block_end = line_idx
                while block_end < len(lines) and lines[block_end].strip().startswith("|"):
                    block_end += 1
                block = [lines[i].strip() for i in range(line_idx, block_end)]
                table = self._parse_table_block(block)
                # Flush pending paragraph first
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                if table:
                    item = {"type": "table", "header": table[0], "rows": table[1]}
                    skip_until = block_end - 1
                else:
                    # Invalid table syntax - fall through as plain text so the
                    # residue check can flag it at publish time
                    item = " ".join(block)
                if current_section:
                    current_section["content"].append(item)
                else:
                    structure["intro_paragraphs"].append(item)
                continue

            # Blockquote (consecutive lines starting with ">")
            if stripped.startswith(">"):
                quote_end = line_idx
                quote_lines = []
                while quote_end < len(lines) and lines[quote_end].strip().startswith(">"):
                    quote_lines.append(lines[quote_end].strip().lstrip(">").strip())
                    quote_end += 1
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                item = {"type": "blockquote", "text": self._join_paragraph([l for l in quote_lines if l])}
                skip_until = quote_end - 1
                if current_section:
                    current_section["content"].append(item)
                else:
                    structure["intro_paragraphs"].append(item)
                continue

            # Container fence (:::type or closing :::)
            if stripped.startswith(":::"):
                if in_container:
                    # Closing fence - save container content
                    if in_container == "summary":
                        # Join container lines, skip the type label if present
                        content_lines = [l for l in container_lines if not l.strip().startswith(":::")]
                        structure["summary"] = " ".join(content_lines).strip()
                    in_container = None
                    container_lines = []
                else:
                    # Opening fence - detect container type
                    # Extract type from ":::type optional-label" -> "type"
                    fence_text = stripped[3:].strip()  # Remove ":::"
                    if fence_text:
                        # Take first word as container type
                        in_container = fence_text.split()[0] if fence_text.split() else "generic"
                    else:
                        in_container = "generic"
                    container_lines = []
                continue
            
            # If inside container, collect lines
            if in_container:
                container_lines.append(stripped)
                continue
            
            # Title
            if stripped.startswith("# ") and not structure["title"]:
                structure["title"] = stripped[2:].strip()
                continue
            
            # Duplicate H1 title - ignore silently instead of leaking "#" into text
            if stripped.startswith("# "):
                continue
            
            # Horizontal rule (skip it - don't add to content)
            if stripped in ("---", "***", "___") or re.match(r'^-{3,}$|^\*{3,}$|^_{3,}$', stripped):
                continue
            
            # Section
            if stripped.startswith("## "):
                intro_done = True
                
                # Save previous paragraph if any
                if current_paragraph_lines:
                    if current_section:
                        current_section["content"].append(self._join_paragraph(current_paragraph_lines))
                    else:
                        structure["intro_paragraphs"].append(self._join_paragraph(current_paragraph_lines))
                    current_paragraph_lines = []
                
                current_section = {
                    "title": stripped[3:].strip(),
                    "content": []
                }
                structure["sections"].append(current_section)
                continue
            
            # List item (- xxx / * xxx / 1. xxx) - flush paragraph first, then emit item
            unordered_match = re.match(r'^[-*]\s+(.+)$', stripped)
            ordered_match = re.match(r'^(\d{1,3})[.、)]\s+(.+)$', stripped)
            if unordered_match or ordered_match:
                # Flush any pending paragraph lines
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                if ordered_match:
                    item = {"type": "list_item", "text": ordered_match.group(2).strip(),
                            "ordered": True, "index": int(ordered_match.group(1))}
                else:
                    item = {"type": "list_item", "text": unordered_match.group(1).strip(),
                            "ordered": False}
                if current_section:
                    current_section["content"].append(item)
                else:
                    structure["intro_paragraphs"].append(item)
                continue
            
            # Subheading (### xxx)
            if stripped.startswith("### "):
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                sub = {"type": "subheading", "text": stripped[4:].strip()}
                if current_section:
                    current_section["content"].append(sub)
                else:
                    structure["intro_paragraphs"].append(sub)
                continue
            
            # Image
            img_match = re.match(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)', stripped)
            if img_match:
                img_url = img_match.group(2)
                if not img_url.startswith(("http://", "https://")):
                    structure["images"].append(img_url)
                
                img_item = {"type": "image", "url": img_url, "alt": img_match.group(1)}
                # Save image as content item (works in intro AND sections)
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                if current_section:
                    current_section["content"].append(img_item)
                else:
                    structure["intro_paragraphs"].append(img_item)
                continue
            
            # Empty line - paragraph break
            if not stripped:
                if current_paragraph_lines:
                    para_text = self._join_paragraph(current_paragraph_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    elif intro_done:
                        pass  # Skip empty lines between sections
                    else:
                        structure["intro_paragraphs"].append(para_text)
                    current_paragraph_lines = []
                continue
            
            # Regular text line
            if stripped:
                current_paragraph_lines.append(stripped)
        
        # Save final paragraph
        if current_paragraph_lines:
            para_text = self._join_paragraph(current_paragraph_lines)
            if current_section:
                current_section["content"].append(para_text)
            elif not intro_done:
                structure["intro_paragraphs"].append(para_text)
        
        # Unclosed container at EOF - salvage content instead of dropping it
        if in_container:
            if in_container == "summary" and container_lines:
                content_lines = [l for l in container_lines if l.strip()]
                structure["summary"] = " ".join(content_lines).strip()
            elif container_lines:
                # Treat remaining lines as a normal paragraph
                text_lines = [l for l in container_lines if l.strip()]
                if text_lines:
                    para_text = self._join_paragraph(text_lines)
                    if current_section:
                        current_section["content"].append(para_text)
                    elif not intro_done:
                        structure["intro_paragraphs"].append(para_text)
        
        return structure
    
    def _parse_table_block(self, block: List[str]) -> Optional[Tuple[List[str], List[List[str]]]]:
        """Parse a block of pipe-table lines.

        Returns (header_cells, rows) when the block is a valid table
        (first data line is a separator row), otherwise None.
        """
        if len(block) < 2:
            return None

        def split_row(line: str) -> List[str]:
            return [c.strip() for c in line.strip().strip("|").split("|")]

        header = split_row(block[0])
        separator = split_row(block[1])
        if len(header) < 2 or len(separator) != len(header):
            return None
        if not all(re.fullmatch(r':?-{2,}:?', c) for c in separator):
            return None

        rows = [split_row(l) for l in block[2:]]
        rows = [r for r in rows if any(r)]
        return header, rows

    def _join_paragraph(self, lines: List[str]) -> str:
        """Join paragraph lines into single text.

        仅当两侧都是 ASCII 字母/数字时插入一个空格（英文单词断行）；
        任一侧是中文、全角字符或标点符号时直接拼接。
        """
        result = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if result:
                prev_c = result[-1]
                next_c = line[0]
                if (prev_c.isascii() and prev_c.isalnum()
                        and next_c.isascii() and next_c.isalnum()):
                    result += " "
            result += line
        return result
    
    def _extract_digest(self, structure: Dict) -> str:
        """Extract article digest from intro paragraphs."""
        first_para = next(
            (p for p in structure["intro_paragraphs"] if isinstance(p, str)), None
        )
        if first_para:
            # Remove markdown syntax
            clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', first_para)
            clean = re.sub(r'==([^=]+)==', r'\1', clean)
            clean = re.sub(r'`([^`]+)`', r'\1', clean)
            return clean[:100] + ("..." if len(clean) > 100 else "")
        elif structure["sections"]:
            # Take first section's first paragraph
            first_section = structure["sections"][0]
            if first_section["content"]:
                first_content = first_section["content"][0]
                if isinstance(first_content, str):
                    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', first_content)
                    return clean[:100] + ("..." if len(clean) > 100 else "")
        return structure["title"][:50]
    
    def _generate_html(self, structure: Dict, author: Optional[str], author_intro: Optional[str]) -> str:
        """Generate WeChat HTML from structure."""
        parts = []
        
        # Container start
        parts.append(
            f'<section style="max-width:677px;margin:0 auto;background:{self.PAGE_BG};'
            f"font-family:{self.FONT_FAMILY};"
            f'color:{self.TEXT_MAIN};line-height:{self.LINE_HEIGHT};letter-spacing:{self.LETTER_SPACING}px;overflow-x:hidden;">'
        )
        
        # Cover (simplified version without image)
        parts.append(self._generate_cover(structure, author))
        
        # Intro paragraphs
        if structure["intro_paragraphs"]:
            parts.append('<section style="margin:0 20px 24px;">')
            for para in structure["intro_paragraphs"]:
                parts.append(self._render_content_item(para))
            parts.append('</section>')
        
        # Sections with auto-numbering
        for idx, section in enumerate(structure["sections"], 1):
            parts.append(self._generate_section(idx, section))
        
        # Summary card (if present)
        if structure.get("summary"):
            parts.append(self._generate_summary_card(structure["summary"]))
        
        # Divider
        parts.append(self._generate_divider())
        
        # Container end
        parts.append('</section>')
        
        return "\n".join(parts)
    
    def _split_title(self, title: str):
        """Split long title into two lines and pull a trailing CJK key phrase."""
        if len(title) > 15:
            mid = len(title) // 2
            split_pos = None
            for i in range(mid - 5, mid + 5):
                if 0 < i < len(title) and title[i] in "，。、：" and i + 1 < len(title):
                    split_pos = i + 1
                    break
            if split_pos is None:
                for i in list(range(mid + 5, min(len(title) - 1, mid + 12))) + list(range(max(1, mid - 12), mid - 5)):
                    if title[i] in "，。、：： ":
                        split_pos = i + 1
                        break
            if split_pos:
                title_line1 = title[:split_pos].strip()
                title_line2 = title[split_pos:].strip()
            else:
                title_line1 = title
                title_line2 = ""
        else:
            title_line1 = title
            title_line2 = ""

        tail = title_line1[-4:] if len(title_line1) > 8 else ""
        if tail and re.fullmatch(r'[\u4e00-\u9fff]{4}', tail):
            green_word = tail
            title_line1 = title_line1[:-4]
        else:
            green_word = ""
        return title_line1, title_line2, green_word

    def _generate_cover(self, structure: Dict, author: Optional[str] = None) -> str:
        """Dispatch cover rendering by layout variant."""
        builder = {
            "card": self._cover_card,
            "masthead": self._cover_masthead,
            "boxed": self._cover_boxed,
            "kicker": self._cover_kicker,
            "plain": self._cover_plain,
            "masthead_serif": self._cover_masthead_serif,
            "poster": self._cover_poster,
        }.get(self.LAYOUT["cover"], self._cover_card)
        return builder(structure, author)

    def _cover_card(self, structure: Dict, author: Optional[str]) -> str:
        """Rounded gradient card cover (classic)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        title_line1, title_line2, green_word = self._split_title(title)
        return f'''
  <section style="margin:0 0 {self.SECTION_MARGIN}px;background:#fff;border:1.5px solid {self._rgba(0.15)};border-radius:{self.LAYOUT['radius']}px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06);width:100%;">
    <section style="padding:32px 28px 28px;">
      <section style="display:flex;align-items:center;gap:8px;margin-bottom:28px;">
        <span style="width:6px;height:6px;background:{self.PRIMARY};border-radius:50%;"><span leaf=""><br></span></span>
        <span style="font-size:11px;font-weight:700;letter-spacing:3px;color:{self.PRIMARY};"><span leaf="">科普辟谣</span></span>
        <section style="flex:1;height:1px;overflow:hidden;background:linear-gradient(to right,{self._rgba(0.12)},transparent);"><span leaf=""><br></span></section>
      </section>
        <p style="font-size:24px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0;line-height:1.05;letter-spacing:-2px;font-family:{self.TITLE_FONT};">
          <span leaf="">{self._escape_html(title_line1)}</span>{f'<span style="color:{self.PRIMARY};"><span leaf="">{self._escape_html(green_word)}</span></span>' if green_word else ""}
        </p>
         {"" if not title_line2 else f'<p style="font-size:24px;font-weight:{self.TITLE_WEIGHT};color:{self.PRIMARY};margin:0 0 16px;line-height:1.05;letter-spacing:-2px;font-family:{self.TITLE_FONT};"><span leaf="">{self._escape_html(title_line2)}</span></p>'}
    </section>
    <section style="background:{self.PRIMARY};padding:12px 28px;display:flex;align-items:center;justify-content:space-between;">
      <p style="font-size:12px;color:rgba(255,255,255,0.9);margin:0;font-weight:600;letter-spacing:0.5px;">
        <span leaf="">{self._escape_html(account_name)}</span>
      </p>
    </section>
  </section>'''

    def _cover_masthead(self, structure: Dict, author: Optional[str]) -> str:
        """Centered editorial masthead with hairline rules (editorial)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:8px 0 {self.SECTION_MARGIN}px;text-align:center;">
    <section style="border-top:2px solid {self.PRIMARY};padding-top:10px;margin:0 20px 22px;">
      <span style="font-size:11px;font-weight:700;letter-spacing:5px;color:{self.PRIMARY};"><span leaf="">科普辟谣</span></span>
    </section>
    <p style="font-size:27px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0 24px 18px;line-height:1.32;font-family:{self.TITLE_FONT};letter-spacing:1px;">
      <span leaf="">{self._escape_html(title)}</span>
    </p>
    <section style="margin:0 60px 14px;border-bottom:1px solid {self._rgba(0.35)};"><span leaf=""><br></span></section>
    <p style="font-size:11px;color:{self.TEXT_GRAY};margin:0;letter-spacing:2px;"><span leaf="">{self._escape_html(account_name)}</span></p>
    <section style="margin:14px 20px 0;border-bottom:1px solid {self._rgba(0.12)};"><span leaf=""><br></span></section>
  </section>'''

    def _cover_boxed(self, structure: Dict, author: Optional[str]) -> str:
        """Sharp bordered box with left color bar and mono label (clinical)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:0 0 {self.SECTION_MARGIN}px;border:1px solid {self._rgba(0.28)};border-left:4px solid {self.PRIMARY};">
    <section style="padding:22px 24px;">
      <p style="font-size:10px;font-weight:700;letter-spacing:4px;color:{self.PRIMARY};margin:0 0 14px;font-family:{ThemeConfig.MONO_MIXED};text-transform:uppercase;">
        <span leaf="">科普辟谣</span>
      </p>
      <p style="font-size:23px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0 0 16px;line-height:1.32;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
      <section style="border-top:1px solid {self._rgba(0.15)};padding-top:10px;display:flex;justify-content:space-between;">
        <span style="font-size:11px;color:{self.TEXT_GRAY};font-family:{ThemeConfig.MONO_MIXED};"><span leaf="">{self._escape_html(account_name)}</span></span>
        <span style="font-size:11px;color:{self.PRIMARY};font-family:{ThemeConfig.MONO_MIXED};"><span leaf="">REPORT</span></span>
      </section>
    </section>
  </section>'''

    def _cover_kicker(self, structure: Dict, author: Optional[str]) -> str:
        """Full-bleed color kicker band over the title (magazine)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:0 0 {self.SECTION_MARGIN}px;">
    <section style="background:{self.PRIMARY};padding:10px 20px;">
      <span style="font-size:11px;font-weight:700;letter-spacing:4px;color:#fff;"><span leaf="">科普辟谣</span></span>
    </section>
    <section style="padding:24px 20px 18px;border-bottom:1px solid {self._rgba(0.2)};">
      <p style="font-size:26px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0 0 14px;line-height:1.3;font-family:{self.TITLE_FONT};">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
      <p style="font-size:12px;color:{self.TEXT_GRAY};margin:0;letter-spacing:1px;"><span leaf="">{self._escape_html(account_name)}</span></p>
    </section>
  </section>'''

    def _cover_plain(self, structure: Dict, author: Optional[str]) -> str:
        """Undecorated big title with a tiny meta line (minimal)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:16px 20px {self.SECTION_MARGIN}px;">
    <p style="font-size:9px;font-weight:600;letter-spacing:4px;color:{self.PRIMARY};margin:0 0 20px;"><span leaf="">科普辟谣</span></p>
    <p style="font-size:26px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0 0 24px;line-height:1.42;letter-spacing:0.5px;">
      <span leaf="">{self._escape_html(title)}</span>
    </p>
    <p style="font-size:11px;color:{self.TEXT_GRAY};margin:0;letter-spacing:1px;"><span leaf="">{self._escape_html(account_name)}</span></p>
  </section>'''

    def _cover_masthead_serif(self, structure: Dict, author: Optional[str]) -> str:
        """Newspaper masthead with double rules (newspaper)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:8px 20px {self.SECTION_MARGIN}px;">
    <section style="border-top:3px double {self.PRIMARY};border-bottom:1px solid {self._rgba(0.3)};padding:8px 0;text-align:center;margin-bottom:20px;">
      <span style="font-size:12px;font-weight:700;letter-spacing:6px;color:{self.PRIMARY};font-family:{self.TITLE_FONT};"><span leaf="">科普辟谣</span></span>
    </section>
    <p style="font-size:30px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0 0 16px;line-height:1.28;text-align:center;font-family:{self.TITLE_FONT};">
      <span leaf="">{self._escape_html(title)}</span>
    </p>
    <section style="border-top:1px solid {self._rgba(0.3)};padding-top:8px;text-align:center;">
      <span style="font-size:11px;color:{self.TEXT_GRAY};letter-spacing:2px;font-family:{self.TITLE_FONT};"><span leaf="">{self._escape_html(account_name)}</span></span>
    </section>
  </section>'''

    def _cover_poster(self, structure: Dict, author: Optional[str]) -> str:
        """Oversized stacked title with a color block (poster)."""
        title = structure["title"]
        account_name = (author or "").strip() or "账号名"
        return f'''
  <section style="margin:0 0 {self.SECTION_MARGIN}px;">
    <section style="padding:20px 20px 0;">
      <span style="display:inline-block;background:{self.PRIMARY};color:#fff;font-size:11px;font-weight:700;letter-spacing:3px;padding:5px 12px;"><span leaf="">科普辟谣</span></span>
    </section>
    <p style="font-size:33px;font-weight:900;color:#111827;margin:16px 20px 10px;line-height:1.14;letter-spacing:-1px;">
      <span leaf="">{self._escape_html(title)}</span>
    </p>
    <section style="margin:0 20px 6px;border-bottom:4px solid {self.PRIMARY};width:64px;"><span leaf=""><br></span></section>
    <p style="font-size:12px;color:{self.TEXT_GRAY};margin:12px 20px 0;letter-spacing:1px;"><span leaf="">{self._escape_html(account_name)}</span></p>
  </section>'''
    
    def _generate_section(self, number: int, section: Dict) -> str:
        """Dispatch section rendering by layout variant."""
        title = section["title"]
        deduped = re.sub(rf'^第?\s*(?:{number:02d}|{number})(?:\s*[、.．:：]\s*|\s+)(?=\S)', '', title)
        if deduped:
            title = deduped

        builder = {
            "badge": self._section_badge,
            "numeral": self._section_numeral,
            "monobox": self._section_monobox,
            "bar": self._section_bar,
            "rule": self._section_rule,
            "ruleserif": self._section_ruleserif,
            "block": self._section_block,
            "sidebarnum": self._section_sidebarnum,
        }.get(self.LAYOUT["section"], self._section_badge)

        header = builder(number, title)
        body = self._render_section_body(section)
        return header + body + '\n</section>'

    def _render_section_body(self, section: Dict) -> str:
        parts = [f'\n  <section style="margin:0 20px 14px;">']
        for item in section["content"]:
            parts.append(self._render_content_item(item))
        parts.append('  </section>')
        return "\n".join(parts)

    def _section_badge(self, number: int, title: str) -> str:
        """Gradient square badge + title (classic)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:20px;">
    <section style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
      <section style="display:flex;align-items:center;justify-content:center;min-width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,{self.PRIMARY},{self.PRIMARY_LIGHT});box-shadow:0 2px 8px {self._rgba(0.25)};">
        <span style="font-size:15px;font-weight:900;color:#fff;"><span leaf="">{number:02d}</span></span>
      </section>
      <p style="font-size:18px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0;line-height:1.4;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''

    def _section_numeral(self, number: int, title: str) -> str:
        """Oversized translucent serif numeral beside title with hairline (editorial)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:16px;">
    <section style="display:flex;align-items:baseline;gap:14px;border-bottom:1px solid {self._rgba(0.18)};padding-bottom:10px;">
      <span style="font-size:44px;font-weight:{self.TITLE_WEIGHT};color:{self._rgba(0.16)};line-height:0.8;font-family:{ThemeConfig.SERIF_STACK};font-style:italic;"><span leaf="">{number:02d}</span></span>
      <p style="font-size:19px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0;line-height:1.3;font-family:{self.TITLE_FONT};flex:1;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''

    def _section_monobox(self, number: int, title: str) -> str:
        """Mono square box number + uppercase title + full rule (clinical)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:16px;">
    <section style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
      <section style="min-width:30px;height:26px;border:1px solid {self.PRIMARY};display:flex;align-items:center;justify-content:center;">
        <span style="font-size:13px;font-weight:700;color:{self.PRIMARY};font-family:{ThemeConfig.MONO_MIXED};"><span leaf="">{number:02d}</span></span>
      </section>
      <p style="font-size:16px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0;line-height:1.4;letter-spacing:0.5px;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
    <section style="height:1px;background:{self._rgba(0.15)};"><span leaf=""><br></span></section>
  </section>'''

    def _section_bar(self, number: int, title: str) -> str:
        """Full-width colored bar containing number and title (magazine)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="margin:0 20px 16px;background:{self.PRIMARY};padding:8px 16px;display:flex;align-items:center;gap:12px;">
    <span style="font-size:20px;font-weight:900;color:rgba(255,255,255,0.55);line-height:1;font-family:{ThemeConfig.SERIF_STACK};"><span leaf="">{number:02d}</span></span>
    <p style="font-size:17px;font-weight:{self.TITLE_WEIGHT};color:#fff;margin:0;line-height:1.3;font-family:{self.TITLE_FONT};">
      <span leaf="">{self._escape_html(title)}</span>
    </p>
  </section>'''

    def _section_rule(self, number: int, title: str) -> str:
        """Left vertical bar + number + title, big whitespace (minimal)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:20px;">
    <section style="display:flex;align-items:center;gap:12px;">
      <section style="width:3px;height:22px;background:{self.PRIMARY};"><span leaf=""><br></span></section>
      <span style="font-size:12px;font-weight:700;color:{self.PRIMARY};letter-spacing:1px;font-family:{ThemeConfig.MONO_MIXED};"><span leaf="">{number:02d}</span></span>
      <p style="font-size:19px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0;line-height:1.4;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''

    def _section_ruleserif(self, number: int, title: str) -> str:
        """Serif title with a top rule and small-caps index (newspaper)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:16px;">
    <section style="border-top:1px solid {self._rgba(0.35)};padding-top:10px;">
      <p style="font-size:11px;font-weight:700;color:{self.PRIMARY};margin:0 0 6px;letter-spacing:3px;font-family:{self.TITLE_FONT};"><span leaf="">第 {number:02d} 节</span></p>
      <p style="font-size:20px;font-weight:{self.TITLE_WEIGHT};color:#1A1A1A;margin:0;line-height:1.3;font-family:{self.TITLE_FONT};">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''

    def _section_block(self, number: int, title: str) -> str:
        """Solid color square with big number + heavy title (poster)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="padding:0 20px;margin-bottom:18px;">
    <section style="display:flex;align-items:center;gap:14px;">
      <section style="width:46px;height:46px;background:{self.PRIMARY};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <span style="font-size:22px;font-weight:900;color:#fff;font-family:{ThemeConfig.SERIF_STACK};"><span leaf="">{number:02d}</span></span>
      </section>
      <p style="font-size:21px;font-weight:900;color:#111827;margin:0;line-height:1.2;letter-spacing:-0.5px;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''

    def _section_sidebarnum(self, number: int, title: str) -> str:
        """Number in a narrow left gutter column with a vertical rule (sidebar)."""
        return f'''
<section style="margin:0 0 {self.SECTION_MARGIN}px;">
  <section style="margin:0 20px 16px;display:flex;align-items:stretch;gap:0;">
    <section style="width:52px;flex-shrink:0;border-right:1px solid {self._rgba(0.2)};display:flex;align-items:flex-start;padding-top:2px;">
      <span style="font-size:30px;font-weight:{self.TITLE_WEIGHT};color:{self.PRIMARY};line-height:1;font-family:{ThemeConfig.SERIF_STACK};"><span leaf="">{number:02d}</span></span>
    </section>
    <section style="flex:1;padding-left:16px;display:flex;align-items:center;">
      <p style="font-size:18px;font-weight:{self.TITLE_WEIGHT};color:#111827;margin:0;line-height:1.35;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>'''
    
    def _render_content_item(self, item) -> str:
        """Render a content item (str paragraph, image, list_item, subheading, table, blockquote)."""
        if isinstance(item, dict):
            t = item.get("type")
            if t == "image":
                return self._generate_image(item)
            if t == "list_item":
                return self._generate_list_item(item)
            if t == "subheading":
                return self._generate_subheading(item["text"])
            if t == "table":
                return self._generate_table(item)
            if t == "blockquote":
                return self._generate_blockquote(item)
            return self._generate_paragraph(str(item))
        return self._generate_paragraph(item)

    def _generate_list_item(self, item: Dict) -> str:
        """Generate a list item (WeChat-safe section+p). Ordered items keep their number."""
        marked_text = self._mark_keywords(item["text"])
        html_text = self._convert_inline_markdown(marked_text)
        if item.get("ordered"):
            marker = (
                f'<span style="position:absolute;left:0;color:{self.PRIMARY};'
                f'font-weight:700;font-size:13px;">{item.get("index", "")}.</span>'
            )
            padding_left = 24
        else:
            marker = f'<span style="position:absolute;left:0;color:{self.PRIMARY};font-weight:700;">•</span>'
            padding_left = 18
        return f'''    <p style="font-size:{self.LAYOUT.get('para_size', 14)}px;line-height:{self.LINE_HEIGHT};color:{self.TEXT_MAIN};margin:0 0 10px;padding-left:{padding_left}px;position:relative;font-weight:{self.BODY_WEIGHT};">
      {marker}{html_text}
    </p>'''

    def _generate_table(self, table: Dict) -> str:
        """Generate a markdown table as a WeChat-safe <table> with theme colors and zebra rows."""
        header = table["header"]
        rows = table["rows"]

        ths = "".join(
            f'<th style="border:1px solid {self._rgba(0.3)};padding:8px 10px;background:{self.PRIMARY};color:#FFFFFF;font-weight:700;font-size:13px;text-align:center;">'
            f'<span leaf="">{self._escape_html(c)}</span></th>'
            for c in header
        )

        body_parts = []
        for i, row in enumerate(rows):
            zebra = f'background:{self._rgba(0.05)};' if i % 2 == 1 else ""
            tds = []
            for cell in row:
                align = "center" if len(cell) <= 8 else "left"
                cell_html = self._convert_inline_markdown(cell)
                tds.append(
                    f'<td style="border:1px solid {self._rgba(0.18)};padding:8px 10px;font-size:13px;color:{self.TEXT_MAIN};text-align:{align};{zebra}">{cell_html}</td>'
                )
            body_parts.append("<tr>" + "".join(tds) + "</tr>")

        return f'''    <section style="margin:16px 0;">
      <table style="width:100%;border-collapse:collapse;table-layout:fixed;">
        <thead><tr>{ths}</tr></thead>
        <tbody>{"".join(body_parts)}</tbody>
      </table>
    </section>'''

    def _generate_blockquote(self, item: Dict) -> str:
        """Generate a blockquote as a theme-colored left-border card."""
        marked_text = self._mark_keywords(item["text"])
        html_text = self._convert_inline_markdown(marked_text)
        return f'''    <section style="margin:14px 0;padding:12px 16px;background:{self._rgba(0.05)};border-left:4px solid {self.PRIMARY};border-radius:0 {self.LAYOUT['radius']}px {self.LAYOUT['radius']}px 0;">
      <p style="font-size:{self.LAYOUT.get('para_size', 14)}px;line-height:{self.LINE_HEIGHT};color:{self.TEXT_MAIN};margin:0;font-weight:{self.BODY_WEIGHT};">{html_text}</p>
    </section>'''

    def _generate_subheading(self, text: str) -> str:
        """Generate a ### subheading."""
        marked_text = self._mark_keywords(text)
        html_text = self._convert_inline_markdown(marked_text)
        return f'''    <p style="font-size:16px;font-weight:700;color:{self.PRIMARY};margin:20px 0 10px;line-height:1.5;">
      {html_text}
    </p>'''

    def _generate_paragraph(self, text: str, is_intro: bool = False) -> str:
        """Generate paragraph with keyword highlighting (variant-aware indent/size)."""
        # Mark keywords
        marked_text = self._mark_keywords(text)
        
        # Convert markdown syntax
        html_text = self._convert_inline_markdown(marked_text)

        indent_css = "text-indent:2em;" if self.LAYOUT["indent"] else ""
        size = self.LAYOUT.get("para_size", 14)
        
        return f'''    <p style="font-size:{size}px;line-height:{self.LINE_HEIGHT};color:{self.TEXT_MAIN};margin:0 0 14px;font-weight:{self.BODY_WEIGHT};{indent_css}">
      {html_text}
    </p>'''
    
    def _mark_keywords(self, text: str) -> str:
        """Mark keywords with underline placeholder."""
        # Skip if already has bold markers
        if "**" in text:
            return text
        
        # Extract keywords using jieba
        # Remove existing markdown
        clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        clean_text = re.sub(r'==([^=]+)==', r'\1', clean_text)
        clean_text = re.sub(r'`([^`]+)`', r'\1', clean_text)
        
        # Extract top keywords (4-15 chars)
        keywords = jieba.analyse.extract_tags(clean_text, topK=3, withWeight=False)
        keywords = [kw for kw in keywords if 2 <= len(kw) <= 15]
        
        # Mark keywords with ++underline++ placeholder (will be converted later)
        marked = text
        for kw in keywords[:2]:  # Max 2 keywords per paragraph
            if kw in marked and "**" + kw not in marked:
                marked = marked.replace(kw, f"++{kw}++", 1)
        
        return marked
    
    def _convert_inline_markdown(self, text: str) -> str:
        """Convert inline markdown to WeChat HTML."""
        html = text
        
        # Bold -> keyword underline (since it's keyword)
        html = re.sub(
            r'\*\*([^*]+)\*\*',
            f'<span style="{self.UNDERLINE_CSS}"><span leaf="">\\1</span></span>',
            html
        )
        
        # Underline marker (from auto-detection) -> keyword underline
        html = re.sub(
            r'\+\+([^+]+)\+\+',
            f'<span style="{self.UNDERLINE_CSS}"><span leaf="">\\1</span></span>',
            html
        )
        
        # Highlight -> yellow background
        html = re.sub(
            r'==([^=]+)==',
            f'<span style="background:{self.theme_cfg.highlight_bg};padding:2px 6px;border-radius:3px;"><span leaf="">\\1</span></span>',
            html
        )
        
        # Code -> gray background
        html = re.sub(
            r'`([^`]+)`',
            r'<span style="background:#F3F4F6;color:#1F2937;padding:2px 6px;border-radius:4px;font-size:13px;font-weight:600;"><span leaf="">\1</span></span>',
            html
        )

        # Links: WeChat strips external hrefs, render as styled text reference
        html = re.sub(
            r'\[([^\]]+)\]\([^)]+\)',
            f'<span style="color:{self.PRIMARY};font-weight:600;text-decoration:underline;">\\1</span>',
            html
        )

        # Wrap remaining text in <span leaf="">
        # Split by tags and wrap plain text segments
        parts = re.split(r'(<[^>]+>)', html)
        wrapped_parts = []
        for part in parts:
            if part.startswith('<'):
                # Keep tag as-is
                wrapped_parts.append(part)
            elif part.strip():
                # Wrap non-empty text
                wrapped_parts.append(f'<span leaf="">{part}</span>')
            elif part:
                # Keep whitespace as-is
                wrapped_parts.append(part)
        
        return ''.join(wrapped_parts)
    
    def _generate_image(self, img: Dict) -> str:
        """Generate image component."""
        url = img["url"]
        alt = img.get("alt", "")
        
        html = f'''    <section style="margin:20px 0;text-align:center;">
      <img src="{self._escape_html(url)}" style="max-width:100%;height:auto;display:block;margin:0 auto;border-radius:8px;" />'''
        
        if alt:
            html += f'''
      <p style="font-size:12px;color:#9CA3AF;margin:8px 0 0;text-align:center;">
        <span leaf="">{self._escape_html(alt)}</span>
      </p>'''
        
        html += '\n    </section>'
        
        return html
    
    
    def _generate_summary_card(self, summary_text: str) -> str:
        """Generate summary card component."""
        return f'''
  <section style="margin:0 20px {self.SECTION_MARGIN}px;">
    <section style="background:linear-gradient(135deg,{self._rgba(0.04)} 0%,{self._rgba(0.08)} 100%);border-left:4px solid {self.PRIMARY};border-radius:{self.LAYOUT['radius']}px;padding:20px 24px;box-shadow:0 2px 8px {self._rgba(0.08)};">
      <section style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <span style="font-size:14px;font-weight:700;color:{self.PRIMARY};letter-spacing:2px;"><span leaf="">一句话版本</span></span>
      </section>
      <p style="font-size:14px;font-weight:500;color:{self.TEXT_MAIN};line-height:1.8;margin:0;letter-spacing:0.5px;">
        {self._convert_inline_markdown(summary_text)}
      </p>
    </section>
  </section>'''
    
    def _generate_divider(self) -> str:
        """Dispatch divider rendering by layout variant."""
        kind = self.LAYOUT["divider"]
        if kind == "none":
            return ""
        if kind == "rule":
            return f'''
  <section style="margin:0 20px 24px;">
    <section style="height:1px;background:{self._rgba(0.2)};"><span leaf=""><br></span></section>
  </section>'''
        if kind == "thinrule":
            return f'''
  <section style="margin:0 20px 24px;">
    <section style="height:1px;background:{self.PRIMARY};opacity:0.35;"><span leaf=""><br></span></section>
  </section>'''
        if kind == "doublerule":
            return f'''
  <section style="margin:0 20px 24px;">
    <section style="border-top:1px solid {self._rgba(0.35)};border-bottom:1px solid {self._rgba(0.35)};height:4px;"><span leaf=""><br></span></section>
  </section>'''
        # ornament (classic)
        return f'''
  <section style="margin:0 20px 24px;">
    <section style="display:flex;align-items:center;gap:8px;">
      <section style="flex:1;height:2px;background:linear-gradient(to right,{self.PRIMARY} 15%,{self.PRIMARY_LIGHT} 50%,transparent);opacity:0.3;"><span leaf=""><br></span></section>
      <span style="font-size:20px;"><span leaf="">✦</span></span>
      <section style="flex:1;height:2px;background:linear-gradient(to left,{self.PRIMARY} 15%,{self.PRIMARY_LIGHT} 50%,transparent);opacity:0.3;"><span leaf=""><br></span></section>
    </section>
  </section>'''
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    # 残留检测：转换产物可见文本中若出现这些 markdown 语法，说明解析器漏接了
    _RESIDUE_PATTERNS = [
        ("表格竖线残留（|）", r"\|"),
        ("容器标记残留（:::）", r":::"),
        ("加粗标记残留（**）", r"\*\*"),
        ("高亮标记残留（==）", r"=="),
        ("下划线标记残留（++）", r"\+\+"),
        ("代码标记残留（`）", r"`"),
        ("图片语法残留（![）", r"!\["),
        ("链接语法残留（](）", r"\]\("),
        ("标题井号残留（行首 #）", r"(?:^|\n)#{1,6}\s"),
        ("引用符号残留（行首 >）", r"(?:^|\n)>\s"),
    ]

    def _check_markdown_residue(self, html: str) -> List[str]:
        """Extract visible text from generated HTML and flag leftover markdown syntax."""
        text = re.sub(r'<[^>]+>', '', html)
        text = _unescape(text)
        residues = []
        for name, pattern in self._RESIDUE_PATTERNS:
            if re.search(pattern, text):
                residues.append(name)
        return residues

    def validate(self, html_path: Path) -> bool:
        """Run validation script on generated HTML."""
        if not self.validate_script or not self.validate_script.exists():
            print("Warning: validation script not available (gzh-design skill not installed)")
            return False
        
        result = subprocess.run(
            ["python3", str(self.validate_script), str(html_path)],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Check if validation passed (no ERROR)
        return "ERROR" not in result.stdout and result.returncode == 0
