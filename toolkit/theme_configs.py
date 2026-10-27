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
    
    # Layout parameters (adaptive themes)
    section_margin: int = 32  # Section bottom margin (px)
    line_height: float = 1.75  # Body line-height
    title_weight: int = 900  # Title font-weight (700-900)
    body_weight: int = 400  # Body font-weight (400-500)
    
    # Metadata
    suitable_for: str = ""  # Recommended use cases
    description: str = ""  # Brief description

    # 版式个性变体（决定 section 标题/列表/卡片的结构风格）
    # classic: 渐变圆角卡片；editorial: 大数字编辑风；clinical: 直角临床风
    style_variant: str = "classic"


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

    "hotpot-warm": ThemeConfig(
        identifier="hotpot-warm",
        display_name="汤底暖橙",
        primary_color="#EA580C",
        primary_light="#FED7AA",
        accent_color="#F97316",
        text_color="#374151",
        secondary_color="#9CA3AF",
        highlight_bg="#FDE68A",
        underline_css="border-bottom:2px solid #FED7AA;font-weight:600;",
        suitable_for="火锅、美食、饮食健康、暖调生活科普",
        description="汤底暖橙渐变，为饮食健康类内容定制"
    ),
}


# 内容语义 → 色相 映射（HSL hue 0-1 范围）
CONTENT_HUE_MAP = {
    "饮食": (0.06, ["火锅", "美食", "汤", "饮食", "烹饪", "三餐", "食材", "吃喝", "锅底", "涮", "外卖"]),
    "食品安全": (0.47, ["食品安全", "剩菜", "打包", "冰箱", "冷藏", "冷冻", "保鲜", "细菌", "变质", "中毒", "保存", "保质期", "加热", "微波", "亚硝酸盐", "沙门氏菌", "分装", "隔夜"]),
    "节庆": (0.985, ["婚宴", "婚礼", "年夜饭", "春节", "团圆", "过节", "宴席", "喜庆"]),
    "心血管": (0.97, ["心血管", "血压", "心脏", "心梗", "中风", "急救", "胸痛"]),
    "睡眠": (0.62, ["睡眠", "熬夜", "失眠", "作息", "褪黑素", "打鼾", "睡眠质量"]),
    "心理": (0.75, ["心理", "情绪", "焦虑", "抑郁", "压力", "成瘾", "手机依赖", "心境"]),
    "眼科": (0.48, ["眼科", "视力", "近视", "眼睛", "屏幕", "用眼", "干眼"]),
    "体检": (0.53, ["体检", "筛查", "结节", "癌症", "肿瘤", "早筛", "指标"]),
    "呼吸": (0.52, ["呼吸", "感冒", "流感", "咳嗽", "肺", "气管", "哮喘"]),
    "骨骼": (0.33, ["骨骼", "久坐", "体态", "腰椎", "颈椎", "关节", "骨质", "运动"]),
    "皮肤": (0.05, ["皮肤", "脱发", "痘痘", "湿疹", "护肤", "光老化"]),
    "用药": (0.58, ["疫苗", "用药", "药物", "抗生素", "副作用", "处方"]),
}

# 类别 → 版式个性变体
CATEGORY_VARIANT = {
    "食品安全": "clinical",
    "体检": "clinical",
    "用药": "clinical",
    "心血管": "clinical",
    "呼吸": "clinical",
    "眼科": "clinical",
    "骨骼": "clinical",
    "饮食": "classic",
    "节庆": "classic",
    "皮肤": "classic",
    "睡眠": "editorial",
    "心理": "editorial",
    "通用": "editorial",
}

# 语义得分低于该值视为弱命中，触发向次类别的色相混合
WEAK_SEMANTIC_SCORE = 8


def _hue_distance(h1: float, h2: float) -> float:
    """圆周上的色相距离（0-0.5，0.5 即 180°）。"""
    return min(abs(h1 - h2), 1.0 - abs(h1 - h2))


def analyze_content_hue(title: str, content: str) -> tuple:
    """分析内容语义，返回 (category, base_hue, score, runner_up_category)。"""
    from collections import Counter
    scores = Counter()
    title_text = title or ""

    for category, (hue, keywords) in CONTENT_HUE_MAP.items():
        for kw in keywords:
            if kw in title_text:
                scores[category] += 3
            hits = content.count(kw)
            if hits:
                scores[category] += min(hits, 8)

    if not scores:
        return "通用", 0.43, 0, None  # 默认品牌绿 hue

    ranked = scores.most_common(2)
    best_cat, top_score = ranked[0]
    base_hue = CONTENT_HUE_MAP[best_cat][0]
    runner_up = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 else None
    return best_cat, base_hue, top_score, runner_up


def extract_cover_hue(cover_path) -> Optional[float]:
    """从封面图提取主色相（HSL hue 0-1）。"""
    try:
        from PIL import Image
        import colorsys, math
        
        img = Image.open(cover_path).convert('RGB').resize((64, 64))
        pixels = list(img.getdata())
        
        saturated = []
        for r, g, b in pixels:
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            if s > 0.35 and 0.25 < l < 0.75:
                saturated.append((h, s, l))
        
        if len(saturated) < len(pixels) * 0.08:
            return None
        
        x = sum(math.cos(2 * math.pi * h) * s for h, s, l in saturated)
        y = sum(math.sin(2 * math.pi * h) * s for h, s, l in saturated)
        if abs(x) < 1e-6 and abs(y) < 1e-6:
            return None
        
        hue = (math.atan2(y, x) % (2 * math.pi)) / (2 * math.pi)
        return hue
    except Exception:
        return None


def generate_adaptive_theme(title: str, content: str, cover_path=None) -> tuple:
    """根据内容自动生成专属主题配色。返回 (ThemeConfig, design_report_str)。"""
    import colorsys
    import math

    # 1. 语义色相（含次类别）
    category, semantic_hue, score, runner_up = analyze_content_hue(title, content)

    # 1.5 语义弱命中（score < 8）时向次类别圆周加权 70/30 靠拢，
    # 避免小众选题落在主类别默认色相上；强命中保持纯语义色相（与已验收文章一致）
    blend_note = ""
    if runner_up and score < WEAK_SEMANTIC_SCORE:
        runner_hue = CONTENT_HUE_MAP[runner_up][0]
        x = 0.7 * math.cos(2 * math.pi * semantic_hue) + 0.3 * math.cos(2 * math.pi * runner_hue)
        y = 0.7 * math.sin(2 * math.pi * semantic_hue) + 0.3 * math.sin(2 * math.pi * runner_hue)
        semantic_hue = (math.atan2(y, x) % (2 * math.pi)) / (2 * math.pi)
        blend_note = f"（弱语义，混入 {runner_up} 30%）"
    style_variant = CATEGORY_VARIANT.get(category, "classic")

    # 2. 封面主色混合（仅在封面与语义色相圆周距离 ≤ 90° 时生效：
    # 封面只做精修，冲突时保持纯语义色相，避免 50/50 中点两头不靠）
    cover_hue = extract_cover_hue(cover_path) if cover_path else None
    if cover_hue is not None and _hue_distance(semantic_hue, cover_hue) <= 0.25:
        x = math.cos(2*math.pi*semantic_hue) + math.cos(2*math.pi*cover_hue)
        y = math.sin(2*math.pi*semantic_hue) + math.sin(2*math.pi*cover_hue)
        final_hue = (math.atan2(y, x) % (2*math.pi)) / (2*math.pi)
        hue_source = "语义+封面混合"
    elif cover_hue is not None:
        final_hue = semantic_hue
        hue_source = f"语义（封面色相 {int(cover_hue*360)}° 冲突已忽略）"
    else:
        final_hue = semantic_hue
        hue_source = "语义"
    hue_source += blend_note

    # 3. 饱和度/明度：内容严肃度
    serious_words = ["深度", "分析", "报告", "数据", "指南", "研究"]
    serious_hits = sum(1 for w in serious_words if w in title or content.count(w) > 0)
    saturation = 0.55 if serious_hits >= 2 else 0.72
    lightness = 0.44
    
    # 3.5 排版参数适配
    layout_rules = {
        "饮食": {"margin": 36, "line_height": 1.85, "title_weight": 800, "body_weight": 400},
        "心血管": {"margin": 28, "line_height": 1.75, "title_weight": 900, "body_weight": 500},
        "睡眠": {"margin": 34, "line_height": 1.8, "title_weight": 800, "body_weight": 400},
        "心理": {"margin": 34, "line_height": 1.8, "title_weight": 800, "body_weight": 400},
        "眼科": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "体检": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "呼吸": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "骨骼": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "皮肤": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "用药": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
        "通用": {"margin": 32, "line_height": 1.75, "title_weight": 900, "body_weight": 400},
    }
    layout = layout_rules.get(category, layout_rules["通用"])
    
    # 4. 生成色板
    r, g, b = colorsys.hls_to_rgb(final_hue, lightness, saturation)
    primary = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
    
    r2, g2, b2 = colorsys.hls_to_rgb(final_hue, 0.85, saturation * 0.48)
    primary_light = f"#{int(r2*255):02X}{int(g2*255):02X}{int(b2*255):02X}"
    
    accent_hue = (final_hue + 0.04) % 1.0
    r3, g3, b3 = colorsys.hls_to_rgb(accent_hue, min(lightness + 0.05, 0.52), saturation)
    accent = f"#{int(r3*255):02X}{int(g3*255):02X}{int(b3*255):02X}"
    
    hl_hue = (final_hue - 0.02) % 1.0
    r4, g4, b4 = colorsys.hls_to_rgb(hl_hue, 0.91, 0.62)
    highlight_bg = f"#{int(r4*255):02X}{int(g4*255):02X}{int(b4*255):02X}"
    
    underline_color = primary_light
    
    theme = ThemeConfig(
        identifier="adaptive",
        display_name=f"自适应-{category}",
        primary_color=primary,
        primary_light=primary_light,
        accent_color=accent,
        text_color="#374151",
        secondary_color="#9CA3AF",
        highlight_bg=highlight_bg,
        underline_css=f"border-bottom:2px solid {underline_color};font-weight:600;",
        section_margin=layout["margin"],
        line_height=layout["line_height"],
        title_weight=layout["title_weight"],
        body_weight=layout["body_weight"],
        style_variant=style_variant,
        suitable_for=f"内容驱动设计（{category}）",
        description=f"根据内容自动生成（色相源: {hue_source}）"
    )

    design_report = (
        f"[自适应主题设计]\n"
        f"  类别: {category}（得分 {score}）\n"
        f"  色相: {hue_source} → {int(final_hue*360)}°\n"
        f"  配色: 主色 {primary} / 浅色 {primary_light} / 强调 {accent}\n"
        f"  版式: {style_variant}\n"
        f"  排版: 间距 {layout['margin']}px / 行高 {layout['line_height']} / 标题 {layout['title_weight']} / 正文 {layout['body_weight']}"
    )
    
    return theme, design_report


def get_theme(identifier: str) -> Optional[ThemeConfig]:
    """Get theme configuration by identifier."""
    return THEMES.get(identifier)


def list_themes() -> dict:
    """List all available themes."""
    return {k: {"name": v.display_name, "desc": v.description, "for": v.suitable_for} 
            for k, v in THEMES.items()}
