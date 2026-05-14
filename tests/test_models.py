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
    LINE_WIDTH_PX,
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


class TestLineWidth:
    def test_keyword_resolves_to_px(self):
        for keyword, expected_px in LINE_WIDTH_PX.items():
            r = Rectangle(type="rectangle", x=0, y=0, width=10, height=10, line_width=keyword)
            assert r.line_width == expected_px

    def test_default_is_regular(self):
        r = Rectangle(type="rectangle", x=0, y=0, width=10, height=10)
        assert r.line_width == LINE_WIDTH_PX["regular"]

    def test_raw_int_rejected(self):
        with pytest.raises(ValidationError):
            Rectangle(type="rectangle", x=0, y=0, width=10, height=10, line_width=5)

    def test_unknown_keyword_rejected(self):
        with pytest.raises(ValidationError):
            Rectangle(type="rectangle", x=0, y=0, width=10, height=10, line_width="thicc")

    def test_none_rejected(self):
        with pytest.raises(ValidationError):
            Rectangle(type="rectangle", x=0, y=0, width=10, height=10, line_width=None)

    def test_applies_to_all_stroked_shapes(self):
        c = Circle(type="circle", x=0, y=0, radius=5, line_width="bold")
        a = Arrow(type="arrow", x1=0, y1=0, x2=5, y2=5, line_width="thin")
        ln = Line(type="line", x1=0, y1=0, x2=5, y2=5, line_width="regular")
        assert c.line_width == LINE_WIDTH_PX["bold"]
        assert a.line_width == LINE_WIDTH_PX["thin"]
        assert ln.line_width == LINE_WIDTH_PX["regular"]

    def test_model_copy_preserves_int_update(self):
        # annotate._scale relies on model_copy(update={"line_width": <int>})
        # bypassing the BeforeValidator that rejects raw ints. If a future
        # Pydantic config (e.g. revalidate_instances="always") breaks that
        # bypass, the css→image scaling path stops working — this test pins
        # the behavior so the regression is loud.
        r = Rectangle(type="rectangle", x=0, y=0, width=10, height=10, line_width="regular")
        scaled = r.model_copy(update={"line_width": 13})
        assert scaled.line_width == 13


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
