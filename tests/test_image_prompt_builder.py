import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))

from image_prompt_builder import BriefError, build_prompt, list_templates

import image_gen


def test_list_templates_covers_five_shapes():
    ids = {item["id"] for item in list_templates()}
    assert ids == {
        "infographic",
        "scientific-scale",
        "nature-science-poster",
        "illustration",
        "scene",
    }


def test_infographic_compiles_modules_and_text_allowlist():
    prompt = build_prompt(
        {
            "template": "flowchart",
            "subject": "血压为什么会波动",
            "title": "一天里的血压曲线",
            "modules": [
                {"title": "起床", "detail": "交感神经兴奋", "icon": "太阳"},
                {"title": "上午", "detail": "活动后升高"},
                {"title": "午后", "detail": "短暂回落"},
                {"title": "夜间", "detail": "睡眠时下降"},
            ],
        }
    )
    assert "画面类型：信息图" in prompt
    assert "信息结构：流程" in prompt
    assert "模块标题「起床」" in prompt
    assert "图中文字：只允许逐字出现" in prompt
    assert "「睡眠时下降」" in prompt
    assert "画面比例：4:3" in prompt


def test_scientific_scale_requires_four_steps():
    brief = {
        "template": "scientific-scale",
        "subject": "颗粒物沉积",
        "scale_steps": [{"name": "鼻腔"}, {"name": "气管"}, {"name": "肺泡"}],
    }
    with pytest.raises(BriefError, match="scale_steps"):
        build_prompt(brief)

    brief["scale_steps"].append({"name": "血液", "detail": "可入血", "unit": "0.1 微米"})
    prompt = build_prompt(brief)
    assert "尺度数量：4 个" in prompt
    assert "「0.1 微米」" in prompt
    assert "画面比例：3:4" in prompt


def test_poster_rejects_more_than_four_key_points():
    brief = {
        "template": "nature-science-poster",
        "subject": "睡眠",
        "key_points": ["入睡", "深睡", "快速眼动", "醒来", "白天"],
    }
    with pytest.raises(BriefError, match="key_points"):
        build_prompt(brief)


def test_illustration_without_text_declares_no_text():
    prompt = build_prompt(
        {
            "template": "illustration",
            "subject": "熬夜后的修复",
            "scene": "清晨窗边一杯温水",
        }
    )
    assert "画面不出现任何文字" in prompt
    assert "1. 画面出现乱码" in prompt


def test_scene_requires_action_and_environment():
    with pytest.raises(BriefError, match="action"):
        build_prompt({"template": "scene", "subject": "测血压", "environment": "客厅"})


def test_unknown_template_and_bad_fields_raise():
    with pytest.raises(BriefError, match="unknown template"):
        build_prompt({"template": "no-such", "subject": "x"})
    with pytest.raises(BriefError, match="subject"):
        build_prompt({"template": "cover"})
    with pytest.raises(BriefError, match="modules"):
        build_prompt(
            {"template": "infographic", "subject": "x", "modules": [{"title": "只有一条"}]}
        )


def test_user_avoid_list_is_appended_and_deduped():
    prompt = build_prompt(
        {
            "template": "illustration",
            "subject": "x",
            "scene": "y",
            "avoid": ["水印、签名、二维码、无关 logo 或手机界面", "出现真实医生姓名"],
        }
    )
    assert "出现真实医生姓名" in prompt
    assert prompt.count("水印、签名、二维码") == 1


def test_generate_image_compiles_brief_before_calling_provider(monkeypatch):
    captured = {}

    class FakeProvider:
        provider_key = "fake"

        def resolve_size(self, size):
            return size

        def generate(self, prompt, size):
            captured["prompt"] = prompt
            return b"image"

    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [FakeProvider()])
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)

    out = Path("/tmp/opencode/brief-single.jpg")
    image_gen.generate_image(
        "",
        str(out),
        config={"image": {}},
        brief={"template": "cover", "subject": "每天走六千步"},
    )
    assert "主题：每天走六千步" in captured["prompt"]
    assert out.exists()


def test_batch_accepts_brief_task(monkeypatch):
    captured = []

    class FakeProvider:
        provider_key = "fake"

        def resolve_size(self, size):
            return size

        def generate(self, prompt, size):
            captured.append(prompt)
            return b"image"

    monkeypatch.setattr(image_gen, "_build_provider_chain", lambda cfg: [FakeProvider()])
    monkeypatch.setattr(image_gen, "_warn_size_mismatch", lambda *a: None)
    monkeypatch.setattr(image_gen, "_center_crop_to_ratio", lambda b, s: b)
    monkeypatch.setattr(image_gen, "_ensure_output_format", lambda b, p: b)

    tasks = [
        {
            "output": "/tmp/opencode/brief-batch.jpg",
            "brief": {"template": "cover", "subject": "标题"},
        }
    ]
    results = image_gen.generate_images_batch(tasks, config={"image": {}}, max_workers=1)
    assert results["ok"]
    assert "画面类型：单主题科普封面" in captured[0]
