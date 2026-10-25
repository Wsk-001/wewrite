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
- Context: 用户两次修改配图规则（图内文字规范；献血配图 AI bug 后要求建立检测流程）
- Instructions:
  - AI 生成配图插入文章前必须先做视觉检测：用 image_analysis 或直接读图自检，服务不可用时人工过一遍；发现 bug 修 prompt 重生成并复检，通过才允许上传
  - 检测清单：医疗设备重力/管路方向（血袋必须低于穿刺点）、游离器械比划、操作步骤合理性、手指数量/肢体畸变、图内文字乱码、物体漂浮穿模、场景与文章事实匹配
  - 图内允许出现文字，但必须清晰正确、与内容一致；严禁乱码、错字、乱拼字符、无意义英文串、伪文字；拿不准就重生成或去掉文字——宁可无字也不许乱码
  - 场景类配图生成前先搜真实流程细节（如献血：肘窝穿刺、止血带、握力球、血袋放采血秤），把正确细节写进 prompt

[Project Knowledge Summary]
- Date: 2026-10-10
- Context: 配置图片生成 API 并实测调通
- Category: Environment Configuration
- Instructions:
  - 图片 API 走 MoAark 平台（https://api.moark.com/v1），OpenAI 兼容 /images/generations 端点，模型 z-image-turbo
  - MoAark 尺寸参数走 width/height 双字段（均为 16 的倍数，否则 400）；`size` 报「参数无效」，`aspect_ratio`/`image_size` 会被静默忽略并恒返 1024x1024 方图；响应是 b64_json 而非 url，toolkit/image_gen.py 已兼容
  - 请求尺寸与实际返回比例差 >2% 时 _warn_size_mismatch 会告警；比例匹配时不再裁切，落盘前用 _ensure_output_format 保证字节格式与扩展名一致
  - SiliconFlow 和 ModelScope 的端点对该 key 均返回认证失败，确认走 MoAark

[Project Knowledge Summary]
- Date: 2026-10-20
- Context: 公众号发布链路与运营规则（API 调试 → 生态调研 → 预检加固）
- Category: Operations & Deployment
- Instructions:
  - 公众号「小科普oao」AppID wx9deec3eb05e1647e，凭据在 config/config.yaml（gitignore）；API 要求出口 IP 白名单，沙箱 IP 123.56.157.253（errcode 40164 表示未加）
  - 发布流程：python3 toolkit/cli.py publish article.md --cover cover.jpg 推草稿箱，后台人工确认发布
  - AI 内容标识是强制合规项：《人工智能生成合成内容标识办法》2025-09 施行，微信「应标未标可直至封号」；AI 配图须加「AI生成」标注并在发布时勾选平台 AI 声明
  - 微信 2026-03《运营规范》新增「非真人自动化创作行为」条款，合规口径是 AI 初稿需人工深加工（真实案例、个人观点、去 AI 味）
  - 2026 推荐流权重：完读率约 35% > 分享约 30% > 收藏约 20% > 互动约 15%，阅读进度不足 30% 退出会被标记低质；搜一搜阈值：核心词进标题前 12 字、密度 2-3%、小标题 ≥3，标题党按作弊处理
  - 健康科普红线：不得虚构病例/疗效，禁用「保证根治」类断言；第一人称场景开场用泛化场景
  - toolkit/cli.py publish 的 _validate_publish_inputs 先于任何网络调用预检：文章/封面缺失、--cover 与 --no-cover 冲突、正文本地图不存在、引用数 ≠ --expect-images、正文无本地图引用 → exit 2 并列出文件；--force 跳过图片检查
  - 图片路径解析兼容原样相对路径、相对文章目录、仅文件名回退；预检与真实上传必须共用 _resolve_image_path，否则预检通过、上传静默丢图；图片引用要 unquote 百分号编码
  - SKILL Step 1 检查 .venv，缺失则跑 install.sh（失败提示装 python3-venv）；Step 8 固定带 --expect-images 4，缺图直接拒推
  - humanness_range 单一来源是 config/writing-config.yaml，humanness_score.py 输出 humanness_range 与 in_range，SKILL 不用硬编码阈值
  - 改 SKILL/references 后重建 dist/openclaw（build_openclaw.py；改 SKILL 时两个 dist 都要重建，只建一个会不一致）；dist/*.zip 是发布归档，不随日常改动重建
  - datacube getarticletotal 有 add_to_fav_count（收藏）字段，fetch_stats.py 未采集

[Project Knowledge Summary]
- Date: 2026-10-16
- Context: 风格提炼 + B 方案目录重构（配置/资料/脚本各归各位）
- Category: Workflow & Collaboration
- Instructions:
  - 「小科普oao」健康科普账号，参考文章 references/examples/source_articles/ref-01~09.md；写作人格 personas/xiaokepuoao.yaml，配图风格（三条路线 + z-image-turbo prompt 模板）在 references/xiaokepuoao-style.md
  - 配置集中在 config/：config.yaml（微信/图片凭据，gitignore）、style.yaml（账号风格）、writing-config.yaml（写作参数），各带 .example；toolkit/config.py 与 scripts/diagnose.py 优先 config/ 并兼容旧根目录
  - references/ 分 5 组：pipeline/、compliance/、guides/、examples/（范文库，gitignore 用户内容）；scripts/ 保持扁平，索引见 scripts/README.md
  - dist/ 只跟踪 dist/openclaw、dist/codex 与两个发布 zip；build_openclaw.py 的 config 目录只打包 *.example，不打包真实配置
  - scripts/fetch_article.py 曾有 img/br/hr void 元素被提前 return 吞掉的 bug，已修复；抓公众号文章先确认 md 里有图再分析

[User Instruction Summary]
- Date: 2026-10-17
- Context: 用户要求联网调研「AI 味」资料并对比自身写作提示词，明确选择 C 档改造
- Instructions:
  - 反 AI 检测走 C 档：脚本硬检测 + 提示词规则 + 结构打破清单，三管齐下
  - 破折号（——）尽量少用，全篇控制在 0-2 处
  - 红旗词（AI 高频书面语/连接词）必须加进脚本硬检测，不能只做提示

[Project Knowledge Summary]
- Date: 2026-10-17
- Context: 实现 C 档反 AI 改造（漏洞：红旗词/humanizer 三项）
- Category: Testing Methods
- Instructions:
  - humanness_score.py Tier2 由 5 项扩为 8 项：新增 flag_words（红旗词，每命中扣 0.25，目标 0）、negation_pairs（否定对举"不是X而是Y"，容差 1 次，超出每次扣 0.4）、formulaic_rhetoric（三段式排比/虚假范围"从X到Y"，容差 1 次，超出每次扣 0.5）
  - 三项新检测为「负向检查」（0 命中=得分高=更人），不加 bell-curve 中心（加中心会反转成"越干净越像 AI"，是错的）
  - 区间随每次检测逻辑修复重算：2026-10-17 新增三项后由 [26,40] 下调；2026-10-21 修 banned_words 反转后为 [20,40]（14 篇 20.1-39.0）；2026-10-22 修 5 处校准缺陷后为 [16,36]（14 篇 17.6-34.2）
  - composite = (1 - humanness)*100，分数越低越人；Tier2 检查数变化会平移 absolute 刻度，改动检测项后必须用历史文章重新校准区间
  - 新增 tests/test_humanness_score.py（7 例）；全量 pytest 81 passed
  - 破折号中断句法同时计入 broken_sentences，过度依赖会让节奏刻意

[Project Knowledge Summary]
- Date: 2026-10-21
- Context: 借鉴 AI-Search-Hub「一个问题分发多个搜索源」思路，给选题加公众号检索源
- Category: Operations & Deployment
- Instructions:
  - 新增 scripts/wechat_search.py（搜狗微信搜索 weixin.sogou.com/weixin?type=2）：唯一公开可用、无需登录/浏览器的公众号文章检索途径，WebSearch 与热搜榜都覆盖不到
  - 搜狗按相关度排序、结果混着 2016 年的老文；时间参数 tsn=1/2/3/4 在本沙箱返回 0 条或 302，不可用 → 近期筛选靠「多翻页 + 客户端按 days_ago 过滤」（--days 90 --pages 3）
  - 结果页结构：ul.news-list > li，标题 h3 a、摘要 p.txt-info、公众号 span.all-time-y2、时间 script timeConvert('epoch')；引号/&amp; 需 unescape
  - 真实链接需同 session 二次请求 /link?url=...，页面用 `url += '...'` 分片拼接（@ 为占位符要删），--resolve 才追；不加则给的是搜狗跳转链
  - 反爬识别：页面含 antispider/请输入验证码 → 脚本 exit 3、blocked=true，流程须退化为 WebSearch 并注明该源缺失
  - references/pipeline/topic-selection.md 新增「检索源分发」表：公众号生态→wechat_search.py、热点→fetch_hotspots.py、公开网页/文献→WebSearch；SKILL Step 2 同步加运行命令
  - 新增 tests/test_wechat_search.py（7 例，离线解析）；全量 pytest 98 passed

[Project Knowledge Summary]
- Date: 2026-10-21
- Context: 全量 BUG 排查（静态检查 + 边界用例 + 计分逻辑复核）
- Category: Troubleshooting & Debugging
- Instructions:
  - humanness_score.py 的 _print_calibration / _calibration_verdict 从建库起就只有调用没有定义 → `--calibrate` 与 `--json --verbose` 必崩 NameError；已补实现（基于 CALIBRATION_BASELINES 输出期望区间与实际判定）
  - `--json` 必须做到 stdout 纯 JSON：verbose 报告与 --calibrate 表格改道 stderr（contextlib.redirect_stdout），否则 SKILL Step 5 的 `--json` 无法解析
  - 否定对举/排比原来逐 pattern 累加：`不是A而是B` 同时命中 `不是…而是` 与 `不是…是` 被计 2 次，把「容差 1 次」变成「一次就罚」；改用 _count_structure_spans 合并重叠 span 后计数
  - FLAG_WORDS 曾重复收录「归根结底」（一处命中扣两次），并有错字「母庸置疑」；BANNED_WORDS 同类错字「莫庸置疑」「值得注意的 是」；均已修正并补入值得注意/不可忽视
  - 修完检测逻辑必须重跑全部历史文章复核区间：当前 14 篇为 17.6-34.2，全部落在 [16,36]
  - cli publish 预检与真实上传必须共用 _resolve_image_path（含仅文件名回退），否则预检通过、上传静默丢图；图片引用要 unquote 百分号编码
  - wechat_search：只有命中 antispider/验证码标记才算 blocked；「无结果列表」不能谎报反爬（改为 warning 字段）；翻页间隔 1s；不要用 apparent_encoding 覆盖已声明的 utf-8
  - 搜狗会因连续查询把出口 IP 打入验证码状态（blocked 持续一段时间），此时脚本 exit 3 并提示退化为 WebSearch；选题阶段每个候选只查一次，沙箱直连可用、无需代理
  - 改 SKILL.md 后要同时重建两个 dist：build_openclaw.py 与 build_codex.py，只重建一个会导致 dist 不一致
  - `_BELL_CURVE_CHECKS` 只放「过犹不及」类指标；单调指标（如 banned_words，命中越少越好）进去会被 overshoot 惩罚反转——0 命中 raw=1.0 直接判 0 分，比 1 命中还低
  - config.yaml 的 author 在根级，`cmd_publish` 曾只读 `wechat` 段导致草稿作者栏为空；改配置读取处要确认层级（根级 fallback 已补）
  - 图片落盘必须让字节格式与扩展名一致：`_center_crop_to_ratio` 比例匹配时原样返回 provider 的 PNG，会写出「.jpg 装 PNG」；微信靠嗅探仍显示，但从返回 URL 可验证（`mmbiz_png` 说明上传的是 PNG，`mmbiz_jpg` 才对），已在 generate_image 落盘前统一转码
  - PNG 存照片体积是 JPEG 的 10 倍（1.7-2.1MB vs 160-230KB），微信图片上限 2MB，转码同时也是体积兜底
   - 调 `draft/get` 校验草稿时用 `r.content.decode("utf-8")`：微信返回 `Content-Type: text/plain` 无 charset，requests 会按 latin-1 解出乱码，误判成文章编码坏了；正文 `media_id` 写错或删稿用 `draft/delete`（errcode 0 即成功）

[Project Knowledge Summary]
- Date: 2026-10-21
- Context: 用户反馈配图环节耗时很久；实测定位为串行生成 + 无效重试逻辑，已改批量并发
- Category: Build Methods
- Instructions:
  - 单张图 API 实测仅 ~7s（z-image-turbo 1024 方图 6.6s + 下载 0.5s），慢的根源是 5 张图逐张串行跑
  - image_gen.py 已支持 --batch <json>（[{prompt, output, size?}]）并发生成，--workers 默认 5，stdout 出 {ok, failed} JSON；配图环节必须批量并发，逐张串行算流程错误
  - 原 attempt 循环 except 后直接 break，重试从未生效；已改为 _generate_with_retry 同 provider 退避重试 2 次（2s/4s），重试耗尽才换链上下一个
  - 所有 provider 请求改用分离式超时 (CONNECT_TIMEOUT=10, READ_TIMEOUT=120)，坏网关时 10s 内快速失败换下一家，避免傻等 120s
  - 实测生成耗时：1024 方图 ~7s、article 1792x1024 ~12s、cover 1920x816 ~13s；5 张并发总耗时 = 最慢一张 ≈ 15s，尺寸对单张耗时影响不大
  - 配图环节另一个大头是视觉自检：SKILL Step 6 已规定自检必须并行读图/并行建任务，只允许「批量生成→并发自检→批量重生成→复检」一轮循环，超两轮要回头修提示词模板
  - 2026-10-22 全流程验收发现并修复 5 处校准缺陷：range 钟形误罚（与 stddev 互斥，range 大反被压 0）、real_sources 漏认「10 月 22 日」「科普里写得很清楚」类真实出处、negative_emotion 目标 20% 与账号指纹 2-10% 冲突、flag_words 误报单独出现的「可见」（改用精确词「由此可见」）、seo --keywords 不认空格分隔。修复后全库 14 篇重评 17.6-34.2（均值 25.7），humanness_range 由 [20,40] 调为 [16,36]，negative_emotion_floor 0.12→0.10。同日新文章《卸载5次又装回》全流程验证：初稿 33.0 分按短板清单（自我修正/词温档位/短行/破句）一轮优化至 20.3 PASS，配图 5 张并发 21.8s 一轮过自检，正文 2044 字（写作前定各节字数预算后未超标）
  - z-image-turbo 生成含中文文字的图约 1/5 概率出伪文字残留，配图统一走「图内无文字」路线最稳

[Project Knowledge Summary]
- Date: 2026-10-24（2026-10-25 更新：旧 converter 已移除，gzh-design 成唯一自动化路径）
- Context: 集成 gzh-design 主题（程序化实现，自动编号+关键词标记+封面智能拆分），随后完成六主题化重构
- Category: Build Methods
- Instructions:
  - toolkit/gzh_converter.py 程序化实现 gzh-design skill 核心能力：自动章节编号（01/02/03 渐变徽章）、关键词提取（jieba TF-IDF + 下划线标记）、封面标题智能拆分（核心主题高亮、其余白色）、签名区、span leaf 包裹与微信合规
  - 2026-10-25 重构：converter.py/theme.py/themes 目录（51 套 YAML）已删除，WeChatConverter 不复存在；排版唯一自动化路径是 gzh_converter.py + theme_configs.py（6 套主题：moyu-green/red-white/graphite-minimal/zen-whitespace/moyu-ticket/olive-journal），`--theme <name>` 选择，config theme 默认 moyu-green
  - 主题配置集中在 toolkit/theme_configs.py 的 THEMES 字典；GzhConverter 全参数化读 ThemeConfig，加新主题只需补一条配置
  - 验证方式：发布用裸 HTML（convert 返回的 result.html）跑 gzh-design validate 合规校验为 PASS（2 个 WARNING：渐变+半角标点，技术能力限制）；`cli.py preview` 产物含浏览器包装外壳（<style>/<div class="phone">），直接拿去校验必然报 3 个 ERROR，属预期
  - 封面卡片顶栏只放分类名不放日期；底部绿条显示账号名（author 从 config 贯穿到 cover）；章节标题手写的「01 」前缀会被自动剥离防与徽章重复（仅当数字等于当前徽章号才剥，防误伤「10 秒测试」类标题）；文末不放任何签名/名片/求三连文案（用户明确：微信原生名片组件无法嵌入文章 HTML，模拟卡片也不要，2026-10-25 确认）
  - jieba 已加入 requirements.txt（gzh_converter 关键词提取依赖）；validate() 在 skill_root 缺失时安全返回 False（gzh-design skill 是 gitignore 的本地依赖，.ai-ready/skills/gzh-design/）
  - 关键词提取用 jieba.analyse.extract_tags TF-IDF，取 top 8（idf_only=False 兼顾词频与通用性）；标记逻辑：精确词匹配，不拆分多字词，避免断词被标记
  - 封面标题拆分规则：提取主语/宾语/核心名词为高亮词（jieba 分词后在 title 首次出现的位置），最多 3 个；其余拆分为 runs（每 2-3 字一段），适配封面设计器 cover_runs 排版
  - gzh-design skill 外部依赖（含源 git 仓库）已从项目移除，.gitignore 排除 .ai-ready/skills/gzh-design/ 目录
  - image_gen.py 增加 OpenAI provider 健壮性：先检查 r.status_code 再解析 JSON（避免 502/503 坏网关时解 HTML 出 JSONDecodeError）
