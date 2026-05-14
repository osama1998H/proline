import pytest
from PIL import ImageFont

from image_annotator_mcp.fonts import load_font


def test_load_font_returns_truetype_font():
    f = load_font(14)
    assert isinstance(f, ImageFont.FreeTypeFont)


def test_load_font_can_render_text():
    """Sanity: the returned font has the methods a renderer needs."""
    f = load_font(14)
    bbox = f.getbbox("A")
    assert bbox is not None
    assert bbox[2] > bbox[0]  # right > left, has some width
    assert bbox[3] > bbox[1]  # bottom > top, has some height


def test_load_font_size_too_small_rejected():
    with pytest.raises(ValueError):
        load_font(3)


def test_load_font_different_sizes_distinct():
    small = load_font(8)
    large = load_font(40)
    # Larger size should yield a wider glyph
    assert large.getbbox("A")[2] > small.getbbox("A")[2]
