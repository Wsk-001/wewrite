# 人格选择指南

## 常驻人格库

| 人格 | 核心特征 | 适合选题 |
| midnight-friend | 深夜好友，极度口语化 | 个人感悟、情绪话题 |
| sharp-journalist | 锐评记者，短句利落 | 热点评论、争议话题 |
| cold-analyst | 冷静研究员，数据为主 | 政策解读、数据分析 |
| industry-observer | 行业观察者，克制专业 | 行业趋势、科技动态 |
| warm-editor | 温暖编辑，故事驱动 | 生活方式、情感 |
| humor-storyteller | 段子手，包袱密集 | 泛科技娱乐、辣评 |
| tech-coder | 技术码农，代码先行 | 技术教程、架构解析 |

## 选择规则

1. 用户明确指定 → 直接加载
2. 未指定 → 按选题特征自动匹配 top 2
3. 最近3篇用过的 → 降权处理

## 快速匹配表

| 选题关键词 | 首选 | 次选 |
| 楼市/房产/政策 | cold-analyst | industry-observer |
| AI/科技/趋势 | industry-observer | cold-analyst |
| 消费/争议/社会 | sharp-journalist | industry-observer |
| 日常/感悟/情绪 | midnight-friend | warm-editor |
| 文化/生活方式 | warm-editor | midnight-friend |
| 段子/吐槽/娱乐 | humor-storyteller | sharp-journalist |
| 技术/编程/开发 | tech-coder | industry-observer |
