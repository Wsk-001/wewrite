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

集成 gzh-design skill 六大主题：

| 主题 | 标识符 | 适用场景 |
|-----|--------|---------|
| 摸鱼绿 | `moyu-green` | 教程、测评、清单、工具盘点、知识整理 |
| 红白色系 | `red-white` | 新闻快讯、观点评论、热点解读、重要通知 |
| 石墨极简 | `graphite-minimal` | 深度分析、专业报告、学术内容 |
| 留白禅意 | `zen-whitespace` | 随笔、散文、生活分享、情感内容 |
| 摸鱼票据 | `moyu-ticket` | 产品发布、活动通知、优惠信息、邀请函 |
| 橄榄手记 | `olive-journal` | 日记式内容、学习笔记、周报月报 |

使用示例：

```bash
# 预览主题效果
python toolkit/cli.py preview article.md --theme red-white

# 发布到公众号
python toolkit/cli.py publish article.md --theme zen-whitespace
```

## 配置

复制 `config/config.example.yaml` 为 `config/config.yaml`，填入你的微信 AppID 和 Secret。

## License

MIT
