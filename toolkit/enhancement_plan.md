# WeWrite 排版增强方案

## 现状分析

1. **现有 converter**：
   - 自动化 Markdown → HTML
   - 单一主题（professional-clean）
   - 基础标记（加粗、引用、列表）
   - 无关键词下划线、无章节编号

2. **gzh-design skill**：
   - AI Agent 驱动，非自动化
   - 6 套主题（摸鱼绿/红白/石墨/禅意/票据/橄榄）
   - 智能关键词标记、自动章节编号
   - 严格合规校验

## 方案：分层增强

### Level 1：快速发布（保留现有流程）
**命令**：`python cli.py publish article.md --cover x.jpg`
**适用**：常规科普、快讯、通知
**优势**：全自动、快速
**保持原样**，不做改动。

### Level 2：主题排版（新增）
**命令**：`python cli.py publish article.md --cover x.jpg --gzh-theme moyu-green`
**流程**：
1. 读取 gzh-design 主题组件库
2. 应用关键词标记、章节编号等智能处理
3. 生成 HTML
4. 运行校验脚本
5. 上传图片、创建草稿

**实现**：
- 在 converter.py 中增加 GzhDesignConverter 类
- 读取 `/.ai-ready/skills/gzh-design/references/theme-*.md`
- 程序化实现章节编号、关键词标记
- 调用校验脚本

### Level 3：手动精细排版（已有）
**方式**：对话调用 `/gzh-design` skill
**适用**：重要文章、复杂布局、自定义主题
**优势**：AI 理解语义、完全定制

## 实施步骤

### Phase 1：集成校验（1 小时）
- 修改 `cli.py publish`，生成 HTML 后自动运行 gzh-design 校验脚本
- 确保现有输出合规

### Phase 2：移植摸鱼绿主题（3 小时）
- 创建 `toolkit/gzh_converter.py`
- 实现：
  - 章节自动编号（01/02/03）
  - 关键词下划线标记（简化版：NLP 提取 or 规则提取）
  - 引言卡片
  - 尾部签名区
- 应用摸鱼绿配色和组件

### Phase 3：多主题支持（2 小时）
- 程序化读取 `theme-index.md`
- 支持 `--gzh-theme <name>` 参数
- 自动加载对应组件库

## 技术挑战

### 1. 关键词标记自动化
**gzh-design**：AI Agent 理解语义，手动标记
**自动化方案**：
- 方案 A：jieba 分词 + TF-IDF 提取关键短语
- 方案 B：规则：加粗词、数字、专有名词
- 方案 C：混合：优先已标记，无标记时用 A 或 B

### 2. 组件库解析
**gzh-design**：组件库是 Markdown 文本，供 AI 阅读
**自动化方案**：
- 解析组件库 Markdown，提取 HTML 模板
- 建立 语义 → 组件 映射表
- 参数化组件（颜色、内容、尺寸）

### 3. 文章类型判定
**gzh-design**：AI 判断（教程/盘点/观点/访谈/数据/随笔/案例）
**自动化方案**：
- 规则启发式：
  - 步骤多（1. 2. 3.）、代码多 → 教程
  - 列表多、并列结构 → 盘点
  - 引号多、对话多 → 访谈
  - 数字、表格多 → 数据
  - 推理论证多 → 观点
- 默认：通用布局

## 推荐路径

**阶段 1（今天）**：
- 集成校验脚本到现有 publish 流程
- 修复现有输出的合规性问题

**阶段 2（1 周内）**：
- 实现 GzhDesignConverter（摸鱼绿主题）
- 添加 `--gzh-theme` 参数
- 测试：用方便面文章对比效果

**阶段 3（2 周内）**：
- 移植其他 5 套主题
- 完善关键词标记算法
- 文档：使用指南

## 结论

- **不替换现有 converter**（保留快速发布能力）
- **增加 gzh-theme 模式**（平衡自动化与精细度）
- **保留 /gzh-design skill**（终极精细排版）

三级体系：快速 → 主题 → 手动，满足不同需求。
