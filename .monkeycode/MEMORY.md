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
- Date: 2026-10-14
- Context: 用户要求写文章时，Agent 每次发布前都停下来问是否推送，用户明确表示不需要
- Instructions:
  - 成文后不要每次询问是否发布，直接推送到公众号草稿箱
  - 仅在真正出错或需要用户提供信息时才停下确认

[User Instruction Summary]
- Date: 2026-10-14
- Context: 用户要求修改配图规则
- Instructions:
  - 图内**允许出现文字**，但必须清晰、正确、可读，准确表达图中含义
  - **严禁**乱码、错字、乱拼字符、无意义英文串、伪文字；严禁文字与实际内容不符
  - 拿不准就用提示词重生成或整图去掉文字——宁可整图不带文字，也不允许出现乱码

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
  - 公众号「小科普oao」AppID wx9deec3eb05e1647e，凭据已写入 config/config.yaml（已 gitignore）
  - 微信 API 要求调用方 IP 在白名单内，沙箱出口 IP 123.56.157.253 需加入公众号后台白名单（errcode 40164 表示未加）
  - 发布流程：python3 toolkit/cli.py publish article.md --cover cover.jpg 推送草稿箱，后台人工确认发布

[Project Knowledge Summary]
- Date: 2026-10-10
- Context: 从账号 9 篇已发文章提炼写作与配图风格
- Category: Workflow & Collaboration
- Instructions:
  - 「小科普oao」是健康科普账号，9 篇参考文章存于 references/examples/source_articles/ref-01~09.md
  - 写作人格 personas/xiaokepuoao.yaml，写作参数 config/writing-config.yaml 已按实测指纹校准
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

[Project Knowledge Summary]
- Date: 2026-10-16
- Context: B 方案目录重构（配置/资料/脚本各归各位）
- Category: Workflow & Collaboration
- Instructions:
  - 配置集中在 config/：config.yaml（微信/图片凭据，gitignore）、style.yaml（账号风格）、writing-config.yaml（写作参数），各带 .example；加载器 toolkit/config.py 与 scripts/diagnose.py 优先 config/，兼容旧根目录
  - references/ 分 5 组：pipeline/（主管道文档）、compliance/（合规SEO）、guides/（指南命令）、examples/（范文库，gitignore 用户内容）；visual/ 已随孤儿文档删除
  - scripts/ 保持扁平，索引见 scripts/README.md；不分子目录，避免 import 与调用路径回归
  - dist/ 只跟踪 dist/openclaw、dist/codex 与两个发布 zip（dist/wewrite-*.zip）；改规则/主题后需重建 dist
  - build_openclaw.py 的 config 目录只打包 *.example，不打包用户真实配置
