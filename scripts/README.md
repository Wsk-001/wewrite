# scripts/ 脚本索引

脚本保持**扁平放置**（不做子目录），原因：脚本之间按扁平名互相 import，且
`SKILL.md` / `commands.md` / `tests/` 均以 `scripts/xxx.py` 路径调用；分子目录会引入
import 与调用路径的回归风险。按职能在此索引，便于查找。

统一调用方式（`{skill_dir}` = 仓库根）：

```bash
python3 {skill_dir}/scripts/<脚本名>.py [参数]
```

## 检查类（质量与合规）

| 脚本 | 用途 |
|------|------|
| `humanness_score.py` | 反 AI 检测评分（0=人 / 100=AI），主管道 Step 5 调用；含红旗词/否定对举/修辞公式化三项硬检测 |
| `compliance_check.py` | 健康科普合规扫描（疗效断言/绝对化/虚构病例/引流/恐吓/标题党） |
| `seo_check.py` | 搜一搜结构自检与文末内链建议 |
| `seo_keywords.py` | 关键词提取与建议 |
| `similarity_check.py` | 与历史文章原创度比对 |
| `diagnose.py` | 安装自检：依赖 / 配置 / 风格 / 增强 / 维度随机化 |
| `context_budget.py` | 主管道文档上下文用量测量（CI 回归护栏） |

## 抓取类（外部素材）

| 脚本 | 用途 |
|------|------|
| `fetch_hotspots.py` | 热点/热搜抓取（选题来源：微博/头条/百度） |
| `wechat_search.py` | 搜狗微信搜索，按关键词搜公众号文章（选题来源：公众号生态；`--days`/`--pages` 控近期，`--resolve` 追真实链接） |
| `fetch_article.py` | 按 URL 抓取文章正文 |
| `fetch_stats.py` | 公众号文章数据抓取（需微信凭据） |

## 学习类（风格与改稿）

| 脚本 | 用途 |
|------|------|
| `learn_edits.py` | 学习用户对文章的修改，沉淀写作 playbook |
| `learn_theme.py` | 从微信文章 URL 学习排版主题 |
| `extract_exemplar.py` | 从范文提取风格 exemplar；`--list` 查看范文库 |

## 构建类（打包产物）

| 脚本 | 用途 |
|------|------|
| `build_openclaw.py` | 构建 OpenClaw skill 到 `dist/openclaw/` |
| `build_codex.py` | 构建 Codex prompt 到 `dist/codex/` |
| `build_playbook.py` | 生成写作 playbook（需 LLM 凭据） |
