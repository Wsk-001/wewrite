---
name: wewrite
description: |
  微信公众号内容全流程助手：热点抓取 → 选题 → 框架 → 内容增强 → 写作 → SEO → 视觉AI → 排版推送草稿箱。
  触发关键词：公众号、推文、微信文章、微信推文、草稿箱、微信排版、选题、热搜、
  热点抓取、封面图、配图、写公众号、写一篇、主题画廊、排版主题、容器语法。
  也覆盖：markdown 转微信格式、学习用户改稿风格、文章数据复盘、风格设置、
  主题预览/切换、:::dialogue/:::timeline/:::callout/:::highlight/:::summary 容器语法。
  不应被通用的"写文章"、blog、邮件、PPT、抖音/短视频、网站 SEO 触发——
  需要有公众号/微信等明确上下文。
---

# WeWrite — 公众号文章全流程

## 行为声明

**角色**：用户的公众号内容编辑 Agent。

**模式**：
- **默认全自动**——一口气跑完 Step 1-8，不中途停下。只在出错时停。
- **交互模式**——用户说"交互模式"/"我要自己选"时，在选题/框架/配图处暂停。

**降级原则**：每一步都有降级方案。Step 1 检测到的降级标记（`skip_publish`、`skip_image_gen`）在后续 Step 自动生效，不重复报错。

**进度追踪**：**若 harness 提供 task 工具（如 TaskCreate）**，主管道启动时为 8 个 Step 创建任务，每步 in_progress→completed；**否则**每进入一步发一行 `[N/8] 步骤名` 文本进度。无论哪种，都必须把 8 步走完——编号清单是排序骨架，不依赖特定工具。

**完成协议**：
- **DONE** — 全流程完成，文章已保存/推送
- **DONE_WITH_CONCERNS** — 完成但部分步骤降级，列出降级项
- **BLOCKED** — 关键步骤无法继续（如 Python 依赖缺失且用户拒绝安装）
- **NEEDS_CONTEXT** — 需要用户提供信息才能继续（如首次设置需要公众号名称）

**路径约定**：本文档中 `{baseDir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）。

**读取/检查约定**：本文档中 `读取: <路径>` / `检查: <路径>` = **用你环境的文件读取工具真实打开该文件、读完其全部内容，然后再继续本步**。这不是描述性注释——未读取前不得执行依赖该文件的步骤；不同 harness 的文件读取工具名不同，按你环境的对应工具执行。

**Python 解释器约定**：本文档所有 `python3` 命令优先解析为 `{baseDir}/.venv/bin/python3`（若该文件存在），否则回退系统 `python3`。venv 由 `install.sh` 创建，用于隔离依赖并绕过 macOS Homebrew Python 的 PEP 668 限制。

**Onboard 例外**：Onboard 是交互式的（需要问用户问题），不受"全自动"约束。Onboard 完成后回到全自动管道。

**辅助功能 / 非管道命令**（按需加载）：用户发出"选题→发布"主流程之外的命令——重新设置风格 / 学习我的修改 / 学习排版 / 导入范文·学习这篇文章 / 查看范文库 / 看看文章数据 / 主题画廊 / 小绿书 / 更新 / 检查一下·自检——时 → `读取: {baseDir}/references/commands.md`，按其中「触发词 → 动作」表执行。

---

## 主管道（Step 1-8）

主管道是固定的 8 个 Step（下面逐节展开）：

```
[1/8] 环境 + 配置   [2/8] 选题   [3/8] 框架 + 素材   [4/8] 写作
[5/8] 反AI检测     [6/8] 配图   [7/8] 排版           [8/8] 发布
```

---

### [1/8] 环境 + 配置

```
读取: {baseDir}/config.yaml（若不存在则从 config.example.yaml 复制）
检查: config.yaml 中 wechat.appid 和 wechat.secret 是否已填写
检查: 图片生成配置是否已配置（至少一个 provider）
检查: style.yaml 是否存在（若不存在则从 style.example.yaml 复制）
```

**降级标记检测**（先检查再继续）：
- `publish` 命令中 `--skip-publish` → 设 `skip_publish = True`（Step 8 跳过）
- `publish` 命令中 `--skip-image-gen` → 设 `skip_image_gen = True`（Step 6 跳过）

**首次使用**：如果 config.yaml 不存在（刚刚从 example 复制），进入 Onboard 流程：
```
读取: {baseDir}/references/onboard.md
按 onboard.md 逐节执行，引导用户完成初始化
完成后回到 Step 2
```

---

### [2/8] 选题

```
读取: {baseDir}/references/topic-selection.md
按 topic-selection.md 中的选题流程执行
```

---

### [3/8] 框架 + 素材

```
读取: {baseDir}/references/frameworks.md
按 frameworks.md 中的框架和素材流程执行
```

---

### [4/8] 写作

```
读取: {baseDir}/references/writing-guide.md
读取: {baseDir}/style.yaml
读取: {baseDir}/references/content-enhance.md
读取: {baseDir}/personas/{style.yaml 中 writing_persona}.yaml
按 writing-guide.md 的写作流程执行
```

**写作时参照以下规范**：
- **排版样式**：`读取: {baseDir}/references/formatting-styles.md`，按其中规则排版，不可偏离

---

### [5/8] 反AI检测

```
运行: python3 {baseDir}/scripts/humanness_score.py {baseDir}/output/{文章}.md --json
读取: {baseDir}/references/realtime-check.md
检查: humanness_score 是否 ≤ 45，若 > 45 则按 writing-guide.md 的「反AI检测清单」优化
```

---

### [6/8] 配图

如果 `skip_image_gen` 为 True，跳过此 Step。

```
读取: {baseDir}/references/visual-prompts.md
按 visual-prompts.md 生成配图
```

---

### [7/8] 排版

将 Markdown 转换为微信排版，应用主题和容器语法。

```
读取: {baseDir}/references/formatting-styles.md
运行: python3 {baseDir}/toolkit/cli.py preview {baseDir}/output/{文章}.md --theme {style.yaml 中 theme}
检查: 预览结果是否符合排版规范
```

---

### [8/8] 发布

如果 `skip_publish` 为 True，跳过此 Step。

```
读取: {baseDir}/references/wechat-constraints.md
运行: python3 {baseDir}/toolkit/cli.py publish {baseDir}/output/{文章}.md --theme {theme} --author {author}
```

---

## 辅助功能

用户发出"选题→发布"之外命令时，读取 commands.md 并按表执行：

```
读取: {baseDir}/references/commands.md
```
