from __future__ import annotations

from PIL import ImageDraw

from .colors import resolve_color
from .models import Circle, Rectangle


def draw_rectangle(draw: ImageDraw.ImageDraw, shape: Rectangle) -> None:
    outline = resolve_color(shape.color)
    fill = resolve_color(shape.fill) if shape.fill is not None else None
    box = (shape.x, shape.y, shape.x + shape.width, shape.y + shape.height)

    if shape.radius > 0:
        draw.rounded_rectangle(
            box,
            radius=shape.radius,
            outline=outline,
            fill=fill,
            width=shape.line_width,
        )
    else:
        draw.rectangle(
            box,
            outline=outline,
            fill=fill,
            width=shape.line_width,
        )


def draw_circle(draw: ImageDraw.ImageDraw, shape: Circle) -> None:
    outline = resolve_color(shape.color)
    fill = resolve_color(shape.fill) if shape.fill is not None else None
    box = (
        shape.x - shape.radius,
        shape.y - shape.radius,
        shape.x + shape.radius,
        shape.y + shape.radius,
    )
    draw.ellipse(box, outline=outline, fill=fill, width=shape.line_width)
