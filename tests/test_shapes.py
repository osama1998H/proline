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


from image_annotator_mcp.models import Text
from image_annotator_mcp.shapes import draw_text


class TestDrawText:
    def test_red_text_paints_some_red_pixels(self):
        shape = Text(type="text", x=20, y=20, text="HELLO", color="red", font_size=24)
        img = _draw_on_blank(shape, draw_text)
        rgb_pixels = img.convert("RGB").load()
        # Sample a 60x30 region starting at (20, 20) and count red-ish pixels.
        red_count = 0
        for px in range(20, 90):
            for py in range(20, 60):
                r, g, b = rgb_pixels[px, py]
                if r > 180 and g < 80 and b < 80:
                    red_count += 1
        assert red_count > 40, f"expected text glyphs to paint many red pixels, got {red_count}"

    def test_background_rectangle_paints_solid(self):
        shape = Text(
            type="text",
            x=20, y=20, text="OK",
            color="white", font_size=24,
            background="black", padding=4,
        )
        img = _draw_on_blank(shape, draw_text)
        # A pixel inside the background rectangle but not on a glyph should be black-ish
        assert_pixel(img, 21, 21, (0, 0, 0))


from image_annotator_mcp.models import NumberedCallout
from image_annotator_mcp.shapes import draw_numbered_callout


class TestDrawNumberedCallout:
    def test_filled_circle_with_white_number(self):
        shape = NumberedCallout(type="numbered_callout", x=100, y=50, number=3, color="red", radius=20)
        img = _draw_on_blank(shape, draw_numbered_callout)
        rgb = img.convert("RGB").load()
        # Center of the callout should be red, white, or near-red (since '3' glyph lives there).
        center = rgb[100, 50]
        # Outside the circle should be unchanged white.
        assert rgb[100, 5] == (255, 255, 255)
        # At a pixel just inside the right edge, expect filled red.
        far_right_inside = rgb[118, 50]
        assert far_right_inside[0] > 180 and far_right_inside[1] < 80 and far_right_inside[2] < 80
        # The glyph should paint at least one white pixel inside the circle.
        white_inside = 0
        for px in range(85, 116):
            for py in range(35, 66):
                if rgb[px, py] == (255, 255, 255):
                    # is this pixel inside the circle?
                    if (px - 100) ** 2 + (py - 50) ** 2 < 20 * 20:
                        white_inside += 1
        assert white_inside >= 5
