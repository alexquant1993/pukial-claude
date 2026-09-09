"""Photoreal frame compositing + drop shadow for ASO scaffolds."""
from PIL import Image, ImageFilter

SHADOW_OFFSET_Y = 24
SHADOW_BLUR_RADIUS = 60
SHADOW_OPACITY = 46  # ≈ 18% of 255


def composite_frame(
    canvas: Image.Image,
    frame_path: str,
    device_x: int,
    device_y: int,
    device_w: int,
    with_shadow: bool = True,
) -> Image.Image:
    """Composite the photoreal frame PNG onto `canvas` at (device_x, device_y).

    The frame is scaled so its width matches device_w (aspect-preserving).
    If with_shadow=True, a Pillow Gaussian drop shadow from the frame's alpha
    channel is composited UNDER the frame.

    Returns a new RGBA image; the input canvas is not mutated.
    """
    canvas = canvas.convert("RGBA").copy()
    frame = Image.open(frame_path).convert("RGBA")

    # Scale frame width → device_w, keeping aspect ratio.
    if frame.width != device_w:
        new_h = int(round(frame.height * (device_w / frame.width)))
        frame = frame.resize((device_w, new_h), Image.LANCZOS)

    if with_shadow:
        shadow = _build_shadow(frame, canvas.size, device_x, device_y)
        canvas = Image.alpha_composite(canvas, shadow)

    # Paste frame on top (alpha-aware).
    frame_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    frame_layer.paste(frame, (device_x, device_y), frame)
    canvas = Image.alpha_composite(canvas, frame_layer)
    return canvas


def _build_shadow(
    frame: Image.Image,
    canvas_size: tuple,
    device_x: int,
    device_y: int,
) -> Image.Image:
    """Build a soft drop-shadow layer the size of the canvas.

    The silhouette is drawn on a padded canvas (blur_radius on each side) so
    Pillow's GaussianBlur can spread the shadow beyond the frame's bounding box.
    """
    pad = SHADOW_BLUR_RADIUS * 2
    padded_w = frame.width + pad * 2
    padded_h = frame.height + pad * 2

    # Extract frame alpha as a grayscale mask.
    alpha = frame.split()[-1]
    # Paint black at SHADOW_OPACITY using the frame alpha as mask, on padded canvas.
    shadow_silhouette = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
    black = Image.new("RGBA", frame.size, (0, 0, 0, SHADOW_OPACITY))
    shadow_silhouette.paste(black, (pad, pad), alpha)
    # Blur — can now spread freely within the padding.
    shadow_silhouette = shadow_silhouette.filter(
        ImageFilter.GaussianBlur(SHADOW_BLUR_RADIUS)
    )
    # Place onto full canvas, accounting for the padding offset.
    # Use paste without mask so the RGBA alpha values are copied directly;
    # the caller uses alpha_composite to blend the shadow under the frame.
    out = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    paste_x = device_x - pad
    paste_y = device_y + SHADOW_OFFSET_Y - pad
    out.paste(shadow_silhouette, (paste_x, paste_y))
    return out
