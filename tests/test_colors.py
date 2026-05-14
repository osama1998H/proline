import pytest
from image_annotator_mcp.colors import resolve_color, ColorError


class TestResolveColor:
    def test_hex_six_digits(self):
        assert resolve_color("#22C55E") == (34, 197, 94, 255)

    def test_hex_six_digits_lowercase(self):
        assert resolve_color("#22c55e") == (34, 197, 94, 255)

    def test_hex_eight_digits_with_alpha(self):
        assert resolve_color("#22C55E80") == (34, 197, 94, 128)

    def test_named_green(self):
        assert resolve_color("green") == (0, 128, 0, 255)

    def test_named_red(self):
        assert resolve_color("red") == (255, 0, 0, 255)

    def test_rgb_tuple_three(self):
        assert resolve_color([34, 197, 94]) == (34, 197, 94, 255)

    def test_rgba_tuple_four(self):
        assert resolve_color([34, 197, 94, 128]) == (34, 197, 94, 128)

    def test_rgb_tuple_out_of_range_raises(self):
        with pytest.raises(ColorError):
            resolve_color([34, 300, 94])

    def test_rgb_tuple_wrong_length_raises(self):
        with pytest.raises(ColorError):
            resolve_color([34, 197])

    def test_unknown_string_raises(self):
        with pytest.raises(ColorError) as exc:
            resolve_color("not-a-color")
        assert "not-a-color" in str(exc.value)

    def test_invalid_hex_raises(self):
        with pytest.raises(ColorError):
            resolve_color("#GGGGGG")

    def test_none_raises(self):
        with pytest.raises(ColorError):
            resolve_color(None)
