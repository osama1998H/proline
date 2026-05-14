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


from image_annotator_mcp.models import Circle
from image_annotator_mcp.shapes import draw_circle


class TestDrawCircle:
    def test_hollow_default_green(self):
        shape = Circle(type="circle", x=100, y=50, radius=30)
        img = _draw_on_blank(shape, draw_circle)
        # Point on the circumference should be green
        assert_pixel(img, 130, 50, (34, 197, 94))
        # Center should be white (hollow)
        assert_pixel_unchanged(img, 100, 50)

    def test_filled_blue(self):
        shape = Circle(type="circle", x=100, y=50, radius=30, color="blue", fill="blue")
        img = _draw_on_blank(shape, draw_circle)
        assert_pixel(img, 100, 50, (0, 0, 255))


from image_annotator_mcp.models import Line
from image_annotator_mcp.shapes import draw_line


class TestDrawLine:
    def test_horizontal_red(self):
        shape = Line(type="line", x1=10, y1=50, x2=190, y2=50, color="red", line_width=2)
        img = _draw_on_blank(shape, draw_line)
        # On-line pixel is red
        assert_pixel(img, 100, 50, (255, 0, 0))
        # Off-line pixel is white
        assert_pixel_unchanged(img, 100, 20)


from image_annotator_mcp.models import Arrow
from image_annotator_mcp.shapes import draw_arrow


class TestDrawArrow:
    def test_horizontal_arrow_has_line_and_head(self):
        shape = Arrow(
            type="arrow", x1=20, y1=50, x2=180, y2=50,
            color="red", line_width=3, head_size=10,
        )
        img = _draw_on_blank(shape, draw_arrow)
        # Somewhere along the shaft is red
        assert_pixel(img, 100, 50, (255, 0, 0))
        # The head tip area (just before x2) is red
        assert_pixel(img, 178, 50, (255, 0, 0))
        # Below the head, a few pixels off the shaft, is red (because the head triangle widens)
        assert_pixel(img, 172, 53, (255, 0, 0))
        # Well above the shaft is white
        assert_pixel_unchanged(img, 100, 20)
