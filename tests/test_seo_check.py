import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from seo_check import _keyword_density, _parse_article, check_article, split_keywords  # noqa: E402

GOOD_ARTICLE = """# 失眠的人别再数羊了，试试这套方法

失眠的人别再数羊了。北京大学第六医院的研究显示，强迫入睡反而延长入睡时间。本文给出一套可操作的方法和判断标准。

## 为什么数羊没有用

数羊把注意力放在还没睡着这件事上。中国睡眠研究会数据显示约 45% 的成年人报告过入睡困难。

## 刺激控制法怎么做

固定起床时间、躺下 20 分钟没睡着就离开床、床只用来睡觉、白天补觉不超过 30 分钟。

## 什么情况该去医院

失眠持续超过三个月、每周三次以上、白天明显影响工作，建议去睡眠专科看看。

## 一份可以直接照做的晚间清单

睡前一小时把房间灯光调暗，手机放到床头柜以外的地方。水温 40 度左右的泡脚被不少睡眠门诊列为放松辅助手段，效果因人而异，核心还是固定作息。

睡前不要看时间。反复看钟表会强化对睡眠时长的焦虑，这在中老年群体里尤其常见，属于典型的睡眠焦虑循环。

晚饭不要过晚过饱。胃食管反流是夜间觉醒的常见诱因，晚餐和入睡之间留出至少三小时。

白天光照要足。晨起后到户外接受十分钟以上自然光，有助于校准昼夜节律，这是睡眠医学里性价比最高的免费干预。

咖啡因的半衰期约五小时，下午两点后的咖啡奶茶都会在深夜起效，敏感人群建议中午以后就别碰。

卧室温度控制在 18-22 度。被窝暖、房间凉的组合更容易触发核心体温下降，而体温下降正是入睡的生理信号之一。

别迷信褪黑素。市面剂量普遍偏高，长期服用的安全性数据还不充分，慢性失眠该去医院就去医院。
"""


def test_parse_article_extracts_title_and_subheadings(tmp_path):
    f = tmp_path / "a.md"
    f.write_text(GOOD_ARTICLE, encoding="utf-8")
    title, subheadings, body, paragraphs = _parse_article(str(f))
    assert title == "失眠的人别再数羊了，试试这套方法"
    assert len(subheadings) >= 3
    assert "数羊" in body


def _long_article() -> str:
    filler = "\n\n".join(
        f"## 补充段落{i}\n\n" + "这段补充内容讲的是睡眠细节，包含具体做法和研究出处。" * 8
        for i in range(12)
    )
    return GOOD_ARTICLE + filler


def test_keyword_density_basic():
    body = "失眠怎么办失眠怎么办"
    assert _keyword_density("失眠", body) > 0.3
    assert _keyword_density("不存在词", body) == 0.0


def test_good_article_passes(tmp_path):
    f = tmp_path / "good.md"
    f.write_text(_long_article(), encoding="utf-8")
    report = check_article(str(f), ["失眠", "数羊"])
    assert report["errors"] == 0, [i["detail"] for i in report["issues"]]


def test_clickbait_title_fails(tmp_path):
    f = tmp_path / "bad.md"
    f.write_text(GOOD_ARTICLE.replace("失眠的人别再数羊了，试试这套方法", "震惊！失眠的人别再数羊了，不看后悔一辈子"), encoding="utf-8")
    report = check_article(str(f), [])
    checks = {i["check"] for i in report["issues"] if i["level"] == "error"}
    assert "clickbait" in checks


def test_long_title_flagged(tmp_path):
    f = tmp_path / "long.md"
    f.write_text(GOOD_ARTICLE.replace("失眠的人别再数羊了，试试这套方法", "关于失眠这件事，我们从数羊的由来说到刺激控制法，再到什么情况必须去医院看看"), encoding="utf-8")
    report = check_article(str(f), [])
    assert any(i["check"] == "title_length" and i["level"] == "error" for i in report["issues"])


def test_few_subheadings_flagged(tmp_path):
    f = tmp_path / "flat.md"
    f.write_text("# 标题在这里占位\n\n" + "段落内容。" * 300 + "\n\n## 只有一个小标题\n\n" + "内容。" * 200, encoding="utf-8")
    report = check_article(str(f), [])
    assert any(i["check"] == "subheadings" and i["level"] == "error" for i in report["issues"])


def test_keyword_density_over_limit(tmp_path):
    body = "# 失眠怎么办\n\n" + "失眠怎么办失眠怎么办失眠怎么办。" * 60
    f = tmp_path / "stuff.md"
    f.write_text(body + "\n\n## 小标题一\n\n内容。\n\n## 小标题二\n\n内容。\n\n## 小标题三\n\n内容。", encoding="utf-8")
    report = check_article(str(f), ["失眠怎么办"])
    assert any(i["check"] == "keyword_density" and i["level"] == "error" for i in report["issues"])


def test_suggest_links_from_history(tmp_path):
    history = tmp_path / "history.yaml"
    history.write_text(
        "articles:\n  - title: 失眠自救指南\n    topic: 睡眠健康\n    link: https://mp.weixin.qq.com/s/abc\n  - title: 完全无关的理财入门\n    topic: 理财\n",
        encoding="utf-8",
    )
    report = check_article_text_with_history(tmp_path, history)
    links = report["suggested_links"]
    assert len(links) == 1
    assert links[0]["title"] == "失眠自救指南"


def check_article_text_with_history(tmp_path, history):
    f = tmp_path / "a.md"
    f.write_text(GOOD_ARTICLE, encoding="utf-8")
    return check_article(str(f), ["失眠"], str(history))


def test_split_keywords_handles_comma():
    assert split_keywords("护眼,伤眼") == ["护眼", "伤眼"]


def test_split_keywords_handles_whitespace_and_cjk_punctuation():
    assert split_keywords("护眼 伤眼，眼健康、干眼") == ["护眼", "伤眼", "眼健康", "干眼"]


def test_split_keywords_empty():
    assert split_keywords("") == []
    assert split_keywords("  , ，、 ") == []
