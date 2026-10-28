#!/usr/bin/env python3
"""
Expanded theme library: 99 themes collected from open-source WeChat formatting
projects. Specs are compact dicts; _build converts them into ThemeConfig.

Sources (color/typography parameters extracted from each project):
- ya-pai        github.com/Walksu/ya-pai (11 themes, g01-g11)
- laomao        github.com/laomao-ai/wechat-gzh-publish theme-lab (18 themes)
- gzh-archive   公众号历史存档主题 (21 themes)
- raphael       github.com/liuxiaopai-ai/raphael-publish (5 + 2 extras)
- mdwechat      github.com/laogou717/md-wechat (16 themes)
- ACKS          github.com/shynloc/ACKS-Markdown-Editor (6 main + 7 milestone)
- visual-director  wechat-visual-director themes.json (11 themes)
- mono-blue-editorial / wxmd-modi (1 + 1)

Dark themes are kept for completeness (6 total) but hidden from auto-matching
by default; users who prefer light backgrounds can pick from the other 100.
"""

from theme_base import ThemeConfig

FONT_STACKS = {
    "": ThemeConfig.DEFAULT_SANS,
    "serif": ThemeConfig.SERIF_STACK,
    "mono": ThemeConfig.MONO_MIXED,
    "rounded": ThemeConfig.ROUNDED_STACK,
}


def _spec(**kw):
    return kw


# ---------------------------------------------------------------------------
# ya-pai (11) - github.com/Walksu/ya-pai
# ---------------------------------------------------------------------------
_YAPAI = [
    _spec(id="yapai-bookish", name="书卷随笔", p="#9A5F32", l="#E5DAC8", a="#C9A87C",
          t="#3D362C", g="#8A7F6A", hl="#F1EBDF", bg="#FFFDF8", font="serif", lh=1.9,
          tw=700, m=36, var="editorial", use="书评/散文/文化随笔",
          desc="暖棕衬线书卷气，来自 ya-pai g01-bookish-essay"),
    _spec(id="yapai-tech-doc", name="技术文档", p="#4E6E8E", l="#DDE3E8", a="#6E93B8",
          t="#2E343B", g="#7C858E", hl="#EDF0F3", bg="#FBFCFC", font="", lh=1.8,
          tw=800, m=28, var="clinical", use="技术文档/教程/工具说明",
          desc="灰蓝理性排版，来自 ya-pai g02-tech-doc"),
    _spec(id="yapai-cool-report", name="炫酷报告", p="#4A6B8A", l="#DCE3EA", a="#697581",
          t="#2F3A46", g="#697581", hl="#E8EDF3", bg="#F9FAFC", lh=1.7,
          tw=900, m=32, var="clinical", use="行业报告/数据解读",
          desc="冷灰蓝商务感，来自 ya-pai g03-cool-report"),
    _spec(id="yapai-magazine", name="杂志封面", p="#906332", l="#F3E7D5", a="#C4A47A",
          t="#2D2A26", g="#756B5B", hl="#FBF9F4", bg="#FFFBF4", font="serif", lh=1.75,
          tw=800, m=34, var="editorial", use="深度特稿/人物专访",
          desc="牛皮纸杂志质感，来自 ya-pai g04-magazine-cover"),
    _spec(id="yapai-poster", name="海报裁决", p="#2E5E8C", l="#D8DDE3", a="#7A5E2E",
          t="#1A1A1A", g="#9FB2BF", hl="#F6EBD3", bg="#FFFFFF", lh=1.7,
          tw=800, m=32, var="editorial", use="观点评论/热点裁决",
          desc="金句海报式撞色，来自 ya-pai g05-poster-verdict"),
    _spec(id="yapai-minimal", name="极简真空", p="#383732", l="#EFEEE8", a="#7A7F6E",
          t="#4B4A45", g="#8E8C84", hl="#FAF9F6", bg="#FAF9F6", lh=2.0,
          tw=900, m=40, var="editorial", use="极简随笔/生活方式",
          desc="大留白低饱和极简，来自 ya-pai g06-minimal-void"),
    _spec(id="yapai-lecture", name="讲义纸", p="#587258", l="#E6EDDB", a="#5F6F5F",
          t="#2F352F", g="#9AAA9A", hl="#EFF1E9", bg="#F6F7F0", lh=1.9,
          tw=900, m=34, var="classic", use="知识讲义/课程笔记",
          desc="豆绿讲义纸质感，来自 ya-pai g07-lecture-paper"),
    _spec(id="yapai-timeline", name="时间线", p="#5F7A62", l="#DDE4D8", a="#7D8B82",
          t="#33413A", g="#7D8B82", hl="#EDF1E9", bg="#F8FAF6", lh=1.8,
          tw=800, m=32, var="editorial", use="复盘/年记/事件梳理",
          desc="时间线叙事绿灰调，来自 ya-pai g08-timeline"),
    _spec(id="yapai-newspaper", name="报纸", p="#9A5F32", l="#E5DAC8", a="#C9A87C",
          t="#3D362C", g="#8A7F6A", hl="#F1E5D5", bg="#FFFDF8", font="serif", lh=1.9,
          tw=900, m=32, var="editorial", use="新闻评论/时事解读",
          desc="仿报纸标题排版，来自 ya-pai g09-newspaper"),
    _spec(id="yapai-letter", name="信件", p="#A96F4B", l="#D9C9B8", a="#EBDCCB",
          t="#4B4239", g="#A89C87", hl="#F8F3EC", bg="#F8F3EC", font="serif", lh=1.85,
          tw=700, m=36, var="editorial", use="书信体/情感随笔",
          desc="信纸米色柔和衬线，来自 ya-pai g10-letter"),
    _spec(id="yapai-terminal", name="终端风", p="#28C840", l="#E2E8F0", a="#FEBC2E",
          t="#E8EAED", g="#9AA4B2", hl="#26292E", bg="#17191C", font="mono", lh=1.7,
          tw=900, m=28, var="clinical", use="程序员/数码测评（深色）",
          desc="深色终端等宽风，来自 ya-pai g11-terminal"),
]

# ---------------------------------------------------------------------------
# laomao theme-lab (18) - github.com/laomao-ai/wechat-gzh-publish
# ---------------------------------------------------------------------------
_LAOMAO = [
    _spec(id="laomao-airy-cobalt", name="透气钴蓝", p="#1456F0", l="#A1BBF9", a="#38BDF8",
          t="#1F2329", g="#8F959E", hl="#F1F5FE", bg="#FFFFFF", lh=1.7,
          tw=800, m=32, var="classic", use="科技资讯/产品发布",
          desc="钴蓝+天青双撞色，来自 laomao airy 系列"),
    _spec(id="laomao-airy-graphite", name="透气石墨", p="#373C43", l="#8F959E", a="#646A73",
          t="#1F2329", g="#8F959E", hl="#F7F8FA", bg="#FFFFFF", lh=1.7,
          tw=800, m=32, var="editorial", use="极简评论/极客随笔",
          desc="全石墨灰极简，来自 laomao airy 系列"),
    _spec(id="laomao-airy-violet", name="透气紫罗兰", p="#6E45E2", l="#C5B5F3", a="#8B6EF0",
          t="#1F2329", g="#8F959E", hl="#F6F4FD", bg="#FFFFFF", lh=1.7,
          tw=800, m=32, var="classic", use="设计/创意/潮流",
          desc="紫罗兰渐变轻快，来自 laomao airy 系列"),
    _spec(id="laomao-clay-indigo", name="黏土靛蓝", p="#3E4C7A", l="#E0E2EA", a="#5A6BA8",
          t="#45403A", g="#A39888", hl="#F1F2F6", bg="#FBF8F3", lh=1.7,
          tw=800, m=34, var="classic", use="人文评论/杂谈",
          desc="陶土暖底+靛蓝标题，来自 laomao clay 系列"),
    _spec(id="laomao-clay-pine", name="黏土松绿", p="#3F6B57", l="#CFE0D6", a="#5E8A74",
          t="#45403A", g="#A39888", hl="#F4EDE2", bg="#FBF8F3", lh=1.7,
          tw=800, m=34, var="classic", use="生活/家居/园艺",
          desc="陶土暖底+松绿标题，来自 laomao clay 系列"),
    _spec(id="laomao-clay-terracotta", name="黏土陶土", p="#B8593A", l="#F4E4DF", a="#C97B5E",
          t="#45403A", g="#A39888", hl="#F4E4DF", bg="#FBF8F3", lh=1.7,
          tw=800, m=34, var="classic", use="美食/手作/慢生活",
          desc="陶土橘暖调，来自 laomao clay 系列"),
    _spec(id="laomao-forest-lake", name="森林湖蓝", p="#0E8C8C", l="#D8EDED", a="#12A6A6",
          t="#111111", g="#66756D", hl="#E7F4F4", bg="#FFFFFF", lh=1.7,
          tw=900, m=32, var="classic", use="科普/健康/环保",
          desc="湖蓝孔雀绿，来自 laomao forest 系列"),
    _spec(id="laomao-forest-leaf", name="森林叶绿", p="#12945F", l="#D9EEE5", a="#94CFB7",
          t="#111111", g="#66756D", hl="#E7F4EF", bg="#FFFFFF", lh=1.7,
          tw=900, m=32, var="classic", use="自然/植物/户外",
          desc="清新叶绿，来自 laomao forest 系列"),
    _spec(id="laomao-forest-pine", name="森林松柏", p="#2E6B4F", l="#DEE7E3", a="#4A8A6B",
          t="#111111", g="#66756D", hl="#EAF0ED", bg="#FFFFFF", lh=1.7,
          tw=900, m=32, var="classic", use="职场/成长/方法论",
          desc="沉稳松柏绿，来自 laomao forest 系列"),
    _spec(id="laomao-grid-cobalt", name="网格钴蓝", p="#1F5BD8", l="#DBE5F9", a="#4A7DE8",
          t="#33363B", g="#7A828E", hl="#EFF4FC", bg="#FFFFFF", lh=1.7,
          tw=800, m=30, var="clinical", use="数据报告/榜单",
          desc="网格卡片+钴蓝，来自 laomao grid 系列"),
    _spec(id="laomao-grid-safety", name="网格安全橙", p="#D9541E", l="#F9E4DB", a="#E8774A",
          t="#33363B", g="#7A828E", hl="#FCF3EF", bg="#FFFFFF", lh=1.7,
          tw=800, m=30, var="clinical", use="警示科普/安全提示",
          desc="安全橙高对比，来自 laomao grid 系列"),
    _spec(id="laomao-grid-signal", name="网格信号绿", p="#0E8A5F", l="#D8ECE5", a="#2BAE85",
          t="#33363B", g="#7A828E", hl="#EEF7F4", bg="#FFFFFF", lh=1.7,
          tw=800, m=30, var="clinical", use="效率工具/教程",
          desc="信号绿直角网格，来自 laomao grid 系列"),
    _spec(id="laomao-journal-cherry", name="日志樱桃", p="#BF4946", l="#F6C9C0", a="#D9534F",
          t="#45403A", g="#9A9086", hl="#EFE6D6", bg="#FFFDF7", font="serif", lh=1.7,
          tw=900, m=34, var="editorial", use="日记体/情感记录",
          desc="樱桃红手账日志，来自 laomao journal 系列"),
    _spec(id="laomao-journal-grass", name="日志草绿", p="#3E8E5A", l="#CFE8D8", a="#5CA876",
          t="#45403A", g="#9A9086", hl="#EFE6D6", bg="#FFFDF7", font="serif", lh=1.7,
          tw=900, m=34, var="editorial", use="日记体/田园随笔",
          desc="草绿手账日志，来自 laomao journal 系列"),
    _spec(id="laomao-journal-ink", name="日志墨蓝", p="#3B5BA9", l="#DCE7F2", a="#5A7AC0",
          t="#45403A", g="#9A9086", hl="#EFE6D6", bg="#FFFDF7", font="serif", lh=1.7,
          tw=900, m=34, var="editorial", use="日记体/读书笔记",
          desc="墨蓝手账日志，来自 laomao journal 系列"),
    _spec(id="laomao-masthead-mint", name="报头薄荷", p="#098462", l="#D8EDE7", a="#0A8F6A",
          t="#111111", g="#555555", hl="#EEF7F5", bg="#FFFFFF", lh=1.7,
          tw=900, m=30, var="editorial", use="周报/栏目化内容",
          desc="报头式大标题薄荷绿，来自 laomao masthead 系列"),
    _spec(id="laomao-masthead-signal", name="报头信号红", p="#D72E1D", l="#FADEDB", a="#E0301E",
          t="#111111", g="#555555", hl="#FDF1EF", bg="#FFFFFF", lh=1.7,
          tw=900, m=30, var="editorial", use="快讯/紧急通知",
          desc="报头式信号红，来自 laomao masthead 系列"),
    _spec(id="laomao-masthead-volt", name="报头荧光蓝", p="#2346F0", l="#DCE1FD", a="#4A66F5",
          t="#111111", g="#555555", hl="#F0F2FE", bg="#FFFFFF", lh=1.7,
          tw=900, m=30, var="editorial", use="前沿科技/电竞",
          desc="报头式荧光蓝，来自 laomao masthead 系列"),
]

# ---------------------------------------------------------------------------
# gzh-archive (21)
# ---------------------------------------------------------------------------
_GZH_ARCHIVE = [
    _spec(id="cardnote", name="卡片笔记", p="#6366F1", l="#C7D2FE", a="#4338CA",
          t="#1F2937", g="#6B7280", hl="#EEF2FF", bg="#F9FAFB", lh=1.68,
          tw=800, m=32, var="classic", use="知识卡片/读书笔记",
          desc="靛蓝卡片笔记风"),
    _spec(id="cream", name="奶油", p="#C08552", l="#EDD5B8", a="#E8A87C",
          t="#4A3F35", g="#9C8A76", hl="#FFF8F2", bg="#FAF6F0", lh=1.74,
          tw=700, m=34, var="classic", use="美食/甜品/咖啡探店",
          desc="奶油焦糖暖调"),
    _spec(id="datainfo", name="数据信息", p="#0891B2", l="#CFFAFE", a="#F97316",
          t="#0F172A", g="#64748B", hl="#ECFEFF", bg="#F8FAFC", lh=1.65,
          tw=800, m=30, var="clinical", use="数据新闻/行业分析",
          desc="青蓝+橙双色信息图风"),
    _spec(id="dianlan", name="靛蓝", p="#2563EB", l="#93C5FD", a="#1E40AF",
          t="#1F2937", g="#6B7280", hl="#EFF6FF", bg="#FFFFFF", lh=1.71,
          tw=800, m=32, var="clinical", use="通用科技/互联网",
          desc="经典靛蓝商务"),
    _spec(id="graphite", name="石墨橙", p="#F97316", l="#E4E4E7", a="#27272A",
          t="#27272A", g="#52525B", hl="#F4F4F5", bg="#FFFFFF", lh=1.68,
          tw=800, m=32, var="editorial", use="设计评论/极简内容",
          desc="石墨灰+活力橙点缀"),
    _spec(id="heibaihui", name="黑白灰", p="#111827", l="#F9FAFB", a="#6B7280",
          t="#1A1A1A", g="#6B7280", hl="#F9FAFB", bg="#FFFFFF", lh=1.7,
          tw=900, m=34, var="editorial", use="严肃评论/杂文",
          desc="纯黑白灰杂志感"),
    _spec(id="heikeji", name="黑科技锈", p="#B05A3C", l="#E7D5CC", a="#44403C",
          t="#44403C", g="#78716C", hl="#FAFAF8", bg="#FAFAF8", lh=1.74,
          tw=800, m=32, var="clinical", use="硬件/工业/制造业",
          desc="锈橙金属工业感"),
    _spec(id="hongbai", name="红白经典", p="#DC2626", l="#FECACA", a="#991B1B",
          t="#1C1917", g="#6B7280", hl="#FEE2E2", bg="#FFFFFF", lh=1.71,
          tw=800, m=32, var="classic", use="节日/喜庆/促销",
          desc="红白高对比经典"),
    _spec(id="hupo", name="琥珀", p="#EA580C", l="#FDBA74", a="#C2410C",
          t="#1C1917", g="#78716C", hl="#FFF7ED", bg="#FFFFFF", lh=1.71,
          tw=800, m=32, var="classic", use="美食/秋日主题",
          desc="琥珀橙暖调"),
    _spec(id="jiaotang", name="焦糖", p="#B45309", l="#FCD34D", a="#92400E",
          t="#1C1917", g="#78716C", hl="#FEF3C7", bg="#FFFBEB", lh=1.71,
          tw=700, m=34, var="classic", use="生活方式/暖系内容",
          desc="焦糖黄暖纸感"),
    _spec(id="lvkeji", name="绿科技", p="#10B981", l="#D1FAE5", a="#059669",
          t="#1A1A1A", g="#6B7280", hl="#ECFDF5", bg="#FFFFFF", lh=1.74,
          tw=800, m=32, var="clinical", use="环保科技/新能源",
          desc="翡翠绿科技风"),
    _spec(id="magfeature", name="杂志专题", p="#A87C4F", l="#DDD6C9", a="#C4A47A",
          t="#1A1A1A", g="#756B5B", hl="#FBF9F4", bg="#FBF9F4", font="serif", lh=1.74,
          tw=800, m=34, var="editorial", use="深度专题/特稿",
          desc="暖棕杂志专题排版"),
    _spec(id="meigui", name="玫瑰", p="#E11D48", l="#FDA4AF", a="#BE123C",
          t="#1C1917", g="#78716C", hl="#FFF1F2", bg="#FFFFFF", lh=1.71,
          tw=800, m=32, var="classic", use="情感/两性/美妆",
          desc="玫瑰红浪漫"),
    _spec(id="mistblue", name="雾蓝", p="#7C9EB2", l="#B8CDD9", a="#5A6B74",
          t="#3E4C55", g="#7C9EB2", hl="#F0F5F8", bg="#F0F5F8", lh=1.73,
          tw=700, m=36, var="editorial", use="治愈系/慢生活",
          desc="雾蓝低饱和治愈"),
    _spec(id="qingshiban", name="青石板", p="#0F172A", l="#E2E8F0", a="#475569",
          t="#0F172A", g="#475569", hl="#F8FAFC", bg="#F8FAFC", lh=1.71,
          tw=900, m=32, var="editorial", use="深度报道/纪实",
          desc="青石板冷灰稳重"),
    _spec(id="rich_hongbai", name="浓郁红白", p="#DC2626", l="#FECACA", a="#FFBD2E",
          t="#1C1917", g="#6B7280", hl="#FEE2E2", bg="#FFFFFF", lh=1.71,
          tw=900, m=30, var="editorial", use="促销/大促活动",
          desc="红白+金黄三色浓郁"),
    _spec(id="rich_morandi", name="莫兰迪", p="#B5828C", l="#D4B5A0", a="#8A5A63",
          t="#4A4A4A", g="#6B6B6B", hl="#F2ECEC", bg="#F5F1F0", lh=1.68,
          tw=700, m=36, var="classic", use="美学/穿搭/家居",
          desc="莫兰迪灰粉豆沙"),
    _spec(id="rich_terminal", name="终端风经典", p="#3FB950", l="#C9D1D9", a="#FFBD2E",
          t="#E6EDF3", g="#8B949E", hl="#21262D", bg="#0D1117", font="mono", lh=1.73,
          tw=800, m=28, var="clinical", use="程序员/开源项目（深色）",
          desc="GitHub 暗色终端风"),
    _spec(id="rich_zen", name="浓郁禅意", p="#4A5D52", l="#EEF3F0", a="#8A8F85",
          t="#2B2B2B", g="#64748B", hl="#EEF3F0", bg="#FFFFFF", font="serif", lh=1.75,
          tw=700, m=38, var="classic", use="禅意/茶道/冥想",
          desc="墨绿禅意衬线"),
    _spec(id="tianlan", name="天蓝", p="#0EA5E9", l="#BAE6FD", a="#0284C7",
          t="#1F2937", g="#6B7280", hl="#F0F9FF", bg="#FFFFFF", lh=1.79,
          tw=800, m=32, var="classic", use="旅行/航空/亲子",
          desc="晴天天蓝轻快"),
    _spec(id="zise", name="紫色", p="#7C3AED", l="#C4B5FD", a="#5B21B6",
          t="#1F2937", g="#6B7280", hl="#F5F3FF", bg="#FFFFFF", lh=1.71,
          tw=800, m=32, var="classic", use="科技前沿/神秘学",
          desc="紫罗兰渐变"),
]

# ---------------------------------------------------------------------------
# mono-blue-editorial + wxmd-modi (2)
# ---------------------------------------------------------------------------
_SINGLE = [
    _spec(id="mono-blue-editorial", name="墨蓝刊读", p="#1B3A8C", l="#D9D9D9", a="#6B6B6B",
          t="#1A1A1A", g="#8A8A8A", hl="#F5F5F5", bg="#FFFFFF", font="serif", lh=1.75,
          tw=900, m=34, var="editorial", use="深度长文/专栏",
          desc="墨蓝大标题编辑风衬线"),
    _spec(id="wxmd-modi", name="墨滴蓝", p="#0284C7", l="#7DD3FC", a="#0EA5E9",
          t="#1F2328", g="#4B5563", hl="#F1F5F9", bg="#F8FAFC", lh=1.75,
          tw=800, m=32, var="classic", use="通用技术/教程",
          desc="墨滴编辑器天蓝改良版"),
]

# ---------------------------------------------------------------------------
# raphael (7) - github.com/liuxiaopai-ai/raphael-publish
# ---------------------------------------------------------------------------
_RAPHAEL = [
    _spec(id="rp-stripe", name="硅谷商务", p="#635BF5", l="#EEF0FF", a="#425466",
          t="#425466", g="#8792A2", hl="#EEF0FF", bg="#F6F9FC", lh=1.7,
          tw=800, m=32, var="clinical", use="SaaS/产品发布/BP",
          desc="Stripe 风靛紫商务"),
    _spec(id="rp-retro", name="羊皮纸复古", p="#8C2211", l="#EFE5CC", a="#6B4423",
          t="#2B2621", g="#6B5D4F", hl="#EFE5CC", bg="#F4ECD8", font="serif", lh=1.7,
          tw=800, m=34, var="editorial", use="历史/人文/藏书",
          desc="羊皮纸底+深砖红"),
    _spec(id="rp-dracula", name="暗夜赛博", p="#BD93F9", l="#44475A", a="#FF79C6",
          t="#F8F8F2", g="#9AA5CE", hl="#44475A", bg="#282A36", lh=1.7,
          tw=800, m=30, var="clinical", use="游戏/二次元（深色）",
          desc="Dracula 配色"),
    _spec(id="rp-sakura", name="樱花", p="#C44569", l="#FCEEF2", a="#E8A0B4",
          t="#4A3F4F", g="#9C8A96", hl="#FCEEF2", bg="#FEF7F9", lh=1.7,
          tw=800, m=32, var="classic", use="美妆/情感/春季",
          desc="樱花粉底"),
    _spec(id="rp-bauhaus", name="包豪斯", p="#E30613", l="#FFF4D6", a="#004D9F",
          t="#1A1A1A", g="#555555", hl="#FFF4D6", bg="#FFFFFF", lh=1.65,
          tw=900, m=30, var="editorial", use="设计/艺术/展览",
          desc="包豪斯红黄蓝三原色"),
    _spec(id="rp-claude", name="燕麦卡其", p="#B75C3D", l="#EDE6D8", a="#6B5D4F",
          t="#2B2B2B", g="#8A8578", hl="#F1EDE3", bg="#F8F6F0", lh=1.7,
          tw=700, m=36, var="editorial", use="AI/知识分享/随笔",
          desc="燕麦色暖底赤陶橙"),
    _spec(id="rp-lavender", name="薰衣草", p="#6B4C9A", l="#E5DBF5", a="#7C5CAD",
          t="#3D3155", g="#8A7FA8", hl="#F5F0FF", bg="#F5F0FF", lh=1.7,
          tw=700, m=36, var="classic", use="心理/疗愈/女性成长",
          desc="薰衣草紫淡底"),
]

# ---------------------------------------------------------------------------
# md-wechat (16) - github.com/laogou717/md-wechat
# ---------------------------------------------------------------------------
_MDWECHAT = [
    _spec(id="swiss-index", name="瑞士索引", p="#E00019", l="#FFE3E6", a="#111111",
          t="#111111", g="#686868", hl="#FDECEC", bg="#FFFFFF", lh=1.78,
          tw=900, m=30, var="clinical", use="杂志目录/快讯榜单",
          desc="瑞士国际主义红黑"),
    _spec(id="night-film", name="夜航胶片", p="#FF7A2D", l="#13203A", a="#FCA85C",
          t="#C6CBD2", g="#7A8699", hl="#13203A", bg="#07111F", lh=1.82,
          tw=800, m=32, var="clinical", use="影视/影评（深色）",
          desc="深夜蓝底橙色胶片感"),
    _spec(id="white-cube", name="白盒展签", p="#143BD1", l="#E8EDFB", a="#202020",
          t="#202020", g="#8A8A8A", hl="#EEF2FB", bg="#FFFFFF", lh=1.84,
          tw=800, m=36, var="editorial", use="艺术评论/展讯",
          desc="美术馆白盒+克莱因蓝标签"),
    _spec(id="pixel-quest", name="像素任务", p="#16D9E5", l="#0A1A3E", a="#3AE8F5",
          t="#D9E1EE", g="#8A97B8", hl="#0A1A3E", bg="#050D25", font="mono", lh=1.78,
          tw=800, m=30, var="clinical", use="游戏攻略/玩家向（深色）",
          desc="像素游戏深蓝青"),
    _spec(id="velocity-report", name="疾速赛报", p="#E01824", l="#FBD9DB", a="#171717",
          t="#171717", g="#757575", hl="#FCEAEA", bg="#F7F7F5", lh=1.72,
          tw=900, m=28, var="clinical", use="体育赛事/竞速战报",
          desc="赛车红白高对比"),
    _spec(id="klein", name="克莱因蓝", p="#002FA7", l="#D6DEF8", a="#111111",
          t="#111111", g="#5A5A5A", hl="#E8EDFB", bg="#FFFFFF", lh=1.8,
          tw=900, m=32, var="editorial", use="艺术/潮流/观点",
          desc="国际克莱因蓝"),
    _spec(id="xuanzhi", name="宣纸", p="#C2352B", l="#F0E3D0", a="#8C2820",
          t="#2B2B2B", g="#9A8E7C", hl="#F7F4EC", bg="#F7F4EC", font="serif", lh=2.0,
          tw=700, m=38, var="editorial", use="国学/书法/诗词",
          desc="宣纸底+朱砂红，双倍行距"),
    _spec(id="morandi-green", name="莫兰迪绿", p="#7D8C7A", l="#DCE3DA", a="#5A6857",
          t="#3A4238", g="#8A9687", hl="#EDEFEA", bg="#FFFFFF", lh=1.85,
          tw=700, m=36, var="classic", use="自然/ gardening/慢生活",
          desc="莫兰迪灰绿"),
    _spec(id="midnight-gold", name="午夜蓝金", p="#1B2A4A", l="#C9A96A", a="#B08D4F",
          t="#1F2937", g="#6B7280", hl="#EEF1F8", bg="#FFFFFF", lh=1.8,
          tw=900, m=32, var="editorial", use="财经/商业评论",
          desc="午夜蓝+香槟金"),
    _spec(id="mint-soda", name="薄荷气泡", p="#2FBF9B", l="#C9EDE2", a="#26A584",
          t="#2F4A42", g="#7FA89D", hl="#E4F6F0", bg="#FFFFFF", font="rounded", lh=1.8,
          tw=700, m=34, var="classic", use="育儿/校园/清新内容",
          desc="薄荷绿圆体气泡感"),
    _spec(id="brick-industry", name="红砖工业", p="#B5402F", l="#F3E0D8", a="#7A2A1E",
          t="#333333", g="#8A8078", hl="#F5E6DF", bg="#FFFFFF", lh=1.75,
          tw=800, m=30, var="clinical", use="城市观察/建筑",
          desc="红砖赤陶工业风"),
    _spec(id="blueprint", name="蓝图", p="#7FD4FF", l="#1A3E75", a="#A8D8F5",
          t="#EEF3FB", g="#9FB8D8", hl="#1A3E75", bg="#16407F", lh=1.85,
          tw=800, m=30, var="clinical", use="工程/架构图解（深色）",
          desc="工程蓝图深蓝底"),
    _spec(id="lemon-sea", name="柠檬海盐", p="#F5C518", l="#FDF3CD", a="#2F6F6A",
          t="#3D3A33", g="#8A8578", hl="#FDF3CD", bg="#FFFFFF", lh=1.8,
          tw=800, m=32, var="classic", use="美食测评/探店",
          desc="柠檬黄+海盐青"),
    _spec(id="hk-neon", name="港风霓虹", p="#23483C", l="#D8CFBB", a="#B08D4F",
          t="#3D3A33", g="#8A8578", hl="#F6F1E7", bg="#F6F1E7", font="serif", lh=1.85,
          tw=900, m=32, var="editorial", use="影评/城市文化/怀旧",
          desc="港风墨绿+米金"),
    _spec(id="latte", name="咖啡拉花", p="#6F4E37", l="#E3D5C5", a="#8A664A",
          t="#4A3A30", g="#A08A78", hl="#F0E8DF", bg="#FAF6F1", font="rounded", lh=1.85,
          tw=700, m=36, var="classic", use="咖啡/烘焙/生活美学",
          desc="拿铁棕圆体暖底"),
    _spec(id="candy-pop", name="糖果波普", p="#FF5DA2", l="#FFD6E8", a="#4FA8D8",
          t="#4A4A5A", g="#8A8A98", hl="#FFE8F2", bg="#FFFFFF", font="rounded", lh=1.8,
          tw=800, m=32, var="classic", use="潮流/娱乐/年轻化内容",
          desc="糖果粉蓝波普"),
]

# ---------------------------------------------------------------------------
# ACKS (13) - github.com/shynloc/ACKS-Markdown-Editor
# ---------------------------------------------------------------------------
_ACKS = [
    _spec(id="acks-gold", name="金色经典", p="#F0B849", l="#FDF8E8", a="#C9971F",
          t="#3F3F3F", g="#6B6B6B", hl="#FDF8E8", bg="#FFFFFF", lh=1.8,
          tw=800, m=32, var="editorial", use="知识付费/课程讲义",
          desc="琥珀金标题白底"),
    _spec(id="acks-receipt", name="票据复古", p="#C0392B", l="#F5E9D8", a="#8C5A2B",
          t="#3F3F3F", g="#8A8078", hl="#FAF0E0", bg="#FAF6EF", lh=1.8,
          tw=800, m=30, var="editorial", use="清单/账单/消费测评",
          desc="牛皮纸票据风"),
    _spec(id="acks-dopamine", name="多巴胺", p="#FF5A2E", l="#FFE5DA", a="#FF3D1F",
          t="#3F3F3F", g="#8A8078", hl="#FFE5DA", bg="#FFFDF9", lh=1.8,
          tw=800, m=32, var="classic", use="生活方式/潮流种草",
          desc="多巴胺亮橙"),
    _spec(id="acks-maximalism", name="极繁叠层", p="#D31B5E", l="#FADCE5", a="#8C1F3F",
          t="#3F3F3F", g="#8A8078", hl="#FADCE5", bg="#FFFDF5", lh=1.8,
          tw=900, m=30, var="editorial", use="时尚/艺术表达",
          desc="极繁主义玫红"),
    _spec(id="acks-collage", name="拼贴手帐", p="#2F6B4F", l="#EAE0C8", a="#B08D4F",
          t="#3F3F3F", g="#8A8078", hl="#EFE6CE", bg="#F3E9D2", lh=1.8,
          tw=800, m=32, var="classic", use="手帐/旅行日记",
          desc="手帐拼贴纸感"),
    _spec(id="acks-guochao", name="先锋国潮", p="#C3272B", l="#F5E8D0", a="#B08D4F",
          t="#3F3F3F", g="#8A8078", hl="#F5E8D0", bg="#FAF6EF", lh=1.8,
          tw=900, m=32, var="editorial", use="国潮/文创/传统节日",
          desc="朱红+描金国潮"),
    _spec(id="ms-social", name="社交长图", p="#F26419", l="#FFE3CE", a="#D9531E",
          t="#333333", g="#8A8078", hl="#FFE3CE", bg="#FFF7F0", lh=1.8,
          tw=800, m=30, var="classic", use="社交分享/种草长图",
          desc="社交橙长图风"),
    _spec(id="ms-aireport", name="AI报告", p="#6D4DFF", l="#E5DEFE", a="#8C6FFF",
          t="#333333", g="#8A8078", hl="#E5DEFE", bg="#FAFAFF", lh=1.8,
          tw=800, m=32, var="clinical", use="AI 工具/产品测评",
          desc="电紫 AI 报告风"),
    _spec(id="ms-euro", name="欧式古典", p="#9C7A3C", l="#EBDDC0", a="#B09455",
          t="#3F3F3F", g="#8A8078", hl="#EBDDC0", bg="#F6F1E7", font="serif", lh=1.8,
          tw=800, m=34, var="editorial", use="西方艺术/音乐/历史",
          desc="欧式古铜金衬线"),
    _spec(id="ms-cnclassic", name="中式古典", p="#9E2B25", l="#EFE0CC", a="#B08D4F",
          t="#3F3F3F", g="#8A8078", hl="#EFE0CC", bg="#F3ECE0", font="serif", lh=1.8,
          tw=800, m=34, var="editorial", use="传统文化/历史人文",
          desc="绛红仿古宣纸"),
    _spec(id="ms-cnvertical", name="中式竖排", p="#8C2820", l="#E8DCC4", a="#A0522D",
          t="#3F3F3F", g="#8A8078", hl="#E8DCC4", bg="#EFE7D6", font="serif", lh=1.8,
          tw=800, m=34, var="editorial", use="古籍/书法/茶道",
          desc="赭石仿竖排古卷"),
    _spec(id="ms-poster", name="前卫海报", p="#FF2D00", l="#FAF0A0", a="#111111",
          t="#1A1A1A", g="#555555", hl="#FAF0A0", bg="#F2F000", lh=1.7,
          tw=900, m=28, var="editorial", use="活动宣传/先锋内容",
          desc="荧光黄海报底"),
    _spec(id="ms-academic", name="学术论文", p="#7A1F2B", l="#EFE8E4", a="#5A3A40",
          t="#333333", g="#8A8078", hl="#EFE8E4", bg="#FCFCFA", font="serif", lh=1.8,
          tw=800, m=34, var="clinical", use="论文解读/学术科普",
          desc="学术绛红纸白"),
]

# ---------------------------------------------------------------------------
# visual-director (11) - wechat-visual-director themes.json
# ---------------------------------------------------------------------------
_VISUAL_DIRECTOR = [
    _spec(id="vd-light-reading", name="轻盈阅读", p="#52766F", l="#F1F7F5", a="#D98268",
          t="#283532", g="#6A7A74", hl="#F1F7F5", bg="#FFFDF9", lh=1.85,
          tw=800, m=34, var="classic", use="散文/随笔/轻阅读",
          desc="灰绿+陶橙点缀轻盈底"),
    _spec(id="vd-warm-humanist", name="温暖人文", p="#8E4B3B", l="#F8EEE9", a="#D66B4D",
          t="#342B28", g="#8A7A72", hl="#F8EEE9", bg="#FFFCF7", lh=1.85,
          tw=800, m=34, var="editorial", use="人文故事/纪实",
          desc="赭红暖调人文"),
    _spec(id="vd-youth-campus", name="青春校园", p="#2D6CDF", l="#EEF4FF", a="#F06F8F",
          t="#20304A", g="#6A7A92", hl="#EEF4FF", bg="#FFFEFB", lh=1.8,
          tw=800, m=32, var="classic", use="校园/青春/成长",
          desc="学院蓝+樱花粉"),
    _spec(id="vd-editorial", name="编辑对比", p="#243B53", l="#EEF2F3", a="#B85C47",
          t="#202B33", g="#5A6A76", hl="#EEF2F3", bg="#FFFDF8", lh=1.8,
          tw=900, m=32, var="editorial", use="深度报道/专栏",
          desc="藏蓝强对比编辑风"),
    _spec(id="vd-structured", name="理性网格", p="#526A43", l="#F0F2E7", a="#C66A51",
          t="#26332F", g="#6A766A", hl="#F0F2E7", bg="#FFFDF8", lh=1.8,
          tw=800, m=30, var="clinical", use="方法论/框架拆解",
          desc="橄榄绿网格理性"),
    _spec(id="vd-future-tech", name="未来科技", p="#304B8E", l="#F3F5FC", a="#FF826E",
          t="#24304F", g="#6A7692", hl="#F3F5FC", bg="#FEFEFF", lh=1.8,
          tw=800, m=32, var="clinical", use="前沿科技/互联网",
          desc="星际蓝+珊瑚橙"),
    _spec(id="vd-oriental", name="新中式雅集", p="#7A2E2E", l="#F4F1E7", a="#B58A4A",
          t="#302C27", g="#8A8276", hl="#F4F1E7", bg="#FFFDF7", font="serif", lh=1.85,
          tw=800, m=36, var="editorial", use="新中式/雅致生活",
          desc="绛红描金新中式"),
    _spec(id="vd-pop-poster", name="波普海报", p="#14213D", l="#EEF1F7", a="#F2385A",
          t="#18213A", g="#5A6480", hl="#EEF1F7", bg="#FDFDF8", lh=1.75,
          tw=900, m=30, var="editorial", use="潮流/市集/青年文化",
          desc="藏青+波普红"),
    _spec(id="vd-natural-atlas", name="自然图鉴", p="#3F6B57", l="#EDF2E9", a="#A8674E",
          t="#2E3A33", g="#6A7A6E", hl="#EDF2E9", bg="#FBFAF3", lh=1.85,
          tw=800, m=34, var="classic", use="自然科普/博物",
          desc="森林绿博物图鉴"),
    _spec(id="vd-business", name="商业画报", p="#17324D", l="#EFF2E8", a="#ED6A5A",
          t="#203243", g="#5A6A7A", hl="#EFF2E8", bg="#F7F4EB", lh=1.8,
          tw=900, m=32, var="editorial", use="商业分析/职场",
          desc="海军蓝+珊瑚红画报"),
    _spec(id="vd-cinematic", name="电影叙事", p="#553B5D", l="#F2E9DD", a="#D35A54",
          t="#332B36", g="#7A6E7A", hl="#F2E9DD", bg="#FAF4E8", font="serif", lh=1.85,
          tw=800, m=34, var="editorial", use="影评/叙事长文",
          desc="暮紫电影质感"),
]

# 汇总全部 spec（保持分组顺序）——保留为来源存档，便于日后按需扩充
_ALL_SPECS = (
    _YAPAI + _LAOMAO + _GZH_ARCHIVE + _SINGLE + _RAPHAEL
    + _MDWECHAT + _ACKS + _VISUAL_DIRECTOR
)

# 去重：同一种结构化版式只保留 1 套代表主题，剔除仅配色不同的重复项。
# 选择标准：浅色底 + 设计辨识度 + 版式契合度。
REPRESENTATIVE_IDS = {
    "cardnote",                # classic   圆角徽章
    "yapai-bookish",           # editorial 杂志编辑
    "yapai-tech-doc",          # clinical  临床直角
    "laomao-masthead-signal",  # magazine  色块刊头
    "mistblue",                # minimal   极简
    "qingshiban",              # newspaper 报纸
    "yapai-poster",            # poster    海报
    "yapai-cool-report",       # sidebar   侧栏书页
}

LIBRARY_SPECS = [s for s in _ALL_SPECS if s["id"] in REPRESENTATIVE_IDS]

# 版式变体分配（structural layout，非仅配色）：
# classic 圆角徽章 / editorial 杂志编辑 / clinical 临床直角 / magazine 色块刊头
# minimal 极简 / newspaper 报纸 / poster 海报 / sidebar 侧栏书页
VARIANT_OVERRIDES = {
    # ya-pai
    "yapai-bookish": "editorial", "yapai-tech-doc": "clinical", "yapai-cool-report": "sidebar",
    "yapai-magazine": "magazine", "yapai-poster": "poster", "yapai-minimal": "minimal",
    "yapai-lecture": "sidebar", "yapai-timeline": "sidebar", "yapai-newspaper": "newspaper",
    "yapai-letter": "editorial", "yapai-terminal": "clinical",
    # laomao
    "laomao-airy-cobalt": "classic", "laomao-airy-graphite": "minimal", "laomao-airy-violet": "magazine",
    "laomao-clay-indigo": "editorial", "laomao-clay-pine": "sidebar", "laomao-clay-terracotta": "magazine",
    "laomao-forest-lake": "classic", "laomao-forest-leaf": "minimal", "laomao-forest-pine": "sidebar",
    "laomao-grid-cobalt": "clinical", "laomao-grid-safety": "clinical", "laomao-grid-signal": "clinical",
    "laomao-journal-cherry": "editorial", "laomao-journal-grass": "editorial", "laomao-journal-ink": "editorial",
    "laomao-masthead-mint": "magazine", "laomao-masthead-signal": "magazine", "laomao-masthead-volt": "magazine",
    # gzh-archive
    "cardnote": "classic", "cream": "magazine", "datainfo": "clinical", "dianlan": "classic",
    "graphite": "minimal", "heibaihui": "editorial", "heikeji": "clinical", "hongbai": "poster",
    "hupo": "magazine", "jiaotang": "editorial", "lvkeji": "clinical", "magfeature": "magazine",
    "meigui": "editorial", "mistblue": "minimal", "qingshiban": "newspaper", "rich_hongbai": "poster",
    "rich_morandi": "editorial", "rich_terminal": "clinical", "rich_zen": "minimal",
    "tianlan": "classic", "zise": "classic",
    # single
    "mono-blue-editorial": "editorial", "wxmd-modi": "clinical",
    # raphael
    "rp-stripe": "clinical", "rp-retro": "newspaper", "rp-dracula": "clinical", "rp-sakura": "editorial",
    "rp-bauhaus": "poster", "rp-claude": "editorial", "rp-lavender": "minimal",
    # md-wechat
    "swiss-index": "poster", "night-film": "clinical", "white-cube": "minimal", "pixel-quest": "clinical",
    "velocity-report": "poster", "klein": "poster", "xuanzhi": "editorial", "morandi-green": "minimal",
    "midnight-gold": "magazine", "mint-soda": "classic", "brick-industry": "clinical", "blueprint": "clinical",
    "lemon-sea": "magazine", "hk-neon": "magazine", "latte": "editorial", "candy-pop": "poster",
    # ACKS
    "acks-gold": "editorial", "acks-receipt": "magazine", "acks-dopamine": "poster", "acks-maximalism": "poster",
    "acks-collage": "magazine", "acks-guochao": "editorial", "ms-social": "classic", "ms-aireport": "clinical",
    "ms-euro": "editorial", "ms-cnclassic": "editorial", "ms-cnvertical": "sidebar", "ms-poster": "poster",
    "ms-academic": "editorial",
    # visual-director
    "vd-light-reading": "minimal", "vd-warm-humanist": "editorial", "vd-youth-campus": "magazine",
    "vd-editorial": "newspaper", "vd-structured": "clinical", "vd-future-tech": "clinical",
    "vd-oriental": "sidebar", "vd-pop-poster": "poster", "vd-natural-atlas": "magazine",
    "vd-business": "magazine", "vd-cinematic": "editorial",
}

SOURCE_CREDITS = {
    "yapai": "github.com/Walksu/ya-pai",
    "laomao": "github.com/laomao-ai/wechat-gzh-publish",
    "gzh-archive": "公众号存档主题集",
    "rp": "github.com/liuxiaopai-ai/raphael-publish",
    "mdwechat": "github.com/laogou717/md-wechat",
    "acks": "github.com/shynloc/ACKS-Markdown-Editor",
    "ms": "github.com/shynloc/ACKS-Markdown-Editor (milestone)",
    "vd": "wechat-visual-director",
}


def _source_of(identifier: str) -> str:
    for prefix, label in (
        ("yapai-", "yapai"), ("laomao-", "laomao"), ("rp-", "rp"),
        ("acks-", "acks"), ("ms-", "ms"), ("vd-", "vd"),
    ):
        if identifier.startswith(prefix):
            return label
    if identifier in ("mono-blue-editorial", "wxmd-modi"):
        return identifier
    return "gzh-archive"


def _build(spec: dict) -> ThemeConfig:
    return ThemeConfig(
        identifier=spec["id"],
        display_name=spec["name"],
        primary_color=spec["p"],
        primary_light=spec["l"],
        accent_color=spec["a"],
        text_color=spec["t"],
        secondary_color=spec["g"],
        highlight_bg=spec["hl"],
        underline_css=(
            f"border-bottom:2px solid {spec['l']};font-weight:600"
        ),
        section_margin=spec["m"],
        line_height=spec["lh"],
        title_weight=spec["tw"],
        body_weight=400,
        font_family=FONT_STACKS.get(spec.get("font", ""), ThemeConfig.DEFAULT_SANS),
        page_bg=spec["bg"],
        letter_spacing=0.5,
        suitable_for=spec["use"],
        description=f"{spec['desc']}（{spec['use']}）",
        style_variant=VARIANT_OVERRIDES.get(spec["id"], spec["var"]),
        source=_source_of(spec["id"]),
    )


def _build_all() -> dict:
    themes = {}
    for spec in LIBRARY_SPECS:
        cfg = _build(spec)
        themes[cfg.identifier] = cfg
    return themes


LIBRARY_THEMES = _build_all()

# 深色主题清单（自动内容匹配时跳过，用户显式选择仍可用）
DARK_THEME_IDS = {"yapai-terminal", "rich_terminal", "rp-dracula",
                  "night-film", "pixel-quest", "blueprint"}


def _hex_luma(hex_color: str) -> float:
    """计算 hex 颜色亮度（0-1），用于判断深浅色。"""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return 1.0
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def is_dark_theme(identifier: str) -> bool:
    cfg = LIBRARY_THEMES.get(identifier)
    if cfg:
        return _hex_luma(cfg.page_bg) < 0.5
    return False


def list_library_themes(include_dark: bool = True) -> list:
    """返回主题库清单（identifier, display_name, suitable_for）。"""
    out = []
    for tid, cfg in LIBRARY_THEMES.items():
        if not include_dark and tid in DARK_THEME_IDS:
            continue
        out.append({
            "identifier": tid,
            "display_name": cfg.display_name,
            "suitable_for": cfg.suitable_for,
            "description": cfg.description,
            "source": cfg.source,
        })
    return out
