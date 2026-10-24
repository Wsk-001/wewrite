#!/usr/bin/env python3
"""
WeWrite 公众号 HTML 渲染器（方案B实验版）
从 Markdown 生成符合微信公众号规范的 HTML，复用 gzh-design-skill 的组件库精简版

用法:
    python3 scripts/render_gzh_html.py input.md output.html
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# 设计变量（从 visual-guidelines.yaml 提取）
PRIMARY_COLOR = "#059669"
PRIMARY_LIGHT = "#A7F3D0"
HIGHLIGHT_YELLOW = "#FDE68A"
TITLE_COLOR = "#111827"
BODY_COLOR = "#374151"
SECONDARY_COLOR = "#6B7280"
BORDER_COLOR = "#D1D5DB"
BG_LIGHT = "#F9FAFB"

FONT_FAMILY = "-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"


def render_global_container(content: str) -> str:
    """全局容器"""
    return f"""<section style="max-width:677px;margin:0 auto;background:#ffffff;font-family:{FONT_FAMILY};color:{BODY_COLOR};line-height:1.75;letter-spacing:0.5px;overflow-x:hidden;">
{content}
</section>"""


def render_h1(text: str) -> str:
    """文章标题"""
    return f"""<section style="margin:0 0 24px;padding:20px 20px 16px;">
  <p style="font-size:26px;font-weight:900;color:{TITLE_COLOR};margin:0;line-height:1.3;letter-spacing:-1px;">
    <span leaf="">{text}</span>
  </p>
</section>"""


def render_h2(text: str, number: str) -> str:
    """章节标题（带编号）"""
    return f"""<section style="margin:32px 20px 16px;display:flex;align-items:center;gap:12px;">
  <span style="font-size:16px;font-weight:900;color:{PRIMARY_COLOR};min-width:36px;">
    <span leaf="">{number}</span>
  </span>
  <p style="font-size:20px;font-weight:800;color:{TITLE_COLOR};margin:0;line-height:1.4;">
    <span leaf="">{text}</span>
  </p>
</section>"""


def render_paragraph(text: str) -> str:
    """正文段落"""
    return f"""<p style="margin:0 20px 16px;font-size:14px;color:{BODY_COLOR};line-height:1.9;letter-spacing:0.5px;">
  <span leaf="">{text}</span>
</p>"""


def render_image(alt: str, src: str) -> str:
    """图片"""
    caption = ""
    if alt:
        caption = f"""<p style="margin:8px 20px 0;font-size:12px;color:{SECONDARY_COLOR};text-align:center;line-height:1.6;">
  <span leaf="">{alt}</span>
</p>"""
    return f"""<section style="margin:20px 0;">
  <img src="{src}" style="max-width:100%;height:auto;display:block;margin:0 auto;border-radius:8px;" />
  {caption}
</section>"""


def render_divider() -> str:
    """分割线"""
    return f"""<section style="margin:24px 20px;height:1px;background:{BORDER_COLOR};">
  <span leaf=""><br></span>
</section>"""


def process_inline_formatting(text: str) -> str:
    """处理行内格式：**加粗**、==高亮==、`代码`，并转换全角标点"""
    # 保护代码块内容（稍后恢复，避免标点转换）
    code_blocks = []
    def save_code(match):
        code_blocks.append(match.group(1))
        return f'<<<CODE_{len(code_blocks)-1}>>>'
    text = re.sub(r'`(.+?)`', save_code, text)
    
    # **加粗** -> 主色加粗
    text = re.sub(
        r'\*\*(.+?)\*\*',
        rf'<strong style="color:{PRIMARY_COLOR};font-weight:700;"><span leaf="">\1</span></strong>',
        text
    )
    # ==高亮== -> 黄色浅底
    text = re.sub(
        r'==(.+?)==',
        rf'<span style="background:{HIGHLIGHT_YELLOW};padding:2px 4px;border-radius:3px;"><span leaf="">\1</span></span>',
        text
    )
    # 恢复代码块并渲染
    for i, code_content in enumerate(code_blocks):
        placeholder = f'<<<CODE_{i}>>>'
        code_html = f'<code style="font-family:Menlo,Monaco,Consolas,monospace;background:#F3F4F6;padding:2px 6px;border-radius:3px;font-size:13px;color:#DC2626;"><span leaf="">{code_content}</span></code>'
        text = text.replace(placeholder, code_html)
    
    return text


def parse_markdown(md_content: str) -> str:
    """解析 Markdown 并渲染为 HTML"""
    lines = md_content.strip().split('\n')
    html_parts = []
    h2_count = 0
    i = 0
    h1_title = ""
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 空行跳过
        if not line:
            i += 1
            continue
        
        # H1 标题
        if line.startswith('# ') and not h1_title:
            h1_title = line[2:].strip()
            html_parts.append(render_h1(h1_title))
            i += 1
            continue
        
        # H2 章节标题
        if line.startswith('## '):
            h2_count += 1
            title = line[3:].strip()
            # 自动识别末章（包含"到底能不能"、"怎么办"、"总结"等）
            is_last = any(kw in title for kw in ['到底', '怎么办', '总结', '结语', '最后'])
            number = "∞" if is_last else f"{h2_count:02d}"
            html_parts.append(render_h2(title, number))
            i += 1
            continue
        
        # 分割线
        if line in ['---', '***', '___']:
            html_parts.append(render_divider())
            i += 1
            continue
        
        # 图片
        img_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
        if img_match:
            alt, src = img_match.groups()
            html_parts.append(render_image(alt, src))
            i += 1
            continue
        
        # 列表项（简化处理：转为缩进段落）
        if line.startswith('- ') or re.match(r'^\d+\.\s', line):
            item_text = re.sub(r'^[-\d]+\.\s*', '', line)
            item_text = process_inline_formatting(item_text)
            # 不用 position:absolute，直接用前缀符号
            html_parts.append(f"""<p style="margin:0 20px 12px 40px;font-size:14px;color:{BODY_COLOR};line-height:1.9;">
  <span style="color:{PRIMARY_COLOR};margin-right:8px;"><span leaf="">·</span></span>
  <span leaf="">{item_text}</span>
</p>""")
            i += 1
            continue
        
        # 普通段落
        paragraph_text = process_inline_formatting(line)
        html_parts.append(render_paragraph(paragraph_text))
        i += 1
    
    return render_global_container('\n'.join(html_parts))


def main():
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} input.md output.html")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    md_content = input_file.read_text(encoding='utf-8')
    html_content = parse_markdown(md_content)
    
    output_file.write_text(html_content, encoding='utf-8')
    print(f"✅ HTML 已生成: {output_file}")
    print(f"   可手动粘贴到公众号编辑器（样式全内联，不掉格式）")


if __name__ == '__main__':
    main()
