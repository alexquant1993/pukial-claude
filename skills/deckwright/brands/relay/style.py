"""The Relay brand's style layer: palette, type scale, grid, radius and rule
scale, spacing rhythm, the three type roles and the slide furniture.

**Three faces, one per role.** `SANS`, `DISPLAY` and `MONO` below are Public
Sans, Space Grotesk and JetBrains Mono - Relay's own three, fetched by
`scripts/fetch_fonts.py` rather than substituted. Every helper here writes
the role Relay's kit writes: the kicker, the footer label and the page
number are mono, the title is display, the sub is body. A builder drawing
this brand's own vocabulary does the same, and
`examples/ai-horizon/build_ai_horizon.py`'s `Draw` is the worked case -
one `Fit` per role, because the measurement factors are per face.

Derived from `brands/relay_design_system/` - its `tokens/colors.css`,
`tokens/typography.css`, `tokens/spacing.css`, `tokens/radius.css`, the
fourteen reference slides in `ui_kits/slides/` and the rules in its
`readme.md`. That directory is read-only here; nothing in this package
edits it.

Two conversions run through every number below.

**Geometry, 1920 -> 1280.** Relay's slide kit is authored at 1920x1080 and
deckwright's canvas is 1280x720, so every length is scaled by 2/3: the
kit's 120 px side padding becomes this file's `L = 80`, its 24 px gutter
becomes `COL_GAP = 16`, its 44 px footer inset becomes 29, and its 3 px
section rule stays 3 because a hairline does not scale (a 2 px rule at 2/3
is 1.33 px, which renders as a fuzzy 1 or 2). Rules are therefore taken
from `tokens/spacing.css` directly - 1 / 1.5 / 2 / 3 - not scaled.

**Type, px -> pt.** Sizes are picked from Relay's own 1.26-ratio scale in
`tokens/typography.css` at the 1280 canvas, then re-derived at px x 0.76
and floored to the repository's minimums
(`references/03-pptx-stage.md`, "Typography does not"). Every `T_*` below
names the px it came from.

Relay's kit carries its own floor - "nothing on a slide goes below 24px",
which is 16 px here and 12.2 pt - and this file does not honour it. That
rule is written for a fourteen-slide reference deck whose densest slide is
a five-row table; the deck this brand was built for puts three domain
boxes and five tags on one slide. The repository's floors (11 pt body,
9.5 pt caption, 9 pt metadata, 8 pt for all-caps micro-labels) govern
instead, and the ruling is in `docs/decisions.md`.

**Inverse (dark) slides are drawn per slide, not by a second layout.**
Relay's cover, section, big-number and quote slides sit on `#0A0A0A`, and
its own kit does this by setting `data-theme="dark"` on the section
element rather than by declaring a second master - the ground belongs to
the slide, not to the template. Matching that here means one full-bleed
`rrect` at the bottom of the shape tree on a dark slide, which
`assert_native.py` counts as an ordinary autoshape (only a slide-sized
*picture* fails it). The alternative, a second layout in the template,
would mean cloning a `p:sldLayout` part and re-minting its relationships
by hand: python-pptx cannot add a layout, and OOXML surgery on the
template is exactly what the gate's doubled COM open exists to catch.
`make_template.py` is therefore unchanged, and `DARK` below is what a
builder paints.

The core library holds no colour values. This is where they live.
"""

from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from deck_kit.geometry import columns, px
from deck_kit.primitives import rrect, rule, textbox

HERE = Path(__file__).resolve().parent

# --- palette: Relay's own names ------------------------------------------
# tokens/colors.css. Black is #0A0A0A, never #000 (readme, "Colors").
INK_1000 = RGBColor(0x0A, 0x0A, 0x0A)
INK_900 = RGBColor(0x14, 0x14, 0x14)
INK_800 = RGBColor(0x1F, 0x1F, 0x1F)
INK_700 = RGBColor(0x2E, 0x2E, 0x2E)
INK_600 = RGBColor(0x4A, 0x4A, 0x4A)
INK_500 = RGBColor(0x6B, 0x6B, 0x6B)
INK_400 = RGBColor(0x8F, 0x8F, 0x8F)
INK_300 = RGBColor(0xB8, 0xB8, 0xB8)
INK_200 = RGBColor(0xD8, 0xD8, 0xD8)
INK_100 = RGBColor(0xEB, 0xEB, 0xEB)
INK_050 = RGBColor(0xF5, 0xF5, 0xF4)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)

# Signal: electric orange, the one aggressive colour. "One orange element
# per view" (readme). Never body text, never a status.
SIGNAL_100 = RGBColor(0xFF, 0xE7, 0xDB)
SIGNAL_500 = RGBColor(0xFF, 0x4F, 0x00)
SIGNAL_600 = RGBColor(0xE0, 0x46, 0x00)

# Volt: acid lime, for diagrams and data artifacts only. Never UI chrome.
VOLT_100 = RGBColor(0xF2, 0xFC, 0xCE)
VOLT_500 = RGBColor(0xC6, 0xF5, 0x1E)

# Status: muted and semantic, each with its tinted ground.
STATE_POSITIVE = RGBColor(0x00, 0x87, 0x3C)
STATE_POSITIVE_BG = RGBColor(0xE4, 0xF4, 0xEA)
STATE_WARNING = RGBColor(0xB3, 0x6A, 0x00)
STATE_WARNING_BG = RGBColor(0xFB, 0xEE, 0xDB)
STATE_NEGATIVE = RGBColor(0xC8, 0x1E, 0x1E)
STATE_NEGATIVE_BG = RGBColor(0xFB, 0xE7, 0xE7)
STATE_INFO = RGBColor(0x0F, 0x5E, 0xFF)
STATE_INFO_BG = RGBColor(0xE5, 0xED, 0xFF)

# --- the shared role names -----------------------------------------------
# `templates/components.css` and `deck_kit.components` read these NAMES, not
# values, so they are the kit's vocabulary rather than Relay's own - a brand
# that renames them renders a draft written with the shared vocabulary
# against browser defaults. Keeping them means such a draft resolves here;
# the values are Relay's throughout, and Relay's own names are above.
BLUE = SIGNAL_500       # the accent role, which in Relay is orange
BLUE_DARK = SIGNAL_600
NAVY = INK_1000
TITLE = INK_1000
GREY = INK_600          # --text-secondary
MUTED = INK_500         # --text-muted
FAINT = INK_400         # --text-faint, the footer's ink
WHITE = PAPER
LINE = INK_200          # --border-hairline
CELL_BD = INK_100       # --border-quiet
RED_BG, RED = STATE_NEGATIVE_BG, STATE_NEGATIVE
AMB_BG, AMB = STATE_WARNING_BG, STATE_WARNING
AMB_TXT = STATE_WARNING
AMB_LEG = STATE_WARNING
# Backgrounds are flat: "No gradients. No mesh, no glow, no blurred blobs."
# make_template.py paints BG_TOP -> BG_BOTTOM down the layout, so the two
# stops are the same colour and the gradient degenerates to a flat white.
BG_TOP = PAPER
BG_BOTTOM = PAPER
DARK = INK_1000         # the inverse ground, painted per slide
DARK_RAISED = INK_900   # --surface-inverse-raised, a panel on a dark slide

INK = INK_600           # body ink; the alias names a role, not a swatch
PANEL = INK_050         # --surface-sunken, a quiet ground

# --- type scale ----------------------------------------------------------
# Geometry transfers 1:1 from the HTML draft; type does not. Each size is a
# px from Relay's 1.26-ratio scale at the 1280 canvas, re-derived at
# px x 0.76 and floored.
T_TAGLINE = 8.4       # px 11  all-caps micro-label: the brand tagline
T_EYEBROW = 9.9       # px 13  the mono kicker, tracked +0.12em
T_TITLE = 29.6        # px 39  --text-3xl, the slide title
T_COVER = 59.3        # px 78  --text-6xl, the cover display line
T_NUMERAL = 47.1      # px 62  --text-5xl, the oversized numeral
T_UNIT = 19.0         # px 25  --text-xl, the small unit beside a numeral
T_HEADLINE = 23.6     # px 31  --text-2xl, the statement line on a horizon slide
T_LEAD = 16.0         # px 21  --text-lg, a lead-in above body copy
T_SUB = 13.7          # px 18  --text-md, --type-body-size
T_COL_HEAD = 12.2     # px 16  column headers: floor is 12 pt
T_COL_SUB = 8.4       # px 11  all-caps micro-label
T_ROW_LABEL = 9.9     # px 13
T_WORDMARK = 12.2     # px 16  "Relay" set in display type, tracked -0.045em
T_PILL = 9.9          # px 13
T_PILL_SUB = 9.9      # px 13  a tag sublabel is a caption, so the caption floor
T_BODY = 12.2         # px 16  body floor is 11
T_CAPTION = 10.6      # px 14  caption floor is 9.5
T_CARD_DESC = 10.6    # px 14
T_LOOP = 10.6         # px 14  the transversal note line
T_LEGEND = 9.9        # px 13
T_FOOT = 8.4          # px 11  all-caps micro-label, the footer's mono
T_META = 9.1          # px 12  copyright, page numbers - mixed case

# Sizes below 9 pt are all-caps micro-labels and nothing else. Every one of
# these is only ever written uppercase and tracked. tests/test_style.py walks
# every OTHER T_* in every brand against the floors.
ALL_CAPS_MICRO = ("T_TAGLINE", "T_COL_SUB", "T_FOOT")

# --- tracking ------------------------------------------------------------
# tokens/typography.css. "Display is always tightened, mono and micro-caps
# are opened up." The values are em; `track()` turns one into the points
# primitives.settext writes as a:rPr/@spc.
TRACK_DISPLAY = -0.035    # --tracking-tighter/-tightest, display type
TRACK_TIGHT = -0.015      # --tracking-tight, large body
TRACK_WORDMARK = -0.045   # guidelines/brand-wordmark.html
TRACK_MONO = 0.12         # --tracking-widest, mono labels set uppercase
TRACK_WIDE = 0.04         # --tracking-wide, the footer's own labels


def track(size_pt, em):
    """Letter-spacing in points for `em` of tracking at `size_pt`.

    One helper rather than a constant per size, because the same em is
    applied at five different sizes and a table of products drifts. The
    result goes to `settext(spc=...)` and to `metrics.width(spc=...)`
    together - measuring untracked text that will be drawn tracked is an
    overflow nothing reports.
    """
    return size_pt * em


# --- line spacing --------------------------------------------------------
LS_FLAT = 0.94        # --leading-flat, the cover line and the numerals
LS_LABEL = 1.0        # single-line labels
LS_TITLE = 1.02       # --leading-tight, titles
LS_CARD = 1.16        # --leading-snug, card titles and short card copy
LS_BODY = 1.34        # between --leading-snug and --leading-normal
LS_PROSE = 1.5        # --leading-normal, prose with room around it

# --- radius, rules and spacing -------------------------------------------
# tokens/radius.css: "Sharp by default. Radius is a rounding of last resort,
# never a style." Surfaces and cards are square; only a control is softened.
RAD_SURFACE = 0
RAD_CONTROL = 2
# tokens/spacing.css, unscaled: a hairline does not survive a 2/3 scale.
HAIR = 1
RULE_MEDIUM = 1.5     # a table header
RULE_STRONG = 2       # the active edge
RULE_HEAVY = 3        # a section opener
# Border widths in POINTS, which is what primitives takes as `lw`.
LW_HAIR = 0.75        # 1 px
LW_MEDIUM = 1.1
LW_STRONG = 1.5

# 4 px base, scaled from the kit's 8 / 16 / 24 / 48 / 128 rhythm.
SPACE_1, SPACE_2, SPACE_3, SPACE_4 = 4, 8, 12, 16
SPACE_6, SPACE_8, SPACE_12, SPACE_16 = 24, 32, 48, 64

# --- grid ----------------------------------------------------------------
# Kit padding 120 px at 1920 -> 80 here; gutter 24 -> 16.
L, R = 80, 1200
W = R - L                 # 1120
ROW_LABEL_W = 176
COL_GAP = 16
# The card grid butts cells against a hairline ground with a 1 px gap
# ("Card grids use 1px gaps over a hairline-colored background"), which is a
# different gap from the column gutter and therefore its own constant.
GRID_HAIR = 1
_COL_W, _COL_X = columns(L, R, ROW_LABEL_W, COL_GAP, 3)
GEOM = {"left": L, "right": R, "width": W, "row_label_w": ROW_LABEL_W,
        "col_w": _COL_W, "col_x": _COL_X, "gap": COL_GAP}

# --- the slide's vertical furniture --------------------------------------
RULE_Y = 56           # the 3 px section opener
KICKER_Y = 70         # the mono kicker under it
TITLE_Y = 92
SUB_Y = 140
CONTENT_TOP = 182     # where a slide's own content may start
CONTENT_BOTTOM = 650
FOOT_Y = 672          # wordmark, copyright, page number
FOOT_H = 16
TITLE_AVAIL = W       # nothing sits top-right: the mark is in the footer
SUB_AVAIL = 940       # one line for every sub in the deck; Relay caps prose at 66ch

# Page-number furniture. In the brand, not the core.
PAGE_X, PAGE_Y, PAGE_W, PAGE_H = R - 60, FOOT_Y, 60, FOOT_H
PAGE_SIZE = T_META
PAGE_COLOR = FAINT

# --- the three faces -----------------------------------------------------
# The names a run is written under in the PPTX, one per type role. They
# repeat `brand.py`'s families rather than reading them, because a builder
# holds the style module and the BrandSpec separately and every other name
# on a slide comes from here. `tests/test_style.py` asserts the two agree.
# The colour key in an icon's filename: brands/relay/icons/ic_<name>_ink.png.
# "icons never carry color of their own: they are ink, inverse, or the
# semantic color of the message they sit in" (Relay's readme), and every icon
# this brand ships is cropped in the ink key. `deck_kit.components.matrix_frame`
# reads it - the kit used to hardcode "blue", which was one brand's value
# living in src/. tests/test_style.py::test_every_brand_names_its_icon_colour_key.
ICON_KEY = "ink"

SANS = "Public Sans"        # --font-body
DISPLAY = "Space Grotesk"   # --font-display: titles, numerals, statements
MONO = "JetBrains Mono"     # --font-mono: kickers, footers, headers, tags
PAGE_FONT = MONO            # the page marker is a mono label like any other

TAGLINE = "Technology that moves the business."
WORDMARK = "Relay"
# Written already uppercase in the source, rather than mixed-case with
# upper=True, so that the spec, the rules file and this constant all read the
# same characters as the slide. `settext` writes
# `text.upper() if upper else text`, so upper=True would land the same string
# in the XML and the [required] check would pass either way - the reason is
# that a reader comparing three files should not have to apply the transform
# in their head. The same argument is why the HTML drafts, which uppercase
# their kickers in CSS, are the one place the lint has to fold case
# (references/05-qa.md#the-html-deck).
COPYRIGHT = "(C) RELAY - CONFIDENTIAL"


def wordmark(slide, x, y, h=13, inverse=False):
    """The Relay mark, placed by its height with its aspect preserved.

    Relay supplied no logo, so the two PNGs are placeholders drawn by
    `scripts/make_placeholder_logos.py` from the wordmark guideline - the
    word set in the display face at -0.045em, in ink and in paper. Returns
    the width it used, so a caller can lay the footer out after it.
    """
    from PIL import Image

    path = HERE / ("logo_inverse.png" if inverse else "logo_primary.png")
    with Image.open(str(path)) as im:
        w = h * im.width / float(im.height)
    slide.shapes.add_picture(str(path), px(x), px(y), px(w), px(h))
    return w


def footer(slide, page, inverse=False, copyright_line=True):
    """The mark, the copyright and the page number, on one mono line.

    Relay's kit gives every slide the same footer - wordmark left, a label
    beside it, the number right - so it is furniture, not a per-slide
    decision. `inverse` picks the paper mark and the inverse ink for a dark
    ground; `copyright_line` is off only on a cover, whose spec says it
    carries none.
    """
    faint = INK_500 if inverse else FAINT
    used = wordmark(slide, L, FOOT_Y + 1, 13, inverse=inverse)
    if copyright_line:
        textbox(slide, L + used + 20, FOOT_Y + 1, 520, 14, COPYRIGHT, T_FOOT,
                faint, MONO, ls=LS_LABEL, wrap=False, spc=track(T_FOOT, TRACK_MONO))
    if page is not None:
        textbox(slide, PAGE_X, PAGE_Y, PAGE_W, PAGE_H, str(page), T_META, faint,
                MONO, PP_ALIGN.RIGHT, ls=LS_LABEL, spc=track(T_META, TRACK_WIDE))


def header(slide, metrics, warn, kicker, title, sub, page, display=None):
    """The standard slide header, and the footer under it.

    Relay opens a section with "a 3px black rule under a mono kicker plus a
    display heading" (readme, "Spacing, grid, layout"), and the kit sets the
    rule as a `border-top` above the kicker - so the order down the slide is
    rule, kicker, title, sub. The first seven parameters are
    `brands/example`'s, unchanged, because every builder and
    `tests/test_style.py` call them positionally.

    `display` is the display role's TextMetrics - `brand.metrics("display")`
    - and defaults to `metrics`. The title is set in Space Grotesk and the
    measurement factors are per face, so measuring it against the body
    metrics would check the wrong face; a caller that passes nothing gets
    the old behaviour, which is what a one-family brand means anyway.
    tests/test_style.py::test_header_measures_the_title_against_the_display_face.

    Both lines are measured. The title is checked for width against
    `TITLE_AVAIL` and the sub for wrapping against `SUB_AVAIL`; the sub's
    check is
    tests/test_style.py::test_header_warns_when_the_sub_would_wrap.
    """
    display = metrics if display is None else display
    rule(slide, L, RULE_Y, W, RULE_HEAVY, INK_1000)
    # Muted, not signal. Relay's kit sets the kicker in --text-muted on every
    # white slide (03, 05, 06, 07, 09, 10, 11) and keeps signal for the ONE
    # orange element the slide's content earns - the live step on the
    # timeline, the last bar on the chart, the right-hand rule on the
    # comparison. A signal kicker on all eight content slides would spend
    # that budget on furniture and leave the deck with no accent left to
    # mean anything.
    textbox(slide, L, KICKER_Y, W, 14, kicker, T_EYEBROW, MUTED, MONO,
            upper=True, ls=LS_LABEL, spc=track(T_EYEBROW, TRACK_MONO))
    textbox(slide, L, TITLE_Y, TITLE_AVAIL, 42, [(title, True)], T_TITLE, TITLE,
            DISPLAY, ls=LS_TITLE, spc=track(T_TITLE, TRACK_DISPLAY))
    textbox(slide, L, SUB_Y, SUB_AVAIL, 24, sub, T_SUB, GREY, SANS, ls=LS_BODY)
    if display.width(title, T_TITLE, bold=True,
                     spc=track(T_TITLE, TRACK_DISPLAY)) > TITLE_AVAIL:
        warn.add("OVERFLOW", "title: " + title)
    # The sub is measured too, against the body metrics it is set in.
    # SUB_AVAIL's comment - "one line for every sub in the deck" - was a
    # claim nothing checked: a sub that wrapped to two lines pushed into the
    # content below it and the build still printed "no warnings". The box is
    # 24 px tall, one line at T_SUB, so a second line is an overflow whether
    # or not the box is wide enough to hide it. `metrics`, not `display`:
    # the sub is written in SANS on the line above.
    if metrics.lines(sub, T_SUB, SUB_AVAIL) > 1:
        warn.add("OVERFLOW", "sub: %s" % sub)
    footer(slide, page)


def dark_ground(slide):
    """Paint the inverse ground, full bleed, behind everything else.

    Called first on a dark slide so it sits at the bottom of the shape tree.
    See the module docstring for why this is per slide rather than a second
    layout in the template.
    """
    sp = rrect(slide, 0, 0, 1280, 720, fill=DARK, rad=RAD_SURFACE)
    sp.line.fill.background()
    return sp
