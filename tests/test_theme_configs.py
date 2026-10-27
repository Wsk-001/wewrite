"""theme_configs 自适应主题回归测试。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))

from theme_configs import (
    analyze_content_hue,
    generate_adaptive_theme,
    CATEGORY_VARIANT,
    CONTENT_HUE_MAP,
    WEAK_SEMANTIC_SCORE,
)


def test_analyze_returns_four_tuple():
    cat, hue, score, runner = analyze_content_hue("火锅汤煮30分钟嘌呤翻10倍", "火锅 汤 涮 美食")
    assert cat == "饮食"
    assert 0.0 <= hue <= 1.0
    assert score > 0
    assert runner is None or runner in CONTENT_HUE_MAP


def test_analyze_default_category_no_runner():
    cat, hue, score, runner = analyze_content_hue("无特征标题", "普通文本内容")
    assert cat == "通用"
    assert score == 0
    assert runner is None


def test_generate_adaptive_theme_no_crash():
    """回归：analyze 返回 4 元组后 generate 必须同步解包，auto 主题不可崩。"""
    theme, report = generate_adaptive_theme("婚宴剩菜打包回家", "剩菜 打包 冰箱 亚硝酸盐 保存 加热")
    assert theme.identifier == "adaptive"
    assert theme.primary_color.startswith("#")
    assert "[自适应主题设计]" in report
    assert theme.style_variant == CATEGORY_VARIANT["食品安全"]


def test_strong_semantic_keeps_pure_hue():
    """强命中（score >= 8）保持纯语义色相，报告无混入标注。"""
    title = "火锅汤煮30分钟嘌呤翻10倍：想喝汤的先看这条时间线"
    content = "火锅 汤底 涮 美食 汤底 涮 美食 火锅 汤 嘌呤" * 2
    _, report = generate_adaptive_theme(title, content)
    assert "混入" not in report


def test_weak_semantic_blends_runner_up():
    """弱命中触发次类别 30% 混合，报告中体现混入来源。"""
    theme, report = generate_adaptive_theme("", "火锅 睡眠")
    cat, _, score, runner = analyze_content_hue("", "火锅 睡眠")
    assert score < WEAK_SEMANTIC_SCORE
    assert runner is not None
    assert f"混入 {runner} 30%" in report


def test_variant_mapping_exists_for_all_categories():
    """每个语义类别都有对应版式变体。"""
    for category in CONTENT_HUE_MAP:
        assert category in CATEGORY_VARIANT


def _solid_image(tmp_path, rgb):
    from PIL import Image
    p = tmp_path / "cover.jpg"
    Image.new("RGB", (32, 32), rgb).save(p)
    return p


def test_cover_hue_agreement_blends(tmp_path):
    """封面与语义色相接近（≤90°）时正常混合。"""
    # 心血管语义 0.97（349°），纯红封面 ~0°，圆周距离极小
    cover = _solid_image(tmp_path, (200, 30, 30))
    _, report = generate_adaptive_theme("心梗胸痛急救", "心梗 胸痛 急救 中风", cover)
    assert "语义+封面混合" in report


def test_cover_hue_conflict_ignored(tmp_path):
    """封面与语义色相相距 >90° 时忽略封面，保持纯语义色相。"""
    # 睡眠语义 0.62（223°），纯红封面 ~0°，冲突
    cover = _solid_image(tmp_path, (200, 30, 30))
    theme, report = generate_adaptive_theme("熬夜失眠", "熬夜 失眠 作息", cover)
    assert "冲突已忽略" in report


def test_cover_conflict_keeps_semantic_hue_value(tmp_path):
    """冲突场景下最终色相应落在语义类别色相附近（±6°）。"""
    import colorsys
    cover = _solid_image(tmp_path, (200, 30, 30))
    theme, report = generate_adaptive_theme("熬夜失眠", "熬夜 失眠 作息", cover)
    h = theme.primary_color
    r, g, b = int(h[1:3], 16)/255, int(h[3:5], 16)/255, int(h[5:7], 16)/255
    hue = colorsys.rgb_to_hls(r, g, b)[0]
    assert abs(hue - CONTENT_HUE_MAP["睡眠"][0]) < 0.017
