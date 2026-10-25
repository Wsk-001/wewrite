#!/usr/bin/env python3
"""
Theme configurations for GZH Design themes.
Extracted from gzh-design skill references.
"""

from dataclasses import dataclass
from typing import Optional


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
    
    # Metadata
    suitable_for: str  # Recommended use cases
    description: str  # Brief description


# Theme definitions
THEMES = {
    "moyu-green": ThemeConfig(
        identifier="moyu-green",
        display_name="摸鱼绿",
        primary_color="#059669",
        primary_light="#A7F3D0",
        accent_color="#34D399",
        text_color="#374151",
        secondary_color="#9CA3AF",
        highlight_bg="#FDE68A",
        underline_css="border-bottom:2px solid #A7F3D0;font-weight:600;",
        suitable_for="教程、测评、清单、工具盘点、知识整理、方法论拆解",
        description="翡翠绿渐变，适合信息密度高的内容"
    ),
    
    "red-white": ThemeConfig(
        identifier="red-white",
        display_name="红白色系",
        primary_color="#DC2626",
        primary_light="#FCA5A5",
        accent_color="#EF4444",
        text_color="#374151",
        secondary_color="#9CA3AF",
        highlight_bg="#FEF3C7",
        underline_css="border-bottom:2px solid #FCA5A5;font-weight:600;",
        suitable_for="新闻快讯、观点评论、热点解读、重要通知",
        description="正红色调，适合需要强调紧急性或重要性的内容"
    ),
    
    "graphite-minimal": ThemeConfig(
        identifier="graphite-minimal",
        display_name="石墨极简风",
        primary_color="#374151",
        primary_light="#9CA3AF",
        accent_color="#6B7280",
        text_color="#1F2937",
        secondary_color="#6B7280",
        highlight_bg="#F3F4F6",
        underline_css="border-bottom:2px solid #9CA3AF;font-weight:600;",
        suitable_for="深度分析、专业报告、学术内容、严肃议题",
        description="纯黑白灰，适合注重内容而非视觉装饰的场景"
    ),
    
    "zen-whitespace": ThemeConfig(
        identifier="zen-whitespace",
        display_name="留白禅意风",
        primary_color="#8B7355",
        primary_light="#D4C4B0",
        accent_color="#B8A490",
        text_color="#4B5563",
        secondary_color="#9CA3AF",
        highlight_bg="#FEF3E2",
        underline_css="border-bottom:1px solid #D4C4B0;font-weight:600;",
        suitable_for="随笔、散文、生活分享、情感内容、个人思考",
        description="大量留白 + 柔和土棕色，适合文学性、慢阅读内容"
    ),
    
    "moyu-ticket": ThemeConfig(
        identifier="moyu-ticket",
        display_name="摸鱼票据风",
        primary_color="#0284C7",
        primary_light="#7DD3FC",
        accent_color="#38BDF8",
        text_color="#374151",
        secondary_color="#6B7280",
        highlight_bg="#FEF3C7",
        underline_css="border-bottom:2px dashed #7DD3FC;font-weight:600;",
        suitable_for="产品发布、活动通知、优惠信息、邀请函",
        description="天空蓝 + 虚线元素，票根撕裂风格，适合事件类内容"
    ),
    
    "olive-journal": ThemeConfig(
        identifier="olive-journal",
        display_name="橄榄手记",
        primary_color="#65A30D",
        primary_light="#BEF264",
        accent_color="#84CC16",
        text_color="#374151",
        secondary_color="#78716C",
        highlight_bg="#FEF3C7",
        underline_css="border-bottom:2px solid #BEF264;font-weight:600;",
        suitable_for="日记式内容、个人成长、学习笔记、周报月报",
        description="橄榄绿 + 日记本元素，适合定期更新的系列内容"
    ),
}


def get_theme(identifier: str) -> Optional[ThemeConfig]:
    """Get theme configuration by identifier."""
    return THEMES.get(identifier)


def list_themes() -> dict:
    """List all available themes."""
    return {k: {"name": v.display_name, "desc": v.description, "for": v.suitable_for} 
            for k, v in THEMES.items()}
