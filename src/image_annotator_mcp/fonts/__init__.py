"""Bundled font access for image_annotator_mcp.

Uses Pillow's internally bundled font (returned by ImageFont.load_default(size=...))
so this server has no dependency on fonts installed on the host system.
"""
from __future__ import annotations

from PIL import ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Return a TrueType font of the given pixel size, sourced from Pillow's bundle."""
    if size < 6:
        raise ValueError(f"font size must be >= 6, got {size}")
    return ImageFont.load_default(size=size)
