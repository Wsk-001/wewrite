#!/usr/bin/env python3
"""
Build a Codex-compatible WeWrite custom prompt from the Claude Code SKILL.md.

Codex (OpenAI Codex CLI) has no SKILL.md auto-trigger mechanism. Its closest
analogue is a custom prompt in ~/.codex/prompts/<name>.md, invoked as /<name>.
This script transforms SKILL.md into such a prompt so Codex users can run the
full 8-step pipeline with `/wewrite 写一篇关于X的文章`.

The Python toolkit is reused from the cloned repo (not mirrored) — the prompt
references it via {skill_dir}, which `--install` substitutes with the repo path.

Usage:
    python3 scripts/build_codex.py              # build dist/codex/ artifacts
    python3 scripts/build_codex.py --install    # also install to ~/.codex/prompts/wewrite.md
    python3 scripts/build_codex.py -o /tmp/cx    # custom output dir
"""

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROMPT_NAME = "wewrite"

CODEX_HEADER = """\
<!-- 由 scripts/build_codex.py 从 SKILL.md 自动生成，请勿直接编辑。改源在 SKILL.md。 -->

**本次写作需求**（在 `/wewrite` 后输入的内容）：$ARGUMENTS

若上面为空，先问用户要写什么主题/选题，再开始。

**Codex 运行环境差异（相对 Claude Code 版）**：
- 没有 TaskCreate/TaskUpdate 工具 —— 每进入一个 Step，用一句话报进度（如「[3/8] 框架 + 素材」）。
- 联网搜索用 Codex 的 `web_search`；读写文件、执行命令用 Codex 自带的 shell / 文件工具。
- 所有 `python3` 命令见下方「Python 解释器约定」（优先用 {skill_dir}/.venv/bin/python3）。

---

"""


def split_frontmatter(text: str) -> tuple[str, str]:
    """Drop YAML frontmatter, return the body."""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end == -1:
        return "", text
    return text[3:end].strip(), text[end + 4:]


def transform_body(body: str) -> str:
    """Convert the SKILL.md body into a Codex-flavored prompt body."""
    body = re.sub(r"(?m)^WebSearch:", "web_search:", body)
    body = re.sub(r'(?<![`/])WebSearch(?=[ "：，）])', "web_search", body)
    body = re.sub(r"(?<=（)WebSearch(?=）)", "web_search", body)
    return body


def build_prompt() -> str:
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, body = split_frontmatter(text)
    transformed = transform_body(body)
    leftovers = re.findall(r"(?m)^(TaskCreate|TaskUpdate):", transformed)
    if leftovers:
        print(f"  \u26a0 警告：转换后正文仍含裸 task 调用行 {leftovers}（SKILL.md 可能未条件化，检查源文件）")
    return CODEX_HEADER + transformed.lstrip("\n")


CODEX_README = """\
# WeWrite for Codex

由 `scripts/build_codex.py` 从 `SKILL.md` 生成的 Codex 自定义 prompt。

## 安装

```bash
# 1. 克隆仓库并装依赖（创建 .venv，绕过 macOS PEP 668）
git clone --depth 1 https://github.com/oaker-io/wewrite.git ~/.codex/skills/wewrite
cd ~/.codex/skills/wewrite && bash install.sh

# 2. 安装 Codex 自定义 prompt（把 {skill_dir} 替换成本仓库路径，写入 ~/.codex/prompts/）
python3 scripts/build_codex.py --install
```

## 使用

在 Codex 里：

```
/wewrite 写一篇关于 AI Agent 的公众号文章
```

prompt 会执行 SKILL.md 的 Step 1-8 全流程。所有 `python3` 调用自动使用
仓库内的 `.venv`，发布/生图等能力复用 `toolkit/`。

> 注：Codex 没有 Claude Code 的 SKILL.md 自动触发机制，所以通过自定义 prompt
> 承载。每次源 `SKILL.md` 更新后，重跑 `python3 scripts/build_codex.py --install`
> 即可同步。
"""


def build(output_dir: Path, install: bool):
    prompt = build_prompt()
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    out_prompt = prompts_dir / f"{PROMPT_NAME}.md"
    out_prompt.write_text(prompt, encoding="utf-8")
    print(f"  prompts/{PROMPT_NAME}.md \u2192 {out_prompt}")
    (output_dir / "README.md").write_text(CODEX_README, encoding="utf-8")
    print(f"  README.md \u2192 {output_dir / 'README.md'}")
    if install:
        dest_dir = Path.home() / ".codex" / "prompts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        resolved = prompt.replace("{skill_dir}", str(REPO_ROOT))
        dest = dest_dir / f"{PROMPT_NAME}.md"
        dest.write_text(resolved, encoding="utf-8")
        print(f"\n\u2713 已安装到 {dest}")
        print(f"  {{skill_dir}} \u2192 {REPO_ROOT}")
        print(f"  在 Codex 里用 /{PROMPT_NAME} 触发。")
    else:
        print(f"\nDone. Codex prompt at: {output_dir}")
        print("  装到 ~/.codex/prompts/ 请加 --install。")


def main():
    parser = argparse.ArgumentParser(description="Build Codex-compatible WeWrite prompt")
    parser.add_argument("-o", "--output", default=str(REPO_ROOT / "dist" / "codex"), help="Output directory (default: dist/codex/)")
    parser.add_argument("--install", action="store_true", help="Also install the prompt to ~/.codex/prompts/ with {skill_dir} resolved.")
    args = parser.parse_args()
    build(Path(args.output), args.install)


if __name__ == "__main__":
    main()
