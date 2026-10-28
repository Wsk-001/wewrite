"""gzh_converter 表格/引用/有序列表/链接渲染与残留检测测试。"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))

from gzh_converter import GzhConverter


def make_converter():
    return GzhConverter("moyu-green")


def visible_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", " ", text)


def test_table_rendered_with_theme_header():
    conv = make_converter()
    md = "# 标题\n\n| 项目 | 数值 |\n| --- | --- |\n| 血钠 | 135 |\n| 体温 | 37 |\n"
    r = conv.convert(md)
    assert "<table" in r.html
    assert "<th" in r.html and "项目" in r.html
    # 斑马纹：第二数据行有主题浅色背景
    assert r.html.count('background:' + conv._rgba(0.05) + '"') + r.html.count(f'background:{conv._rgba(0.05)};') >= 1
    assert "血钠" in r.html and "135" in r.html
    assert r.residues == []


def test_invalid_table_falls_back_and_flags_residue():
    conv = make_converter()
    # 缺分隔行 → 回退为纯文本，残留检测应拦下
    md = "# 标题\n\n| 项目 | 数值 |\n| 血钠 | 135 |\n"
    r = conv.convert(md)
    assert "<table" not in r.html
    assert any("竖线" in x for x in r.residues)


def test_ordered_list_keeps_numbers():
    conv = make_converter()
    md = "# 标题\n\n1. 第一步冷藏\n2. 第二步分装\n3. 第三步加热\n"
    r = conv.convert(md)
    text = visible_text(r.html)
    assert "1." in text and "2." in text and "3." in text
    assert "•第一步" not in text
    assert r.residues == []


def test_unordered_list_keeps_bullet():
    conv = make_converter()
    md = "# 标题\n\n- 项目一\n- 项目二\n"
    r = conv.convert(md)
    text = visible_text(r.html)
    assert "•" in text and "项目一" in text
    assert r.residues == []


def test_blockquote_rendered_as_card():
    conv = make_converter()
    md = "# 标题\n\n> 引用内容测试\n"
    r = conv.convert(md)
    assert "border-left" in r.html
    assert "引用内容测试" in visible_text(r.html)
    assert not re.search(r"(?:^|\n)\s*>", visible_text(r.html))
    assert r.residues == []


def test_inline_link_converted():
    conv = make_converter()
    md = "# 标题\n\n参见 [指南原文](https://example.com/guide)\n"
    r = conv.convert(md)
    assert "指南原文" in r.html
    assert "](https" not in r.html
    assert r.residues == []


def test_residue_checker_detects_injected_residues():
    conv = make_converter()
    dirty = "<p>a | b **c** ==d== `e` ![f](g) [h](i)</p><p>:::x</p>"
    residues = conv._check_markdown_residue(dirty)
    assert any("竖线" in r for r in residues)
    assert any("加粗" in r for r in residues)
    assert any("高亮" in r for r in residues)
    assert any("代码" in r for r in residues)
    assert any("图片" in r for r in residues)
    assert any("链接" in r for r in residues)
    assert any("容器" in r for r in residues)


def test_clean_html_no_false_positive():
    conv = make_converter()
    clean = "<p>体温 37.5℃，血压 140 mmHg，话题 #健康科普# 相关。</p>"
    assert conv._check_markdown_residue(clean) == []


def test_summary_card_converts_inline_markdown():
    """回归：summary 卡曾用纯文本渲染导致 ** 字面上线（伤眼文章实际事故）。"""
    conv = make_converter()
    md = "# 标题\n\n:::summary\n**一页纸记住** 核心提示\n:::\n"
    r = conv.convert(md)
    text = visible_text(r.html)
    assert "**" not in text
    assert "一页纸记住" in text
    assert r.residues == []


def test_end_to_end_smoke_all_elements():
    conv = make_converter()
    md = (
        "# 测试标题\n\n"
        "开头段落，含 **重点** 与 ==高亮==。\n\n"
        "> 引用一句话\n\n"
        "- 无序项\n"
        "1. 有序项一\n"
        "2. 有序项二\n\n"
        "| 项目 | 数值 |\n"
        "| --- | --- |\n"
        "| 血钠 | 135 |\n\n"
        "## 第一节\n\n"
        "正文段落。\n\n"
        ":::summary\n一句话版本内容\n:::\n"
    )
    r = conv.convert(md)
    assert r.residues == []
    assert "<table" in r.html
    assert "border-left" in r.html
    text = visible_text(r.html)
    assert "1." in text and "2." in text
    assert "一句话版本" in text


def test_all_container_types_preserve_content():
    """回归：:::callout / :::highlight / :::timeline / :::quote 曾被静默丢弃。"""
    conv = make_converter()
    md = (
        "# 标题\n\n"
        "## 第一节\n\n"
        ":::callout 关键提醒\n"
        "- 第一条要点\n"
        "- 第二条要点\n"
        ":::\n\n"
        ":::highlight 重点结论\n"
        "这里是正文\n"
        ":::\n\n"
        ":::timeline\n"
        "72小时内冷敷\n"
        "48小时后热敷\n"
        ":::\n\n"
        ":::quote\n"
        "站得高才能看得远\n"
        ":::\n"
    )
    r = conv.convert(md)
    text = visible_text(r.html)
    for kw in ["关键提醒", "第一条要点", "第二条要点", "重点结论", "这里是正文",
               "72小时内冷敷", "48小时后热敷", "站得高才能看得远"]:
        assert kw in text, f"容器内容丢失: {kw}"
    assert ":::" not in text
    assert r.residues == []


def test_dialogue_container_renders_both_speakers():
    conv = make_converter()
    md = (
        "# 标题\n\n"
        ":::dialogue\n"
        "读者：崴脚后先冷敷还是热敷？\n"
        "医生：刚受伤的48小时内先冷敷。\n"
        ":::\n"
    )
    r = conv.convert(md)
    text = visible_text(r.html)
    assert "读者" in text and "医生" in text
    assert "崴脚后先冷敷还是热敷" in text
    assert "刚受伤的48小时内先冷敷" in text
    assert ":::" not in text
    assert r.residues == []
