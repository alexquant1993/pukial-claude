"""Tests for the photoreal frame compositor."""
import os
from PIL import Image
import frame_composite


def test_compose_frame_preserves_screen_transparency(assets_dir):
    """A pixel inside the frame's screen area should equal the UI behind it."""
    frame_path = os.path.join(assets_dir, "iphone-6.9-frame.png")
    # 1056x2155 base (matches iPhone 6.9 device_w when frame is scaled).
    bg = Image.new("RGBA", (1056, 2868), (255, 215, 240, 255))
    # Paint a green pixel at the center of where the screen will be.
    bg.putpixel((528, 1700), (0, 255, 0, 255))
    result = frame_composite.composite_frame(
        canvas=bg,
        frame_path=frame_path,
        device_x=0,
        device_y=738,
        device_w=1056,
    )
    # Frame screen-interior is transparent → green pixel should still show.
    assert result.getpixel((528, 1700))[:3] == (0, 255, 0)


def test_drop_shadow_renders_below_phone(assets_dir):
    frame_path = os.path.join(assets_dir, "iphone-6.9-frame.png")
    bg = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    result = frame_composite.composite_frame(
        canvas=bg,
        frame_path=frame_path,
        device_x=132,
        device_y=738,
        device_w=1056,
        with_shadow=True,
    )
    # A pixel just outside the chassis on the right, at mid-height, should
    # be darker than the pure bg because the shadow extends a bit.
    bg_color = (255, 215, 240)
    chassis_right_x = 132 + 1056
    shadow_sample = result.getpixel((chassis_right_x + 20, 1700))[:3]
    assert shadow_sample[0] < bg_color[0]  # darker red component
