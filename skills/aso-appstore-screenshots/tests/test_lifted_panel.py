"""Tests for the literal-mode lifted UI panel renderer."""
from PIL import Image
import lifted_panel


def test_lifts_a_source_rect_onto_canvas():
    canvas = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    # Source UI: a 100x100 yellow square inside a larger white canvas.
    src = Image.new("RGBA", (500, 1000), (255, 255, 255, 255))
    from PIL import ImageDraw
    ImageDraw.Draw(src).rectangle([100, 100, 200, 200], fill=(255, 255, 0, 255))

    out, panel_bbox = lifted_panel.render(
        canvas=canvas,
        shot=src,
        rect=(100, 100, 100, 100),   # the yellow square in source coords
        screen_x=147,
        screen_y=753,
        screen_scale=1056 / 500,     # screen width 1056 / source width 500
        device_x=132,
        device_w=1056,
        anchor="left",
        scale_factor=1.5,
        overflow=100,
    )
    px, py, pw, ph = panel_bbox
    # Sample inside the panel — should be yellow-ish (with rounded corners
    # so the corners might be the bg; sample middle).
    mid = out.getpixel((px + pw // 2, py + ph // 2))[:3]
    assert mid == (255, 255, 0)
