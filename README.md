# WeWrite

公众号文章全流程 AI Skill —— 从热点抓取到草稿箱推送，一句话搞定。

## 快速开始

```bash
pip install -r requirements.txt
```

## 功能

- 热点抓取
- 选题推荐
- 框架写作
- 素材增强
- SEO 优化
- 视觉 AI
- 排版推送

## 视觉主题

集成 gzh-design 主题系统：**支持内容自适应配色**和 50 套固定主题（核心 7 套 + 库内代表 43 套）。

### 自适应生成（推荐）

`--theme auto` 根据文章内容**自动设计专属配色**，而非从固定主题中挑选：

- **语义分析**：提取关键词识别领域（饮食/心血管/睡眠/心理/眼科/体检/呼吸/骨骼/皮肤/用药）
- **色相生成**：每个领域映射基础色相（如 饮食→暖橙19°、心血管→绛红349°、睡眠→靛蓝223°）
- **封面混合**：若有封面图，提取主色相与语义色相混合，确保视觉一致性
- **动态派生**：从基础色相自动计算主色、浅色、强调色、高亮底色，确保对比度适读
- **排版自适应**：根据内容调性自动调整间距/行高/字重（如 饮食类松弛 36px/1.85/800，心血管类紧凑 28px/1.75/900）

示例：

```bash
# 内容自适应设计（推荐）
python toolkit/cli.py preview article.md --theme auto

# 输出示例：
# [自适应主题设计]
#   类别: 饮食（得分 37）
#   色相: 语义+封面混合 → 19°
#   配色: 主色 #AD5A32 / 浅色 #E2D5CE / 强调 #C18638
#   排版: 间距 36px / 行高 1.85 / 标题 800 / 正文 400
```

### 固定主题库（50 套）

50 套主题均可通过 `--theme {id}` 显式指定。下表只列 7 套核心主题，完整清单运行 `python3 toolkit/cli.py themes` 查看。

| 主题 | 标识符 | 适用场景 |
|-----|--------|---------|
| 摸鱼绿 | `moyu-green` | 教程、测评、清单、工具盘点、知识整理 |
| 红白色系 | `red-white` | 新闻快讯、观点评论、热点解读、重要通知 |
| 石墨极简 | `graphite-minimal` | 深度分析、专业报告、学术内容 |
| 留白禅意 | `zen-whitespace` | 随笔、散文、生活分享、情感内容 |
| 摸鱼票据 | `moyu-ticket` | 产品发布、活动通知、优惠信息、邀请函 |
| 橄榄手记 | `olive-journal` | 日记式内容、学习笔记、周报月报 |
| 汤底暖橙 | `hotpot-warm` | 火锅、美食、饮食健康、暖调生活科普 |

使用示例：

```bash
# 显式指定固定主题（可用 cli.py themes 查看全部 50 套）
python toolkit/cli.py preview article.md --theme red-white

# 发布到公众号（auto 推荐）
python toolkit/cli.py publish article.md --theme auto
```

## 配置

复制 `config/config.example.yaml` 为 `config/config.yaml`，填入你的微信 AppID 和 Secret。

## License

MIT
