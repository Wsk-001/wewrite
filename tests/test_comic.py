"""Tests for toolkit/comic.py (comic tietu pipeline)."""

import json
import sys
from pathlib import Path

import pytest

TOOLKIT_DIR = str(Path(__file__).resolve().parent.parent / "toolkit")
if TOOLKIT_DIR not in sys.path:
    sys.path.insert(0, TOOLKIT_DIR)

import comic  # noqa: E402


def _base_storyboard(**overrides):
    sb = {
        "post_title": "9块9的尿素霜，别往脸上乱涂",
        "post_body": "脸用2%-5%，身体5%-10%。",
        "style_anchor": "低饱和写实条漫插画",
        "panels": [
            {"no": 1, "caption": "9块9，300毫升", "scene": "浴室置物架前的一支白色软管"},
            {"no": 2, "caption": "一张图记住浓度", "render": "recap"},
        ],
    }
    sb.update(overrides)
    return sb


def test_validate_accepts_minimal_storyboard(tmp_path):
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(_base_storyboard(), ensure_ascii=False), encoding="utf-8")
    sb = comic.load_storyboard(path)
    assert comic.validate_storyboard(sb) == []


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda sb: sb.update(panels=[]), "non-empty"),
        (lambda sb: sb["panels"].append({"no": 1, "caption": "重复"}), "duplicate"),
        (lambda sb: sb["panels"].append({"no": 3, "caption": ""}), "caption"),
        (lambda sb: sb.update(post_title="x" * 33), "post_title"),
        (lambda sb: sb.update(post_body="x" * 1001), "post_body"),
        (lambda sb: sb.update(panels=[{"no": i, "caption": "c"} for i in range(1, 22)]), "at most"),
    ],
)
def test_validate_rejects_bad_storyboard(mutate, message):
    sb = _base_storyboard()
    mutate(sb)
    with pytest.raises(comic.ComicError, match=message):
        comic.validate_storyboard(sb)


def test_more_than_nine_panels_warns():
    panels = [{"no": i, "caption": f"c{i}", "scene": f"场景{i}"} for i in range(1, 11)]
    warnings = comic.validate_storyboard(_base_storyboard(panels=panels))
    assert any("9-image" in w for w in warnings)


def test_build_batch_skips_recap_and_adds_avoid(tmp_path):
    sb = _base_storyboard()
    tasks = comic.build_batch(sb, tmp_path / "raw")
    assert len(tasks) == 1
    task = tasks[0]
    assert task["output"].endswith("raw-1.jpg")
    assert task["brief"]["template"] == "scene"
    assert task["brief"]["aspect"] == "3:4"
    assert "文字" in task["brief"]["avoid"]
    assert task["size"] == comic.DEFAULT_GEN_SIZE


def test_build_batch_prefers_explicit_brief(tmp_path):
    sb = _base_storyboard()
    sb["panels"][0]["brief"] = {"template": "illustration", "scene": "静物"}
    tasks = comic.build_batch(sb, tmp_path)
    assert tasks[0]["brief"]["template"] == "illustration"
    assert tasks[0]["brief"]["scene"] == "静物"


def _has_font():
    try:
        comic._find_font_path("regular")
        comic._find_font_path("bold")
        return True
    except comic.ComicError:
        return False


@pytest.mark.skipif(not _has_font(), reason="no CJK font installed")
def test_render_writes_panels_recap_and_preview(tmp_path):
    from PIL import Image

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for no in (1, 2):
        Image.new("RGB", (1152, 1536), (220, 210, 195)).save(raw_dir / f"raw-{no}.jpg")

    sb = _base_storyboard()
    sb["panels"][1]["no"] = 3
    out_dir = tmp_path / "out"
    result = comic.render(sb, raw_dir, out_dir)

    assert [Path(p).name for p in result["panels"]] == ["tietu-1.jpg", "tietu-3.jpg"]
    assert all(size == [1080, 1440] for size in result["sizes"])
    assert Path(result["preview"]).exists()
    assert Path(result["preview_html"]).exists()
    assert (out_dir / "title.txt").read_text(encoding="utf-8").startswith("9块9")
    html = Path(result["preview_html"]).read_text(encoding="utf-8")
    assert "tietu-1.jpg" in html and "tietu-3.jpg" in html


@pytest.mark.skipif(not _has_font(), reason="no CJK font installed")
def test_render_fails_when_raw_missing(tmp_path):
    sb = _base_storyboard()
    with pytest.raises(comic.ComicError, match="missing raw images"):
        comic.render(sb, tmp_path / "raw", tmp_path / "out")
