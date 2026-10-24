#!/usr/bin/env python3
"""
GZH Design Converter - Automated WeChat article formatting.
Implements gzh-design skill's core capabilities programmatically.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import Counter
from dataclasses import dataclass, field
import jieba
import jieba.analyse


@dataclass
class ConvertResult:
    """Conversion result compatible with WeChatConverter."""
    html: str
    title: str
    digest: str
    images: list[str] = field(default_factory=list)


class GzhConverter:
    """Convert Markdown to WeChat HTML using gzh-design moyu-green theme."""
    
    # Theme colors
    PRIMARY = "#059669"
    PRIMARY_LIGHT = "#A7F3D0"
    HIGHLIGHT_BG = "#FDE68A"
    TEXT_MAIN = "#374151"
    TEXT_GRAY = "#9CA3AF"
    
    def __init__(self, skill_root: Path):
        self.skill_root = skill_root
        self.validate_script = skill_root / "scripts" / "validate_gzh_html.py"
        
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
            images=structure["images"]
        )
    
    def _parse_markdown(self, md_text: str) -> Dict:
        """Parse markdown structure."""
        lines = md_text.split("\n")
        
        structure = {
            "title": "",
            "intro_paragraphs": [],
            "sections": [],
            "images": []
        }
        
        current_section = None
        intro_done = False
        current_paragraph_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Title
            if stripped.startswith("# ") and not structure["title"]:
                structure["title"] = stripped[2:].strip()
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
            
            # Image
            img_match = re.match(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)', stripped)
            if img_match:
                img_url = img_match.group(2)
                if not img_url.startswith(("http://", "https://")):
                    structure["images"].append(img_url)
                
                # Save image as content item
                if current_section:
                    if current_paragraph_lines:
                        current_section["content"].append(self._join_paragraph(current_paragraph_lines))
                        current_paragraph_lines = []
                    current_section["content"].append({"type": "image", "url": img_url, "alt": img_match.group(1)})
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
        
        return structure
    
    def _join_paragraph(self, lines: List[str]) -> str:
        """Join paragraph lines into single text."""
        return " ".join(lines)
    
    def _extract_digest(self, structure: Dict) -> str:
        """Extract article digest from intro paragraphs."""
        if structure["intro_paragraphs"]:
            # Take first intro paragraph, max 100 chars
            first_para = structure["intro_paragraphs"][0]
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
            '<section style="max-width:677px;margin:0 auto;background:#ffffff;'
            'font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\',sans-serif;'
            'color:#374151;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">'
        )
        
        # Cover (simplified version without image)
        parts.append(self._generate_cover(structure))
        
        # Intro paragraphs
        if structure["intro_paragraphs"]:
            parts.append('<section style="margin:0 20px 24px;">')
            for para in structure["intro_paragraphs"]:
                parts.append(self._generate_paragraph(para, is_intro=True))
            parts.append('</section>')
        
        # Sections with auto-numbering
        for idx, section in enumerate(structure["sections"], 1):
            parts.append(self._generate_section(idx, section))
        
        # Divider
        parts.append(self._generate_divider())
        
        # Author signature
        parts.append(self._generate_signature(author, author_intro))
        
        # Container end
        parts.append('</section>')
        
        return "\n".join(parts)
    
    def _generate_cover(self, structure: Dict) -> str:
        """Generate cover component."""
        title = structure["title"]
        date = datetime.now().strftime("%Y-%m-%d")
        
        # Split title into lines (simple heuristic)
        if len(title) > 15:
            # Try to split at punctuation or spaces
            mid = len(title) // 2
            split_pos = mid
            for i in range(mid - 5, mid + 5):
                if i < len(title) and title[i] in "，。、 ":
                    split_pos = i + 1
                    break
            title_line1 = title[:split_pos].strip()
            title_line2 = title[split_pos:].strip()
        else:
            title_line1 = title
            title_line2 = ""
        
        # Extract key phrase for green highlight (simple: take last few chars of line1)
        if len(title_line1) > 8:
            green_word = title_line1[-4:]
            title_line1 = title_line1[:-4]
        else:
            green_word = ""
        
        return f'''
  <section style="margin:0 0 32px;background:#fff;border:1.5px solid rgba(5,150,105,0.15);border-radius:20px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06);width:100%;">
    <section style="padding:32px 28px 28px;">
      <section style="display:flex;align-items:center;gap:8px;margin-bottom:28px;">
        <span style="width:6px;height:6px;background:#059669;border-radius:50%;"><span leaf=""><br></span></span>
        <span style="font-size:11px;font-weight:700;letter-spacing:3px;color:#059669;"><span leaf="">科普辟谣</span></span>
        <section style="flex:1;height:1px;overflow:hidden;background:linear-gradient(to right,rgba(5,150,105,0.12),transparent);"><span leaf=""><br></span></section>
        <span style="font-size:10px;color:#D1D5DB;font-weight:600;"><span leaf="">{date}</span></span>
      </section>
      <section>
        <p style="font-size:24px;font-weight:900;color:#111827;margin:0;line-height:1.05;letter-spacing:-2px;">
          <span leaf="">{self._escape_html(title_line1)}</span>{"" if not green_word else f'<span style="color:#059669;"><span leaf="">{self._escape_html(green_word)}</span></span>'}
        </p>
        {"" if not title_line2 else f'<p style="font-size:24px;font-weight:900;color:#059669;margin:0 0 16px;line-height:1.05;letter-spacing:-2px;"><span leaf="">{self._escape_html(title_line2)}</span></p>'}
        <section style="width:48px;height:3px;background:linear-gradient(to right,#059669,#34D399);border-radius:2px;margin-bottom:12px;">
          <span leaf=""><br></span>
        </section>
      </section>
    </section>
    <section style="background:#059669;padding:12px 28px;display:flex;align-items:center;justify-content:space-between;">
      <p style="font-size:12px;color:rgba(255,255,255,0.9);margin:0;font-weight:600;letter-spacing:0.5px;">
        <span leaf="">MonkeyCode-AI 智能开发平台</span>
      </p>
    </section>
  </section>'''
    
    def _generate_section(self, number: int, section: Dict) -> str:
        """Generate section with auto-numbering."""
        title = section["title"]
        
        parts = [f'''
<section style="margin:0 0 32px;">
  <section style="padding:0 20px;margin-bottom:20px;">
    <section style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
      <section style="display:flex;align-items:center;justify-content:center;min-width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#059669,#34D399);box-shadow:0 2px 8px rgba(5,150,105,0.25);">
        <span style="font-size:15px;font-weight:900;color:#fff;"><span leaf="">{number:02d}</span></span>
      </section>
      <p style="font-size:18px;font-weight:800;color:#111827;margin:0;line-height:1.4;">
        <span leaf="">{self._escape_html(title)}</span>
      </p>
    </section>
  </section>''']
        
        # Section content
        parts.append('  <section style="margin:0 20px 14px;">')
        for item in section["content"]:
            if isinstance(item, dict) and item.get("type") == "image":
                parts.append(self._generate_image(item))
            else:
                parts.append(self._generate_paragraph(item))
        parts.append('  </section>')
        
        parts.append('</section>')
        
        return "\n".join(parts)
    
    def _generate_paragraph(self, text: str, is_intro: bool = False) -> str:
        """Generate paragraph with keyword highlighting."""
        # Mark keywords
        marked_text = self._mark_keywords(text)
        
        # Convert markdown syntax
        html_text = self._convert_inline_markdown(marked_text)
        
        return f'''    <p style="font-size:14px;line-height:1.9;color:#374151;margin:0 0 14px;">
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
        
        # Bold -> green underline (since it's keyword)
        html = re.sub(
            r'\*\*([^*]+)\*\*',
            r'<span style="border-bottom:2px solid #A7F3D0;font-weight:600;"><span leaf="">\1</span></span>',
            html
        )
        
        # Underline marker (from auto-detection) -> green underline
        html = re.sub(
            r'\+\+([^+]+)\+\+',
            r'<span style="border-bottom:2px solid #A7F3D0;font-weight:600;"><span leaf="">\1</span></span>',
            html
        )
        
        # Highlight -> yellow background
        html = re.sub(
            r'==([^=]+)==',
            r'<span style="background:#FDE68A;padding:2px 6px;border-radius:3px;"><span leaf="">\1</span></span>',
            html
        )
        
        # Code -> gray background
        html = re.sub(
            r'`([^`]+)`',
            r'<span style="background:#F3F4F6;color:#1F2937;padding:2px 6px;border-radius:4px;font-size:13px;font-weight:600;"><span leaf="">\1</span></span>',
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
    
    def _generate_divider(self) -> str:
        """Generate divider."""
        return '''
  <section style="margin:0 20px 24px;">
    <section style="display:flex;align-items:center;gap:8px;">
      <section style="flex:1;height:2px;background:linear-gradient(to right,#059669 15%,#6EE7B7 50%,transparent);opacity:0.3;"><span leaf=""><br></span></section>
      <span style="font-size:20px;"><span leaf="">✦</span></span>
      <section style="flex:1;height:2px;background:linear-gradient(to left,#059669 15%,#6EE7B7 50%,transparent);opacity:0.3;"><span leaf=""><br></span></section>
    </section>
  </section>'''
    
    def _generate_signature(self, author: Optional[str], author_intro: Optional[str]) -> str:
        """Generate author signature and CTA."""
        author_name = author or "{{作者名}}"
        intro = author_intro or "{{一句话简介，如：热衷于分享 AI 观察与干货}}"
        
        return f'''
  <section style="margin:0 20px 28px;padding:20px 18px;border-radius:12px;background:linear-gradient(135deg,#ECFDF5 0%,#F0FDF4 100%);border:1px solid #BBF7D0;">
    <p style="font-size:13px;color:#6B7280;margin:0 0 6px;line-height:1.7;">
      <span leaf="">我是 {self._escape_html(author_name)}，{self._escape_html(intro)}。</span>
    </p>
    <p style="font-size:13px;color:#6B7280;margin:0;line-height:1.7;">
      <span leaf="">如果你觉得今天这篇有收获，欢迎</span><span style="border-bottom:2px solid #A7F3D0;font-weight:600;"><span leaf="">点赞、在看、转发</span></span><span leaf="">三连，我们下篇见。</span>
    </p>
  </section>'''
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
    
    def validate(self, html_path: Path) -> bool:
        """Run validation script on generated HTML."""
        if not self.validate_script.exists():
            print(f"Warning: validation script not found: {self.validate_script}")
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
