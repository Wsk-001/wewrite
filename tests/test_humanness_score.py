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
