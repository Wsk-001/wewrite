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
