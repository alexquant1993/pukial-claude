"""Kit furniture: the primitives the matrix example does not reach.

Ported from furniture.html. Covers footer() and lockup(), the conic raster
path (the maturity balls, and with them the content-keyed asset cache), a
native linear gradient, and a freeform curve with an arrowhead.

The matrix builder draws its own bottom furniture and has no curves and no
conic fill, so without this slide three pieces of the kit would ship
untested.

Built on `brands/relay`, and DELIBERATELY off-brand in two places: Relay's own
system says "No gradients" and spends at most one orange element per view,
and this slide draws a native linear gradient and labels five sections in the
signal colour. That is the point - the artifact under test is the kit, not a
Relay slide, and a primitive nothing draws is a primitive nothing proves.
`examples/ai-horizon/` is the deck that shows what Relay actually looks like.

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \
       --with pillow python examples/kit-furniture/build_furniture.py \
       --template out/template.pptx --out out/furniture.pptx
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from deck_kit.brand import load_brand
from deck_kit.deck import add_slide, open_deck
from deck_kit.metrics import WarnRegister
from deck_kit.paths import arrow_head, bezier_points, polyline
from deck_kit.primitives import ball, ensure_balls, footer, rrect, textbox
from deck_kit.xmlfill import grad

# Lifted verbatim from furniture.html. The S command reflects the previous
# control point; a parser that ignores that produces a visible kink.
CURVE = "M0 0 C60 0 60 -40 120 -40 S180 -70 240 -70"
RING = (0xB8, 0xBD, 0xC4, 255)
BODY = (0xFF, 0xFF, 0xFF, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    spec = load_brand("relay")
    s = spec.style()
    m = spec.metrics()
    warn = WarnRegister()

    prs = open_deck(args.template, spec)
    slide = add_slide(prs, spec)
    s.header(slide, m, warn, "02. Kit", "Kit furniture",
             "Every primitive the capability matrix does not reach.", 2)

    # Every y below is 32 px lower than the draft's, which is the difference
    # between the fixture brand's content top (150, under a 10.5 pt sub at
    # y=94) and Relay's CONTENT_TOP = 182, under a 13.7 pt sub at y=140. The
    # relative geometry inside each block is unchanged, so the curve still
    # meets the arrowhead at the vertical middle of the Target box.

    # Maturity balls: the conic raster path. DrawingML has no angular
    # gradient, so these five are pre-rendered PNGs by design - one of the
    # only two places raster is allowed.
    textbox(slide, s.L, s.CONTENT_TOP, 400, 14, [("CONIC FILL, PRE-RENDERED", True)],
            s.T_COL_SUB, s.BLUE, s.SANS, upper=True, ls=s.LS_LABEL)
    balls_dir = ROOT / "out" / "balls"
    ensure_balls(balls_dir, [s.BLUE], ring=RING, body=BODY)
    for i, frac in enumerate((0, 25, 50, 75, 100)):
        x = s.L + i * 56
        ball(slide, balls_dir, x, 204, 18, frac, s.BLUE)
        textbox(slide, x - 8, 226, 34, 12, "%d%%" % frac, s.T_META, s.GREY,
                s.SANS, PP_ALIGN.CENTER, ls=s.LS_LABEL)

    # A native linear gradient: editable in PowerPoint, not a picture.
    textbox(slide, s.L, 272, 400, 14, [("NATIVE LINEAR GRADIENT", True)],
            s.T_COL_SUB, s.BLUE, s.SANS, upper=True, ls=s.LS_LABEL)
    rail = rrect(slide, s.L, 294, s.W, 18, fill=s.BLUE, rad=9)
    grad(rail, [(0, s.BLUE, 10), (60, s.BLUE, 30), (100, s.BLUE, 55)], ang=0)
    textbox(slide, s.L, 294, s.W, 18, [("a:gradFill written on the shape", True)],
            s.T_COL_SUB, s.TITLE, s.SANS, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE,
            ls=s.LS_LABEL, wrap=False)

    # A freeform curve with an arrowhead, coordinates lifted from the draft.
    textbox(slide, s.L, 352, 500, 14, [("FREEFORM CURVE AND ARROWHEAD", True)],
            s.T_COL_SUB, s.BLUE, s.SANS, upper=True, ls=s.LS_LABEL)
    box_a = rrect(slide, s.L, 432, 170, 52, fill=s.WHITE, line=s.BLUE, lw=1.2, rad=8)
    textbox(slide, s.L, 432, 170, 52, [("Source", True)], s.T_CAPTION, s.NAVY,
            s.SANS, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, ls=s.LS_LABEL)
    ox, oy = s.L + 178, 458
    polyline(slide, bezier_points(CURVE), ox, oy, s.BLUE, 1.5)
    arrow_head(slide, ox + 244, oy - 70, "right", s.BLUE)
    box_b = rrect(slide, ox + 254, 362, 170, 52, fill=s.WHITE, line=s.BLUE,
                  lw=1.2, rad=8)
    textbox(slide, ox + 254, 362, 170, 52, [("Target", True)], s.T_CAPTION,
            s.NAVY, s.SANS, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, ls=s.LS_LABEL)

    # The kit's own footer primitive, which the matrix builder bypasses by
    # drawing its bottom furniture inside header(). It appears above the
    # brand's own footer line on purpose: this slide demonstrates the
    # primitive, so both are visible at once.
    textbox(slide, s.L, 578, 500, 14, [("FOOTER PRIMITIVE", True)],
            s.T_COL_SUB, s.BLUE, s.SANS, upper=True, ls=s.LS_LABEL)
    # y=600: the primitive draws a rule on that line and its text 6 below,
    # 16 tall, so it ends at 622 - 50 px clear of Relay's own FOOT_Y = 672,
    # which is what keeps the two footers legibly separate.
    footer(slide, "Kit furniture example", 2, s.SANS, s.GREY, s.LINE, s.T_META,
           width=s.W, left=s.L, y=600)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(args.out))
    print("wrote", args.out, "slides:", len(prs.slides))
    warn.exit_if_dirty()


if __name__ == "__main__":
    main()
