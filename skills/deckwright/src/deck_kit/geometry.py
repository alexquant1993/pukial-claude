"""Geometry. 1 CSS pixel is 9525 EMU at 96 dpi, so a 1280x720 design
maps 1:1 onto a 13.333 x 7.5 in slide and every coordinate authored in
the HTML draft transfers to the builder unchanged.

Typography does NOT transfer 1:1 - see the brand's type scale.
"""

from pptx.util import Emu

EMU = 9525

CANVAS_W = 1280
CANVAS_H = 720
SLIDE_W_EMU = CANVAS_W * EMU
SLIDE_H_EMU = CANVAS_H * EMU


def px(v):
    """CSS pixels -> EMU."""
    return Emu(int(round(v * EMU)))


def columns(left, right, label_w, gap, n):
    """Split the band between `left` and `right` into `n` columns after a
    row-label gutter of `label_w`, separated by `gap`.

    Returns (column_width, [x0, x1, ...]). Widths stay float so the
    columns land on exact pixel fractions rather than accumulating
    rounding error across the row.
    """
    band = right - left - label_w - n * gap
    col_w = band / float(n)
    x0 = left + label_w + gap
    return col_w, [x0 + i * (col_w + gap) for i in range(n)]
