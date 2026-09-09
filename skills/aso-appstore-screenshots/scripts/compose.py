#!/usr/bin/env python3
"""ASO scaffold composer — Pillow-only.

Pipeline per slot:
  1. Render background per chosen style (one of 8) — bg_renderer.render
  2. Composite the source app UI into the screen area
  3. Composite the photoreal phone frame (+ Pillow drop shadow underneath)
  4. Draw the headline above the phone
  5. Optionally render a literal lifted UI panel beside the phone
  6. Write scaffold.png + scaffold.meta.json

The AI is NOT involved at this stage. The output is a finished-looking
screenshot that the user can ship as-is for clean / literal slots, or as
a base for the optional hero card (Phase 7 → enhance_card.py).
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import bg_renderer
import frame_composite
import headline_render
import lifted_panel

# ── Device profiles ─────────────────────────────────────────────────
DEVICE_PROFILES = {
    "iphone-6.7": {
        "canvas": (1290, 2796),
        "device_w": 1030,
        "bezel": 15,
        "screen_corner_r": 62,
        "device_y": 720,
        "text_top": 200,
        "frame_file": "iphone-6.9-frame.png",
    },
    "iphone-6.5": {
        "canvas": (1242, 2688),
        "device_w": 994,
        "bezel": 15,
        "screen_corner_r": 60,
        "device_y": 692,
        "text_top": 192,
        "frame_file": "iphone-6.9-frame.png",
    },
    "iphone-6.9": {
        "canvas": (1320, 2868),
        "device_w": 1056,
        "bezel": 55,
        "bezel_top": 157,
        "screen_corner_r": 64,
        "device_y": 738,
        "text_top": 205,
        "frame_file": "iphone-6.9-frame.png",
    },
    "android": {
        # 1080x1920 (9:16) — Google Play caps max-side ratio at 2:1; the
        # earlier 1080x2400 (9:20, 2.22:1) was rejection-prone.
        "canvas": (1080, 1920),
        # device_w=720 (67% of canvas width) keeps the phone fully visible
        # on the shorter 9:16 canvas. The Android frame asset is 486×1024
        # (h/w=2.107) so 720×2.107=1517px tall; at device_y=500 that
        # leaves only ~97px of bottom bleed — close to iOS proportions.
        # The earlier 864 (80%) made the phone 1820px tall and clipped
        # 400px off the bottom.
        "device_w": 720,
        "bezel": 8,
        # 80 instead of 44: Android source captures include the phone's own
        # rounded-corner dark border baked into the pixels. A larger mask
        # radius cuts that border off so it doesn't show as a double-curve
        # inside our frame asset's screen window.
        "screen_corner_r": 80,
        "device_y": 500,
        "text_top": 130,
        # Per-profile font ratios. iOS canvas is much taller (2868 vs 1920),
        # so the default headline ratios (which scale by canvas_w) leave
        # the iOS headline taking ~10.4% of canvas height, but on Android
        # the same ratios eat ~15.6% — squeezing the gap to the phone.
        # These Android-specific ratios make the headline occupy the same
        # PROPORTION of canvas HEIGHT as on iOS (~10.4%), so the visual
        # balance matches iOS at any aspect ratio.
        "verb_max_ratio": 0.162,
        "desc_max_ratio": 0.079,
        "frame_file": "android-frame.png",
    },
}

BOTTOM_BLEED_PX = 500


def _default_frame_path(device: str, project_override_dir: str = None) -> str:
    """Resolve the frame asset path. Project override takes precedence."""
    profile = DEVICE_PROFILES[device]
    if project_override_dir:
        override = os.path.join(project_override_dir, profile["frame_file"])
        if os.path.exists(override):
            return override
    return os.path.join(SKILL_DIR, "assets", profile["frame_file"])


def _build_screen_mask_from_frame(
    frame_path: str,
    device_x: int, device_y: int, device_w: int,
    canvas_size: tuple, seed_x: int, seed_y: int,
):
    """Use the frame asset's own alpha channel as the source-content mask.

    Flood-fills from (seed_x, seed_y) — a known-interior point of the
    screen window on the rendered canvas — through every transparent
    frame pixel reachable. The resulting mask exactly matches the frame's
    screen window curve (including any subtle non-circular corners or
    notch cutouts), so source content never spills past the frame edge
    and there is no curve mismatch.
    """
    from collections import deque
    from PIL import ImageFilter
    frame = Image.open(frame_path).convert("RGBA")
    fw = frame.size[0]
    scale = device_w / fw
    new_size = (int(frame.size[0] * scale), int(frame.size[1] * scale))
    frame_resized = frame.resize(new_size, Image.LANCZOS)
    canvas_w, canvas_h = canvas_size
    framed = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    framed.paste(frame_resized, (device_x, device_y))

    fpx = framed.load()
    mask = Image.new("L", canvas_size, 0)
    mpx = mask.load()
    visited = bytearray(canvas_w * canvas_h)
    queue = deque()
    # Flood-fill threshold of 128 picks up the frame's anti-aliased edge
    # pixels too, so source content extends under the frame's soft border
    # instead of leaving a hairline gap of background color visible.
    threshold = 128
    if 0 <= seed_x < canvas_w and 0 <= seed_y < canvas_h:
        queue.append((seed_x, seed_y))
        visited[seed_y * canvas_w + seed_x] = 1
    while queue:
        x, y = queue.popleft()
        if fpx[x, y][3] >= threshold:
            continue
        mpx[x, y] = 255
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < canvas_w and 0 <= ny < canvas_h:
                idx = ny * canvas_w + nx
                if not visited[idx]:
                    visited[idx] = 1
                    if fpx[nx, ny][3] < threshold:
                        queue.append((nx, ny))
    # Belt-and-braces: dilate by 2 px so source covers the gap even if
    # the frame edge is sharper than the anti-alias threshold catches.
    mask = mask.filter(ImageFilter.MaxFilter(5))
    return mask


def _detect_screen_rect(frame_path: str):
    """Auto-detect the main rectangular transparent region (screen cutout)
    of a device frame asset by scanning the alpha channel in horizontal/vertical
    strips. Returns (x, y, w, h) in asset coords, or None if not detectable.

    Strategy:
      - Center column scan: find the largest contiguous transparent run that is
        not adjacent to the asset's edge (the screen body, not the outer margin
        or top/bottom asset padding).
      - Center row scan inside that vertical run: find the largest contiguous
        transparent run that is not adjacent to the edge (the screen body width,
        not the asset's side margin).
    """
    im = Image.open(frame_path).convert("RGBA")
    w, h = im.size
    px = im.load()
    margin_threshold = 10  # alpha below this = transparent

    def _runs(samples):
        runs, start, prev = [], 0, samples[0]
        for i in range(1, len(samples)):
            if samples[i] != prev:
                runs.append((prev, start, i - 1))
                start = i
                prev = samples[i]
        runs.append((prev, start, len(samples) - 1))
        return runs

    # Scan a column off-center so the centered notch / Dynamic Island doesn't
    # break the screen window's transparent run. ~20% from the left side hits
    # screen area on every device profile we support.
    off_x = max(1, int(w * 0.2))
    col = [px[off_x, y][3] < margin_threshold for y in range(h)]
    transparent_runs = [r for r in _runs(col) if r[0]]
    interior_runs = [
        r for r in transparent_runs
        if r[1] > 0 and r[2] < h - 1 and (r[2] - r[1]) > h * 0.2
    ]
    if not interior_runs:
        return None
    _, y0, y1 = max(interior_runs, key=lambda r: r[2] - r[1])

    mid_y = (y0 + y1) // 2
    row = [px[x, mid_y][3] < margin_threshold for x in range(w)]
    transparent_runs = [r for r in _runs(row) if r[0]]
    interior_runs = [
        r for r in transparent_runs
        if r[1] > 0 and r[2] < w - 1 and (r[2] - r[1]) > w * 0.2
    ]
    if not interior_runs:
        return None
    _, x0, x1 = max(interior_runs, key=lambda r: r[2] - r[1])

    return (x0, y0, x1 - x0 + 1, y1 - y0 + 1)


def compose(
    device: str,
    bg_style: str,
    bg_colors: list,
    verb: str,
    desc: str,
    text_color: str,
    screenshot_path: str,
    output_path: str,
    frame_path: str = None,
    font_path: str = None,
    desc_font_path: str = None,
    bg_blob_position: str = "center",
    bg_blob_positions: str = "upper-left,lower-right",
    breakout_zone: tuple = None,
    breakout_rect: tuple = None,
    breakout_anchor: str = None,
    breakout_scale: float = 1.5,
    breakout_overflow: int = 100,
    breakout_corner_r: int = 24,
    source_inset: int = 0,
    device_y_override: int = None,
    text_top_override: int = None,
    max_desc_lines: int = 2,
) -> None:
    if bg_style is None:
        bg_style = "plain"
    profile = DEVICE_PROFILES[device]
    canvas_w, canvas_h = profile["canvas"]
    device_w = profile["device_w"]
    bezel = profile["bezel"]
    bezel_top = profile.get("bezel_top", bezel)
    device_y = device_y_override if device_y_override is not None else profile["device_y"]
    text_top = text_top_override if text_top_override is not None else profile["text_top"]
    device_x = (canvas_w - device_w) // 2

    # Try to auto-detect the screen window from the frame asset itself —
    # eliminates drift between hardcoded bezel values and the asset.
    _frame_path_for_detect = frame_path or _default_frame_path(device)
    detected = _detect_screen_rect(_frame_path_for_detect)
    if detected is not None:
        asset_w = Image.open(_frame_path_for_detect).size[0]
        s = device_w / asset_w
        dx0, dy0, dw, dh = detected
        screen_x = int(device_x + dx0 * s)
        screen_y = int(device_y + dy0 * s)
        screen_w = int(dw * s)
        screen_h_visible = int(dh * s)
    else:
        screen_w = device_w - 2 * bezel
        screen_x = device_x + bezel
        screen_y = device_y + bezel_top
        screen_h_visible = None

    # 1. Background.
    bg = bg_renderer.render(
        style=bg_style,
        size=(canvas_w, canvas_h),
        colors=bg_colors,
        blob_position=bg_blob_position,
        blob_positions=bg_blob_positions,
    ).convert("RGBA")

    # 2. App UI fills the detected screen window exactly (stretch-to-fit,
    #    independent x/y scale — drift is <5% for matching device profiles,
    #    invisible at this resolution, and avoids cropping or letterbox).
    shot = Image.open(screenshot_path).convert("RGBA")
    # Some platforms' source captures include the phone's own rounded screen
    # border baked into the pixels (e.g. Android). Cropping a few px on each
    # side discards that border so it doesn't bleed through our frame.
    if source_inset > 0:
        shot = shot.crop((
            source_inset, source_inset,
            shot.width - source_inset, shot.height - source_inset,
        ))
    if screen_h_visible is not None:
        sc_w, sc_h = screen_w, screen_h_visible
        screen_h_for_mask = screen_h_visible
    else:
        screen_scale_legacy = screen_w / shot.width
        sc_w = screen_w
        sc_h = int(shot.height * screen_scale_legacy)
        screen_h_for_mask = canvas_h - screen_y + BOTTOM_BLEED_PX
    screen_scale = sc_w / shot.width
    shot_scaled = shot.resize((sc_w, sc_h), Image.LANCZOS)

    # Build the source-content mask from the frame asset's actual screen
    # window (flood-fill of its transparent region). This guarantees the
    # source's edge exactly tracks the frame's screen-window curve, with no
    # corner-radius guesswork or visible mismatch band.
    seed_x = screen_x + screen_w // 2
    seed_y = screen_y + (screen_h_visible if screen_h_visible else 100) // 2
    scr_mask = _build_screen_mask_from_frame(
        _frame_path_for_detect, device_x, device_y, device_w,
        (canvas_w, canvas_h), seed_x, seed_y,
    )
    scr_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    scr_layer.paste(shot_scaled, (screen_x, screen_y))
    scr_layer.putalpha(scr_mask)
    canvas = Image.alpha_composite(bg, scr_layer)

    # 3. Photoreal frame + drop shadow.
    frame_path = frame_path or _default_frame_path(device)
    canvas = frame_composite.composite_frame(
        canvas=canvas,
        frame_path=frame_path,
        device_x=device_x,
        device_y=device_y,
        device_w=device_w,
        with_shadow=True,
    )

    # 4. Headline.
    canvas, headline_band = headline_render.draw_headline(
        canvas=canvas,
        verb=verb,
        desc=desc,
        text_top=text_top,
        canvas_w=canvas_w,
        text_color=text_color,
        font_path=font_path,
        desc_font_path=desc_font_path,
        max_desc_lines=max_desc_lines,
        verb_max_ratio=profile.get("verb_max_ratio"),
        desc_max_ratio=profile.get("desc_max_ratio"),
    )

    # 5. Optional literal lifted panel (literal mode).
    panel_bbox = None
    panel_mode = "clean"
    derived_zone = None
    if breakout_rect is not None:
        if breakout_anchor not in ("left", "right", "center"):
            raise ValueError("breakout_anchor required for literal mode")
        canvas, panel_bbox = lifted_panel.render(
            canvas=canvas, shot=shot, rect=breakout_rect,
            screen_x=screen_x, screen_y=screen_y, screen_scale=screen_scale,
            device_x=device_x, device_w=device_w,
            anchor=breakout_anchor, scale_factor=breakout_scale,
            overflow=breakout_overflow,
            corner_r=breakout_corner_r,
        )
        panel_mode = "literal"
        derived_zone = list(panel_bbox)
    elif breakout_zone is not None:
        panel_mode = "hero"
        derived_zone = list(breakout_zone)

    # 6. Save image + sidecar.
    canvas.convert("RGB").save(output_path, "PNG")
    print(f"✓ {output_path} ({canvas_w}×{canvas_h}) [{device}, mode={panel_mode}]")

    meta = {
        "device": device,
        "canvas": [canvas_w, canvas_h],
        "device_y": device_y,
        "screen_rect": [
            screen_x, screen_y, screen_w,
            screen_h_visible if screen_h_visible is not None else canvas_h - screen_y,
        ],
        "panel_mode": panel_mode,
        "breakout_zone": derived_zone,
        "preserve_panel": list(panel_bbox) if panel_bbox else None,
        "headline_band": list(headline_band),
        "background": {"style": bg_style, "colors": bg_colors},
    }
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


def _parse_rect(s):
    parts = [int(p.strip()) for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"Rect must be 'x,y,w,h', got {s!r}")
    return tuple(parts)


def main():
    p = argparse.ArgumentParser(description="Compose store screenshot (Pillow-only).")
    p.add_argument("--device", choices=list(DEVICE_PROFILES.keys()), default="iphone-6.9")
    p.add_argument("--bg-style", default="plain", choices=[
        "plain", "linear-vertical", "linear-diagonal", "radial",
        "vignette", "blob", "dual-blob", "mesh-gradient",
    ])
    p.add_argument("--bg-color", required=True, help="Primary hex color")
    p.add_argument("--bg-color-2", default=None, help="Secondary hex (styles 2-8)")
    p.add_argument("--bg-color-3", default=None, help="Tertiary hex (dual-blob, mesh-gradient)")
    p.add_argument("--bg-color-4", default=None, help="Quaternary hex (mesh-gradient only)")
    p.add_argument("--bg-blob-position", default="center",
                   choices=list(bg_renderer.BLOB_POSITIONS.keys()))
    p.add_argument("--bg-blob-positions", default="upper-left,lower-right",
                   help="Comma-separated positions for dual-blob")
    p.add_argument("--verb", required=True)
    p.add_argument("--desc", required=True)
    p.add_argument("--text-color", default="white")
    p.add_argument("--screenshot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--frame-path", default=None,
                   help="Override frame asset path (default: skill-bundled).")
    p.add_argument("--font-path", default=None)
    p.add_argument("--desc-font-path", default=None)
    p.add_argument("--breakout-rect", type=_parse_rect, default=None,
                   help="Literal mode source rect")
    p.add_argument("--breakout-zone", type=_parse_rect, default=None,
                   help="Hero mode canvas zone")
    p.add_argument("--breakout-anchor", choices=["left", "right", "center"], default=None)
    p.add_argument("--breakout-scale", type=float, default=1.5)
    p.add_argument("--breakout-overflow", type=int, default=100)
    p.add_argument("--breakout-corner-r", type=int, default=24,
                   help="Lifted panel corner radius in canvas px (literal mode)")
    p.add_argument("--source-inset", type=int, default=0,
                   help="Crop N pixels from each side of the source before "
                        "placing into the frame. Use to discard a baked-in "
                        "phone-edge border (Android source captures).")
    p.add_argument("--device-y", type=int, default=None,
                   help="Override the profile's device_y (vertical position of the "
                        "phone frame). Use to push hero slots' phone down so the "
                        "headline has more breathing room.")
    p.add_argument("--text-top", type=int, default=None,
                   help="Override the profile's text_top (y where headline starts).")
    p.add_argument("--max-desc-lines", type=int, default=2,
                   help="Max lines for the desc text after word-wrap. Desc font "
                        "size auto-shrinks until it fits within this many lines "
                        "(default 2). Keeps long-locale phrases from crowding "
                        "the device frame below.")
    args = p.parse_args()

    if args.breakout_rect is not None and args.breakout_zone is not None:
        p.error("--breakout-rect and --breakout-zone are mutually exclusive.")

    bg_colors = [args.bg_color]
    for extra in (args.bg_color_2, args.bg_color_3, args.bg_color_4):
        if extra is not None:
            bg_colors.append(extra)

    compose(
        device=args.device,
        bg_style=args.bg_style,
        bg_colors=bg_colors,
        verb=args.verb, desc=args.desc, text_color=args.text_color,
        screenshot_path=args.screenshot, output_path=args.output,
        frame_path=args.frame_path,
        font_path=args.font_path, desc_font_path=args.desc_font_path,
        bg_blob_position=args.bg_blob_position,
        bg_blob_positions=args.bg_blob_positions,
        breakout_zone=args.breakout_zone,
        breakout_rect=args.breakout_rect,
        breakout_anchor=args.breakout_anchor,
        breakout_scale=args.breakout_scale,
        breakout_overflow=args.breakout_overflow,
        breakout_corner_r=args.breakout_corner_r,
        source_inset=args.source_inset,
        device_y_override=args.device_y,
        text_top_override=args.text_top,
        max_desc_lines=args.max_desc_lines,
    )


if __name__ == "__main__":
    main()
