import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from converter import WeChatConverter


def test_basic_conversion():
    converter = WeChatConverter(theme_name="professional-clean")
    md = "# Hello\n\nThis is a test."
    result = converter.convert(md)
    assert result.title == "Hello"
    assert "test" in result.html
    assert "Hello" not in result.html  # H1 should be stripped


def test_container_callout():
    converter = WeChatConverter(theme_name="professional-clean")
    md = ":::callout tip\nThis is a tip\n:::"
    result = converter.convert(md)
    assert "tip" in result.html.lower()
    assert "This is a tip" in result.html


def test_container_highlight():
    converter = WeChatConverter(theme_name="professional-clean")
    md = ":::highlight\n**Key Point**\nThis is important\n:::"
    result = converter.convert(md)
    assert "Key Point" in result.html
    assert "<strong>" in result.html


def test_container_summary():
    converter = WeChatConverter(theme_name="professional-clean")
    md = ":::summary\n**Conclusion**\nThe main takeaways\n:::"
    result = converter.convert(md)
    assert "<strong>" in result.html or "Conclusion" in result.html


def test_image_extraction():
    converter = WeChatConverter(theme_name="professional-clean")
    md = "# Article\n\n![alt](test.png)"
    result = converter.convert(md)
    assert len(result.images) == 1
    assert "test.png" in result.images[0]


def test_digest_generation():
    converter = WeChatConverter(theme_name="professional-clean")
    md = "# Title\n\n" + "A" * 200
    result = converter.convert(md)
    assert len(result.digest.encode("utf-8")) <= 120
