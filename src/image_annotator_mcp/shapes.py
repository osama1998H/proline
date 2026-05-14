from __future__ import annotations

import math

from PIL import ImageDraw

from .colors import resolve_color
from .fonts import load_font
from .models import Arrow, Circle, Line, Rectangle, Text


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


def draw_line(draw: ImageDraw.ImageDraw, shape: Line) -> None:
    color = resolve_color(shape.color)
    draw.line(
        (shape.x1, shape.y1, shape.x2, shape.y2),
        fill=color,
        width=shape.line_width,
    )


def draw_arrow(draw: ImageDraw.ImageDraw, shape: Arrow) -> None:
    color = resolve_color(shape.color)
    # Shaft
    draw.line(
        (shape.x1, shape.y1, shape.x2, shape.y2),
        fill=color,
        width=shape.line_width,
    )
    # Head: filled isoceles triangle at the destination, pointing along the shaft.
    dx = shape.x2 - shape.x1
    dy = shape.y2 - shape.y1
    length = math.hypot(dx, dy)
    if length == 0:
        return  # zero-length arrow: nothing more to draw
    ux, uy = dx / length, dy / length  # unit vector along shaft
    px, py = -uy, ux                    # unit vector perpendicular to shaft
    base_cx = shape.x2 - ux * shape.head_size
    base_cy = shape.y2 - uy * shape.head_size
    half_width = shape.head_size * 0.6
    left = (round(base_cx + px * half_width), round(base_cy + py * half_width))
    right = (round(base_cx - px * half_width), round(base_cy - py * half_width))
    tip = (shape.x2, shape.y2)
    draw.polygon([left, right, tip], fill=color, outline=color)


def draw_text(draw: ImageDraw.ImageDraw, shape: Text) -> None:
    color = resolve_color(shape.color)
    font = load_font(shape.font_size)
    if shape.background is not None:
        bg = resolve_color(shape.background)
        # Measure text bounding box
        left, top, right, bottom = draw.textbbox(
            (shape.x, shape.y), shape.text, font=font, anchor="lt"
        )
        pad = shape.padding
        draw.rectangle(
            (left - pad, top - pad, right + pad, bottom + pad),
            fill=bg,
        )
    draw.text((shape.x, shape.y), shape.text, fill=color, font=font, anchor="lt")
