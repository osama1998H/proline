import pytest
from pydantic import ValidationError
from image_annotator_mcp.models import (
    Annotation,
    Rectangle,
    Circle,
    Arrow,
    Line,
    Text,
    NumberedCallout,
    AnnotateImageInput,
    parse_annotation,
)


class TestRectangle:
    def test_minimum_fields(self):
        r = Rectangle(type="rectangle", x=10, y=20, width=30, height=40)
        assert r.x == 10
        assert r.color == "#22C55E"
        assert r.line_width == 4
        assert r.fill is None
        assert r.radius == 0

    def test_negative_width_rejected(self):
        with pytest.raises(ValidationError):
            Rectangle(type="rectangle", x=10, y=20, width=-1, height=40)

    def test_negative_height_rejected(self):
        with pytest.raises(ValidationError):
            Rectangle(type="rectangle", x=10, y=20, width=30, height=-1)


class TestCircle:
    def test_minimum_fields(self):
        c = Circle(type="circle", x=10, y=20, radius=5)
        assert c.radius == 5

    def test_zero_radius_rejected(self):
        with pytest.raises(ValidationError):
            Circle(type="circle", x=10, y=20, radius=0)


class TestArrow:
    def test_minimum_fields(self):
        a = Arrow(type="arrow", x1=0, y1=0, x2=10, y2=10)
        assert a.head_size == 12


class TestText:
    def test_minimum_fields(self):
        t = Text(type="text", x=10, y=20, text="hello")
        assert t.font_size == 14
        assert t.background is None


class TestNumberedCallout:
    def test_minimum_fields(self):
        n = NumberedCallout(type="numbered_callout", x=10, y=20, number=1)
        assert n.radius == 14
        assert n.font_size == 16


class TestParseAnnotation:
    def test_dispatches_on_type(self):
        annotation = parse_annotation({"type": "rectangle", "x": 1, "y": 2, "width": 3, "height": 4})
        assert isinstance(annotation, Rectangle)

    def test_unknown_type_raises(self):
        with pytest.raises(ValidationError):
            parse_annotation({"type": "ellipse", "x": 1, "y": 2, "radius": 3})

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            parse_annotation({"type": "rectangle", "x": 1, "y": 2})


class TestAnnotateImageInput:
    def test_requires_one_of_input_path_or_base64(self):
        with pytest.raises(ValidationError):
            AnnotateImageInput(annotations=[])

    def test_rejects_both_inputs(self):
        with pytest.raises(ValidationError):
            AnnotateImageInput(
                input_path="/tmp/x.png",
                input_base64="abc",
                annotations=[],
            )

    def test_css_requires_device_scale(self):
        with pytest.raises(ValidationError):
            AnnotateImageInput(
                input_path="/tmp/x.png",
                coordinate_space="css",
                annotations=[],
            )

    def test_base64_requires_output_path(self):
        with pytest.raises(ValidationError):
            AnnotateImageInput(input_base64="abc", annotations=[])

    def test_valid_path_input(self):
        v = AnnotateImageInput(
            input_path="/tmp/x.png",
            annotations=[{"type": "rectangle", "x": 1, "y": 2, "width": 3, "height": 4}],
        )
        assert v.coordinate_space == "image"
        assert v.output_format == "png"
