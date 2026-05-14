import pytest
from image_annotator_mcp.scaling import scale_value, scale_rect, scale_point, ScalingError


class TestScaleValue:
    def test_image_space_returns_value_unchanged(self):
        assert scale_value(10, space="image", device_scale=None) == 10

    def test_image_space_ignores_device_scale(self):
        assert scale_value(10, space="image", device_scale=2.0) == 10

    def test_css_space_doubles_at_2x(self):
        assert scale_value(10, space="css", device_scale=2.0) == 20

    def test_css_space_banker_rounding(self):
        # 5 * 1.5 = 7.5 -> rounds to 8 under banker's rounding
        assert scale_value(5, space="css", device_scale=1.5) == 8
        # 7 * 1.5 = 10.5 -> rounds to 10 under banker's rounding
        assert scale_value(7, space="css", device_scale=1.5) == 10

    def test_css_space_without_device_scale_raises(self):
        with pytest.raises(ScalingError):
            scale_value(10, space="css", device_scale=None)

    def test_css_space_with_zero_device_scale_raises(self):
        with pytest.raises(ScalingError):
            scale_value(10, space="css", device_scale=0)

    def test_css_space_with_negative_device_scale_raises(self):
        with pytest.raises(ScalingError):
            scale_value(10, space="css", device_scale=-1)


class TestScaleRect:
    def test_image_space_passthrough(self):
        assert scale_rect(10, 20, 30, 40, space="image", device_scale=None) == (10, 20, 30, 40)

    def test_css_space_2x_doubles_all(self):
        assert scale_rect(10, 20, 30, 40, space="css", device_scale=2.0) == (20, 40, 60, 80)

    def test_css_space_fractional_keeps_right_edge_stable(self):
        # x=5, w=7 -> right=12 in CSS. At 1.5x: right=18, left=8, so width=10 (not round(7*1.5)=10).
        # x=7, w=3 -> right=10 in CSS. At 1.5x: right=15 (round(10.5)=10? banker -> 10), left=10 (round(10.5)=10), width=0.
        # Use a case where independent rounding would drift.
        # x=3, w=5 -> right=8 at css. At 1.5x: left=round(4.5)=4, right=round(12)=12, width=8.
        # Independent rounding of w: round(5*1.5)=round(7.5)=8. Same here. Pick a drift case:
        # x=1, w=3 -> right=4. At 1.5x: left=round(1.5)=2, right=round(6)=6, width=4. Indep w: round(4.5)=4. Same.
        # Pick: x=2, w=3 -> right=5. At 1.5x: left=round(3)=3, right=round(7.5)=8, width=5. Indep w: round(4.5)=4. Drift!
        assert scale_rect(2, 0, 3, 1, space="css", device_scale=1.5) == (3, 0, 5, 2)


class TestScalePoint:
    def test_image_space_passthrough(self):
        assert scale_point(10, 20, space="image", device_scale=None) == (10, 20)

    def test_css_space_2x(self):
        assert scale_point(10, 20, space="css", device_scale=2.0) == (20, 40)
