#!/usr/bin/env python3
"""
Showcase Image Generator
Creates a preview image showing the deck of final App Store screenshots
on a white background with an optional GitHub link at the bottom. Defaults
to a single row; use --cols to wrap into multiple rows when the deck has
many slots (e.g., --cols 3 for a 5-slot deck → 3 on top, 2 on bottom).
"""

import argparse
import os
from PIL import Image, ImageDraw, ImageFont

# ── Layout ──────────────────────────────────────────────────────────
PADDING = 60
GAP = 40
BOTTOM_BAR_H = 100
FONT_SIZE_MAX = 48
FONT_SIZE_MIN = 16
TEXT_COLOUR = "#000000"
BG_COLOUR = (255, 255, 255)


def _resolve_font_path() -> str:
    """Mirror compose.py's resolver — same chain across macOS/Linux/Windows."""
    candidates = [
        "/Library/Fonts/SF-Pro-Display-Regular.otf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None  # caller will fall back to PIL's bitmap default.


FONT_PATH = _resolve_font_path()


def fit_text_font(text, max_w, size_max, size_min):
    """Return the largest font size where text fits within max_w."""
    if FONT_PATH is None:
        return ImageFont.load_default()
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(size_max, size_min - 1, -2):
        try:
            font = ImageFont.truetype(FONT_PATH, size)
        except OSError:
            return ImageFont.load_default()
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(FONT_PATH, size_min)


def create_showcase(screenshots, output_path, github_url=None, cols=None):
    # Load screenshots.
    images = [Image.open(p).convert("RGBA") for p in screenshots]
    n = len(images)
    if cols is None or cols <= 0:
        cols = n  # single-row default.
    cols = min(cols, n)
    rows = (n + cols - 1) // cols

    # Scale all to the same height for in-row alignment.
    target_h = 800
    scaled = []
    for img in images:
        ratio = target_h / img.height
        scaled.append(img.resize((int(img.width * ratio), target_h), Image.LANCZOS))

    # Compute per-row widths to size the canvas to the widest row.
    def row_width(row_idx):
        row_imgs = scaled[row_idx * cols:(row_idx + 1) * cols]
        if not row_imgs:
            return 0
        return sum(s.width for s in row_imgs) + GAP * (len(row_imgs) - 1)

    widest_row = max(row_width(r) for r in range(rows))
    total_w = widest_row + PADDING * 2
    total_h = target_h * rows + GAP * (rows - 1) + PADDING * 2 + (BOTTOM_BAR_H if github_url else 0)

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOUR)

    # Place each row centered horizontally.
    for r in range(rows):
        row_imgs = scaled[r * cols:(r + 1) * cols]
        rw = row_width(r)
        x = (total_w - rw) // 2
        y = PADDING + r * (target_h + GAP)
        for s in row_imgs:
            canvas.paste(s, (x, y), s if s.mode == "RGBA" else None)
            x += s.width + GAP

    # Add GitHub URL text.
    if github_url:
        draw = ImageDraw.Draw(canvas)
        max_text_w = total_w - PADDING * 2
        font = fit_text_font(github_url, max_text_w, FONT_SIZE_MAX, FONT_SIZE_MIN)

        text_y = PADDING + rows * target_h + (rows - 1) * GAP + (BOTTOM_BAR_H // 2)
        draw.text(
            (total_w // 2, text_y),
            github_url,
            fill=TEXT_COLOUR,
            font=font,
            anchor="mm",
        )

    canvas.save(output_path, "PNG")
    print(f"✓ {output_path} ({total_w}×{total_h}) [{n} screenshots, {rows}×{cols}]")


def main():
    p = argparse.ArgumentParser(description="Generate showcase image")
    p.add_argument(
        "--screenshots",
        nargs="+",
        required=True,
        help="Paths to final screenshot PNGs (any count — typically 5 for an App Store deck).",
    )
    p.add_argument("--output", required=True, help="Output file path")
    p.add_argument("--github", default=None, help="GitHub URL to display at bottom")
    p.add_argument(
        "--cols",
        type=int,
        default=None,
        help="Screenshots per row (default: all in one row). Use 3 or 4 to wrap a 5-slot deck across 2 rows.",
    )
    args = p.parse_args()

    create_showcase(args.screenshots, args.output, args.github, cols=args.cols)


if __name__ == "__main__":
    main()
