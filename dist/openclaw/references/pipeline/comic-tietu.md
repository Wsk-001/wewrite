# 贴图（小绿书 / 漫画贴图）模块

从一篇已完成的公众号文章派生一组竖版漫画贴图，发布为微信「图片帖」。贴图是文章的
二次分发入口，用来在信息流里争取点击，再把读者导回文章。

主管道 Step 9 默认执行本模块。跳过条件：用户明确说不要贴图，或 `publish` 带
`--no-tietu`；内容无法画面化时也应在 storyboard 阶段说明后跳过。

## 一、什么时候做

| 场景 | 是否适合 |
|---|---|
| 文章有一个明确结论、一组数字或一个反常识点 | 适合，贴图做钩子 |
| 文章是长故事、多线叙事 | 只取一条主线做 5-6 格 |
| 内容依赖大量文字论证、无法画面化 | 不适合，直接跳过 |
| 原文仍在草稿箱、尚无公开链接 | 可以先做草稿，发布前必须补链接 |

默认 6 格；信息少做 5 格，信息多做 7-8 格。微信图片帖编辑上限 9 张，首张即封面。

## 二、流程

```
写 storyboard.json
  → comic-plan          # 生成 batch.json（只含 AI 格）
  → image_gen --batch   # 并发生成 raw-N.jpg
  → 并发读图自检         # 逐张核对，不通过改 brief 重生成
  → comic-render        # 叠字、回顾卡、preview.html
  → comic-post          # 建图片帖草稿
```

命令（`{skill_dir}` 为仓库根目录）：

```bash
python3 {skill_dir}/toolkit/cli.py comic-plan  {skill_dir}/output/<slug>-tietu/storyboard.json
python3 {skill_dir}/toolkit/image_gen.py --batch {skill_dir}/output/<slug>-tietu/batch.json --workers 5
python3 {skill_dir}/toolkit/cli.py comic-render {skill_dir}/output/<slug>-tietu/storyboard.json
python3 {skill_dir}/toolkit/cli.py comic-post   {skill_dir}/output/<slug>-tietu/storyboard.json
```

`comic-plan` 默认把底图写到 `<storyboard 目录>/raw/`，batch 写到同目录 `batch.json`；
`comic-render` 默认读取同目录 `raw/`，输出到同目录；`comic-post` 读取同目录
`tietu-N.jpg`，建完草稿后写 `manifest.json` 与 `clean-media-ids.json`。

## 三、storyboard.json

```json
{
  "article": "output/foo.md",
  "article_title": "文章完整标题",
  "article_draft_media_id": "可选，文章草稿 media_id",
  "post_title": "贴图标题，<= 32 字",
  "post_body": "贴图正文，<= 1000 字",
  "style_anchor": "统一画风与场景锚点",
  "environment": "默认环境描述，供未写 brief 的格子复用",
  "palette": "米白、浅木、暖灰",
  "avoid": ["文字", "字母", "数字", "标签", "logo", "水印", "二维码", "伪文字"],
  "size": "1152x1536",
  "recap_label": "贴图回顾",
  "recap_title": "一张图记住要点",
  "recap_sub": "一行结论",
  "recap_cta": "见公众号文章",
  "recap_note": "补充一句",
  "recap_tail": "完整内容见公众号文章",
  "panels": [
    {
      "no": 1,
      "beat": "hook",
      "scene": "画面里发生什么，一句完整描述",
      "caption": "叠在图上的一句话，<= 16 字为宜",
      "source_fact": "对应文章中的事实或数字",
      "render": "ai"
    },
    {
      "no": 6,
      "beat": "cta",
      "scene": "本地回顾卡",
      "caption": "把结论收成一句",
      "render": "recap"
    }
  ]
}
```

字段约定：

- `panels[].no`：从 1 连续编号，决定文件名与排序，不可重复
- `panels[].render`：`ai` 走生图；`recap` 用本地回顾卡（只允许最后一格）
- `panels[].caption`：必填，叠字内容；图上文字只来自 caption 与 recap_* 字段
- `panels[].scene`：`ai` 格的画面描述，写动作、环境、构图，不写文字
- `panels[].brief`：可选，直接给 `image_prompt_builder` 的完整 brief；给了就优先用
- `panels[].subject`：可选，生图核心对象；省略时取 `scene` 第一个逗号前的短句

`comic-plan` 自动补 `avoid`（图内文字黑名单）与 `aspect: 3:4`。画面里出现文字、字母、
数字是贴图最常见的翻车点，生成前必须确认 `avoid` 生效、`caption` 不要写进 `scene`。

## 四、分镜写法

6 格的标准节奏：

| 格 | beat | 作用 | 例子 |
|---|---|---|---|
| 1 | hook | 一个具体数字或反常识点，先勾住人 | 「9块9，300毫升」 |
| 2 | identity | 解释是什么，或纠正误解 | 「尿素不是尿」 |
| 3 | rule | 给核心规则、剂量、对比 | 「脸2%-5%，身体5%-10%」 |
| 4 | apply | 落到一个具体场景 | 「20%留给脚后跟」 |
| 5 | warning | 一条必须避开的错误做法 | 「破皮、刷酸，先停」 |
| 6 | cta | 回顾卡，收束并导向文章 | 「一张图记住浓度」 |

规则：

- 一格只讲一件事，caption 尽量 16 字以内
- 数字、剂量、部位必须与文章一致，不新增原文没有的结论
- 每格 `source_fact` 回填文章出处，方便发布前核对
- 第 1 格承担封面职责，主体居中，别把关键信息放在会被裁掉的位置

## 五、生成规格

- 目标尺寸 1080x1440（3:4）；生图尺寸用 1152x1536（宽高均为 16 的倍数，provider 只接受）
- 渲染时按 3:4 居中裁切到 1080x1440，不要直接请求 1080x1440
- 竖版构图：主体居中偏下，上方约 18%、下方约 22% 留白给编号与字幕
- 画面禁止出现文字、字母、数字、标点、标签、水印、logo、二维码、UI、对话框
- 同一组贴图共用 `style_anchor`，场景、光线、配色保持一致
- 手部、脚部特写最容易畸变；能不用手就不用，必要时改静物或器物特写
- prompt 里避免「血腥」「尸体」「伤口」这类否定词，会触发 provider 内容审核，
  改成「画面克制，适合健康科普」

## 六、自检清单

生成后必须逐张读图，按下面清单核对；任何一项不过就改 brief 只重生成那一张。

1. 主体数量、朝向、部位正确，没有多手多脚
2. 动作与 `scene` 描述一致，没有出现文案里的错误部位
3. 画面无文字、乱码、伪文字、标签、水印、logo
4. 没有医疗器械、药物包装等会误导的物件
5. 3:4 裁切后主体完整，字幕区没有压住关键信息
6. 同一组之间风格、场景、光线一致

渲染后还要看 `preview.jpg` 或 `preview.html`，核对叠字没有错字、没有被截断，
回顾卡缩略图干净（用原始底图，不要嵌带字幕的成品图）。

## 七、发布

- `post_title` <= 32 字，`post_body` <= 1000 字；正文里写清「完整内容见公众号文章」
- 首图即封面，顺序按 `no` 排；发布前在后台确认 9 张以内
- 图片和正文都不加「AI 生成」字样；平台侧如需声明，由发布时勾选
- 文章已发布：在后台给贴图补原文链接，再发布
- 文章仍是草稿：可以先建贴图草稿，在 `manifest.json` 的 `note` 写明
  「文章发布后补原文链接再发布」，不要带无效链接上线
- 群发通知一天只有一次：文章 D0 群发，贴图 D1 群发；同日发就关掉贴图的群发通知
- 贴图发布后不要删除旧版素材，重发时新建草稿并在 `history.yaml` 记录新版本

## 八、归档

在 `{skill_dir}/output/history.yaml` 的 `tietu:` 列表追加记录：

```yaml
tietu:
- id: 2026-11-01-<slug>-tietu
  date: '2026-11-01'
  kind: tietu-newspic
  title: 贴图标题
  article: output/<slug>.md
  article_title: 文章标题
  storyboard: output/<slug>-tietu/storyboard.json
  images: [output/<slug>-tietu/tietu-1.jpg, ...]
  status: draft
  drafts:
  - version: v1
    note: 6 格、自检通过、图片与正文无 AI 字样
    media_id: <草稿 media_id>
    action: 待文章发布后补原文链接再发布
```

同一篇贴图重发时在 `drafts` 下追加版本，旧版本 `action` 改为 `待删除`。
