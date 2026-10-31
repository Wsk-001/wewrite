# 视觉 AI 模块

配图提示词由 `toolkit/image_prompt_builder.py` 编译：先写结构化 brief，再生成稳定、
可复用的中文提示词。模板结构参考 freestylefly/awesome-gpt-image-2（MIT License），
针对健康科普场景补充了图内文字白名单、医学事实与器械约束。许可说明见
`THIRD_PARTY_NOTICES.md`。

## 一、选模板

| 文章内容 | template | 说明 |
|---|---|---|
| 流程、对比、框架、时间线、因果链、知识卡 | `infographic`（别名 `flowchart` / `comparison` / `framework` / `timeline`） | 3-5 个模块 |
| 从微观到宏观、剂量到反应、轻到重的机制 | `scientific-scale` | 4-8 个尺度 |
| 公众号封面、单主题科普海报 | `nature-science-poster`（别名 `cover` / `poster`） | 默认 2.35:1 |
| 封面创意、情绪场景、视觉隐喻 | `illustration` | 默认无文字 |
| 真实动作、就医场景、生活场景、器物使用 | `scene` | 默认无文字 |

封面 3 组创意仍然有效：直觉冲击型、氛围渲染型、信息图表型。分别对应
`illustration`、`scene`、`nature-science-poster` 或 `infographic`。

### 实体锚定（必须）

从文章中提取 3-5 个具体实体，每条 brief 的 `subject` 与模块文案至少覆盖 2 个实体。
实体写具体名词（如“上臂袖带”“肺动脉”“深睡眠”），避免“身体”“健康”这类空词。

## 二、写 brief

通用字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `template` | 是 | 模板名或别名 |
| `subject` | 是 | 这张图要说明的核心对象，一句话 |
| `title` | 否 | 图内标题；省略时用 `subject` |
| `text` | 否 | 额外允许出现的图内文字，逐条列出 |
| `avoid` | 否 | 额外禁止项，逐条列出 |
| `aspect` | 否 | 覆盖默认比例，如 `4:3`、`3:4`、`2.35:1` |
| `purpose` | 否 | 默认“微信公众号文章配图” |
| `style` / `palette` | 否 | 风格与配色；同一篇内保持一致 |
| `extra` | 否 | 补充要求，一句话 |

各模板专属字段：

- `infographic`：`modules` 3-5 项，每项 `title` 必填，`detail` 建议 18 字内，
  `icon` 可选；`layout` 可写流程/对比/框架/时间线/因果链；`data` 为关键数字列表；
  `audience` 可选。
- `scientific-scale`：`scale_steps` 4-8 项，每项 `name` 必填，`detail`、`unit` 可选；
  `direction` 默认“从微观到宏观”。
- `nature-science-poster`：`key_points` 最多 4 条短标签；`subtitle` 可选。
- `illustration`：`scene` 必填；`mood` 可选，默认克制温和。
- `scene`：`action`、`environment` 必填；`camera`、`lighting` 可选。

示例：

```json
{
  "template": "flowchart",
  "subject": "高血压患者为什么容易漏服药",
  "title": "漏服背后的四个环节",
  "modules": [
    {"title": "忘记", "detail": "生活节奏打乱", "icon": "闹钟"},
    {"title": "担心", "detail": "怕副作用"},
    {"title": "好转", "detail": "自行停药"},
    {"title": "漏服", "detail": "血压波动"}
  ],
  "layout": "因果链"
}
```

## 三、图内文字规范（必须）

- 只有 brief 中的 `title`、模块文案、`data`、`text` 允许出现在画面里，编译器会把
  它们写成逐字白名单。
- 未提供任何文字时，编译器明确要求画面不出现文字、字母、数字或伪文字。
- 生成后必须读图核对：文字逐字正确、数字与原文一致、没有乱码/错字/伪英文。
- 文字出错时先改 brief 或减少文字量重生成；仍不稳定就整图去文字，改用图形与图标。

## 四、生成前：场景实况检索

涉及真实动作、医疗器械、就医流程、生活器物时，先 websearch 查清细节再写 brief：

- 动作要领与体位（如测血压坐姿、袖带与心脏同高）
- 器物方位与连接关系（如雾化器面罩、血糖采血部位）
- 步骤顺序与常见错误
- 图示不能误导的解剖结构

把查到的具体细节写进 `action` / `environment` / 模块文案。检索不到可靠来源时，
降低画面确定性，改用 `illustration` 表达概念，并在文中注明信息边界。

## 五、风格锚定

封面确认后提取视觉锚点：主色、光线、材质、人物风格、构图密度。后续所有
内文图在 brief 的 `style` / `palette` 复用同一组描述，保证整篇观感统一。

## 六、生成

多张图必须一次批量并发，逐张串行算流程错误。

```bash
# 先编译检查提示词，不调用 provider、不产生费用
python3 toolkit/image_gen.py --batch output/.imgbatch.json --dry-run

# 确认提示词后批量生成
python3 toolkit/image_gen.py --batch output/.imgbatch.json --workers 5
```

batch 文件支持直接写 `brief`，也兼容已写好的 `prompt`：

```json
[
  {
    "output": "output/文章-cover.jpg",
    "size": "cover",
    "brief": {
      "template": "cover",
      "subject": "久坐一小时身体发生了什么",
      "key_points": ["血流变慢", "肌肉停工", "腰椎受压"]
    }
  },
  {
    "output": "output/文章-1.jpg",
    "size": "article",
    "brief": {
      "template": "flowchart",
      "subject": "久坐后的身体变化",
      "modules": [
        {"title": "0 分钟", "detail": "正常血流"},
        {"title": "20 分钟", "detail": "代谢减慢"},
        {"title": "45 分钟", "detail": "肌肉僵硬"},
        {"title": "60 分钟", "detail": "腰背不适"}
      ]
    }
  }
]
```

单张调试：

```bash
python3 toolkit/image_gen.py --brief /tmp/brief.json --output output/test.jpg --size article --dry-run
```

`size` 只控制输出分辨率，不会改变 brief 里的构图比例。封面用 `cover`，内文图用
`article`，竖版机制图用 `vertical`。

## 七、生成后：视觉 bug 自检闭环

每张图生成后必须读图，按下列清单逐项核对：

1. 文字：逐字正确，无乱码/错字/伪文字，数字与原文一致
2. 结构：模块数量、顺序、箭头方向与 brief 一致
3. 解剖与器物：器官位置、器械方位、动作流程符合检索到的事实
4. 风格：与封面锚点一致，无突兀换色
5. 干扰物：无水印、签名、二维码、无关 logo、手机界面、多余边框
6. 裁切：主体完整，封面 2.35:1 未被切掉标题或主体

同一批图片必须在同一条消息里并行读图，或并行建 image_analysis 任务后统一收结果。
不通过的图收集成第二批，一次 batch 重生成后再并发复检。整个 Step 6 只允许
“批量生成 → 并发自检 → 批量重生成 → 复检”一轮循环；超过两轮说明 brief 或模板
有系统性问题，回头修模板。

## 八、插入正文

按“提取结构 → 逐个论点判断 → 确定图片类型 → 确定位置”的顺序规划。

**用 Markdown 图片语法 `![](相对路径)` 插入到对应段落下方。**

发布时 `toolkit/cli.py publish` 会扫描文章中的 `![]()` 引用，自动上传图片并替换为
微信图床 URL。正文没有图片引用、或引用数不等于 `--expect-images`、或文件不存在时，
publish 会直接报错退出，不静默产出缺图草稿。

## 九、辅助功能

提示词修改、创意切换、配图场景调整时，优先改 brief 字段并重新 `--dry-run`，
确认编译结果后再生成。
