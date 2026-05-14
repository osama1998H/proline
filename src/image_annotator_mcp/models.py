from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter, model_validator


Color = Union[str, list[int]]


class _ShapeBase(BaseModel):
    color: Color = "#22C55E"
    line_width: int = Field(default=4, ge=1)


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
