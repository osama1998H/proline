from __future__ import annotations

import base64
import shutil
from pathlib import Path

import pytest
from PIL import Image

from image_annotator_mcp.server import annotate_image_tool

SAMPLE_SOURCE = Path(__file__).resolve().parents[1] / "samples" / "hourly.jpg"


def test_writes_to_explicit_output_path(blank_white, tmp_path):
    out = tmp_path / "annotated.png"
    result = annotate_image_tool(
        input_path=str(blank_white),
        output_path=str(out),
        annotations=[{"type": "rectangle", "x": 10, "y": 10, "width": 30, "height": 30, "color": "red"}],
    )
    assert Path(result["saved_path"]) == out
    assert out.exists()
    assert result["width"] == 200
    assert result["height"] == 100
    img = Image.open(out).convert("RGB")
    assert img.getpixel((10, 10))[0] > 180


def test_derived_output_path(blank_white):
    result = annotate_image_tool(
        input_path=str(blank_white),
        annotations=[{"type": "rectangle", "x": 10, "y": 10, "width": 30, "height": 30}],
    )
    expected = blank_white.with_suffix("").as_posix() + ".annotated.png"
    assert result["saved_path"] == expected
    assert Path(expected).exists()


def test_returns_image_content_block(blank_white):
    result = annotate_image_tool(
        input_path=str(blank_white),
        annotations=[{"type": "rectangle", "x": 10, "y": 10, "width": 30, "height": 30}],
    )
    image = result["image"]
    assert image["type"] == "image"
    assert image["mimeType"] == "image/png"
    raw = base64.b64decode(image["data"])
    # decodable by Pillow
    from io import BytesIO
    img = Image.open(BytesIO(raw))
    assert img.size == (200, 100)


def test_missing_input_path(tmp_path):
    bogus = tmp_path / "nope.png"
    with pytest.raises(FileNotFoundError):
        annotate_image_tool(
            input_path=str(bogus),
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


def test_both_inputs_rejected(blank_white):
    with pytest.raises(ValueError):
        annotate_image_tool(
            input_path=str(blank_white),
            input_base64="abc",
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


def test_neither_input_rejected():
    with pytest.raises(ValueError):
        annotate_image_tool(
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


def test_css_without_device_scale_rejected(blank_white):
    with pytest.raises(ValueError):
        annotate_image_tool(
            input_path=str(blank_white),
            coordinate_space="css",
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


def test_base64_without_output_path_rejected():
    with pytest.raises(ValueError):
        annotate_image_tool(
            input_base64="iVBORw0KGgo=",  # arbitrary, doesn't need to decode
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


def test_output_parent_must_exist(blank_white, tmp_path):
    missing_dir = tmp_path / "does_not_exist" / "out.png"
    with pytest.raises(FileNotFoundError):
        annotate_image_tool(
            input_path=str(blank_white),
            output_path=str(missing_dir),
            annotations=[{"type": "rectangle", "x": 1, "y": 1, "width": 2, "height": 2}],
        )


@pytest.mark.skipif(not SAMPLE_SOURCE.exists(), reason="reference sample not present")
def test_smoke_annotate_real_screenshot(tmp_path):
    # Copy the sample so we don't write next to it.
    work = tmp_path / "hourly.png"
    Image.open(SAMPLE_SOURCE).convert("RGB").save(work)

    result = annotate_image_tool(
        input_path=str(work),
        annotations=[
            {"type": "rectangle", "x": 220, "y": 195, "width": 70, "height": 30, "color": "green", "line_width": 4},
            {"type": "rectangle", "x": 398, "y": 195, "width": 95, "height": 30, "color": "green", "line_width": 4},
            {"type": "text", "x": 230, "y": 160, "text": "verified", "color": "red", "font_size": 14},
        ],
    )
    saved = Path(result["saved_path"])
    assert saved.exists()
    img = Image.open(saved).convert("RGB")
    # Pixel on the first rectangle's top edge should be green-ish.
    px = img.getpixel((250, 195))
    assert px[1] > px[0] and px[1] > px[2], f"expected green border, got {px}"
