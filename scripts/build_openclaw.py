#!/usr/bin/env python3
"""
Build OpenClaw-compatible SKILL.md from Claude Code source.

Usage:
    python3 scripts/build_openclaw.py              # output to dist/openclaw/
    python3 scripts/build_openclaw.py -o /tmp/oc   # custom output dir
"""

import argparse
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

COPY_DIRS = ["references", "scripts", "toolkit", "personas", "config"]

COPY_EXAMPLE_ONLY = {
    "config": ["config.example.yaml", "style.example.yaml", "writing-config.example.yaml"],
}

COPY_FILES = [
    "requirements.txt",
    "install.sh",
    "VERSION",
]

STRIP_FRONTMATTER_KEYS = {"allowed-tools"}


def transform_frontmatter(frontmatter: str) -> str:
    lines = frontmatter.split("\n")
    result = []
    skip_block = False
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(f"{key}:") for key in STRIP_FRONTMATTER_KEYS):
            skip_block = True
            continue
        if skip_block:
            if stripped.startswith("- ") or stripped == "":
                continue
            skip_block = False
        result.append(line)
    return "\n".join(result)


def transform_body(body: str) -> str:
    body = body.replace("{skill_dir}", "{baseDir}")
    body = re.sub(r'(?m)^WebSearch:', 'web_search:', body)
    body = re.sub(r'(?<![`/])WebSearch(?=[ "：，）])', 'web_search', body)
    body = re.sub(r'(?<=（)WebSearch(?=）)', 'web_search', body)
    return body


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    fm = text[3:end].strip()
    body = text[end + 4:]
    return fm, body


def build(output_dir: Path):
    skill_src = REPO_ROOT / "SKILL.md"
    text = skill_src.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    fm = transform_frontmatter(fm)
    body = transform_body(body)
    out_skill = output_dir / "SKILL.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_skill.write_text(f"---\n{fm}\n---{body}", encoding="utf-8")
    print(f"  SKILL.md \u2192 {out_skill}")
    for d in COPY_DIRS:
        src = REPO_ROOT / d
        dst = output_dir / d
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            if d in COPY_EXAMPLE_ONLY:
                dst.mkdir(parents=True, exist_ok=True)
                for name in COPY_EXAMPLE_ONLY[d]:
                    f = src / name
                    if f.is_file():
                        shutil.copy2(f, dst / name)
            else:
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", "*.pyo",
                    "source_articles", "xiaokepuoao-style.md", "xiaokepuoao.yaml",
                ))
            print(f"  {d}/ \u2192 {dst}")
    for f in COPY_FILES:
        src = REPO_ROOT / f
        if src.is_file():
            shutil.copy2(src, output_dir / f)
            print(f"  {f} \u2192 {output_dir / f}")
    print(f"\nDone. OpenClaw skill at: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build OpenClaw-compatible WeWrite skill")
    parser.add_argument("-o", "--output", default=str(REPO_ROOT / "dist" / "openclaw"), help="Output directory (default: dist/openclaw/)")
    args = parser.parse_args()
    build(Path(args.output))


if __name__ == "__main__":
    main()
