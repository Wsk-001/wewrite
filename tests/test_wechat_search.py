"""Tests for scripts/wechat_search.py (Sogou WeChat search parsing).

Network-free: all parsing/filtering helpers are exercised on fixture HTML.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from wechat_search import (  # noqa: E402
    detect_block,
    has_result_list,
    filter_items,
    join_redirect_parts,
    parse_results,
)

FIXTURE = """
<div class="wrapper">
<ul class="news-list">
  <li id="sogou_vr_11002601_box_0">
    <div class="txt-box">
      <h3><a href="/link?url=abc&amp;type=2">熬夜欠的<em><!--red_beg-->睡眠债<!--red_end--></em>能补回来吗</a></h3>
      <p class="txt-info" id="s0">周末补觉<em>睡眠</em>能不能抵消...</p>
      <div class="s-p">
        <span class="all-time-y2">某某健康</span>
        <span class="s2"><script>document.write(timeConvert('1791960000'))</script></span>
      </div>
    </div>
  </li>
  <li id="sogou_vr_11002601_box_1">
    <div class="txt-box">
      <h3><a href="http://mp.weixin.qq.com/s?x=1">高血压患者打呼噜要当心</a></h3>
      <p class="txt-info" id="s1">睡眠呼吸暂停...</p>
      <div class="s-p">
        <span class="all-time-y2">心内科普</span>
        <span class="s2"><script>document.write(timeConvert('1614556800'))</script></span>
      </div>
    </div>
  </li>
  <li id="no_title_box">
    <div class="txt-box"><h3><a></a></h3></div>
  </li>
</ul>
</div>
"""


def test_parse_results_extracts_fields():
    items = parse_results(FIXTURE)
    assert len(items) == 2
    first = items[0]
    assert first["title"] == "熬夜欠的睡眠债能补回来吗"
    assert first["account"] == "某某健康"
    assert first["summary"].startswith("周末补觉")
    assert first["date"] == "2026-10-14"
    assert isinstance(first["days_ago"], int)


def test_parse_results_makes_relative_urls_absolute():
    items = parse_results(FIXTURE)
    assert items[0]["url"].startswith("https://weixin.sogou.com/link?url=")
    assert "&amp;" not in items[0]["url"]
    assert items[1]["url"].startswith("http://mp.weixin.qq.com/")


def test_parse_results_dedupes_and_skips_empty_titles():
    html = FIXTURE.replace("高血压患者打呼噜要当心", "熬夜欠的睡眠债能补回来吗")
    items = parse_results(html)
    assert len(items) == 1


def test_detect_block_flags_antispider():
    assert detect_block("<html>请输入验证码</html>")
    assert detect_block('<div id="seccodeImage"></div> antispider')
    assert detect_block("<html>访问过于频繁</html>")


def test_detect_block_does_not_flag_pages_without_markers():
    # 没有列表也没验证码 → 可能是 0 结果或被限流，不能谎报反爬
    assert detect_block("<html>something unrelated</html>") == ""


def test_has_result_list():
    assert has_result_list(FIXTURE)
    assert has_result_list('<div class="no-result">没有找到相关的微信公众号文章</div>')
    assert not has_result_list("<html>something unrelated</html>")


def test_detect_block_allows_result_and_empty_pages():
    assert detect_block(FIXTURE) == ""
    assert detect_block('<div class="no-result">没有找到相关的微信公众号文章</div>') == ""


def test_join_redirect_parts_strips_at_markers():
    assert join_redirect_parts(["https://mp.weixin.qq.com/s?", "a=1@", "b=2"]) == (
        "https://mp.weixin.qq.com/s?a=1b=2"
    )


def test_filter_items_applies_days_and_limit():
    items = [{"title": "a", "days_ago": 3}, {"title": "b", "days_ago": 90}, {"title": "c"}]
    assert [i["title"] for i in filter_items(items, days=30)] == ["a", "c"]
    assert [i["title"] for i in filter_items(items, limit=2)] == ["a", "b"]
    assert filter_items(items) == items
