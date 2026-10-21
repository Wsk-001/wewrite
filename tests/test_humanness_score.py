import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from humanness_score import (  # noqa: E402
    score_article,
    score_flag_words,
    score_negation_pairs,
    score_formulaic_rhetoric,
)


def test_flag_words_clean_scores_full():
    r = score_flag_words("这活儿说白了就是多喝水，没别的门道。")
    assert r["score"] == 1.0
    assert "0 flag words" in r["detail"]


def test_flag_words_penalizes_each_hit():
    r = score_flag_words("因而我们需要重视。因此建议早睡。")
    assert r["score"] < 1.0
    assert "flag words" in r["detail"]


def test_negation_pairs_tolerates_one():
    r = score_negation_pairs("这不是运气问题，而是方法问题。")
    assert r["score"] == 1.0


def test_negation_pairs_penalizes_repeats():
    text = "这不是A，而是B。不在于C，而在于D。不是E，而是F。"
    r = score_negation_pairs(text)
    assert r["score"] < 1.0


def test_formulaic_rhetoric_tolerates_one():
    r = score_formulaic_rhetoric("它从早到晚都在变化。")
    assert r["score"] == 1.0


def test_formulaic_rhetoric_penalizes_repeats():
    text = "不仅快，而且稳，更重要的是省。不仅A，而且B，更重要的是C。"
    r = score_formulaic_rhetoric(text)
    assert r["score"] < 1.0


def test_tier2_includes_new_checks():
    r = score_article("# 标题\n\n这是一段普通的正文内容，用来触发评分流程。" * 20)
    checks = r["tier2"]["_summary"]
    names = [k for k in r["tier2"].keys() if not k.startswith("_")]
    assert "flag_words" in names
    assert "negation_pairs" in names
    assert "formulaic_rhetoric" in names
    assert r["tier2"]["_summary"]["count"] == 8


def test_flag_words_table_has_no_duplicates():
    from humanness_score import FLAG_WORDS

    assert len(FLAG_WORDS) == len(set(FLAG_WORDS))
    # 这个词曾重复出现，导致一处命中被扣两次
    assert FLAG_WORDS.count("归根结底") == 1


def test_flag_words_catches_words_named_in_writing_guide():
    """writing-guide/SKILL 点名要求 0 命中的词，必须真的能被检测到。"""
    from humanness_score import score_flag_words

    for word in ("值得注意", "值得注意的是", "不可忽视", "毋庸置疑", "归根结底", "由此可见"):
        assert score_flag_words(f"讲真，{word}这事没那么简单。")["score"] < 1.0, word


def test_overlapping_patterns_count_one_structure():
    """同一句只算一处结构——两条 pattern 命中同段文本不应各记一次。"""
    r = score_negation_pairs("这不是懒而是病。")
    assert r["detail"].startswith("1 negation-pair")
    assert r["score"] == 1.0


def test_distinct_structures_still_count_separately():
    r = score_negation_pairs("不是A而是B，也不是C而是D。")
    assert r["detail"].startswith("2 negation-pair")


def test_calibration_helpers_exist():
    """这两个函数曾被调用但从未定义，--calibrate 与 --json --verbose 直接崩。"""
    from humanness_score import _calibration_verdict, _print_calibration

    result = {"composite_score": 30.0}
    verdict = _calibration_verdict(result)
    assert verdict["composite_score"] == 30.0
    assert verdict["baselines"]["target_range"]["in_expected"] is True
    _print_calibration(result)  # 不应抛异常
