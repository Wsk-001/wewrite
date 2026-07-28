"""Test that context budget tracking is properly initialized."""


def test_imports():
    """At minimum, test that core modules can be imported."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
    from converter import WeChatConverter, ConvertResult
    from theme import Theme, load_theme, list_themes
    assert ConvertResult
    assert Theme


def test_theme_list():
    """Test that theme listing returns results."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
    from theme import list_themes
    themes = list_themes()
    assert len(themes) > 0
    assert "professional-clean" in themes
