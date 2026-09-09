"""Curves and connectors as native freeform shapes.

SVG coordinates are lifted verbatim from the HTML draft and passed through
python-pptx's own shapes.build_freeform(..., scale=EMU), which keeps the
whole path in CSS pixels. Nothing here rasterises.

Only the M, C and S commands are supported. Anything else raises: a parser
that silently skips a command it does not know feeds that command's numbers
to whichever command is still active, and the result is wrong geometry with
no error anywhere.
"""

import re

from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Pt

from .geometry import EMU, px

SUPPORTED = "MCS"
# A command letter, or a number. The number pattern accepts a leading dot
# (".5"), which every SVG optimiser emits, and exponent notation.
_TOKENS = re.compile(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _floats(toks, i, n, cmd):
    if i + n > len(toks):
        raise ValueError("command %r is missing coordinates" % cmd)
    out = []
    for tok in toks[i:i + n]:
        try:
            out.append(float(tok))
        except ValueError:
            raise ValueError(
                "command %r expected %d numbers but hit %r" % (cmd, n, tok))
    return out


def bezier_points(path, steps=18):
    """Parse the M, C and S subset of an SVG path into a dense polyline."""
    toks = _TOKENS.findall(path)
    pts, i, cur, prev_c2, cmd = [], 0, None, None, None
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            if t not in SUPPORTED:
                raise ValueError(
                    "unsupported path command %r; deck_kit.paths handles only "
                    "%s (absolute). Convert the path or extend this parser."
                    % (t, ", ".join(SUPPORTED)))
            cmd, i = t, i + 1
            continue
        if cmd is None:
            raise ValueError("path starts with a coordinate, not a command")
        if cmd == "M":
            cur = tuple(_floats(toks, i, 2, cmd))
            i += 2
            pts.append(cur)
            prev_c2 = None
            continue
        if cur is None:
            raise ValueError("command %r before any M" % cmd)
        if cmd == "C":
            v = _floats(toks, i, 6, cmd)
            c1, c2, p1 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            i += 6
        else:  # S reflects the previous second control point
            v = _floats(toks, i, 4, cmd)
            c1 = (2 * cur[0] - prev_c2[0], 2 * cur[1] - prev_c2[1]) if prev_c2 else cur
            c2, p1 = (v[0], v[1]), (v[2], v[3])
            i += 4
        p0 = cur
        for st in range(1, steps + 1):
            u = st / float(steps)
            v_ = 1 - u
            pts.append((
                v_ ** 3 * p0[0] + 3 * v_ * v_ * u * c1[0] + 3 * v_ * u * u * c2[0] + u ** 3 * p1[0],
                v_ ** 3 * p0[1] + 3 * v_ * v_ * u * c1[1] + 3 * v_ * u * u * c2[1] + u ** 3 * p1[1]))
        cur, prev_c2 = p1, c2
    if not pts:
        raise ValueError("path produced no points: %r" % path)
    return pts


def polyline(slide, pts, ox, oy, color, lw, dash=False):
    abs_pts = [(ox + x, oy + y) for x, y in pts]
    fb = slide.shapes.build_freeform(abs_pts[0][0], abs_pts[0][1], scale=EMU)
    fb.add_line_segments(abs_pts[1:], close=False)
    sp = fb.convert_to_shape()
    sp.fill.background()
    sp.line.color.rgb = color
    sp.line.width = Pt(lw)
    sp.shadow.inherit = False
    if dash:
        sp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    return sp


def arrow_head(slide, cx, cy, direction, color, w=9, h=9):
    """A triangular head. Shares its geometry with primitives.tri; this one
    exists because a connector's head is sized and named differently from a
    standalone marker."""
    from .primitives import tri
    return tri(slide, cx, cy, direction, color, w=w, h=h)
