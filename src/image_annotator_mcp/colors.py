from __future__ import annotations

from typing import Union

from PIL import ImageColor

Color = Union[str, list[int], tuple[int, ...]]
RGBA = tuple[int, int, int, int]


class ColorError(ValueError):
    """Raised when a color value cannot be resolved to RGBA."""


def resolve_color(value: Color | None) -> RGBA:
    if value is None:
        raise ColorError("color is required")

    if isinstance(value, str):
        return _resolve_string(value)

    if isinstance(value, (list, tuple)):
        return _resolve_sequence(value)

    raise ColorError(f"unsupported color type: {type(value).__name__}")


def _resolve_string(value: str) -> RGBA:
    stripped = value.strip()
    try:
        rgba = ImageColor.getcolor(stripped, "RGBA")
    except ValueError as exc:
        raise ColorError(f"unknown color: {value!r}") from exc
    if len(rgba) == 3:
        return (rgba[0], rgba[1], rgba[2], 255)
    return rgba  # type: ignore[return-value]


def _resolve_sequence(value: list[int] | tuple[int, ...]) -> RGBA:
    if len(value) not in (3, 4):
        raise ColorError(f"rgb tuple must have 3 or 4 elements, got {len(value)}")
    for channel in value:
        if not isinstance(channel, int) or not 0 <= channel <= 255:
            raise ColorError(f"rgb channel out of range: {channel!r}")
    if len(value) == 3:
        return (value[0], value[1], value[2], 255)
    return (value[0], value[1], value[2], value[3])
