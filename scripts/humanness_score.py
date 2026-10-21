#!/usr/bin/env python3
"""
Humanness scoring for WeWrite articles.

Three-tier evaluation aligned with writing-guide.md's anti-AI checklist:

  Tier 1 (Statistical, 50%): 6 checks measuring statistical properties
         that AI detectors analyze (burstiness, distribution, variance).
  Tier 2 (Pattern, 30%):     8 checks for specific linguistic patterns
         (banned words, broken sentences, real sources, word temperature,
          self-correction, flag words, negation pairs, formulaic rhetoric).
  Tier 3 (LLM, 20%):        Semantic analysis done by the agent in SKILL.md
         (style drift, density waves, coherence). Passed via --tier3 flag.

Each check outputs a continuous 0-1 score and maps to a writing-config
parameter, so the optimization loop knows which knob to turn.

Standalone mode (no --tier3): weights redistribute to T1=62.5%, T2=37.5%.

Usage:
    python3 humanness_score.py article.md                    # single score
    python3 humanness_score.py article.md --verbose          # detailed report
    python3 humanness_score.py article.md --json             # full JSON
    python3 humanness_score.py article.md --json --tier3 0.7 # with agent score
"""

import argparse
import contextlib
import json
import re
import sys
from pathlib import Path

BANNED_WORDS = ["\u9996\u5148", "\u5176\u6b21", "\u518d\u8005", "\u6700\u540e", "\u603b\u4e4b", "\u7efc\u4e0a\u6240\u8ff0", "\u603b\u800c\u8a00\u4e4b", "\u6b64\u5916", "\u53e6\u5916", "\u4e0e\u6b64\u540c\u65f6", "\u4e0d\u4ec5\u5982\u6b64", "\u66f4\u91cd\u8981\u7684\u662f", "\u5728\u6b64\u57fa\u7840\u4e0a", "\u4f5c\u4e3a\u4e00\u4e2a", "\u8ba9\u6211\u4eec", "\u503c\u5f97\u6ce8\u610f\u7684\u662f", "\u9700\u8981\u6307\u51fa\u7684\u662f", "\u4e0d\u53ef\u5426\u8ba4", "\u6bcb\u5eb8\u7f6e\u7591", "\u4f17\u6240\u5468\u77e5", "\u4e8b\u5b9e\u4e0a", "\u663e\u800c\u6613\u89c1", "\u53ef\u4ee5\u8bf4", "\u4ece\u67d0\u79cd\u610f\u4e49\u4e0a\u8bf4", "\u975e\u5e38\u91cd\u8981", "\u81f3\u5173\u91cd\u8981", "\u4e0d\u8a00\u800c\u55bb", "\u5177\u6709\u91cd\u8981\u610f\u4e49", "\u53d1\u6325\u7740\u91cd\u8981\u4f5c\u7528", "\u610f\u4e49\u6df1\u8fdc", "\u5f71\u54cd\u6df1\u8fdc", "\u5f15\u53d1\u4e86\u5e7f\u6cdb\u5173\u6ce8", "\u5f15\u8d77\u4e86\u70ed\u70c8\u8ba8\u8bba", "\u603b\u7684\u6765\u8bf4", "\u7efc\u5408\u6765\u770b", "\u7531\u6b64\u53ef\u89c1", "\u4e0d\u96be\u53d1\u73b0", "\u901a\u8fc7\u4ee5\u4e0a\u5206\u6790", "\u6b63\u5982\u6211\u4eec\u6240\u770b\u5230\u7684"]

REAL_SOURCE_PATTERNS = [r'[A-Z][a-z]+\s+[A-Z][a-z]+', r'[\u4e00-\u9fff]{2,4}(?:\u8868\u793a|\u6307\u51fa|\u8ba4\u4e3a|\u5199\u9053|\u63d0\u5230|\u8bf4\u8fc7)', r'(?:\u636e|\u6839\u636e|\u6765\u81ea)\s*[\u4e00-\u9fff]+(?:\u62a5\u544a|\u6570\u636e|\u7814\u7a76|\u8c03\u67e5)', r'20[12]\d\s*\u5e74', r'\d+(?:\.\d+)?%', r'(?:\u4ebf|\u4e07)\s*(?:\u7f8e\u5143|\u5143|\u4eba\u6c11\u5e01)']

NEGATIVE_MARKERS = ["\u5931\u671b", "\u7cdf\u7cd5", "\u626f", "\u5751", "\u70c2", "\u5dee\u52b2", "\u5d29\u6e83", "\u5410\u69fd", "\u9a82", "\u6012", "\u70e6", "\u7126\u8651", "\u62c5\u5fe7", "\u4e0d\u6ee1", "\u6076\u5fc3", "\u53ef\u6015", "\u53ef\u60b2", "\u53ef\u7b11", "\u79bb\u8c31", "\u5c34\u5c2c", "\u65e0\u8bed", "\u8822", "\u60e8", "\u4e8f", "\u5371", "\u7edd\u671b", "\u8ff7\u832b", "\u5fc3\u7d2f", "\u4e27", "\u540e\u6094", "\u540e\u6015", "\u5fc3\u5bd2", "\u9a97", "\u5ffd\u60a0", "\u5272\u83dc\u8359", "\u5957\u8def", "\u753b\u5927\u997c", "\u6d17\u8111", "\u767d\u8d39", "\u767d\u642d", "\u6ca1\u620f", "\u9ec4\u4e86", "\u51c9\u4e86", "\u5e9f\u4e86", "\u50bb", "\u5929\u771f", "\u5403\u4e8f", "\u81ea\u5609", "\u6253\u8138", "\u5475\u5475", "\u597d\u5427", "\u884c\u5427", "\u771f\u670d\u4e86", "\u592a\u626f\u4e86", "\u8bf4\u5b9e\u8bdd\u6211\u5f88\u5931\u671b", "\u641e\u4ec0\u4e48", "\u4e0d\u9760\u8c31", "\u53d7\u4e0d\u4e86", "\u53d7\u591f\u4e86", "\u60f3\u54ed", "\u4f24\u5fc3", "\u82e6\u54c8\u54c8", "\u5f97\u8fc7\u4e14\u8fc7"]

COMMON_ADVERBS = ["\u975e\u5e38", "\u5341\u5206", "\u6781\u5176", "\u7279\u522b", "\u76f8\u5f53", "\u5c24\u5176", "\u683c\u5916", "\u66f4\u52a0", "\u8d8a\u6765\u8d8a", "\u9010\u6e10", "\u4e0d\u65ad", "\u59cb\u7ec8", "\u4e00\u76f4", "\u5df2\u7ecf", "\u6b63\u5728", "\u5c06\u8981", "\u53ef\u80fd", "\u5927\u6982", "\u6216\u8bb8", "\u4f3c\u4e4e", "\u663e\u7136", "\u660e\u663e", "\u786e\u5b9e", "\u679c\u7136", "\u5c45\u7136", "\u7adf\u7136", "\u7b80\u76f4", "\u51e0\u4e4e", "\u5b8c\u5168", "\u7edd\u5bf9", "\u5fc5\u7136"]

COLD_WORDS = ["\u8fb9\u9645", "\u8ba4\u77e5\u8d1f\u8377", "\u4fe1\u606f\u4e0d\u5bf9\u79f0", "\u8def\u5f84\u4f9d\u8d56", "\u5546\u4e1a\u6a21\u5f0f", "\u751f\u6001\u7cfb\u7edf", "\u589e\u91cf", "\u6280\u672f\u6808", "\u6807\u51c6\u5316", "\u7ed3\u6784\u6027", "\u89c4\u6a21\u5316", "\u62a4\u57ce\u6cb3", "\u98de\u8f6e", "\u95ed\u73af", "\u8d5b\u9053", "\u58c1\u5792", "\u65b9\u6cd5\u8bba", "\u5e95\u5c42\u903b\u8f91", "\u7b2c\u4e00\u6027\u539f\u7406", "\u6760\u6746", "\u590d\u5229", "ROI", "PMF", "\u4ee3\u8fd0\u8425", "\u4f9b\u7ed9\u4fa7", "\u9700\u6c42\u4fa7"]

WARM_WORDS = ["\u8bf4\u767d\u4e86", "\u5176\u5b9e\u5427", "\u8bb2\u771f", "\u8bf4\u5b9e\u8bdd", "\u5766\u767d\u8bb2", "\u61c2\u7684\u90fd\u61c2", "\u600e\u4e48\u8bf4\u5462", "\u8001\u5b9e\u8bf4", "\u8fd9\u4e48\u8bf4\u5427", "\u4f60\u60f3\u554a", "\u522b\u6025", "\u6162\u6162\u6765", "\u6709\u610f\u601d\u7684\u662f", "\u597d\u73a9\u7684\u662f", "\u5de7\u7684\u662f", "\u8bf4\u6765\u8bdd\u957f", "\u8bdd\u8bf4\u56de\u6765"]

HOT_WORDS = ["DNA\u52a8\u4e86", "\u683c\u5c40\u6253\u5f00", "\u9065\u9065\u9886\u5148", "\u5377", "\u5185\u5377", "\u70b8\u4e86", "\u6740\u75af\u4e86", "\u5403\u7070", "\u51e1\u5c14\u8d5b", "\u6807\u9898\u515a", "\u8eba\u5e73", "\u6446\u70c2", "\u7834\u9632", "\u4e0a\u5934", "\u5185\u8017", "\u84b8\u53d1", "\u51fa\u5708", "\u964d\u7ef4\u6253\u51fb", "\u5f2f\u9053\u8d85\u8f66"]

WILD_WORDS = ["\u6574\u631a\u597d", "\u4e0d\u9760\u8c31", "\u778e\u6298\u817e", "\u6401\u8fd9\u513f", "\u7cca\u5f04", "\u626f", "\u5617", "\u82e6\u54c8\u54c8", "\u50bb\u4e4e\u4e4e", "\u7a00\u91cc\u7cca\u6d82", "\u5f97\u4e86\u5427", "\u7b97\u4e86\u5427", "\u6454\u4e86\u8dcc", "\u4ea4\u5b66\u8d39", "\u8e29\u5751", "\u7ffb\u8f66", "\u683d\u4e86"]

SELF_CORRECTION_PATTERNS = [r'\u4e0d\u5bf9[\uff0c,]', r'\u51c6\u786e\u8bf4', r'\u7b97\u4e86', r'\u8bf4\u9519\u4e86', r'\u5176\u5b9e\u4e0d\u662f', r'\u6211\u8bb0\u6df7\u4e86', r'\u5e94\u8be5\u8bf4', r'\u66f4\u51c6\u786e\u5730\u8bf4', r'\uff08[^\uff09]{4,}\uff09']

BROKEN_SENTENCE_PATTERNS = [r'\u2014\u2014(?!.*[\u3002\uff0c\uff01\uff1f])', r'\.{3,}|\u2026', r'\u4e0d\u5bf9[\uff0c,]', r'\u7b97\u4e86']

# \u7ea2\u65d7\u8bcd\uff08AI \u9ad8\u9891\u4e66\u9762\u8bed/\u8fde\u63a5\u8bcd\uff09\u2014\u2014\u51fa\u73b0\u5373\u6263\u5206\u3002\u4e0e BANNED_WORDS
# \u91cd\u5408\u65f6\u4ee5\u672c\u8868\u4e3a\u51c6\uff08\u672c\u8868\u9762\u5411\u201cAI \u5473\u5019\u9009\u66ff\u6362\u201d\uff0cBANNED_WORDS \u9762\u5411\u201c\u7a7a\u8bdd\u5957\u8bdd\u201d\uff09\u3002
# \u6765\u6e90\uff1a\u7fd4\u5b87\u5de5\u4f5c\u6d41\u300cAI \u5473\u516b\u5927\u7279\u5f81\u300d\u7ea2\u65d7\u8bcd\u8868 + qu-ai-wei \u4e2d\u6587 AI \u5473\u7ed3\u6784\u6e05\u5355\u3002
FLAG_WORDS = [
    "\u56e0\u800c", "\u65e8\u5728", "\u56e0\u6b64", "\u4ece\u800c", "\u57fa\u4e8e\u6b64", "\u9274\u4e8e",
    "\u503c\u5f97\u6ce8\u610f", "\u503c\u5f97\u4e00\u63d0", "\u503c\u5f97\u4e00\u8bf4",
    "\u4e0d\u5bb9\u5ffd\u89c6", "\u4e0d\u53ef\u5ffd\u89c6", "\u4e0d\u53ef\u5c0f\u89d1",
    "\u4e0d\u5bb9\u7f6e\u7591", "\u6bcb\u5eb8\u7f6e\u7591", "\u52a1\u5fc5", "\u5207\u8bb0", "\u8bf7\u8bb0\u4f4f",
    "\u5f52\u6839\u7ed3\u5e95", "\u4ece\u672c\u8d28\u4e0a\u8bb2", "\u4e0d\u96be\u770b\u51fa", "\u53ef\u89c1", "\u8db3\u89c1",
    "\u4e0d\u8a00\u800c\u55bb", "\u4e8b\u5b9e\u4e0a", "\u5b9e\u9645\u4e0a",
    "\u65e0\u5f62\u4e2d", "\u6f5c\u79fb\u9ed8\u5316", "\u4e0e\u6b64\u540c\u65f6", "\u7efc\u4e0a\u6240\u8ff0",
    "\u603b\u800c\u8a00\u4e4b", "\u4e0e\u5176\u8bf4", "\u5728\u5f53\u4e0b", "\u5728\u5f53\u4eca",
    "\u4e0d\u5f97\u4e0d\u8bf4", "\u65e0\u7591", "\u663e\u800c\u6613\u89c1", "\u4e0e\u6b64\u76f8\u53cd",
]

# \u5426\u5b9a\u5bf9\u4e3e\uff1a\u201c\u4e0d\u662f X\uff0c\u800c\u662f Y\u201d\u7c7b\u7ed3\u6784\u3002AI \u4e2d\u6587\u6700\u5178\u578b\u75d5\u8ff9\u4e4b\u4e00\uff0c
# \u5076\u5c14\u4e00\u6b21\u65e0\u59a8\uff0c\u53cd\u590d\u51fa\u73b0\u5373\u4e3a\u624b\u5370\u3002
NEGATION_PAIR_PATTERNS = [
    r'\u4e0d\u662f[^\u3002\uff0c\uff1b\uff01\uff1f]{1,30}\uff0c?\u800c\u662f',
    r'\u4e0d\u5728\u4e8e[^\u3002\uff0c\uff1b]{1,30}\uff0c?\u800c\u5728\u4e8e',
    r'\u4e0d\u662f[^\u3002\uff0c\uff1b\uff01\uff1f]{1,30}\uff0c?\u662f',
    r'\u4e0d\u4ec5[^\u3002\uff0c\uff1b]{1,30}\uff0c?\u800c\u4e14',
    r'\u4e0d\u4ec5[^\u3002\uff0c\uff1b]{1,30}\uff0c?\u66f4',
]

# \u4fee\u8f9e\u516c\u5f0f\u5316\uff1a\u4e09\u6bb5\u5f0f\u6392\u6bd4 / \u865a\u5047\u8303\u56f4\uff08\u4ece X \u5230 Y\uff09/ \u4e09\u91cd\u5f8b\u3002
FORMULAIC_RHETORIC_PATTERNS = [
    r'\u4e0d\u4ec5[^\u3002]{1,20}\uff0c?\u800c\u4e14[^\u3002]{1,20}\uff0c?\u66f4\u91cd\u8981\u7684\u662f',
    r'\u4ece[^\u3002\uff0c]{1,15}\u5230[^\u3002\uff0c]{1,15}\uff0c\u4ece[^\u3002\uff0c]{1,15}\u5230[^\u3002\uff0c]{1,15}',
]


def _split_sentences(text):
    sentences = re.split(r'[\u3002\uff01\uff1f\uff1b;\u2026\n]', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


def _split_paragraphs(text):
    return [p.strip() for p in text.split('\n\n') if p.strip() and not p.strip().startswith('#')]


def _make_result(score, detail, param=None):
    r = {"score": round(max(0.0, min(1.0, score)), 4), "detail": detail}
    r["param"] = param
    return r


def score_sentence_length_stddev(text):
    sentences = _split_sentences(text)
    if len(sentences) < 5:
        return _make_result(0.5, "too few sentences to measure", "sentence_variance")
    lengths = [len(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    stddev = variance ** 0.5
    score = min(1.0, stddev / 25.0)
    return _make_result(score, f"stddev={stddev:.1f} (target \u226515)", "sentence_variance")


def score_sentence_length_range(text):
    sentences = _split_sentences(text)
    if len(sentences) < 5:
        return _make_result(0.5, "too few sentences", "sentence_variance")
    lengths = [len(s) for s in sentences]
    rng = max(lengths) - min(lengths)
    range_score = min(1.0, rng / 40.0)
    lines = text.split('\n')
    short_paras = sum(1 for l in lines if l.strip() and 1 <= len(l.strip()) <= 5 and not l.strip().startswith('#'))
    expected = max(1, len(text) / 500)
    short_score = min(1.0, short_paras / expected)
    score = range_score * 0.6 + short_score * 0.4
    return _make_result(score, f"range={rng} (target \u226530), short_paras={short_paras}", "sentence_variance")


def score_paragraph_length_variance(text):
    paragraphs = _split_paragraphs(text)
    if len(paragraphs) < 3:
        return _make_result(0.5, "too few paragraphs", "paragraph_rhythm")
    total_pairs = len(paragraphs) - 1
    similar = sum(1 for i in range(total_pairs) if abs(len(paragraphs[i]) - len(paragraphs[i + 1])) <= 20)
    score = 1.0 - (similar / total_pairs) if total_pairs > 0 else 0.5
    return _make_result(score, f"{similar}/{total_pairs} consecutive similar-length pairs", "paragraph_rhythm")


def score_vocabulary_richness(text):
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)
    if len(cjk_chars) < 20:
        return _make_result(0.5, "too few CJK characters", "word_temperature_bias")
    bigrams = [cjk_chars[i] + cjk_chars[i + 1] for i in range(len(cjk_chars) - 1)]
    ttr = len(set(bigrams)) / len(bigrams) if bigrams else 0
    ttr_score = min(1.0, ttr / 0.7)
    found_temps = sum([any(w in text for w in COLD_WORDS), any(w in text for w in WARM_WORDS), any(w in text for w in HOT_WORDS), any(w in text for w in WILD_WORDS)])
    temp_bonus = found_temps / 4.0 * 0.3
    score = min(1.0, ttr_score * 0.7 + temp_bonus)
    return _make_result(score, f"bigram_ttr={ttr:.3f}, temps={found_temps}/4", "word_temperature_bias")


def score_negative_emotion_ratio(text):
    sentences = _split_sentences(text)
    if not sentences:
        return _make_result(0.5, "no sentences", "emotional_arc")
    negative_count = sum(1 for s in sentences if any(m in s for m in NEGATIVE_MARKERS))
    ratio = negative_count / len(sentences)
    score = min(1.0, ratio / 0.25)
    return _make_result(score, f"negative={negative_count}/{len(sentences)} ({ratio:.0%}, target \u226520%)", "emotional_arc")


def score_adverb_density(text):
    char_count = len(text)
    if char_count < 50:
        return _make_result(0.5, "text too short", "adverb_max_per_100")
    total_adverbs = sum(text.count(adv) for adv in COMMON_ADVERBS)
    density = total_adverbs / char_count * 100
    sentences = _split_sentences(text)
    consecutive_adverb_starts = 0
    for i in range(len(sentences) - 1):
        a_starts = any(sentences[i].startswith(adv) for adv in COMMON_ADVERBS)
        b_starts = any(sentences[i + 1].startswith(adv) for adv in COMMON_ADVERBS)
        if a_starts and b_starts:
            consecutive_adverb_starts += 1
    score = 1.0
    if density > 3.0:
        score -= min(0.5, (density - 3.0) * 0.1)
    score -= consecutive_adverb_starts * 0.3
    return _make_result(score, f"density={density:.1f}/100chars, consecutive_starts={consecutive_adverb_starts}", "adverb_max_per_100")


def score_banned_words(text):
    found = [w for w in BANNED_WORDS if w in text]
    score = max(0.0, 1.0 - len(found) * 0.2)
    detail = "0 banned words" if not found else f"{len(found)} found: {found[:5]}"
    return _make_result(score, detail, None)


def score_broken_sentences(text):
    count = 0
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for p in BROKEN_SENTENCE_PATTERNS:
            count += len(re.findall(p, line))
        if 1 <= len(line) <= 10 and not line.startswith('#'):
            count += 1
    char_count = len(text)
    expected = max(3, char_count / 500 * 3)
    score = min(1.0, count / expected)
    return _make_result(score, f"{count} broken structures (expected \u2265{expected:.0f})", "broken_sentence_rate")


def score_real_sources(text):
    count = 0
    for pattern in REAL_SOURCE_PATTERNS:
        count += len(re.findall(pattern, text))
    score = min(1.0, count / 5.0)
    return _make_result(score, f"{count} real-source indicators (target \u22655)", "real_data_density")


def score_word_temperature_mix(text):
    found_temps = sum([any(w in text for w in COLD_WORDS), any(w in text for w in WARM_WORDS), any(w in text for w in HOT_WORDS), any(w in text for w in WILD_WORDS)])
    score = max(0.0, (found_temps - 1) / 3.0)
    return _make_result(score, f"{found_temps}/4 temperature bands", "word_temperature_bias")


def score_self_correction(text):
    count = 0
    for pattern in SELF_CORRECTION_PATTERNS:
        count += len(re.findall(pattern, text))
    score = min(1.0, count / 3.0)
    return _make_result(score, f"{count} self-corrections/insertions (target \u22653)", "self_correction_rate")


def score_flag_words(text):
    found = [w for w in FLAG_WORDS if w in text]
    score = max(0.0, 1.0 - len(found) * 0.25)
    detail = "0 flag words" if not found else f"{len(found)} flag words: {found[:5]}"
    return _make_result(score, detail, "flag_words")


def _count_structure_spans(text, patterns):
    """Count distinct structures, merging overlapping pattern matches.

    多条 pattern 会命中同一段文本（如 `不是A而是B` 同时命中
    `不是...而是` 与 `不是...是`），直接累加会把一处结构记成两次，
    让「容差 1 次」变成「一次就罚」。
    """
    spans = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if match.end() > match.start():
                spans.append((match.start(), match.end()))
    if not spans:
        return 0
    spans.sort()
    count = 1
    current_end = spans[0][1]
    for start, end in spans[1:]:
        if start >= current_end:
            count += 1
            current_end = end
        else:
            current_end = max(current_end, end)
    return count


def score_negation_pairs(text):
    count = _count_structure_spans(text, NEGATION_PAIR_PATTERNS)
    score = max(0.0, 1.0 - max(0, count - 1) * 0.4)
    return _make_result(score, f"{count} negation-pair structures (target 0-1)", "negation_pairs")


def score_formulaic_rhetoric(text):
    count = _count_structure_spans(text, FORMULAIC_RHETORIC_PATTERNS)
    score = max(0.0, 1.0 - max(0, count - 1) * 0.5)
    return _make_result(score, f"{count} formulaic-rhetoric structures (target 0-1)", "formulaic_rhetoric")


TIER1_CHECKS = [("sentence_length_stddev", score_sentence_length_stddev), ("sentence_length_range", score_sentence_length_range), ("paragraph_length_variance", score_paragraph_length_variance), ("vocabulary_richness", score_vocabulary_richness), ("negative_emotion_ratio", score_negative_emotion_ratio), ("adverb_density", score_adverb_density)]

TIER2_CHECKS = [("banned_words", score_banned_words), ("broken_sentences", score_broken_sentences), ("real_sources", score_real_sources), ("word_temperature_mix", score_word_temperature_mix), ("self_correction", score_self_correction), ("flag_words", score_flag_words), ("negation_pairs", score_negation_pairs), ("formulaic_rhetoric", score_formulaic_rhetoric)]


def run_tier(checks, text):
    results = {}
    scores = []
    for name, fn in checks:
        r = fn(text)
        results[name] = r
        scores.append(r["score"])
    results["_summary"] = {"count": len(checks), "mean_score": round(sum(scores) / len(scores), 4) if scores else 0, "scores": [round(s, 4) for s in scores]}
    return results


_BELL_CURVE_CHECKS = {"broken_sentences": 0.39, "self_correction": 0.20, "sentence_length_range": 0.71, "paragraph_length_variance": 0.52, "banned_words": 0.73}


def _bell_curve(raw_score, center):
    if center <= 0:
        return raw_score
    if raw_score <= center:
        return raw_score / center
    else:
        overshoot = (raw_score - center) / (1.0 - center) if center < 1 else 0
        return max(0.0, 1.0 - overshoot * overshoot)


def calibrate_tiers(tier1, tier2):
    for tier in [tier1, tier2]:
        for name, data in tier.items():
            if name.startswith("_"):
                continue
            if name in _BELL_CURVE_CHECKS:
                raw = data["score"]
                center = _BELL_CURVE_CHECKS[name]
                calibrated = round(max(0.0, min(1.0, _bell_curve(raw, center))), 4)
                data["raw_score"] = raw
                data["score"] = calibrated
                data["detail"] += f" [calibrated from {raw:.2f}, center={center}]"
    all_scores = []
    for tier in [tier1, tier2]:
        for name, data in tier.items():
            if not name.startswith("_"):
                all_scores.append(data["score"])
    high_count = sum(1 for s in all_scores if s > 0.8)
    over_opt_ratio = high_count / len(all_scores) if all_scores else 0
    penalty = 1.0
    if over_opt_ratio >= 0.6:
        penalty = 0.85
    if penalty < 1.0:
        for tier in [tier1, tier2]:
            for name, data in tier.items():
                if not name.startswith("_"):
                    data["score"] = round(data["score"] * penalty, 4)
    for tier in [tier1, tier2]:
        scores = [data["score"] for name, data in tier.items() if not name.startswith("_")]
        tier["_summary"]["mean_score"] = round(sum(scores) / len(scores), 4) if scores else 0
        tier["_summary"]["scores"] = [round(s, 4) for s in scores]
    return penalty


def compute_composite(tier1, tier2, tier3_score=None):
    t1_mean = tier1["_summary"]["mean_score"]
    t2_mean = tier2["_summary"]["mean_score"]
    if tier3_score is not None:
        humanness = t1_mean * 0.50 + t2_mean * 0.30 + tier3_score * 0.20
        weights = {"tier1": 0.50, "tier2": 0.30, "tier3": 0.20}
    else:
        humanness = t1_mean * 0.625 + t2_mean * 0.375
        weights = {"tier1": 0.625, "tier2": 0.375}
    composite = round((1 - humanness) * 100, 2)
    return composite, weights


def build_param_scores(tier1, tier2):
    param_map = {}
    for tier in [tier1, tier2]:
        for name, data in tier.items():
            if name.startswith("_"):
                continue
            param = data.get("param")
            if param is None:
                continue
            if param not in param_map:
                param_map[param] = []
            param_map[param].append(data["score"])
    return {p: round(sum(scores) / len(scores), 4) for p, scores in param_map.items()}


def score_article(text, verbose=False, tier3_score=None):
    clean = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE).strip()
    tier1 = run_tier(TIER1_CHECKS, clean)
    tier2 = run_tier(TIER2_CHECKS, clean)
    over_opt_penalty = calibrate_tiers(tier1, tier2)
    composite, weights = compute_composite(tier1, tier2, tier3_score)
    param_scores = build_param_scores(tier1, tier2)
    result = {"composite_score": composite, "tier1": tier1, "tier2": tier2, "tier3": {"score": tier3_score, "source": "agent" if tier3_score is not None else "not_available"}, "weights": weights, "param_scores": param_scores, "over_optimization_penalty": over_opt_penalty, "char_count": len(clean)}
    if verbose:
        _print_verbose(result)
    return result


def _print_verbose(result):
    composite = result["composite_score"]
    print(f"\n{'=' * 60}")
    print(f"HUMANNESS SCORE: {composite:.1f}/100 (lower = more human)")
    print(f"{'=' * 60}")
    for tier_name, tier_label, weight in [("tier1", "Tier 1 \u2014 Statistical", result["weights"].get("tier1", 0)), ("tier2", "Tier 2 \u2014 Pattern", result["weights"].get("tier2", 0))]:
        tier = result[tier_name]
        summary = tier["_summary"]
        print(f"\n{tier_label} (weight {weight:.0%}, mean {summary['mean_score']:.2f})")
        for name, data in tier.items():
            if name.startswith("_"):
                continue
            bar = "\u2588" * int(data["score"] * 10) + "\u2591" * (10 - int(data["score"] * 10))
            param_tag = f" [{data['param']}]" if data.get("param") else ""
            print(f"  {bar} {data['score']:.2f}  {name}{param_tag}")
            print(f"         {data['detail']}")
    t3 = result["tier3"]
    if t3["score"] is not None:
        t3_weight = result["weights"].get("tier3", 0)
        print(f"\nTier 3 \u2014 LLM (weight {t3_weight:.0%})")
        print(f"  Score: {t3['score']:.2f} (source: {t3['source']})")
    else:
        print("\nTier 3 \u2014 LLM: not available (standalone mode)")
    print(f"\nComposite: {composite:.1f} (0=\u5b8c\u7f8e\u4eba\u7c7b, 100=\u660e\u663eAI)")
    print(f"Weights: {result['weights']}")
    param_scores = result["param_scores"]
    if param_scores:
        sorted_params = sorted(param_scores.items(), key=lambda x: x[1])
        print("\nLowest-scoring parameters (optimize these first):")
        for param, score in sorted_params[:3]:
            print(f"  {param}: {score:.2f}")


CALIBRATION_BASELINES = {"pure_ai": {"label": "Pure AI (typical ChatGPT output)", "expected_composite_min": 75, "expected_composite_max": 85}, "ai_with_editing": {"label": "AI draft + human editing", "expected_composite_min": 40, "expected_composite_max": 55}, "human_written": {"label": "Genuine human blog post", "expected_composite_min": 15, "expected_composite_max": 30}, "target_range": {"label": "WeWrite target range", "expected_composite_min": 20, "expected_composite_max": 38}}


DEFAULT_HUMANNESS_RANGE = (20.0, 38.0)


def _calibration_verdict(result: dict) -> dict:
    """Compare the composite score against the calibration baselines."""
    score = result["composite_score"]
    baselines = {}
    for key, base in CALIBRATION_BASELINES.items():
        lo = base["expected_composite_min"]
        hi = base["expected_composite_max"]
        baselines[key] = {
            "label": base["label"],
            "expected_range": [lo, hi],
            "in_expected": lo <= score <= hi,
        }
    return {"composite_score": score, "baselines": baselines}


def _print_calibration(result: dict) -> None:
    data = _calibration_verdict(result)
    score = data["composite_score"]
    print(f"\nCalibration \u2014 composite {score:.1f}")
    for base in data["baselines"].values():
        lo, hi = base["expected_range"]
        mark = "\u2713" if base["in_expected"] else "\u00b7"
        tail = "" if base["in_expected"] else "  (outside)"
        print(f"  {mark} {base['label']}: {lo}-{hi}{tail}")


def load_humanness_range(start: Path = None) -> tuple:
    """Read humanness_range from writing-config.yaml; fall back to the default.

    Single source of truth: config/writing-config.yaml.
    """
    try:
        import yaml
    except ImportError:
        return DEFAULT_HUMANNESS_RANGE
    here = (start or Path(__file__)).resolve()
    for base in [here.parent, *here.parents]:
        for rel in ("config/writing-config.yaml", "writing-config.yaml"):
            candidate = base / rel
            if candidate.is_file():
                try:
                    cfg = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                except Exception:
                    continue
                rng = cfg.get("humanness_range")
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    try:
                        return (float(rng[0]), float(rng[1]))
                    except (TypeError, ValueError):
                        pass
    return DEFAULT_HUMANNESS_RANGE


def main():
    parser = argparse.ArgumentParser(description="Score article humanness (0=human, 100=AI)")
    parser.add_argument("input", help="Markdown article file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed report")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--tier3", type=float, default=None, help="Tier 3 LLM score (0-1), passed by agent from SKILL.md")
    parser.add_argument("--calibrate", action="store_true", help="Compare scores against calibration baselines")
    args = parser.parse_args()
    text = Path(args.input).read_text(encoding="utf-8")
    if args.json and args.verbose:
        # --json 要求 stdout 只有 JSON；把 verbose 报告改道到 stderr
        with contextlib.redirect_stdout(sys.stderr):
            result = score_article(text, verbose=True, tier3_score=args.tier3)
    else:
        result = score_article(text, verbose=args.verbose, tier3_score=args.tier3)
    low, high = load_humanness_range(Path(args.input))
    result["humanness_range"] = [low, high]
    result["in_range"] = low <= result["composite_score"] <= high
    if args.calibrate:
        if args.json:
            with contextlib.redirect_stdout(sys.stderr):
                _print_calibration(result)
        else:
            _print_calibration(result)
    if args.json:
        if args.verbose or args.calibrate:
            result["calibration"] = _calibration_verdict(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not args.verbose and not args.calibrate:
        score = result["composite_score"]
        verdict = "PASS" if result["in_range"] else "OUT_OF_RANGE"
        print(f"{score:.1f}  [{low:g}, {high:g}]  {verdict}")


if __name__ == "__main__":
    main()
