from __future__ import annotations

from typing import Literal, Optional

Space = Literal["image", "css"]


class ScalingError(ValueError):
    """Raised when coordinate-space scaling parameters are invalid."""


def _check_css_params(space: Space, device_scale: Optional[float]) -> None:
    if space != "css":
        return
    if device_scale is None:
        raise ScalingError("device_scale is required when coordinate_space='css'")
    if device_scale <= 0:
        raise ScalingError(f"device_scale must be positive, got {device_scale}")


def scale_value(value: float, *, space: Space, device_scale: Optional[float]) -> int:
    _check_css_params(space, device_scale)
    if space == "image":
        return int(value)
    return round(value * device_scale)  # type: ignore[operator]


def scale_point(
    x: float, y: float, *, space: Space, device_scale: Optional[float]
) -> tuple[int, int]:
    _check_css_params(space, device_scale)
    if space == "image":
        return int(x), int(y)
    return round(x * device_scale), round(y * device_scale)  # type: ignore[operator]


def scale_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    space: Space,
    device_scale: Optional[float],
) -> tuple[int, int, int, int]:
    """Scale rectangle preserving right and bottom edges.

    Scales (x, y, x+width, y+height) independently with banker's rounding,
    then derives width/height from the rounded edges. This prevents a 1px
    drift between the rounded width and the rounded right edge when the
    scale factor is fractional.
    """
    _check_css_params(space, device_scale)
    if space == "image":
        return int(x), int(y), int(width), int(height)
    s = device_scale  # type: ignore[assignment]
    left = round(x * s)
    top = round(y * s)
    right = round((x + width) * s)
    bottom = round((y + height) * s)
    return left, top, right - left, bottom - top
