#!/usr/bin/env python3
"""
Adapter for gzh-design skill to integrate with cli.py publish command.
"""

import subprocess
import re
from pathlib import Path
from typing import List, Tuple


class GzhDesignAdapter:
    """Adapter to call gzh-design skill from Python."""
    
    def __init__(self, skill_root: Path):
        self.skill_root = skill_root
        self.validate_script = skill_root / "scripts" / "validate_gzh_html.py"
        self.theme_index = skill_root / "references" / "theme-index.md"
    
    def convert_markdown(
        self, 
        md_path: Path, 
        output_dir: Path,
        theme: str = "moyu-green",
        author_name: str = None,
        author_intro: str = None
    ) -> Tuple[Path, List[str]]:
        """
        Convert markdown to WeChat HTML using gzh-design components.
        
        Returns:
            (html_path, image_refs) where image_refs are local image paths
        """
        md_text = md_path.read_text(encoding="utf-8")
        
        # Extract images
        image_refs = self._extract_images(md_text)
        
        # Parse markdown structure
        structure = self._parse_markdown(md_text)
        
        # Generate HTML using theme components
        html_content = self._generate_html(structure, theme, author_name, author_intro)
        
        # Save HTML
        output_path = output_dir / f"{md_path.stem}_排版_{theme}.html"
        output_path.write_text(html_content, encoding="utf-8")
        
        # Validate
        self._validate(output_path)
        
        return output_path, image_refs
    
    def _extract_images(self, md_text: str) -> List[str]:
        """Extract image references from markdown."""
        pattern = r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)"
        matches = re.finditer(pattern, md_text)
        return [m.group(2) for m in matches if not m.group(2).startswith(("http://", "https://"))]
    
    def _parse_markdown(self, md_text: str) -> dict:
        """Parse markdown structure."""
        lines = md_text.split("\n")
        
        structure = {
            "title": "",
            "intro_paragraphs": [],
            "sections": [],
            "images": {}
        }
        
        current_section = None
        intro_done = False
        
        for line in lines:
            line = line.strip()
            
            # Title
            if line.startswith("# ") and not structure["title"]:
                structure["title"] = line[2:].strip()
                continue
            
            # Section
            if line.startswith("## "):
                intro_done = True
                current_section = {
                    "title": line[3:].strip(),
                    "content": []
                }
                structure["sections"].append(current_section)
                continue
            
            # Content
            if line and not intro_done:
                structure["intro_paragraphs"].append(line)
            elif line and current_section:
                current_section["content"].append(line)
        
        return structure
    
    def _generate_html(self, structure: dict, theme: str, author_name: str, author_intro: str) -> str:
        """Generate HTML from structure using theme components."""
        # This is a simplified version. In production, you should:
        # 1. Read theme components from references/theme-{theme}.md
        # 2. Apply component templates
        # 3. Handle all markdown syntax
        
        # For now, return a basic HTML structure
        # You would integrate the actual gzh-design component generation here
        
        html_parts = ['<section style="max-width:677px;margin:0 auto;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Hiragino Sans GB\',\'Microsoft YaHei\',sans-serif;color:#374151;line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">']
        
        # Add sections
        for i, section in enumerate(structure["sections"], 1):
            html_parts.append(f'  <!-- Section {i:02d} -->')
            # Component generation would go here
        
        # Author signature
        author_placeholder = author_name or "{{作者名}}"
        intro_placeholder = author_intro or "{{一句话简介}}"
        html_parts.append(f'  <!-- Author: {author_placeholder}, {intro_placeholder} -->')
        
        html_parts.append('</section>')
        
        return "\n".join(html_parts)
    
    def _validate(self, html_path: Path):
        """Run validation script."""
        if not self.validate_script.exists():
            print(f"Warning: validation script not found: {self.validate_script}")
            return
        
        result = subprocess.run(
            ["python3", str(self.validate_script), str(html_path)],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
