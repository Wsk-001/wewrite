#!/usr/bin/env python3
"""
ThemeConfig dataclass shared by core themes and the expanded theme library.
"""

from dataclasses import dataclass


@dataclass
class ThemeConfig:
    """Theme configuration data."""
    identifier: str  # moyu-green, red-white, etc.
    display_name: str
    
    # Core colors
    primary_color: str  # Main brand color
    primary_light: str  # Light variant (for gradients)
    accent_color: str  # Optional accent (default: primary_light)
    text_color: str  # Main text color
    secondary_color: str  # Secondary text / gray
    
    # Highlight styles
    highlight_bg: str  # Background for highlighted text
    underline_css: str  # CSS for keyword underline
    
    # Layout parameters (adaptive themes)
    section_margin: int = 32  # Section bottom margin (px)
    line_height: float = 1.75  # Body line-height
    title_weight: int = 900  # Title font-weight (700-900)
    body_weight: int = 400  # Body font-weight (400-500)

    # Typography (expanded library themes)
    font_family: str = ""  # Empty = default sans stack
    page_bg: str = "#ffffff"  # Article page background
    letter_spacing: float = 0.5  # Body letter-spacing (px)

    # Metadata
    suitable_for: str = ""  # Recommended use cases
    description: str = ""  # Brief description

    # 版式个性变体（决定 section 标题/列表/卡片的结构风格）
    # classic: 渐变圆角卡片；editorial: 大数字编辑风；clinical: 直角临床风
    style_variant: str = "classic"

    # 主题来源（core: 初始 7 套；library: 扩充样例库主题）
    source: str = "core"

    DEFAULT_SANS = (
        "-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
    )
    SERIF_STACK = (
        "'Noto Serif SC','Source Han Serif SC','Songti SC','SimSun',serif"
    )
    MONO_MIXED = (
        "'SF Mono',Consolas,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',monospace"
    )
    ROUNDED_STACK = (
        "'Yuanti SC','YouYuan','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
    )
