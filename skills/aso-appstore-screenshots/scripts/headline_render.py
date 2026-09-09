"""Headline text rendering for ASO scaffolds (Pillow-deterministic)."""
import os
from PIL import Image, ImageDraw, ImageFont

TEXT_W_RATIO = 0.92
VERB_SIZE_MAX_RATIO = 0.198
VERB_SIZE_MIN_RATIO = 0.116
DESC_SIZE_MAX_RATIO = 0.096
DESC_SIZE_MIN_RATIO = 0.065
VERB_DESC_GAP = 20
DESC_LINE_GAP = 24
MAX_DESC_LINES_DEFAULT = 2


def _resolve_default_font() -> str:
    for p in (
        "/Library/Fonts/SF-Pro-Display-Black.otf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/Arial Black.ttf",
    ):
        if os.path.exists(p):
            return p
    raise RuntimeError("No suitable heavy/black font found.")


def _word_wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_font(text, font_path, max_w, size_max, size_min):
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = ImageFont.truetype(font_path, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
    return ImageFont.truetype(font_path, size_min)


def _fit_desc_font(text, font_path, max_w, size_max, size_min, max_lines):
    """Shrink desc font size until wrapped line count ≤ max_lines.

    Mirrors _fit_font but constrains on line-count rather than single-line
    width. Long phrases (e.g., ES "LO QUE NECESITAS GRATIS") otherwise wrap
    to 3+ lines at the base size and crowd the device frame below.
    """
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for size in range(size_max, size_min - 1, -4):
        font = ImageFont.truetype(font_path, size)
        lines = _word_wrap(dummy, text, font, max_w)
        if len(lines) <= max_lines:
            return font
    return ImageFont.truetype(font_path, size_min)


def _draw_centered(draw, y, text, font, canvas_w, max_w, fill):
    lines = _word_wrap(draw, text, font, max_w) if max_w else [text]
    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        line_w = bbox[2] - bbox[0]
        max_line_w = max(max_line_w, line_w)
        draw.text((canvas_w // 2, y - bbox[1]), line, fill=fill, font=font, anchor="mt")
        y += h + DESC_LINE_GAP
    return y, max_line_w


def draw_headline(
    canvas: Image.Image,
    verb: str,
    desc: str,
    text_top: int,
    canvas_w: int,
    text_color: str,
    font_path: str = None,
    desc_font_path: str = None,
    max_desc_lines: int = MAX_DESC_LINES_DEFAULT,
    verb_max_ratio: float = None,
    desc_max_ratio: float = None,
) -> tuple:
    """Draw the headline onto `canvas` in place. Returns (canvas, headline_band).

    headline_band is (x, y, w, h) in canvas coords — a tight rect around the
    rendered text with ~30px padding on each side, used downstream by the
    sidecar so future masking / overlay tools can identify the headline area.

    `verb_max_ratio` / `desc_max_ratio` override the canvas-width-based
    defaults. Use to make the headline occupy the same PROPORTION of canvas
    height across profiles with different aspect ratios (e.g., Android 9:16
    is shorter than iOS ~9:19.5, so its ratios must shrink).
    """
    font_path = font_path or _resolve_default_font()
    desc_font_path = desc_font_path or font_path
    max_text_w = int(canvas_w * TEXT_W_RATIO)
    verb_ratio = verb_max_ratio if verb_max_ratio is not None else VERB_SIZE_MAX_RATIO
    desc_ratio = desc_max_ratio if desc_max_ratio is not None else DESC_SIZE_MAX_RATIO
    verb_size_max = int(canvas_w * verb_ratio)
    verb_size_min = int(canvas_w * VERB_SIZE_MIN_RATIO)
    desc_size_max = int(canvas_w * desc_ratio)
    desc_size_min = int(canvas_w * DESC_SIZE_MIN_RATIO)

    draw = ImageDraw.Draw(canvas)
    verb_font = _fit_font(verb.upper(), font_path, max_text_w, verb_size_max, verb_size_min)
    desc_font = _fit_desc_font(
        desc.upper(), desc_font_path, max_text_w,
        desc_size_max, desc_size_min, max_desc_lines,
    )

    y = text_top
    y, verb_max_w = _draw_centered(draw, y, verb.upper(), verb_font, canvas_w, None, text_color)
    y += VERB_DESC_GAP
    y, desc_max_w = _draw_centered(
        draw, y, desc.upper(), desc_font, canvas_w, max_text_w, text_color
    )
    text_bottom = y - DESC_LINE_GAP  # strip the trailing gap

    max_line_w = max(verb_max_w, desc_max_w)
    pad = 30
    band_x = max(0, (canvas_w - max_line_w) // 2 - pad)
    band_y = max(0, text_top - pad)
    band_w = min(canvas_w - band_x, max_line_w + 2 * pad)
    band_h = (text_bottom - text_top) + 2 * pad
    return canvas, (band_x, band_y, band_w, band_h)
