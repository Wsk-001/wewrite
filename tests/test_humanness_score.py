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


def test_banned_words_score_is_monotonic_after_calibration():
    """禁用词越少分越高——0 命中曾被钟形校准压成 0 分，比 1 命中还低。"""
    from humanness_score import score_banned_words, calibrate_tiers

    clean = {"banned_words": score_banned_words("这句话用了禁词的替代写法。"), "_summary": {}}
    dirty = {"banned_words": score_banned_words("首先，其次，总之，综上所述，值得注意的是，毋庸置疑。"), "_summary": {}}
    assert clean["banned_words"]["score"] > dirty["banned_words"]["score"]

    calibrate_tiers(clean, dirty)
    assert clean["banned_words"]["score"] > dirty["banned_words"]["score"]
    assert clean["banned_words"]["score"] == 1.0


def test_sentence_range_large_no_longer_bell_penalized():
    """range 越大越像人。曾因钟形校准把 range=78 压到 0 分，与 stddev≥15 互斥。"""
    from humanness_score import score_sentence_length_range, calibrate_tiers
    from humanness_score import _BELL_CURVE_CHECKS

    assert "sentence_length_range" not in _BELL_CURVE_CHECKS
    long = "这句稍微长一些，用来撑开句子长度的上界，也顺带制造一点节奏差。"
    text = "\n".join(["短。", long, "又是一句很短的话。", long, "短句。", long])
    r = score_sentence_length_range(text)
    assert r["score"] >= 0.8, r


def test_real_sources_recognizes_date_and_authority_citation():
    """“央视新闻 10 月 22 日”“云南卫健委的科普里写得很清楚”属真实出处。"""
    from humanness_score import score_real_sources

    text = "央视新闻 10 月 22 日发了条提醒。云南卫健委的科普里写得很清楚：别乱揉。"
    r = score_real_sources(text)
    assert "0 real-source" not in r["detail"], r["detail"]
    count = int(r["detail"].split()[0])
    assert count >= 2, r["detail"]


def test_real_sources_counts_overlaps_once():
    from humanness_score import score_real_sources

    r = score_real_sources("王主任医师指出，熬夜确实伤眼。")
    assert r["detail"].startswith("1 real-source"), r["detail"]


def test_negative_emotion_target_matches_persona_fingerprint():
    """账号指纹负面情绪 2-10%，目标线由 20% 下调到 10%。"""
    from humanness_score import score_negative_emotion_ratio

    text = "。".join(["今天又熬夜了，烦"] + ["这是普通的一句描述"] * 11) + "。"
    r = score_negative_emotion_ratio(text)
    assert "target ≥10%" in r["detail"]
    assert r["score"] >= 0.7, r


def test_flag_words_no_false_positive_on_visible_importance():
    from humanness_score import score_flag_words

    assert score_flag_words("它的重要性可见，别忽视。")["score"] == 1.0
    assert score_flag_words("由此可见，问题不在眼睛。")["score"] < 1.0
