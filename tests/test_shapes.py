from __future__ import annotations

from PIL import Image, ImageDraw

from image_annotator_mcp.models import Rectangle
from image_annotator_mcp.shapes import draw_rectangle

from .conftest import assert_pixel, assert_pixel_unchanged  # noqa: F401


def _draw_on_blank(shape, draw_fn, size=(200, 100)):
    img = Image.new("RGBA", size, color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    draw_fn(draw, shape)
    return img


class TestDrawRectangle:
    def test_hollow_default_green(self):
        shape = Rectangle(type="rectangle", x=20, y=20, width=60, height=40)
        img = _draw_on_blank(shape, draw_rectangle)
        # Top-left corner pixel on the border should be green-ish (#22C55E ≈ (34,197,94))
        assert_pixel(img, 20, 20, (34, 197, 94))
        # Center of the rectangle should still be white (hollow)
        assert_pixel_unchanged(img, 50, 40)
        # Pixel well outside the rect should be white
        assert_pixel_unchanged(img, 5, 5)

    def test_filled_red(self):
        shape = Rectangle(
            type="rectangle",
            x=20, y=20, width=60, height=40,
            color="red", fill="red", line_width=2,
        )
        img = _draw_on_blank(shape, draw_rectangle)
        # Interior should now be red
        assert_pixel(img, 50, 40, (255, 0, 0))

    def test_line_width_respected(self):
        shape = Rectangle(
            type="rectangle",
            x=20, y=20, width=60, height=40,
            color="#22C55E", line_width=8,
        )
        img = _draw_on_blank(shape, draw_rectangle)
        # 4 pixels inside the top edge should still be green (line_width=8)
        assert_pixel(img, 50, 24, (34, 197, 94))
        # 10 pixels inside the top edge should be white again
        assert_pixel_unchanged(img, 50, 32)
