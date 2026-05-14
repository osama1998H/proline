from __future__ import annotations

import base64
from pathlib import Path
from io import BytesIO

import pytest
from PIL import Image

from image_annotator_mcp.annotate import annotate_image_bytes
from image_annotator_mcp.models import AnnotateImageInput


def _load_input(blank_white: Path, annotations, **kwargs) -> AnnotateImageInput:
    return AnnotateImageInput(input_path=str(blank_white), annotations=annotations, **kwargs)


def test_batch_applies_all_annotations(blank_white):
    payload = _load_input(
        blank_white,
        annotations=[
            {"type": "rectangle", "x": 10, "y": 10, "width": 30, "height": 30, "color": "red"},
            {"type": "rectangle", "x": 60, "y": 10, "width": 30, "height": 30, "color": "green"},
        ],
    )
    out_bytes = annotate_image_bytes(payload)
    img = Image.open(BytesIO(out_bytes)).convert("RGB")
    # First rectangle's border pixel is red
    assert img.getpixel((10, 10))[0] > 180
    assert img.getpixel((10, 10))[2] < 80
    # Second rectangle's border pixel is green
    g_pixel = img.getpixel((60, 10))
    assert g_pixel[0] < 100
    assert g_pixel[1] > 100


def test_later_annotation_overdraws_earlier(blank_white):
    payload = _load_input(
        blank_white,
        annotations=[
            {"type": "rectangle", "x": 20, "y": 20, "width": 60, "height": 30, "color": "red", "fill": "red"},
            {"type": "rectangle", "x": 30, "y": 25, "width": 20, "height": 20, "color": "green", "fill": "green"},
        ],
    )
    out_bytes = annotate_image_bytes(payload)
    img = Image.open(BytesIO(out_bytes)).convert("RGB")
    # Inside the second rectangle: green
    inside_second = img.getpixel((35, 30))
    assert inside_second[1] > inside_second[0]


def test_css_space_2x_scales_coords(blank_white):
    # Source is 200x100. With 2x scaling the rect at (5,5,10,10) lands at (10,10,20,20).
    payload = _load_input(
        blank_white,
        annotations=[
            {"type": "rectangle", "x": 5, "y": 5, "width": 10, "height": 10, "color": "red", "line_width": 2}
        ],
        coordinate_space="css",
        device_scale=2.0,
    )
    out_bytes = annotate_image_bytes(payload)
    img = Image.open(BytesIO(out_bytes)).convert("RGB")
    # Inside the un-scaled region (1,1) should still be white.
    assert img.getpixel((1, 1)) == (255, 255, 255)
    # The border at (10, 10) should be red.
    assert img.getpixel((10, 10))[0] > 180


def test_base64_input_round_trip(blank_white):
    raw = blank_white.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    payload = AnnotateImageInput(
        input_base64=b64,
        output_path="/tmp/_annotator_test_round.png",
        annotations=[
            {"type": "rectangle", "x": 10, "y": 10, "width": 30, "height": 30, "color": "red"}
        ],
    )
    out_bytes = annotate_image_bytes(payload)
    img = Image.open(BytesIO(out_bytes)).convert("RGB")
    assert img.size == (200, 100)
    assert img.getpixel((10, 10))[0] > 180


def test_unknown_input_path_raises(tmp_path):
    bogus = tmp_path / "nope.png"
    payload = AnnotateImageInput(
        input_path=str(bogus),
        annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
    )
    with pytest.raises(FileNotFoundError):
        annotate_image_bytes(payload)
