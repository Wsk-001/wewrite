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
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - TaskCreate
  - TaskUpdate
  - Task
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

**路径约定**：本文档中 `{skill_dir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）。

**读取/检查约定**：本文档中 `读取: <路径>` / `检查: <路径>` = **用你环境的文件读取工具真实打开该文件、读完其全部内容，然后再继续本步**。这不是描述性注释——未读取前不得执行依赖该文件的步骤；不同 harness 的文件读取工具名不同，按你环境的对应工具执行。

**Python 解释器约定**：本文档所有 `python3` 命令优先解析为 `{skill_dir}/.venv/bin/python3`（若该文件存在），否则回退系统 `python3`。venv 由 `install.sh` 创建，用于隔离依赖并绕过 macOS Homebrew Python 的 PEP 668 限制。

**Onboard 例外**：Onboard 是交互式的（需要问用户问题），不受"全自动"约束。Onboard 完成后回到全自动管道。

**辅助功能 / 非管道命令**（按需加载）：用户发出"选题→发布"主流程之外的命令——重新设置风格 / 学习我的修改 / 学习排版 / 导入范文·学习这篇文章 / 查看范文库 / 看看文章数据 / 主题画廊 / 小绿书 / 更新 / 检查一下·自检——时 → `读取: {skill_dir}/references/guides/commands.md`，按其中「触发词 → 动作」表执行。

---

## 主管道（Step 1-8）

主管道是固定的 8 个 Step（下面逐节展开）：

```
[1/8] 环境 + 配置   [2/8] 选题   [3/8] 框架 + 素材   [4/8] 写作
[5/8] 反AI检测+合规 [6/8] 配图   [7/8] 排版         [8/8] 发布
```

---

### [1/8] 环境 + 配置

```
读取: {skill_dir}/config/config.yaml（若不存在则从 config/config.example.yaml 复制）
检查: {skill_dir}/.venv/bin/python3 是否存在；不存在则运行 bash {skill_dir}/install.sh
检查: config.yaml 中 wechat.appid 和 wechat.secret 是否已填写
检查: 图片生成配置是否已配置（至少一个 provider）
检查: config/style.yaml 是否存在（若不存在则从 config/style.example.yaml 复制）
```

**降级标记检测**（先检查再继续）：
- `publish` 命令中 `--skip-publish` → 设 `skip_publish = True`（Step 8 跳过）
- `publish` 命令中 `--skip-image-gen` → 设 `skip_image_gen = True`（Step 6 跳过）

**首次使用**：如果 config/config.yaml 不存在（刚刚从 example 复制），进入 Onboard 流程：
```
读取: {skill_dir}/references/guides/onboard.md
按 onboard.md 逐节执行，引导用户完成初始化
完成后回到 Step 2
```

---

### [2/8] 选题

```
读取: {skill_dir}/references/pipeline/topic-selection.md
运行: python3 {skill_dir}/scripts/fetch_hotspots.py --limit 20
运行: python3 {skill_dir}/scripts/wechat_search.py "候选关键词" --days 90 --pages 3 --json
按 topic-selection.md 中的「检索源分发」表分源取料，合并去重后再评分
检查: wechat_search 若 exit 3 / blocked=true（搜狗反爬）→ WebSearch 兜底并在选题报告注明该源缺失
```

---

### [3/8] 框架 + 素材

```
读取: {skill_dir}/references/pipeline/frameworks.md
按 frameworks.md 中的框架和素材流程执行
```

---

### [4/8] 写作

```
读取: {skill_dir}/references/pipeline/writing-guide.md
读取: {skill_dir}/config/style.yaml
读取: {skill_dir}/references/pipeline/content-enhance.md
读取: {skill_dir}/personas/{config/style.yaml 中 writing_persona}.yaml
按 writing-guide.md 的写作流程执行
```

**写作时参照以下规范**：
- **排版样式**：`读取: {skill_dir}/references/pipeline/formatting-styles.md`，按其中规则排版，不可偏离

---

### [5/8] 反AI检测 + 合规扫描

```
运行: python3 {skill_dir}/scripts/humanness_score.py {skill_dir}/output/{文章}.md --json
读取: {skill_dir}/references/pipeline/realtime-check.md
检查: humanness_score 是否落在账号校准区间——唯一来源是 config/writing-config.yaml 的
      humanness_range（默认 [16, 36]）；脚本输出的 in_range 字段即为判定结果，
      不要再使用其他硬编码阈值
注意: 分数语义为 0=人、100=AI。低于区间下限同样需复核（过度口语化会显得刻意）
重点复核新增三项硬检测的命中明细（--verbose 可见）：
      - flag_words（红旗词：因而/因此/旨在/值得注意/不可忽视/归根结底/由此可见/事实上…）应为 0
      - negation_pairs（否定对举"不是X而是Y"）> 1 次即改写
      - formulaic_rhetoric（三段式排比/虚假范围"从X到Y"）> 1 次即改写
若超出区间或上述任一项命中超限，则按 writing-guide.md 的「反AI检测清单」与
「红旗词与 AI 结构专项」优化后重新评分

运行: python3 {skill_dir}/scripts/compliance_check.py {skill_dir}/output/{文章}.md
检查: 合规扫描是否通过（健康科普红线：疗效断言/绝对化用语/虚构病例/引流导诊/恐吓传播/标题党）
若出现 error 级命中则按脚本输出的建议改写后重新扫描，扫描通过才允许进入 Step 6
```

---

### [6/8] 配图

如果 `skip_image_gen` 为 True，跳过此 Step。

```
读取: {skill_dir}/references/pipeline/visual-prompts.md
按 visual-prompts.md 生成配图，并强制执行其中两节：
- 「生成前：场景实况检索」——配图涉及真实场景/动作/流程/器物时，先 websearch 查清
  真实细节（动作要领、器物方位、步骤顺序）写进提示词，再生成
- 「生成后：视觉 bug 自检闭环」——每张图生成后必须读图自检（按清单逐项核对），
  不通过则修订提示词重生成，全部通过才允许进入 Step 7

多张配图（封面 + 正文图）必须一次批量并发生成，逐张串行调用会被判为流程错误：
1. 写 batch 文件 {skill_dir}/output/.imgbatch.json：
   [{"prompt": "...", "output": "{skill_dir}/output/xxx-1.jpg", "size": "article"},
    {"prompt": "...", "output": "{skill_dir}/output/cover-xxx.jpg", "size": "cover"}]
2. 运行: python3 {skill_dir}/toolkit/image_gen.py --batch {skill_dir}/output/.imgbatch.json --workers 5
3. 读 stdout JSON 确认 ok/failed；failed 的图修 prompt 后单独重跑该张
4. 自检不通过的图只重生成该一张，其余不动

视觉自检同样禁止逐张串行：把本批全部图片在同一条消息里并行读图（或并行建
image_analysis 任务后统一收结果），一次性按清单核对；不通过的收集成第二批，
一次 batch 重生成后再并发复检。整个 Step 6 只允许「批量生成 → 并发自检 →
批量重生成 → 复检」一轮循环，超过两轮说明提示词本身有系统性问题，回头修提示词模板。
```

---

### [7/8] 排版

将 Markdown 转换为微信排版，应用 gzh-design 主题（6 套：moyu-green/red-white/graphite-minimal/zen-whitespace/moyu-ticket/olive-journal）。

```
读取: {skill_dir}/references/pipeline/formatting-styles.md
运行: python3 {skill_dir}/toolkit/cli.py preview {skill_dir}/output/{文章}.md --theme {style.yaml 中 theme}
检查: 预览结果是否符合排版规范
```

---

### [8/8] 发布

如果 `skip_publish` 为 True，跳过此 Step。

**发布前自检**（SEO error 未清零不建议推送）：

```
运行: python3 {skill_dir}/scripts/seo_check.py {skill_dir}/output/{文章}.md --keywords "本文核心词" --history {skill_dir}/output/history.yaml
检查: error 项清零；根据脚本输出的「建议文末内链」把 1-2 条相关历史文章链接加到文末
```

```
运行: python3 {skill_dir}/toolkit/cli.py publish {skill_dir}/output/{文章}.md --theme {theme} --cover {封面图路径} --expect-images 4 --author {author}
```

**推送前预检（publish 内置，先于任何网络调用）**：封面缺失、封面文件不存在、正文 `![](路径)`
指向的本地图不存在、内文图数量 ≠ `--expect-images`、正文没有任何本地图引用、转换产物存在
markdown 语法残留（表格竖线 `|`、`**`、`==`、`:::`、行首 `#`/`>` 等，代表解析器漏接、内容会以
降级形态上线）——任一命中都会以 exit 2 停止并列出具体项。修好再推；确需跳过用 `--force`。

**要点**：
- `--cover` 必传（Step 6 生成的封面图文件路径）；确实无封面时须显式加 `--no-cover`，否则直接报错（不再静默产出无封面草稿）
- `--expect-images 4` 与排版规范的「每篇固定 4 张内文图（不含封面）」对齐，图数不对就别推
- 排版约束已由 GzhConverter 自动处理；发布报 errcode 40164 = 调用方 IP 不在公众号后台「设置与开发-IP 白名单」内，将出口 IP 加入白名单后重试（沙箱/容器环境出口 IP 变动后需重新添加）
- **发布时间建议**：推送前告诉用户健康科普读者的活跃时段——早通勤 7-9 点、午休 12-14 点、晚 20-22 点；**默认直接推送到草稿箱，不暂停询问**（除非处于交互模式或用户明确要求先确认），推完在结果里附上活跃时段建议
- 发布前确认草稿会勾选「声明原创」（搜一搜优先展示原创内容）；提醒用户在后台「搜索开放权限」已开启的前提下发布

**发布成功后归档**（必须执行）：
- 追加一条记录到 `{skill_dir}/output/history.yaml`（不存在则创建），字段：`id`（日期-标题slug）、`date`、`title`、`topic`、`article`、`theme`、`humanness_score`、`cover`、`inline_images`、`status: draft`、`drafts`（每版含 `version`/`note`/`media_id`/`action`）
- 同一文章重发新版本时，在 `drafts` 下追加新版本，旧版本 `action` 改为 `待删除`

**草稿箱清理提醒**：微信 publish 每次新建草稿、不覆盖旧稿。提醒用户清理前，**先调 `draft/batchget` API 查询草稿箱实时列表**，只提醒本档案中 `action: 待删除` 且在实时列表中真实存在的旧版——档案可能与实际不同步，实时 API 为准；用户确认删除后，立即把对应版本的 `action` 更新为 `已删除`，避免重复提醒。

---

## 辅助功能

用户发出"选题→发布"之外命令时，读取 commands.md 并按表执行：

```
读取: {skill_dir}/references/guides/commands.md
```
