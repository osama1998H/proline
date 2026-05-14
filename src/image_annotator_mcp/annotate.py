from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from .colors import resolve_color
from .models import (
    AnnotateImageInput,
    Annotation,
    Arrow,
    Circle,
    Line,
    NumberedCallout,
    Rectangle,
    Text,
)
from .scaling import scale_point, scale_rect, scale_value
from .shapes import (
    draw_arrow,
    draw_circle,
    draw_line,
    draw_numbered_callout,
    draw_rectangle,
    draw_text,
)


def _bbox_of(ann: Annotation) -> tuple[int, int, int, int]:
    """Image-space axis-aligned bounding box of an annotation. Coords are inclusive of the
    drawn area: line width is accounted for by inflating by line_width/2 + 1 where applicable.
    """
    if isinstance(ann, Rectangle):
        pad = ann.line_width
        return (ann.x - pad, ann.y - pad, ann.x + ann.width + pad, ann.y + ann.height + pad)
    if isinstance(ann, Circle):
        pad = ann.line_width
        return (ann.x - ann.radius - pad, ann.y - ann.radius - pad,
                ann.x + ann.radius + pad, ann.y + ann.radius + pad)
    if isinstance(ann, (Arrow, Line)):
        head = ann.head_size if isinstance(ann, Arrow) else 0
        pad = ann.line_width + head
        return (min(ann.x1, ann.x2) - pad, min(ann.y1, ann.y2) - pad,
                max(ann.x1, ann.x2) + pad, max(ann.y1, ann.y2) + pad)
    if isinstance(ann, Text):
        # Conservative: assume each character is ~font_size wide
        width_est = max(1, len(ann.text) * ann.font_size)
        return (ann.x, ann.y, ann.x + width_est, ann.y + ann.font_size)
    if isinstance(ann, NumberedCallout):
        return (ann.x - ann.radius, ann.y - ann.radius, ann.x + ann.radius, ann.y + ann.radius)
    raise TypeError(f"no bbox rule for {type(ann).__name__}")


def annotate_image_bytes(payload: AnnotateImageInput) -> bytes:
    """Apply annotations to an image and return the encoded output bytes.

    Does not write to disk. The caller (server.py) handles output paths.
    """
    # JPEG + alpha pre-check (cheap, runs before opening the image).
    if payload.output_format == "jpeg":
        for ann in payload.annotations:
            for field in ("color", "fill", "background"):
                value = getattr(ann, field, None)
                if value is None:
                    continue
                rgba = resolve_color(value)
                if rgba[3] != 255:
                    raise ValueError(
                        f"output_format='jpeg' is incompatible with alpha < 255 on annotation field {field!r}"
                    )

    img = _open_input(payload).convert("RGBA")
    img_w, img_h = img.size
    scaled = [_scale(ann, payload.coordinate_space, payload.device_scale) for ann in payload.annotations]

    # Out-of-bounds pre-check (runs after scaling so CSS-space annotations are checked in image space).
    for idx, ann in enumerate(scaled):
        bx1, by1, bx2, by2 = _bbox_of(ann)
        # Standard interval overlap test:
        if bx2 < 0 or by2 < 0 or bx1 > img_w or by1 > img_h:
            raise ValueError(
                f"annotation[{idx}] of type {ann.type!r} lies fully outside the image bounds "
                f"(image is {img_w}x{img_h}, annotation bbox is {(bx1, by1, bx2, by2)})"
            )

    draw = ImageDraw.Draw(img, "RGBA")
    for ann in scaled:
        _dispatch(draw, ann)
    out = BytesIO()
    fmt = "PNG" if payload.output_format == "png" else "JPEG"
    flat = img if fmt == "PNG" else img.convert("RGB")
    flat.save(out, format=fmt)
    return out.getvalue()


def _open_input(payload: AnnotateImageInput) -> Image.Image:
    if payload.input_path is not None:
        path = Path(payload.input_path)
        if not path.exists():
            raise FileNotFoundError(f"input_path does not exist: {payload.input_path}")
        return Image.open(path)
    assert payload.input_base64 is not None
    raw = base64.b64decode(payload.input_base64, validate=True)
    return Image.open(BytesIO(raw))


def _scale(ann: Annotation, space, device_scale) -> Annotation:
    if isinstance(ann, Rectangle):
        x, y, w, h = scale_rect(ann.x, ann.y, ann.width, ann.height, space=space, device_scale=device_scale)
        return ann.model_copy(update={
            "x": x, "y": y, "width": w, "height": h,
            "line_width": scale_value(ann.line_width, space=space, device_scale=device_scale),
            "radius": scale_value(ann.radius, space=space, device_scale=device_scale),
        })
    if isinstance(ann, Circle):
        x, y = scale_point(ann.x, ann.y, space=space, device_scale=device_scale)
        return ann.model_copy(update={
            "x": x, "y": y,
            "radius": scale_value(ann.radius, space=space, device_scale=device_scale),
            "line_width": scale_value(ann.line_width, space=space, device_scale=device_scale),
        })
    if isinstance(ann, (Arrow, Line)):
        x1, y1 = scale_point(ann.x1, ann.y1, space=space, device_scale=device_scale)
        x2, y2 = scale_point(ann.x2, ann.y2, space=space, device_scale=device_scale)
        updates = {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "line_width": scale_value(ann.line_width, space=space, device_scale=device_scale),
        }
        if isinstance(ann, Arrow):
            updates["head_size"] = scale_value(ann.head_size, space=space, device_scale=device_scale)
        return ann.model_copy(update=updates)
    if isinstance(ann, Text):
        x, y = scale_point(ann.x, ann.y, space=space, device_scale=device_scale)
        return ann.model_copy(update={
            "x": x, "y": y,
            "font_size": scale_value(ann.font_size, space=space, device_scale=device_scale),
            "padding": scale_value(ann.padding, space=space, device_scale=device_scale),
        })
    if isinstance(ann, NumberedCallout):
        x, y = scale_point(ann.x, ann.y, space=space, device_scale=device_scale)
        return ann.model_copy(update={
            "x": x, "y": y,
            "radius": scale_value(ann.radius, space=space, device_scale=device_scale),
            "font_size": scale_value(ann.font_size, space=space, device_scale=device_scale),
        })
    raise TypeError(f"unsupported annotation type: {type(ann).__name__}")


_DISPATCH: dict[type, Callable] = {
    Rectangle: draw_rectangle,
    Circle: draw_circle,
    Arrow: draw_arrow,
    Line: draw_line,
    Text: draw_text,
    NumberedCallout: draw_numbered_callout,
}


def _dispatch(draw: ImageDraw.ImageDraw, ann: Annotation) -> None:
    fn = _DISPATCH.get(type(ann))
    if fn is None:
        raise TypeError(f"no renderer registered for {type(ann).__name__}")
    fn(draw, ann)
