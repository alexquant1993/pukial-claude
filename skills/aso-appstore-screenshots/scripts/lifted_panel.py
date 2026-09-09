"""Pillow rendering of the `literal` mode lifted UI panel."""
from PIL import Image, ImageDraw, ImageFilter

PANEL_CORNER_R_DEFAULT = 24
PANEL_SHADOW_OFFSET = (8, 14)
PANEL_SHADOW_BLUR = 24
PANEL_SHADOW_ALPHA = 110
PANEL_SHADOW_PAD = 60


def render(
    canvas: Image.Image,
    shot: Image.Image,
    rect: tuple,
    screen_x: int,
    screen_y: int,
    screen_scale: float,
    device_x: int,
    device_w: int,
    anchor: str,
    scale_factor: float,
    overflow: int,
    corner_r: int = PANEL_CORNER_R_DEFAULT,
) -> tuple:
    """Paint a lifted UI panel. Returns (canvas, panel_bbox)."""
    rect_x, rect_y, rect_w, rect_h = rect
    PANEL_CORNER_R = corner_r
    panel_src = shot.crop(
        (rect_x, rect_y, rect_x + rect_w, rect_y + rect_h)
    ).convert("RGBA")

    final_w = int(rect_w * screen_scale * scale_factor)
    final_h = int(rect_h * screen_scale * scale_factor)
    if final_w <= 0 or final_h <= 0:
        raise ValueError(f"Invalid panel size: {final_w}x{final_h}")
    panel_src = panel_src.resize((final_w, final_h), Image.LANCZOS)

    panel = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    corner_mask = Image.new("L", (final_w, final_h), 0)
    ImageDraw.Draw(corner_mask).rounded_rectangle(
        [0, 0, final_w, final_h], radius=PANEL_CORNER_R, fill=255,
    )
    panel.paste(panel_src, (0, 0), corner_mask)

    src_center_y_on_canvas = screen_y + (rect_y + rect_h / 2) * screen_scale
    panel_y = int(src_center_y_on_canvas - final_h / 2)
    if anchor == "left":
        panel_x = device_x - overflow
    elif anchor == "right":
        panel_x = device_x + device_w + overflow - final_w
    elif anchor == "center":
        panel_x = device_x + (device_w - final_w) // 2
    else:
        raise ValueError(
            f"anchor must be 'left', 'right', or 'center', got {anchor!r}"
        )

    sw = final_w + 2 * PANEL_SHADOW_PAD
    sh = final_h + 2 * PANEL_SHADOW_PAD
    shadow_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_layer).rounded_rectangle(
        [PANEL_SHADOW_PAD, PANEL_SHADOW_PAD,
         PANEL_SHADOW_PAD + final_w, PANEL_SHADOW_PAD + final_h],
        radius=PANEL_CORNER_R, fill=(0, 0, 0, PANEL_SHADOW_ALPHA),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(PANEL_SHADOW_BLUR))

    shadow_full = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_full.alpha_composite(
        shadow_layer,
        (panel_x - PANEL_SHADOW_PAD + PANEL_SHADOW_OFFSET[0],
         panel_y - PANEL_SHADOW_PAD + PANEL_SHADOW_OFFSET[1]),
    )
    canvas = Image.alpha_composite(canvas, shadow_full)

    panel_full = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    panel_full.alpha_composite(panel, (panel_x, panel_y))
    canvas = Image.alpha_composite(canvas, panel_full)

    return canvas, (panel_x, panel_y, final_w, final_h)
