import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from compliance_check import check_article  # noqa: E402

CLEAN_ARTICLE = """
# 失眠的人别再数羊了

北京大学第六医院的研究显示，强迫入睡会升高皮层唤醒水平。

## 刺激控制法

中国睡眠研究会发布的指南收录了四条核心做法，其中固定起床时间排在第一位。
"""


def test_clean_article_passes():
    report = check_article(CLEAN_ARTICLE)
    assert report["passed"] is True
    assert report["errors"] == 0


def test_curative_claims_detected():
    report = check_article("这套方法保证根治，零风险。")
    hits = report["results"][0]["hits"]
    rules = {h["rule"] for h in hits}
    assert "保证根治" in rules
    assert "零风险" in rules
    assert report["errors"] > 0


def test_fabricated_case_detected():
    report = check_article("我二姨查出高血压，吃了秘方三个月就痊愈了。")
    fab = next(r for r in report["results"] if r["check"] == "fabricated_cases")
    assert len(fab["hits"]) == 1
    assert fab["hits"][0]["level"] == "error"


def test_diversion_and_scare_detected():
    report = check_article("想知道配方的扫码进群。再不调理就会死，马上转发。")
    checks = {r["check"]: r["hits"] for r in report["results"]}
    assert checks["diversion"]
    assert checks["scare_tactics"]


def test_non_case_relative_mention_not_flagged():
    report = check_article("我妈转发过一篇养生文，里面说熬夜伤肝，和疾控的数据对得上。")
    fab = next(r for r in report["results"] if r["check"] == "fabricated_cases")
    assert len(fab["hits"]) == 0


def test_warnings_do_not_fail():
    report = check_article("他说这个方法立竿见影。")
    assert report["passed"] is True
    assert report["warnings"] == 1


def test_code_blocks_ignored():
    report = check_article("```\n保证根治零风险\n```")
    assert report["errors"] == 0
