from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter, WithJsonSchema, model_validator


Color = Union[str, list[int]]


# Stroke-width presets. Keywords map to base CSS-pixel values; the css→image
# scaling step (annotate._scale) multiplies these by device_scale.
LINE_WIDTH_PX: dict[str, int] = {"thin": 2, "regular": 4, "bold": 7}
_LINE_WIDTH_DEFAULT_KEYWORD = "regular"
_LINE_WIDTH_DEFAULT_PX = LINE_WIDTH_PX[_LINE_WIDTH_DEFAULT_KEYWORD]


def _resolve_line_width(v: Any) -> int:
    # External callers must pass a keyword string. annotate._scale writes a
    # scaled int back via model_copy(update=...), which in Pydantic v2 does NOT
    # re-run BeforeValidator — that bypass is load-bearing and pinned by
    # test_models.TestLineWidth.test_model_copy_preserves_int_update.
    if isinstance(v, bool) or not isinstance(v, str):
        raise ValueError(
            f"line_width must be one of {sorted(LINE_WIDTH_PX)} "
            f"(e.g. {_LINE_WIDTH_DEFAULT_KEYWORD!r}), got {type(v).__name__}={v!r}"
        )
    if v not in LINE_WIDTH_PX:
        raise ValueError(
            f"line_width must be one of {sorted(LINE_WIDTH_PX)}, got {v!r}"
        )
    return LINE_WIDTH_PX[v]


LineWidth = Annotated[
    int,
    BeforeValidator(_resolve_line_width),
    WithJsonSchema({
        "type": "string",
        "enum": sorted(LINE_WIDTH_PX),
        "default": _LINE_WIDTH_DEFAULT_KEYWORD,
        "description": (
            "Stroke preset. Keywords map to CSS-pixel values: "
            "'thin'=2, 'regular'=4, 'bold'=7. When coordinate_space='css' the "
            "resolved value is multiplied by device_scale before drawing."
        ),
    }),
]


class _ShapeBase(BaseModel):
    # validate_default ensures the keyword default flows through BeforeValidator
    # (so the stored value is the resolved int) and the JSON schema's default
    # stays in step with the enum.
    model_config = ConfigDict(validate_default=True)

    color: Color = "#22C55E"
    line_width: LineWidth = _LINE_WIDTH_DEFAULT_KEYWORD  # type: ignore[assignment]


class Rectangle(_ShapeBase):
    type: Literal["rectangle"]
    x: int
    y: int
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    fill: Optional[Color] = None
    radius: int = Field(default=0, ge=0)


class Circle(_ShapeBase):
    type: Literal["circle"]
    x: int
    y: int
    radius: int = Field(ge=1)
    fill: Optional[Color] = None


class Arrow(_ShapeBase):
    type: Literal["arrow"]
    x1: int
    y1: int
    x2: int
    y2: int
    head_size: int = Field(default=12, ge=1)


class Line(_ShapeBase):
    type: Literal["line"]
    x1: int
    y1: int
    x2: int
    y2: int


class Text(BaseModel):
    type: Literal["text"]
    x: int
    y: int
    text: str = Field(min_length=1)
    color: Color = "#22C55E"
    font_size: int = Field(default=14, ge=6)
    background: Optional[Color] = None
    padding: int = Field(default=4, ge=0)


class NumberedCallout(BaseModel):
    type: Literal["numbered_callout"]
    x: int
    y: int
    number: int = Field(ge=0)
    color: Color = "#22C55E"
    radius: int = Field(default=14, ge=6)
    font_size: int = Field(default=16, ge=6)


Annotation = Annotated[
    Union[Rectangle, Circle, Arrow, Line, Text, NumberedCallout],
    Field(discriminator="type"),
]


_annotation_adapter = TypeAdapter(Annotation)


def parse_annotation(data: dict[str, Any]) -> Annotation:
    return _annotation_adapter.validate_python(data)


class AnnotateImageInput(BaseModel):
    input_path: Optional[str] = None
    input_base64: Optional[str] = None
    output_path: Optional[str] = None
    output_format: Literal["png", "jpeg"] = "png"
    coordinate_space: Literal["image", "css"] = "image"
    device_scale: Optional[float] = None
    annotations: list[Annotation]

    @model_validator(mode="after")
    def _check_inputs(self) -> "AnnotateImageInput":
        has_path = self.input_path is not None
        has_b64 = self.input_base64 is not None
        if has_path == has_b64:
            raise ValueError("exactly one of input_path or input_base64 must be supplied")
        if has_b64 and self.output_path is None:
            raise ValueError("output_path is required when input_base64 is used")
        if self.coordinate_space == "css" and self.device_scale is None:
            raise ValueError("device_scale is required when coordinate_space='css'")
        if self.device_scale is not None and self.device_scale <= 0:
            raise ValueError(f"device_scale must be positive, got {self.device_scale}")
        return self
