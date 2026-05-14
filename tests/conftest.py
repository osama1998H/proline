from __future__ import annotations

import pytest
from pathlib import Path
from PIL import Image


@pytest.fixture
def blank_white(tmp_path: Path) -> Path:
    """A 200x100 fully-white PNG written to a temp file."""
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    out = tmp_path / "blank.png"
    img.save(out)
    return out


@pytest.fixture
def blank_image_obj() -> Image.Image:
    """A 200x100 fully-white in-memory Pillow image, never saved."""
    return Image.new("RGBA", (200, 100), color=(255, 255, 255, 255))


def assert_pixel(img: Image.Image, x: int, y: int, expected: tuple[int, int, int]) -> None:
    """Assert that the pixel at (x, y) is approximately the expected RGB.
    Antialiased edges may shift channels by a few, so we allow ±20 per channel.
    """
    actual = img.convert("RGB").getpixel((x, y))
    diffs = [abs(a - b) for a, b in zip(actual, expected)]
    assert all(d <= 20 for d in diffs), f"pixel at ({x},{y}): got {actual}, expected ≈ {expected}"


def assert_pixel_unchanged(img: Image.Image, x: int, y: int) -> None:
    """Assert that the pixel at (x, y) is still pure white (the conftest blank background)."""
    actual = img.convert("RGB").getpixel((x, y))
    assert actual == (255, 255, 255), f"pixel at ({x},{y}): got {actual}, expected white"
