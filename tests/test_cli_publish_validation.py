"""
Tests for toolkit/cli.py publish pre-flight validation.

Covers: cover requirement, --no-cover, missing local image files,
inline image reference counting, --expect-images, and --force bypass.
"""

import sys
from argparse import Namespace
from pathlib import Path

import pytest

TOOLKIT_DIR = str(Path(__file__).resolve().parent.parent / "toolkit")
if TOOLKIT_DIR not in sys.path:
    sys.path.insert(0, TOOLKIT_DIR)

from cli import _local_image_refs, _validate_publish_inputs  # noqa: E402


def _args(**kwargs):
    base = {
        "input": None,
        "cover": None,
        "no_cover": False,
        "force": False,
        "expect_images": None,
    }
    base.update(kwargs)
    return Namespace(**base)


@pytest.fixture()
def article_dir(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"x")
    (tmp_path / "post-1.jpg").write_bytes(b"x")
    (tmp_path / "post-2.jpg").write_bytes(b"x")
    return tmp_path


def test_requires_cover_when_omitted(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(_args(input=str(md)))
    assert exc.value.code == 2


def test_rejects_missing_cover_file(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(
            _args(input=str(md), cover=str(article_dir / "nope.jpg"))
        )
    assert exc.value.code == 2


def test_rejects_cover_and_no_cover_together(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(
            _args(
                input=str(md),
                cover=str(article_dir / "cover.jpg"),
                no_cover=True,
            )
        )
    assert exc.value.code == 2


def test_rejects_article_without_inline_refs(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n正文没有图片引用。\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(
            _args(input=str(md), cover=str(article_dir / "cover.jpg"))
        )
    assert exc.value.code == 2


def test_rejects_reference_to_missing_file(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n\n![](ghost.jpg)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(
            _args(input=str(md), cover=str(article_dir / "cover.jpg"))
        )
    assert exc.value.code == 2


def test_accepts_valid_article(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n\n![](post-2.jpg)\n", encoding="utf-8")
    _validate_publish_inputs(
        _args(
            input=str(md),
            cover=str(article_dir / "cover.jpg"),
            expect_images=2,
        )
    )


def test_expect_images_mismatch_rejected(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _validate_publish_inputs(
            _args(
                input=str(md),
                cover=str(article_dir / "cover.jpg"),
                expect_images=2,
            )
        )
    assert exc.value.code == 2


def test_force_bypasses_image_checks(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n正文没有图片引用。\n", encoding="utf-8")
    _validate_publish_inputs(
        _args(input=str(md), cover=str(article_dir / "cover.jpg"), force=True)
    )


def test_no_cover_flag_allows_coverless_publish(article_dir):
    md = article_dir / "post.md"
    md.write_text("# 标题\n\n![](post-1.jpg)\n", encoding="utf-8")
    _validate_publish_inputs(_args(input=str(md), no_cover=True))


def test_local_refs_ignore_remote_and_data_uris():
    text = (
        "![](local.jpg)\n![](https://example.com/a.png)\n"
        "![](data:image/png;base64,AAAA)\n"
    )
    assert _local_image_refs(text) == ["local.jpg"]
