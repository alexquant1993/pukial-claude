from deck_kit import geometry
from deck_kit.geometry import px, columns, CANVAS_W, CANVAS_H, SLIDE_W_EMU, SLIDE_H_EMU


def test_package_exposes_emu_constant():
    assert geometry.EMU == 9525


def test_px_converts_css_pixels_to_emu():
    assert px(1) == 9525
    assert px(0) == 0
    assert px(1280) == SLIDE_W_EMU
    assert px(720) == SLIDE_H_EMU


def test_px_rounds_to_the_nearest_emu():
    assert px(0.5) == 4762  # 4762.5 rounds to even under banker's rounding
    assert px(1.5) == 14288


def test_canvas_matches_a_16_by_9_slide():
    assert (CANVAS_W, CANVAS_H) == (1280, 720)
    assert SLIDE_W_EMU == CANVAS_W * 9525
    assert SLIDE_H_EMU == CANVAS_H * 9525


def test_columns_divides_the_content_band_evenly():
    col_w, xs = columns(left=48, right=1232, label_w=172, gap=12, n=3)
    assert len(xs) == 3
    assert col_w == (1232 - 48 - 172 - 3 * 12) / 3.0
    assert xs[0] == 48 + 172 + 12
    for a, b in zip(xs, xs[1:]):
        assert round(b - a, 6) == round(col_w + 12, 6)
    assert xs[-1] + col_w <= 1232
