import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cssutils
import yaml

cssutils.log.setLevel(logging.CRITICAL)


@dataclass
class Theme:
    name: str
    description: str
    base_css: str
    colors: dict = field(default_factory=dict)


def _default_themes_dir() -> str:
    return str(Path(__file__).parent / "themes")


def load_theme(name: str, themes_dir: str = None) -> Theme:
    if themes_dir is None:
        themes_dir = _default_themes_dir()
    theme_path = os.path.join(themes_dir, f"{name}.yaml")
    if not os.path.exists(theme_path):
        raise FileNotFoundError(f"Theme file not found: {theme_path}")
    with open(theme_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid theme file: {theme_path}")
    required = ("name", "description", "base_css", "colors")
    for key in required:
        if key not in data:
            raise ValueError(f"Theme file missing required field '{key}': {theme_path}")
    theme = Theme(name=data["name"], description=data["description"], base_css=data["base_css"], colors=data.get("colors", {}))
    theme._raw_data = data
    return theme


def list_themes(themes_dir: str = None) -> list[str]:
    if themes_dir is None:
        themes_dir = _default_themes_dir()
    if not os.path.isdir(themes_dir):
        return []
    names = []
    for filename in os.listdir(themes_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            names.append(filename.rsplit(".", 1)[0])
    return sorted(names)


def _resolve_css_variables(css_text: str, colors: dict) -> str:
    def replacer(match: re.Match) -> str:
        var_name = match.group(1).strip()
        key = var_name.lstrip("-")
        key_underscore = key.replace("-", "_")
        if key in colors:
            return str(colors[key])
        if key_underscore in colors:
            return str(colors[key_underscore])
        return match.group(0)
    return re.sub(r"var\(\s*--([a-zA-Z0-9_-]+)\s*\)", replacer, css_text)


def _is_simple_selector(selector: str) -> bool:
    selector = selector.strip()
    reject_chars = (":", "@", ">", "+", "~", "[", "*")
    for ch in reject_chars:
        if ch in selector:
            return False
    return True


def get_inline_css_rules(theme: Theme) -> dict[str, dict[str, str]]:
    resolved_css = _resolve_css_variables(theme.base_css, theme.colors)
    sheet = cssutils.parseString(resolved_css, validate=False)
    rules: dict[str, dict[str, str]] = {}
    for rule in sheet:
        if rule.type != rule.STYLE_RULE:
            continue
        selector_text = rule.selectorText
        selectors = [s.strip() for s in selector_text.split(",")]
        props: dict[str, str] = {}
        for prop in rule.style:
            props[prop.name] = prop.value
        if not props:
            continue
        for selector in selectors:
            if not _is_simple_selector(selector):
                continue
            if selector in rules:
                rules[selector].update(props)
            else:
                rules[selector] = dict(props)
    return rules
