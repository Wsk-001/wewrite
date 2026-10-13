# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

[User Instruction Summary]
- Date: 2026-10-10
- Context: 献血科普文配图出现 AI bug（血袋贴上臂、采血管方向像输血、游离针头），用户要求建立检测流程
- Instructions:
  - 以后每次 AI 生成配图，插入文章前必须先做 AI bug 视觉检测，检测通过才允许上传使用
  - 检测方式：用视觉分析工具（image_analysis）或直接读图自检；服务不可用时读图人工过一遍
  - 检测清单（沉淀自本次案例）：医疗设备重力/管路方向逻辑（血袋必须低于穿刺点）、游离器械比划、操作步骤合理性、手指数量/肢体畸变、图内文字乱码、物体漂浮穿模、场景与文章事实匹配
  - 发现 bug 后修 prompt 重新生成并复检，通过后再发布
  - 场景类配图生成前，先搜索真实流程细节（如献血：肘窝穿刺、止血带、握力球、血袋放采血秤），把正确细节写进 prompt

[Project Knowledge Summary]
- Date: 2026-10-10
- Context: 配置图片生成 API 并实测调通
- Category: Environment Configuration
- Instructions:
  - 图片 API 走 MoAark 平台（https://api.moark.com/v1），OpenAI 兼容 /images/generations 端点，模型 z-image-turbo
  - MoAark 尺寸参数名是 image_size（不是 size，传 size 会 400"参数无效"）；响应返回 b64_json 而非 url，toolkit/image_gen.py 已做兼容
  - z-image-turbo 固定输出 1024x1024 方图，忽略尺寸参数；image_gen.py 已加中心裁剪逻辑适配封面比例
  - SiliconFlow 和 ModelScope 的端点对该 key 均返回认证失败，确认走 MoAark

[Project Knowledge Summary]
- Date: 2026-10-10
- Context: 微信公众号 API 调试
- Category: Operations & Deployment
- Instructions:
  - 公众号「小科普oao」AppID wx9deec3eb05e1647e，凭据已写入 config.yaml（已 gitignore）
  - 微信 API 要求调用方 IP 在白名单内，沙箱出口 IP 123.56.157.253 需加入公众号后台白名单（errcode 40164 表示未加）
  - 发布流程：python3 toolkit/cli.py publish article.md --cover cover.jpg 推送草稿箱，后台人工确认发布

[Project Knowledge Summary]
- Date: 2026-10-10
- Context: 从账号 9 篇已发文章提炼写作与配图风格
- Category: Workflow & Collaboration
- Instructions:
  - 「小科普oao」是健康科普账号，9 篇参考文章存于 references/source_articles/ref-01~09.md
  - 写作人格 personas/xiaokepuoao.yaml，写作参数 writing-config.yaml 已按实测指纹校准
  - 配图风格规范（三条路线 + z-image-turbo prompt 模板）在 references/xiaokepuoao-style.md
  - scripts/fetch_article.py 曾有 img/br/hr void 元素被提前 return 吞掉的 bug，已修复；抓公众号文章先确认 md 里有图再分析

[Project Knowledge Summary]
- Date: 2026-10-13
- Context: 联网调研 2026 微信公众号生态规则，用于 WeWrite 流程优化
- Category: Operations & Deployment
- Instructions:
  - AI 内容标识是强制合规项：《人工智能生成合成内容标识办法》2025-09 施行，2026 年已处置 1.3 万+未标注账号，微信「应标未标可直至封号」；AI 配图必须加「AI生成」标注，发布时勾选平台 AI 声明
  - 微信 2026-03《运营规范》新增「非真人自动化创作行为」条款，官方合规口径：AI 初稿需人工深加工（补真实案例、加个人观点、去 AI 味）
  - 2026 推荐流算法权重：完读率约 35% > 分享转发约 30% > 收藏约 20% > 互动质量约 15%；阅读进度不足 30% 退出被标记低质
  - 搜一搜 SEO 关键阈值：核心词进标题前 12 字、关键词密度 2-3%、小标题 >=3、标题党词按作弊处理
  - 健康科普红线：不得虚构病例/疗效结果、禁用「保证根治」类断言；第一人称场景开场用泛化场景
  - datacube getarticletotal 有 add_to_fav_count（收藏）字段，fetch_stats.py 目前未采集
