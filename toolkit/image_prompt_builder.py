#!/usr/bin/env python3
"""把结构化配图 brief 编译成可直接交给图片模型的提示词。

模板结构参考 freestylefly/awesome-gpt-image-2（MIT），针对公众号健康科普
场景做了收敛：中文输出、限制图内文字、补医学事实与器械约束、去掉空泛画质词。

Usage:
    python3 image_prompt_builder.py --list
    python3 image_prompt_builder.py --brief brief.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class BriefError(ValueError):
    """结构化 brief 不完整或字段类型错误。"""


DEFAULT_AVOID = [
    "画面出现乱码、伪文字、错别字或无法辨认的符号",
    "添加原文没有的数字、器官名、药品名、剂量或诊断结论",
    "水印、签名、二维码、无关 logo 或手机界面",
    "多余手指、器械穿模、错误解剖结构或不符合真实流程的动作",
    "把长段正文塞进画面",
    "使用空泛画质形容词堆砌效果",
]

TEMPLATE_ALIASES = {
    "infographic": "infographic",
    "info": "infographic",
    "chart": "infographic",
    "flowchart": "infographic",
    "comparison": "infographic",
    "framework": "infographic",
    "timeline": "infographic",
    "scientific-scale": "scientific-scale",
    "scientific": "scientific-scale",
    "scale": "scientific-scale",
    "mechanism": "scientific-scale",
    "nature-science-poster": "nature-science-poster",
    "science-poster": "nature-science-poster",
    "cover": "nature-science-poster",
    "poster": "nature-science-poster",
    "illustration": "illustration",
    "art": "illustration",
    "scene": "scene",
    "photo": "scene",
    "realistic": "scene",
}

TEMPLATE_INFO = {
    "infographic": {
        "label": "信息图",
        "use_for": "流程、对比、框架、时间线、因果链、知识卡",
        "required": ["subject", "modules"],
        "default_aspect": "4:3",
    },
    "scientific-scale": {
        "label": "科学尺度图",
        "use_for": "从微观到宏观、从剂量到反应、从轻到重的机制解释",
        "required": ["subject", "scale_steps"],
        "default_aspect": "3:4",
    },
    "nature-science-poster": {
        "label": "科普封面",
        "use_for": "公众号封面、单主题科普海报",
        "required": ["subject"],
        "default_aspect": "2.35:1",
    },
    "illustration": {
        "label": "概念插画",
        "use_for": "封面创意、情绪场景、视觉隐喻",
        "required": ["subject", "scene"],
        "default_aspect": "4:3",
    },
    "scene": {
        "label": "实景图",
        "use_for": "真实动作、就医场景、生活场景、器物使用",
        "required": ["subject", "action", "environment"],
        "default_aspect": "4:3",
    },
}

LAYOUT_BY_ALIAS = {
    "flowchart": "流程",
    "comparison": "对比",
    "framework": "框架",
    "timeline": "时间线",
    "chart": "数据关系",
}


def list_templates() -> list[dict[str, str]]:
    """Return template metadata for CLI and agent discovery."""
    return [
        {
            "id": key,
            "label": info["label"],
            "use_for": info["use_for"],
            "required": ", ".join(info["required"]),
            "default_aspect": info["default_aspect"],
        }
        for key, info in TEMPLATE_INFO.items()
    ]


def _required_text(brief: dict, key: str) -> str:
    value = brief.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BriefError(f"missing or empty field: {key}")
    return " ".join(value.split())


def _optional_text(brief: dict, key: str) -> str:
    value = brief.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BriefError(f"field '{key}' must be a string")
    return " ".join(value.split())


def _text_list(brief: dict, key: str) -> list[str]:
    value = brief.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise BriefError(f"field '{key}' must be a list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BriefError(f"field '{key}' contains an empty item")
        result.append(" ".join(item.split()))
    return result


def _object_list(
    brief: dict,
    key: str,
    min_items: int,
    max_items: int,
    label_key: str,
) -> list[dict[str, str]]:
    value = brief.get(key)
    if not isinstance(value, list):
        raise BriefError(f"field '{key}' must be a list")
    if not min_items <= len(value) <= max_items:
        raise BriefError(
            f"field '{key}' needs {min_items}-{max_items} items, got {len(value)}"
        )
    result = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            item = {label_key: item}
        if not isinstance(item, dict):
            raise BriefError(f"field '{key}[{index}]' must be an object or string")
        label = item.get(label_key)
        if not isinstance(label, str) or not label.strip():
            raise BriefError(f"field '{key}[{index}].{label_key}' is required")
        normalized = {}
        for field_name, value in item.items():
            if not isinstance(value, str):
                raise BriefError(f"field '{key}[{index}].{field_name}' must be a string")
            normalized[field_name] = " ".join(value.split())
        result.append(normalized)
    return result


def _resolve_template(raw: str) -> str:
    if not raw:
        raise BriefError("missing field: template")
    key = raw.strip().lower().replace("_", "-")
    template = TEMPLATE_ALIASES.get(key)
    if template is None:
        available = ", ".join(TEMPLATE_INFO)
        raise BriefError(f"unknown template '{raw}'. Available: {available}")
    return template


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _text_block(texts: list[str]) -> list[str]:
    texts = _dedupe(texts)
    if not texts:
        return ["图中文字：画面不出现任何文字、字母、数字或伪文字。"]
    quoted = "；".join(f"「{text}」" for text in texts)
    return [
        f"图中文字：只允许逐字出现以下内容：{quoted}",
        "文字要求：中文清晰可读，字号足够，位置固定；不增加、不缩写、不改写，不做艺术字变形。",
    ]


def _constraint_block(
    template_avoid: list[str], brief: dict
) -> list[str]:
    avoid = _dedupe(DEFAULT_AVOID + template_avoid + _text_list(brief, "avoid"))
    lines = ["禁止出现："]
    lines.extend(f"{index}. {item}" for index, item in enumerate(avoid, 1))
    return lines


def _extra_block(brief: dict) -> list[str]:
    extra = _optional_text(brief, "extra")
    if not extra:
        return []
    return [f"补充要求：{extra}"]


def _output_block(brief: dict, template: str) -> list[str]:
    aspect = _optional_text(brief, "aspect") or TEMPLATE_INFO[template]["default_aspect"]
    purpose = _optional_text(brief, "purpose") or "微信公众号文章配图"
    return [
        f"画面比例：{aspect}",
        f"输出用途：{purpose}",
        "输出要求：单张成品图，构图完整，主体清晰，适合直接作为公众号配图。",
    ]


def _render_infographic(
    brief: dict, subject: str, layout_default: str
) -> tuple[list[str], list[str], list[str]]:
    modules = _object_list(brief, "modules", 3, 5, "title")
    layout = _optional_text(brief, "layout") or layout_default
    title = _optional_text(brief, "title") or subject
    audience = _optional_text(brief, "audience")
    style = _optional_text(brief, "style") or "专业科普信息图，扁平插画，浅色背景"
    palette = _optional_text(brief, "palette")
    data = _text_list(brief, "data")

    lines = [
        "画面类型：信息图",
        f"主题：{subject}",
        f"标题区文字：「{title}」",
        f"信息结构：{layout}",
        f"模块数量：{len(modules)} 个",
    ]
    if audience:
        lines.append(f"目标读者：{audience}")
    lines.extend(
        [
            "画面结构：",
            "标题在上，模块按阅读顺序排列，信息层级为标题、模块标题、短说明。",
            f"模块之间用箭头、色块或细线表达{layout}关系，留白充足。",
        ]
    )
    texts = [title]
    for index, module in enumerate(modules, 1):
        module_title = module["title"]
        detail = module.get("detail", "")
        icon = module.get("icon", "")
        line = f"{index}. 模块标题「{module_title}」"
        if detail:
            line += f"；短说明「{detail}」"
        if icon:
            line += f"；图标：{icon}"
        lines.append(line)
        texts.append(module_title)
        if detail:
            texts.append(detail)
    if data:
        lines.append("关键数据：" + "；".join(data))
        texts.extend(data)
    lines.extend(
        [
            f"风格：{style}",
            "短说明控制在 18 个汉字内，避免长段落。",
        ]
    )
    if palette:
        lines.append(f"配色：{palette}")
    return lines, texts, ["画面出现超过 5 个模块或重复层级"]


def _render_scientific_scale(
    brief: dict, subject: str
) -> tuple[list[str], list[str], list[str]]:
    steps = _object_list(brief, "scale_steps", 4, 8, "name")
    title = _optional_text(brief, "title") or subject
    direction = _optional_text(brief, "direction") or "从微观到宏观"
    style = _optional_text(brief, "style") or "科学编辑信息图，精准微距光，清晰层级"
    palette = _optional_text(brief, "palette")

    lines = [
        "画面类型：科学尺度信息图",
        f"主题：{subject}",
        f"标题区文字：「{title}」",
        f"排列方向：{direction}",
        f"尺度数量：{len(steps)} 个",
        "画面结构：",
        "每个尺度使用独立框体，按顺序用细线连接，框体大小可有差异。",
        "每框包含尺度名称、短洞察、单位或放大倍率，以及该尺度下的高细节画面。",
    ]
    texts = [title]
    for index, step in enumerate(steps, 1):
        name = step["name"]
        detail = step.get("detail", "")
        unit = step.get("unit", "")
        line = f"{index}. 尺度「{name}」"
        if detail:
            line += f"；短洞察「{detail}」"
        if unit:
            line += f"；单位或倍率「{unit}」"
        lines.append(line)
        texts.append(name)
        if detail:
            texts.append(detail)
        if unit:
            texts.append(unit)
    lines.append(f"风格：{style}")
    if palette:
        lines.append(f"配色：{palette}")
    return lines, texts, ["所有尺度框画成相同大小或使用通用放大镜图标"]


def _render_nature_science_poster(
    brief: dict, subject: str
) -> tuple[list[str], list[str], list[str]]:
    title = _optional_text(brief, "title") or subject
    subtitle = _optional_text(brief, "subtitle")
    scene = _optional_text(brief, "scene")
    points = _text_list(brief, "key_points")
    if len(points) > 4:
        raise BriefError("field 'key_points' supports at most 4 items")
    style = _optional_text(brief, "style") or "温暖科普插画，干净留白，柔和自然光"
    palette = _optional_text(brief, "palette")

    lines = [
        "画面类型：单主题科普封面",
        f"主题：{subject}",
        f"标题文字：「{title}」",
    ]
    if subtitle:
        lines.append(f"副标题文字：「{subtitle}」")
    if scene:
        lines.append(f"场景：{scene}")
    lines.extend(
        [
            "构图：主体占据画面 45%-65%，标题区留白，视觉中心明确。",
            "背景：干净浅色背景，避免医疗恐惧感和拥挤装饰。",
        ]
    )
    texts = [title]
    if subtitle:
        texts.append(subtitle)
    if points:
        lines.append("信息栏目：")
        for index, point in enumerate(points, 1):
            lines.append(f"{index}. 短标签「{point}」")
            texts.append(point)
        lines.append("信息栏目放在主体边缘，使用短标签，不遮挡主体。")
    lines.append(f"风格：{style}")
    if palette:
        lines.append(f"配色：{palette}")
    return lines, texts, ["画面出现长段说明文字或超过 4 个信息栏目"]


def _render_illustration(
    brief: dict, subject: str
) -> tuple[list[str], list[str], list[str]]:
    scene = _required_text(brief, "scene")
    mood = _optional_text(brief, "mood") or "克制、温和、有希望感"
    style = _optional_text(brief, "style") or "温暖扁平科普插画，细腻纹理，柔和光影"
    palette = _optional_text(brief, "palette")

    lines = [
        "画面类型：概念插画",
        f"主题：{subject}",
        f"场景：{scene}",
        f"情绪：{mood}",
        "构图：主体明确，前景、中景、背景层次清楚，留出呼吸空间。",
        f"风格：{style}",
    ]
    if palette:
        lines.append(f"配色：{palette}")
    texts = _text_list(brief, "text")
    return lines, texts, ["画面出现塑料感 AI 默认风格或过度装饰"]


def _render_scene(
    brief: dict, subject: str
) -> tuple[list[str], list[str], list[str]]:
    action = _required_text(brief, "action")
    environment = _required_text(brief, "environment")
    camera = _optional_text(brief, "camera") or "平视中景，50mm 视角"
    lighting = _optional_text(brief, "lighting") or "柔和自然光"
    style = _optional_text(brief, "style") or "真实生活摄影，自然质感"

    lines = [
        "画面类型：实景图",
        f"主题：{subject}",
        f"动作：{action}",
        f"环境：{environment}",
        f"镜头：{camera}",
        f"光线：{lighting}",
        "真实感：动作符合真实流程，器物方位正确，材质和比例可信。",
        f"风格：{style}",
    ]
    texts = _text_list(brief, "text")
    return lines, texts, ["动作反关节、器械穿模或场景像摆拍广告"]


def build_prompt(brief: dict[str, Any]) -> str:
    """Compile a structured brief into a Chinese image prompt."""
    if not isinstance(brief, dict):
        raise BriefError("brief must be a JSON object")

    raw_template = str(brief.get("template", ""))
    template = _resolve_template(raw_template)
    subject = _required_text(brief, "subject")

    if template == "infographic":
        layout_default = LAYOUT_BY_ALIAS.get(
            raw_template.strip().lower().replace("_", "-"), "框架"
        )
        body, texts, template_avoid = _render_infographic(
            brief, subject, layout_default
        )
    elif template == "scientific-scale":
        body, texts, template_avoid = _render_scientific_scale(brief, subject)
    elif template == "nature-science-poster":
        body, texts, template_avoid = _render_nature_science_poster(brief, subject)
    elif template == "illustration":
        body, texts, template_avoid = _render_illustration(brief, subject)
    else:
        body, texts, template_avoid = _render_scene(brief, subject)

    lines = body
    lines.extend(_text_block(texts + _text_list(brief, "text")))
    lines.extend(_constraint_block(template_avoid, brief))
    lines.extend(_extra_block(brief))
    lines.extend(_output_block(brief, template))
    return "\n".join(lines)


def _print_templates() -> None:
    print("Available image prompt templates:")
    for info in list_templates():
        print(
            f"  {info['id']:<22} {info['label']:<8} "
            f"aspect={info['default_aspect']:<7} required={info['required']}"
        )
        print(f"  {'':22} {info['use_for']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile image brief into a prompt")
    parser.add_argument("--brief", help="Path to a JSON brief file")
    parser.add_argument("--list", action="store_true", help="List available templates")
    args = parser.parse_args(argv)

    if args.list:
        _print_templates()
        return 0
    if not args.brief:
        parser.print_help()
        return 2

    try:
        brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
        print(build_prompt(brief))
    except (OSError, json.JSONDecodeError, BriefError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
