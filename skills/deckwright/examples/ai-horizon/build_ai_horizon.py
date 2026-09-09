"""AI and humanity, 2026 to 2050 and beyond, in the Relay design system.

Ten slides on `brands/relay`, ported from the ten HTML drafts in
`examples/ai-horizon/drafts/` (route B for every slide), which were authored
FIRST - the drafts were served, screenshotted and iterated on before a line
of this file was written, which is the pipeline's order. Geometry transfers
1:1 from those files: every coordinate below is the number the draft carries
inline.

There was once a second build of nine of these slides, on the fixture
brand the repository used to carry. It was deleted: two builds of one deck
proved that a builder can be ported and nothing else, and it cost a
duplicated copy deck and a second `Fit`. `docs/decisions.md`, "relay
default", is the ruling; the fixture brand itself went in "one brand".

Deltas from the drafts: none of substance. Two things the drafts express
differently because CSS can and DrawingML cannot:

  - the butt-joined card grid is `gap: 1px` over a hairline background in
    CSS and one hairline-filled rect with N paper rects on top here. Same
    picture, one shape more, no gap arithmetic in the renderer.
  - the numeral's unit is `.num sup` in CSS and a second run at `T_UNIT` on
    the same baseline here. DrawingML's baseline shift and a measured
    layout do not agree, and a raised unit that measures as unraised
    overflows its box.

What the Relay system asked for, and what it forbade:

  - no gradients anywhere. Relay's readme forbids them outright, so the
    example deck's four faded horizon bands and its blue headline band
    become rules, ink ramps and a numeral.
  - no rounded surfaces. Radius is 0 for a card and 2 for a control, so
    nine of the ten slides draw with `deck_kit.primitives` and a local
    `Draw` rather than with `deck_kit.components`, whose furniture is the
    kit's default 8 and 7. S09 is the exception: it draws the kit's
    `matrix_frame` and `flow_pills` and hands them Relay's own radii
    (`cell_rad=RAD_SURFACE`, `rad=RAD_CONTROL`) and Relay's own ink
    (`accent=NAVY`), which is what those parameters exist for. The slide is
    where `examples/capability-matrix`'s coverage of the kit went when that
    example was deleted; the ledger has both rulings.
  - the confidence grades are a monochrome ink ramp (solid ink, solid
    ink-600, hairline outline, faint outline) rather than a colour scale.
    Relay forbids orange as a status colour, and a green-to-red ramp would
    read as good-to-bad, which confidence is not.
  - one orange element per slide, which is Relay's own rule. The kicker is
    muted on every white slide; the accent goes to the thing that earns it -
    the nearest horizon, the live milestone, the year the forecast lands on,
    the column that would push the dates back.
  - the cover is an inverse slide, painted per slide rather than by a second
    layout in the template. `brands/relay/style.py`'s module docstring says
    why, and `make_template.py` is unchanged.

Type: every size is a `T_*` in `brands/relay/style.py`, re-derived from
Relay's own 1.26 scale at px x 0.76 and floored. Tracking is load-bearing
in this brand - display type at -0.035em, mono labels at +0.12em - and
every measurement passes the same `spc` the text is written with, because
a mono label measured untracked is a fifth narrower than it is drawn.

THREE faces, one per role: Space Grotesk on the display runs, Public Sans
on body copy, JetBrains Mono on every kicker, footer label, table header
and grade tag. `scripts/fetch_fonts.py` puts them on disk and `brand.py`
carries a width and wrap factor per family, so `Draw` holds one `Fit` per
role rather than one for the deck - measuring a Space Grotesk title against
Public Sans's factor is exactly the silent overflow the register exists to
stop.

Every text box is measured before it is placed: `Fit` counts lines with
`TextMetrics` and registers a HEIGHT warning when a stack does not fit its
box, so the build exits non-zero rather than shipping a clipped cell.

Shape arithmetic for assert_native.py (derived, then confirmed by `check()`,
which counts the saved package the same way the script does). Text boxes are
not autoshapes and are not in this count; pictures are the footer wordmark
and the row icons.

  header() per content slide: the 3 px section rule       9 x 1  =   9
  S01 cover: the full-bleed inverse ground                           1
  S02: grid ground 1 + 4 cells; 4 name rules; 4 grade tags;
       4 legend tags; 1 heavy rule                                  18
  S03: segment rule 1 + 3 dividers; rail 1; 7 markers;
       7 ticks; the heavy rule 1; the note hairline 1               21
  S04..S07: heavy rule 1 + grade tag 1 + grid ground 1 + 3 cells
       + note hairline 1 = 7, plus the tags (5, 5, 4, 3)            45
  S08: header rule 1; 4 row hairlines; 4 legend tags                 9
  S09: matrix_frame's 3 column rules + 12 cell rects (the empty one
       is drawn and then backgrounded) = 15; 16 capability pills
       (len(RD_CAPS)); 3 enabler pills; 1 legend box                 35
  S10: 2 column rules; 4 item hairlines; 1 closing rule              7
                                                             total 145
  pictures: the wordmark on all 10 slides                           10
            S04..S07 three row icons each                           12
            S08 four row icons                                       4
            S09 four row icons                                       4
            S10 two column icons                                     2
                                                              total 32

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \
       --with pillow python examples/ai-horizon/build_ai_horizon.py \
       --template out/ai-horizon/template.pptx \
       --out out/ai-horizon/deck.pptx \
       --notes both --teleprompter out/ai-horizon/teleprompter.html
     (--notes defaults to none: speaker notes are opt-in; --teleprompter is
     needed only with --notes teleprompter or both. run.ps1 passes both.)
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
# notes_data.py sits next to this file; the path insert is what lets the
# builder be run from the repository root as run.ps1 does.
sys.path.insert(0, str(ROOT / "examples" / "ai-horizon"))

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Pt

from deck_kit.brand import load_brand
from deck_kit.components import (Pill, PillStyle, draw_pill, flow_pills,
                                 matrix_frame, pill_w)
from deck_kit.deck import add_slide, open_deck
from deck_kit.geometry import columns
from deck_kit.merge import refuse_in_place
from deck_kit.metrics import PT_TO_PX, WarnRegister
from deck_kit.notes import NOTES_MODES, emit_notes, read_notes
from deck_kit.pagenums import MarkerStyle, renumber
from deck_kit.primitives import add_para, icon, rrect, rule, settext, textbox
from deck_kit.textedit import iter_shapes
from notes_data import NOTES, TITLE

# --- content, closed copy from examples/ai-horizon/spec.md section 5 -------

COVER_LINES = ("AI and humanity,", "2026 to 2050 and beyond")
COVER_SUB = "Forecasts by horizon, with the confidence each one deserves"
COVER_NOTE = "An opinion deck. Every forecast is graded; none is a measurement."

READING_RULE = "Every figure on these slides is a judgement, not a measurement."
CLOSING_RULE = "The dates will be wrong. The direction is the forecast."
MAP_RULE = "Reading rule: the further right, the wider the error bars."

GRADES = {
    "high": ("High", "High: would be surprised if wrong"),
    "medium": ("Medium", "Medium: more likely than not"),
    "low": ("Low", "Low: one plausible path among several"),
    "speculative": ("Speculative", "Speculative: a direction, not a date"),
}
GRADE_ORDER = ("high", "medium", "low", "speculative")


@dataclass(frozen=True)
class Horizon:
    key: str
    years: str          # the year label on S02 and the matrix column
    name: str           # short name
    grade: str
    start: int          # first year on the rail
    end: int            # last year on the rail; None for "beyond"
    numeral: str        # the oversized year on the horizon slide
    unit: str           # the small run beside it, "" for most
    card_lines: tuple   # three one-line forecasts on S02
    kicker: str
    title: str
    sub: str
    headline: str
    domains: tuple      # ((title, desc), ...) x 3
    tags: tuple
    signpost: str


HORIZONS = (
    Horizon(
        "next", "2026 to 2030", "The next years", "high", 2026, 2030, "2030", "",
        ("Agents take over routine digital work", "AI in every classroom and clinic",
         "Rules lag behind use"),
        "03. The next years", "2026 to 2030: the agent decade begins",
        "What is already in motion, and will be ordinary by 2030.",
        "By 2030, AI agents do most routine digital office work.",
        (("Work", "Agents draft, file, reconcile and schedule. The job that remains "
                  "is checking, deciding and being accountable."),
         ("Science and health", "AI reads every paper and every scan. Diagnosis support "
                                "becomes standard and reaches clinics without specialists."),
         ("Society", "Cheap persuasion at scale. Elections, scams and schooling all feel "
                     "it before the law catches up.")),
        ("A personal agent on every phone", "Entry-level desk jobs shrink",
         "Cheaper software, more of it", "AI in every classroom",
         "Deepfakes as a daily nuisance"),
        "Signpost: an agent completes a week-long task without a human check-in."),
    Horizon(
        "decade", "The 2030s", "The next decade", "medium", 2030, 2040, "2040", "",
        ("Whole functions run on agents", "Automated science closes the loop",
         "Countries diverge on sharing the gains"),
        "04. The next decade", "The 2030s: the loop closes",
        "When agents stop assisting work and start running it.",
        "By 2040, AI runs the experiment and the human chooses the question.",
        (("Work", "Whole functions run on agents with a small human crew. Wages split: "
                  "scarce judgement is paid more, routine cognition less."),
         ("Science and health", "Automated labs close the loop from hypothesis to result. "
                                "Drug pipelines shorten from a decade to a few years."),
         ("Society", "Countries diverge on whether AI gains are shared. Universal services "
                     "in some places, a compute divide in others.")),
        ("Self-driving in most cities", "Tutors for every child",
         "Robots in warehouses and farms", "Materials and energy designed by AI",
         "New rules for liability"),
        "Signpost: a discovery credited to an AI system wins a major prize."),
    Horizon(
        "toward", "The 2040s", "Toward 2050", "low", 2040, 2050, "2050", "",
        ("Robots make physical labour cheap", "Ageing itself is treated",
         "Income begins to decouple from work"),
        "05. Approaching midcentury", "The 2040s: physical labour follows digital",
        "When robots get cheap, the question stops being jobs and becomes distribution.",
        "By 2050, most paid work is supervision, judgement and care.",
        (("Work", "Physical labour follows digital labour as robots get cheap. Paid work "
                  "concentrates in care, craft and deciding what to build."),
         ("Science and health", "Life expectancy moves again as ageing itself is treated. "
                                "Diagnosis is continuous rather than an appointment."),
         ("Society", "The question shifts from jobs to distribution. Some societies "
                     "decouple income from work; others do not.")),
        ("Working week under thirty hours", "Robots in most homes",
         "Personalised medicine as the default", "Cities rebuilt around autonomy"),
        "Signpost: a country funds a basic income mainly from AI-driven output."),
    Horizon(
        "beyond", "After 2050", "Beyond", "speculative", 2050, None, "2050", "+",
        ("Work optional for most people", "Science outruns institutions",
         "Who decides becomes the question"),
        "06. Beyond midcentury", "After 2050: capability is not the question",
        "Past this line the error bars cover every outcome. What remains is a direction.",
        "Beyond 2050, the open question is not capability but who decides.",
        (("Work", "Work becomes optional for most people in wealthy societies. Status and "
                  "meaning come from what people choose to do."),
         ("Science and health", "Research runs faster than institutions can absorb it. "
                                "Fusion, engineered biology and off-world industry are on "
                                "the table."),
         ("Society", "Governance of AI is the central political question. Concentration "
                     "of control is the risk; broad participation is the prize.")),
        ("Human and AI collaboration as the norm", "Aligned systems as public infrastructure",
         "New forms of collective decision"),
        "Signpost: none. Past 2050 the error bars cover every outcome."),
)

# (year, label, grade), spec section 5, S03
MILESTONES = (
    (2027, "Agents handle most routine office tasks", "high"),
    (2029, "AI-designed drugs in late-stage trials", "high"),
    (2032, "A tutor for every connected child", "medium"),
    (2036, "Automated labs run the whole loop", "medium"),
    (2040, "Self-driving is the default in cities", "low"),
    (2045, "Ageing treated as a condition", "low"),
    (2050, "Work optional in wealthy societies", "speculative"),
)
TICK_YEARS = (2026, 2030, 2035, 2040, 2045, 2050)

# The three domain icons, in the order the domains appear. Relay's technical
# set (its readme, "Which glyphs"), cropped in the one colour key an icon is
# allowed to carry.
DOMAIN_ICONS = ("terminal", "activity", "users")
MATRIX_ROWS = (("terminal", "Work"), ("activity", "Science and health"),
               ("users", "Society and governance"), ("zap", "Daily life"))
# rows x horizons, spec section 5, S08
MATRIX = (
    ("Agents do routine desk work", "Functions run on agents",
     "Robots do physical labour", "Work becomes optional"),
    ("AI reads every scan", "Automated labs", "Ageing treated",
     "Science outruns institutions"),
    ("Persuasion at scale", "Countries diverge", "Income decouples from work",
     "Who decides"),
    ("An agent on every phone", "Tutors and self-driving", "Robots at home",
     "Meaning over employment"),
)

# S09, the readiness matrix. Spec section 5, S09.
# Columns are the first three horizons; the fourth is past the point where a
# dependency can be named, which is what S07 already says.
RD_COLS = (("2026 to 2030", "THE NEXT YEARS. HIGH"),
           ("The 2030s", "THE NEXT DECADE. MEDIUM"),
           ("The 2040s", "TOWARD 2050. LOW"))
# Relay ships six marks - activity, terminal, users, zap and two arrows - so
# two of these four rows take the nearest one rather than the one they would
# choose. The ledger has the ruling.
RD_ROWS = (("zap", "Data &\ncompute"),
           ("terminal", "Models &\nagents"),
           ("users", "Institutions\n& law"),
           ("activity", "Skills &\npeople"))
# (row, col, title, state, sublabel). state: "plain" in place today, "amber"
# partial today and carrying its gap, "red" absent today.
RD_CAPS = (
    (0, 0, "Frontier compute at scale", "plain", None),
    (0, 0, "Clean enterprise data", "amber", "today: mostly in lakes"),
    (0, 1, "Compute priced like power", "amber", "today: scarce and lumpy"),
    (1, 0, "Tool use in every workflow", "plain", None),
    (1, 0, "Agents reliable for a day", "amber", "today: minutes at a time"),
    (1, 1, "Agents reliable for a week", "red", None),
    (1, 1, "Automated experiment loops", "amber", "today: single steps"),
    (1, 2, "Robots cheap enough to rent", "red", None),
    (2, 0, "Audit trails on decisions", "amber", "today: pilots only"),
    (2, 0, "Liability rules for agents", "red", None),
    (2, 1, "Rules agreed across borders", "red", None),
    (2, 2, "Income decoupled from work", "red", None),
    (3, 0, "Supervision as a taught skill", "amber", "today: taught nowhere"),
    (3, 0, "Public trust in agents", "amber", "today: falling"),
    (3, 1, "Retraining at national scale", "red", None),
    (3, 2, "Care and craft paid properly", "red", None),
)
# Data & compute in the 2040s asks for nothing new: by then the compute
# question is answered. Drawn as the dashed, unfilled cell with a dash in it,
# and the speaker note says so out loud.
RD_EMPTY = {(0, 2)}
RD_ENABLERS = ("Energy", "Chips and fabs", "Public trust")
RD_LEGEND_RED = "RED absent today"
RD_LEGEND_AMBER = "AMBER partial today"

FORWARD = (
    ("Compute keeps getting cheaper",
     "Each halving of cost brings the next horizon a year or two closer."),
    ("Agents prove reliable on long tasks",
     "Weeks of unsupervised work is the threshold for whole functions."),
    ("Robots reach consumer prices",
     "The 2040s arrive in the 2030s the year a capable home robot costs what a car does."),
)
BACK = (
    ("Energy and chips become the bottleneck",
     "Demand outruns grids and fabs and the curve flattens for a decade."),
    ("A serious safety failure",
     "One well-publicised harm freezes deployment in health, finance and government."),
    ("Regulation freezes key sectors",
     "Liability rules that nobody can meet keep agents out of exactly the work they "
     "would change most."),
)

# --- geometry, taken from the drafts one to one ----------------------------
# S01: the hero measures 1019 px at T_COVER with tracking, which is what
# the 1.12 width factor makes of a browser line that looked like 910.
COVER_W = 1100
# S02
S02_GRID_Y, S02_GRID_H = 190, 284
S02_LINE_SLOT = 48      # two lines of T_CARD_DESC at LS_BODY, with air: at 40 the
                        # first card's wrapped line touched the next line in the export
S02_LEGEND_Y = (486, 516)
S02_NOTE_Y = 566
# S03: x(year) = RAIL_X0 + (year - 2026) * PER_YEAR
RAIL_X0, RAIL_X2050, RAIL_END = 110.0, 1020.0, 1170.0
PER_YEAR = (RAIL_X2050 - RAIL_X0) / 24.0
SEG_Y, SEG_H = 190, 48
MS_NUM_Y, RAIL_Y, TICK_Y, YEAR_Y = 272, 292, 296, 310
STEP_RULE_Y, STEP_Y = 372, 388
STEP_LABEL_H, STEP_GRADE_Y = 64, 480
S03_NOTE_Y = 566
# S04..S07
HZ_RULE_Y, HZ_NUM_Y, HZ_HEAD_Y, HZ_TAG_Y = 190, 204, 206, 216
# The headline's box is FIXED, not derived from the measured tag. The four
# horizon slides share one layout and the composed strip is asserted across
# them, so a box that is 65 px wider on the slide with the shortest tag puts
# one headline on one line and its neighbour on two for no design reason.
# 742 = R - HZ_HEAD_X - the widest tag - 24 of air. The widest tag is
# SPECULATIVE, which measured 124 when the tags were set in Noto Sans and
# measures 134 now that they are set in JetBrains Mono; the box lost 10 px
# with the face, and none of the four headlines wraps differently for it -
# the longest line one of the four reaches 1021, and the box ends at 1042.
HZ_HEAD_X, HZ_HEAD_W = 300, 742
HZ_CELLS_Y, HZ_CELLS_H = 298, 158
HZ_NOTICE_Y, HZ_TAGS_Y, HZ_NOTE_Y = 490, 510, 572
# S08
TBL_Y, TBL_HEAD_H, TBL_ROW_H = 196, 40, 82
S08_LEGEND_Y = (588, 616)
# S09, the readiness matrix. Derived so the whole slide sits inside Relay's
# content band, CONTENT_TOP 182 to CONTENT_BOTTOM 650:
#   matrix_frame draws a header row of hdr_h=32, then rgap=8, then four rows
#   of RD_ROW_H separated by rgap, so its bottom is
#     CONTENT_TOP + 32 + 8 + 4*RD_ROW_H + 3*8 = 246 + 4*RD_ROW_H.
#   At RD_ROW_H = 86 that is 590, which leaves 60 px to CONTENT_BOTTOM for
#   one bottom row of 26.
# RD_ROW_H 86, not more: the tallest cell is two pills with sublabels,
# 32 + 3 + 32 = 67, and flow_pills wants total <= RD_ROW_H - 6, so 86 clears
# it by 13 px. Not less either: at 76 the same cell would be 3 px short and
# the build would exit non-zero rather than clip, which is the point.
RD_TOP, RD_ROW_H = 182, 86
# One bottom row, not two. The strip measures 305 px from the first column's
# left edge (272) and the legend 302 px back from the right edge (1200), so
# they cannot meet inside 1120; two rows would put the second past
# CONTENT_BOTTOM at any row height that fits a two-sublabel cell.
RD_STRIP_Y, RD_STRIP_H = 604, 26
RD_LEGEND_H = 18
# S10
SP_RULE_Y, SP_LABEL_Y = 196, 215
SP_ITEM_Y = (252, 350, 448)
SP_HAIR_Y = (330, 428)
SP_NOTE_Y = 580
SP_COL_W, SP_GAP = 520, 80


# --- styling helpers -------------------------------------------------------

def grade_tag_ink(s, grade):
    """(fg, fill, border) for a confidence tag.

    A monochrome ramp from a solid ink fill to a hairline outline. Relay's
    status colours are green/amber/red and its readme forbids orange as a
    status, so a coloured ramp here would either read as good-to-bad or
    spend the one orange element on a legend.
    """
    return {
        "high": (s.PAPER, s.INK_1000, s.INK_1000),
        "medium": (s.PAPER, s.INK_600, s.INK_600),
        "low": (s.INK_600, s.PAPER, s.INK_300),
        "speculative": (s.FAINT, s.PAPER, s.INK_200),
    }[grade]


class Fit:
    """Measure-then-place for stacked text, for ONE type role.

    A Fit binds a face name to the TextMetrics calibrated for that face, so
    a caller cannot measure with one family's factors and write another
    family's name. `Draw` holds three of these.

    `spc` is on every method because this brand tracks nearly everything,
    and a line measured untracked that is drawn tracked overflows without a
    warning.
    """

    def __init__(self, metrics, warn, font):
        self.m, self.warn, self.font = metrics, warn, font

    def lines(self, runs, pt, w, spc=0):
        runs = [(runs, False)] if isinstance(runs, str) else runs
        return self.m.lines(runs, pt, w, spc=spc)

    def height(self, runs, pt, w, ls, spc=0):
        return self.lines(runs, pt, w, spc) * pt * PT_TO_PX * ls

    def check(self, label, needed, avail):
        if needed > avail:
            self.warn.add("HEIGHT", "%s needs %.0f > %.0f" % (label, needed, avail))

    def text(self, slide, x, y, w, h, runs, pt, color, label, ls=1.34, spc=0, **kw):
        self.check(label, self.height(runs, pt, w, ls, spc), h)
        return textbox(slide, x, y, w, h, runs, pt, color, self.font, ls=ls, spc=spc, **kw)

    def wide(self, label, text, pt, avail, bold=False, spc=0):
        """A single line that must not wrap. Returns the measured width."""
        w = self.m.width(text, pt, bold=bold, spc=spc)
        if w > avail:
            self.warn.add("OVERFLOW", "%s %.0f > %.0f wide: %s" % (label, w, avail, text))
        return w


class Draw:
    """The Relay vocabulary this deck draws with, bound to one slide set.

    Not in `deck_kit.components`: every method below carries a radius, a
    rule weight or a tracking that is Relay's, and the core library holds no
    brand knowledge. It is the counterpart of `brands/relay/slide.css`'s
    classes, one method per class.
    """

    def __init__(self, brand, style, metrics, warn):
        self.brand, self.s, self.m, self.warn = brand, style, metrics, warn
        # One face and one Fit per role. `self.font` and `self.fit` stay the
        # body pair, so every call that does not name a role gets body type,
        # which is what a run with no role of its own is.
        self.font = brand.sans
        self.fit = Fit(metrics, warn, brand.sans)
        self.disp_font = brand.family("display")
        self.disp_m = brand.metrics("display")
        self.fit_disp = Fit(self.disp_m, warn, self.disp_font)
        self.mono_font = brand.family("mono")
        self.mono_m = brand.metrics("mono")
        self.fit_mono = Fit(self.mono_m, warn, self.mono_font)

    # .k
    def mono(self, slide, x, y, w, h, text, color, size=None, align=PP_ALIGN.LEFT,
             label=None):
        s = self.s
        size = s.T_COL_SUB if size is None else size
        spc = s.track(size, s.TRACK_MONO)
        if label:
            self.fit_mono.wide(label, text.upper(), size, w, spc=spc)
        return textbox(slide, x, y, w, h, text, size, color, self.mono_font, align,
                       upper=True, ls=s.LS_LABEL, wrap=False, spc=spc)

    # .disp
    def display(self, slide, x, y, w, h, text, size, color, label, ls=None):
        s = self.s
        ls = s.LS_TITLE if ls is None else ls
        return self.fit_disp.text(slide, x, y, w, h, [(text, True)], size, color,
                                  label, ls=ls, spc=s.track(size, s.TRACK_DISPLAY))

    # .r-rule
    def hair(self, slide, x, y, w, color=None, h=None):
        s = self.s
        return rule(slide, x, y, w, s.HAIR if h is None else h,
                    s.LINE if color is None else color)

    # .gcells / .gcell
    def cell_grid(self, slide, x, y, w, h, n):
        """The butt-joined card grid: a hairline ground with n paper cells.

        Returns the cell boxes. CSS does this with `gap: 1px` over a
        coloured background; two rects say the same thing and keep the gap
        out of the renderer.
        """
        s = self.s
        rrect(slide, x, y, w, h, fill=s.LINE, rad=s.RAD_SURFACE)
        cw = (w - (n - 1) * s.GRID_HAIR) / float(n)
        boxes = []
        for i in range(n):
            cx = x + i * (cw + s.GRID_HAIR)
            rrect(slide, cx, y, cw, h, fill=s.PAPER, rad=s.RAD_SURFACE)
            boxes.append((cx, y, cw, h))
        return boxes

    # .tag
    def tag(self, slide, x, y, grade, text=None, right=None, label=None):
        """A 2px-radius control, never a pill. Returns its measured width."""
        s = self.s
        text = GRADES[grade][0] if text is None else text
        fg, fill, border = grade_tag_ink(s, grade)
        spc = s.track(s.T_PILL, s.TRACK_MONO)
        w = self.mono_m.width(text.upper(), s.T_PILL, bold=True, spc=spc) + 18
        if right is not None:
            x = right - w
        sp = rrect(slide, x, y, w, 20, fill=fill, line=border, lw=s.LW_HAIR,
                   rad=s.RAD_CONTROL)
        settext(sp, [(text, True)], s.T_PILL, fg, self.mono_font, PP_ALIGN.CENTER,
                MSO_ANCHOR.MIDDLE, ls=s.LS_LABEL, wrap=False, upper=True, spc=spc)
        if label and x < s.L:
            self.warn.add("OVERFLOW", "%s tag starts at %.0f, left of the band" % (label, x))
        return w

    # .chiplist: an outline tag carrying prose rather than a grade
    def chips(self, slide, x, y, w, texts, label):
        s = self.s
        spc = s.track(s.T_PILL, s.TRACK_TIGHT)
        cx, gap = x, 8
        for text in texts:
            tw = self.m.width(text, s.T_PILL, bold=False, spc=spc) + 18
            if cx + tw > x + w:
                self.warn.add("OVERFLOW", "%s tags run past %.0f: %s" % (label, x + w, text))
            sp = rrect(slide, cx, y, tw, 22, fill=s.PAPER, line=s.INK_300,
                       lw=s.LW_HAIR, rad=s.RAD_CONTROL)
            settext(sp, text, s.T_PILL, s.INK_1000, self.font, PP_ALIGN.CENTER,
                    MSO_ANCHOR.MIDDLE, ls=s.LS_LABEL, wrap=False, spc=spc)
            cx += tw + gap
        return cx - gap - x

    # .legendrow
    def legend(self, slide, x, y, grade):
        s = self.s
        w = self.tag(slide, x, y, grade)
        text = GRADES[grade][1]
        tw = self.fit.wide("legend " + grade, text, s.T_LEGEND, 420)
        self.fit.text(slide, x + w + 10, y, tw + 6, 20, text, s.T_LEGEND, s.GREY,
                      "legend " + grade, ls=s.LS_LABEL, wrap=False,
                      anchor=MSO_ANCHOR.MIDDLE)
        return w + 10 + tw

    # .noteline
    def noteline(self, slide, y, text, weight="hair", size=None, bold=False):
        s = self.s
        size = s.T_LOOP if size is None else size
        colour, h = {"hair": (s.LINE, s.HAIR),
                     "heavy": (s.INK_1000, s.RULE_HEAVY),
                     "signal": (s.SIGNAL_500, s.RULE_HEAVY)}[weight]
        rule(slide, s.L, y, s.W, h, colour)
        # The bold variant is a statement set in display type; the quiet one
        # is a body line under a hairline.
        spc = s.track(size, s.TRACK_DISPLAY) if bold else 0
        fit = self.fit_disp if bold else self.fit
        fit.wide("noteline", text, size, s.W, bold=bold, spc=spc)
        fit.text(slide, s.L, y + 12, s.W, size * PT_TO_PX * 1.6,
                 [(text, bold)], size, s.INK_1000 if bold else s.GREY,
                 "noteline", ls=s.LS_TITLE if bold else s.LS_LABEL, wrap=False,
                 spc=spc)


# --- slides ----------------------------------------------------------------

def cover(prs, brand, s, d):
    """Relay slide type 01: black ground, mono tagline, the hero low.

    The hero is two explicit paragraphs. Greedy wrap cannot break this title
    after its comma at any size - "2026 to 2050 and beyond" is wider than
    "AI and humanity, 2026", so any width that fits line two also pulls
    "2026" onto line one.
    """
    slide = add_slide(prs, brand)
    s.dark_ground(slide)
    d.mono(slide, s.L, 72, 700, 14, s.TAGLINE, s.SIGNAL_500, label="tagline")
    spc = s.track(s.T_COVER, s.TRACK_DISPLAY)
    for line in COVER_LINES:
        d.fit_disp.wide("cover line", line, s.T_COVER, COVER_W, bold=True, spc=spc)
    tb = d.fit_disp.text(slide, s.L, 356, COVER_W, 150, [(COVER_LINES[0], True)],
                         s.T_COVER, s.PAPER, "cover line 1", ls=s.LS_FLAT, spc=spc,
                         wrap=False)
    add_para(tb.text_frame, [(COVER_LINES[1], True)], s.T_COVER, s.PAPER, d.disp_font,
             ls=s.LS_FLAT, spc=spc)
    d.fit.text(slide, s.L, 538, 820, 30, COVER_SUB, s.T_LEAD, s.INK_300, "cover sub",
               ls=s.LS_CARD, spc=s.track(s.T_LEAD, s.TRACK_TIGHT))
    d.mono(slide, s.L, 580, 820, 14, COVER_NOTE, s.FAINT, label="cover note")
    s.footer(slide, None, inverse=True, copyright_line=False)
    return slide


def how_to_read(prs, brand, s, d):
    """Relay slide type 06 widened to four: a butt-joined card grid."""
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, "01. How to read this",
             "Four horizons, four grades of confidence",
             "The further right on the timeline, the wider the error bars. The grade "
             "on each slide says how wide.", 2, display=d.disp_m)
    cells = d.cell_grid(slide, s.L, S02_GRID_Y, s.W, S02_GRID_H, 4)
    for i, (hz, (cx, cy, cw, ch)) in enumerate(zip(HORIZONS, cells)):
        avail = cw - 40
        # The nearest horizon is the one orange element on this slide.
        d.mono(slide, cx + 20, cy + 20, avail, 14, hz.years,
               s.SIGNAL_600 if i == 0 else s.FAINT, label="card years %d" % i)
        d.display(slide, cx + 20, cy + 44, avail, 26, hz.name, s.T_LEAD, s.INK_1000,
                  "card name %d" % i, ls=s.LS_CARD)
        d.hair(slide, cx + 20, cy + 80, avail)
        # A fixed slot per line, not a measured one. Measuring each line and
        # stacking the results reserves two lines' height for a line the
        # renderer sets in one - the 1.12 width factor is deliberately
        # generous - and the four columns then step down at four different
        # rhythms, which reads as a bug rather than as breathing room.
        for k, line in enumerate(hz.card_lines):
            d.fit.text(slide, cx + 20, cy + 88 + k * S02_LINE_SLOT, avail,
                       S02_LINE_SLOT, line, s.T_CARD_DESC, s.GREY,
                       "card %d line %d" % (i, k), ls=s.LS_BODY)
        d.tag(slide, cx + 20, cy + ch - 38, hz.grade, label="card tag %d" % i)
    half = s.W / 2.0
    for k, grade in enumerate(GRADE_ORDER):
        used = d.legend(slide, s.L + (k % 2) * half, S02_LEGEND_Y[k // 2], grade)
        if used > half - 20:
            d.warn.add("OVERFLOW", "legend %s is %.0f wide, over %.0f"
                       % (grade, used, half - 20))
    d.noteline(slide, S02_NOTE_Y, READING_RULE, weight="heavy", size=s.T_LEAD, bold=True)
    return slide


def horizon_map(prs, brand, s, d):
    """Relay slide type 09: the year rail to scale, then the same seven
    milestones as seven equal columns under a 3 px rule."""
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, "02. The horizon map", "Seven milestones on one rail",
             "Where each forecast lands, and how sure this deck is about it.", 3,
             display=d.disp_m)

    def X(year):
        return RAIL_X0 + (year - 2026) * PER_YEAR

    # the four horizon segments, widths proportional to their year span
    rule(slide, 90, SEG_Y, 1100, s.RULE_STRONG, s.INK_1000)
    for hz in HORIZONS:
        bx = X(hz.start)
        if hz.start != 2026:
            d.hair(slide, bx, SEG_Y, 1, h=SEG_H)
        d.mono(slide, bx + 8, SEG_Y + 10, 200, 14, hz.name, s.INK_1000,
               label="segment " + hz.key)
        d.mono(slide, bx + 8, SEG_Y + 26, 200, 14, GRADES[hz.grade][0], s.FAINT)

    # the rail: numbers above it, markers on it, ticks and years below
    rule(slide, 90, RAIL_Y, 1100, s.RULE_STRONG, s.INK_1000)
    for i, (year, _, _) in enumerate(MILESTONES):
        cx = X(year)
        d.mono(slide, cx - 10, MS_NUM_Y, 20, 14, str(i + 1),
               s.SIGNAL_600 if i == 0 else s.FAINT, align=PP_ALIGN.CENTER)
        rule(slide, cx - 4, RAIL_Y - 4, 8, 8, s.SIGNAL_500 if i == 0 else s.INK_1000)
    for year in TICK_YEARS:
        rule(slide, X(year) - 0.75, TICK_Y, 1.5, 9, s.FAINT)
        d.mono(slide, X(year) - 30, YEAR_Y, 60, 14, str(year), s.FAINT,
               align=PP_ALIGN.CENTER)
    rule(slide, RAIL_END - 0.75, TICK_Y, 1.5, 9, s.FAINT)
    d.mono(slide, RAIL_END - 30, YEAR_Y, 60, 14, "beyond", s.FAINT, align=PP_ALIGN.CENTER)

    # the seven columns
    rule(slide, s.L, STEP_RULE_Y, s.W, s.RULE_HEAVY, s.INK_1000)
    col_w = (s.W - 6 * 12) / 7.0
    for i, (year, label, grade) in enumerate(MILESTONES):
        cx = s.L + i * (col_w + 12)
        d.mono(slide, cx, STEP_Y, col_w, 14,
               "%02d - %d" % (i + 1, year), s.SIGNAL_600 if i == 0 else s.INK_1000,
               label="milestone head %d" % (i + 1))
        d.fit.text(slide, cx, STEP_Y + 20, col_w, STEP_LABEL_H, label, s.T_BODY,
                   s.GREY, "milestone %d" % (i + 1), ls=s.LS_CARD)
        d.mono(slide, cx, STEP_GRADE_Y, col_w, 14, GRADES[grade][0], s.FAINT)
    d.noteline(slide, S03_NOTE_Y, MAP_RULE)
    return slide


def horizon_slide(prs, brand, s, d, hz, page):
    """Relay slide types 04 and 06 on one layout: the oversized year, the
    statement, three butt-joined cells, the tags, the signpost."""
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, hz.kicker, hz.title, hz.sub, page, display=d.disp_m)
    rule(slide, s.L, HZ_RULE_Y, s.W, s.RULE_HEAVY, s.INK_1000)

    # the oversized numeral, with its unit as a second run on the same
    # baseline. The signature device, and this slide's one orange element.
    num_spc = s.track(s.T_NUMERAL, s.TRACK_DISPLAY)
    runs = [(hz.numeral, True)]
    if hz.unit:
        runs.append((hz.unit, True))
    d.fit_disp.wide("numeral " + hz.key, hz.numeral, s.T_NUMERAL, 200, bold=True,
                    spc=num_spc)
    tb = textbox(slide, s.L, HZ_NUM_Y, 200, 66, runs, s.T_NUMERAL, s.SIGNAL_500,
                 d.disp_font, ls=s.LS_FLAT, wrap=False, spc=num_spc)
    if hz.unit:
        # The unit is a second run at T_UNIT on the same baseline. settext
        # writes every run at one size, so the size is reset here rather than
        # given a second parameter nothing else in the kit would use.
        tb.text_frame.paragraphs[0].runs[1].font.size = Pt(s.T_UNIT)

    tag_w = d.tag(slide, 0, HZ_TAG_Y, hz.grade, right=s.R, label="grade " + hz.key)
    if s.R - tag_w < HZ_HEAD_X + HZ_HEAD_W:
        d.warn.add("OVERFLOW", "grade tag %s reaches the headline box" % hz.key)
    d.display(slide, HZ_HEAD_X, HZ_HEAD_Y, HZ_HEAD_W, 70, hz.headline,
              s.T_HEADLINE, s.INK_1000, "headline " + hz.key)

    cells = d.cell_grid(slide, s.L, HZ_CELLS_Y, s.W, HZ_CELLS_H, 3)
    for i, ((title, desc), (cx, cy, cw, ch)) in enumerate(zip(hz.domains, cells)):
        avail = cw - 40
        icon(slide, brand.icon_dir, DOMAIN_ICONS[i], "ink", cx + 20, cy + 20, 18)
        d.fit.text(slide, cx + 20, cy + 52, avail, 22, [(title, True)], s.T_COL_HEAD,
                   s.INK_1000, "domain head %d" % i, ls=s.LS_CARD,
                   spc=s.track(s.T_COL_HEAD, s.TRACK_TIGHT))
        d.fit.text(slide, cx + 20, cy + 78, avail, ch - 96, desc, s.T_CARD_DESC,
                   s.GREY, "domain desc %s %d" % (hz.key, i), ls=s.LS_BODY)

    d.mono(slide, s.L, HZ_NOTICE_Y, 400, 14, "What you will notice", s.FAINT)
    d.chips(slide, s.L, HZ_TAGS_Y, s.W, hz.tags, "notice " + hz.key)
    d.noteline(slide, HZ_NOTE_Y, hz.signpost)
    return slide


def matrix_slide(prs, brand, s, d):
    """Relay slide type 11: mono headers over a 1.5 px rule, hairline rows."""
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, "07. Impact by domain", "Four domains across four horizons",
             "The same forecasts, placed by domain, each carrying its grade.", 8,
             display=d.disp_m)
    col_w, col_x = columns(s.L, s.R, s.ROW_LABEL_W, s.COL_GAP, 4)

    d.mono(slide, s.L, TBL_Y, s.ROW_LABEL_W, 14, "Domain", s.MUTED)
    for c, hz in enumerate(HORIZONS):
        d.mono(slide, col_x[c], TBL_Y, col_w, 14, hz.years,
               s.SIGNAL_600 if c == 0 else s.MUTED, label="column head %d" % c)
    rule(slide, s.L, TBL_Y + TBL_HEAD_H - 2, s.W, s.RULE_MEDIUM, s.INK_1000)

    for r, (icon_name, label) in enumerate(MATRIX_ROWS):
        y = TBL_Y + TBL_HEAD_H + r * TBL_ROW_H
        icon(slide, brand.icon_dir, icon_name, "ink", s.L, y + 18, 18)
        d.fit.text(slide, s.L + 28, y + 12, s.ROW_LABEL_W - 28, 40, [(label, True)],
                   s.T_COL_HEAD, s.INK_1000, "row label %d" % r, ls=s.LS_CARD,
                   spc=s.track(s.T_COL_HEAD, s.TRACK_TIGHT))
        for c in range(4):
            grade = HORIZONS[c].grade
            lead = grade == "high"
            d.fit.text(slide, col_x[c], y + 12, col_w, 36,
                       [(MATRIX[r][c], lead)], s.T_CAPTION,
                       s.INK_1000 if lead else s.GREY,
                       "cell r%dc%d" % (r, c), ls=s.LS_CARD)
            d.mono(slide, col_x[c], y + 52, col_w, 14, GRADES[grade][0], s.FAINT)
        d.hair(slide, s.L, y + TBL_ROW_H - 4, s.W)

    for k, grade in enumerate(GRADE_ORDER):
        used = d.legend(slide, s.L + (k % 2) * 560, S08_LEGEND_Y[k // 2], grade)
        if used > 540:
            d.warn.add("OVERFLOW", "matrix legend %s is %.0f wide" % (grade, used))
    return slide


def readiness(prs, brand, s, d):
    """The kit's capability matrix, in Relay's radius scale.

    The only slide in this deck drawn with `deck_kit.components` rather than
    with `Draw`: `matrix_frame`, `flow_pills` and the status pills had
    exactly one caller in the repository, an example directory from another
    engagement, and folding that coverage onto a slide this deck's argument
    needs is why the slide exists. The ledger has the ruling.

    Two brand values reach the kit as arguments rather than as literals in
    `src/`: `accent=s.NAVY` keeps the frame in ink (three orange header rules
    would spend the slide's one orange element on furniture, and the
    "Enablers" label is what earns it), and `cell_rad` / `rad` carry Relay's
    radius scale - 0 for a surface, 2 for a control - into a component that
    used to hard-code 8 and 7.
    """
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, "08. What has to be true",
             "What has to be true by when",
             "Every horizon rests on capabilities that are not in place yet.", 9,
             display=d.disp_m)

    plain = PillStyle(fill=s.PAPER, line=s.LINE, lw=s.LW_MEDIUM, fg=s.INK_1000)
    amber = PillStyle(fill=s.AMB_BG, line=s.AMB, lw=s.LW_STRONG, fg=s.INK_1000,
                      sub_fg=s.AMB_TXT)
    red = PillStyle(fill=s.RED_BG, line=s.RED, lw=s.LW_STRONG, fg=s.INK_1000)
    styles = {"plain": plain, "amber": amber, "red": red}

    cells = matrix_frame(slide, RD_TOP, RD_ROW_H, RD_COLS, RD_ROWS, s.GEOM, s,
                         s.SANS, brand.icon_dir, empty=RD_EMPTY, accent=s.NAVY,
                         cell_rad=s.RAD_SURFACE)
    grouped = {}
    for r, c, title, state, sub in RD_CAPS:
        grouped.setdefault((r, c), []).append(
            Pill(title, styles[state], sub=sub))
    for key, items in sorted(grouped.items()):
        # The ladder starts at the brand's own T_PILL rather than at the
        # kit's 9.5: every one of these cells fits at 9.9, and a cell that
        # dropped a rung would set its pills smaller than its neighbours for
        # no reason a reader could see. The two lower rungs stay, so a longer
        # title shrinks rather than failing the build.
        flow_pills(slide, cells[key], items, d.m, s.SANS, d.warn,
                   ladder=(s.T_PILL, 9.5, 9.0), sub_pt=s.T_PILL_SUB,
                   rad=s.RAD_CONTROL, label="readiness r%dc%d" % key)

    # The enablers strip: the label in the row-label gutter, the pills from
    # the first column's left edge. The one orange element on this slide -
    # they are transversal, so they sit outside the time axis entirely.
    d.mono(slide, s.L, RD_STRIP_Y + 6, s.ROW_LABEL_W - 6, 14, "Enablers",
           s.SIGNAL_600, size=s.T_EYEBROW, align=PP_ALIGN.RIGHT, label="enablers")
    x = s.GEOM["col_x"][0]
    for title in RD_ENABLERS:
        pill = Pill(title, plain)
        w = pill_w(d.m, pill, s.T_PILL, s.T_PILL_SUB)
        draw_pill(slide, x, RD_STRIP_Y + (RD_STRIP_H - 23) / 2.0, w, 23, pill,
                  s.SANS, s.T_PILL, s.T_PILL_SUB, rad=s.RAD_CONTROL)
        x += w + 8

    # The legend, right-aligned to the content band and vertically centred on
    # the strip's row. Its two states are exact strings from spec section 3.
    runs = [("RED", True, s.RED), (" absent today", True, s.GREY),
            ("     ", True, s.GREY),
            ("AMBER", True, s.AMB_LEG), (" partial today", True, s.GREY)]
    flat = "".join(r[0] for r in runs)
    lw = d.m.width(flat, s.T_LEGEND, bold=True) + 24
    box = rrect(slide, s.R - lw, RD_STRIP_Y + (RD_STRIP_H - RD_LEGEND_H) / 2.0,
                lw, RD_LEGEND_H, fill=s.PAPER, line=s.LINE, lw=s.LW_HAIR,
                rad=s.RAD_CONTROL)
    settext(box, runs, s.T_LEGEND, s.GREY, s.SANS, PP_ALIGN.CENTER,
            MSO_ANCHOR.MIDDLE, ls=s.LS_LABEL, wrap=False)
    # The strip accumulates left to right with nothing to stop it, so it is
    # measured against the legend's left edge rather than against the band.
    if x - 8 > s.R - lw - 20:
        d.warn.add("OVERFLOW", "enabler strip ends at %.0f, inside the legend at %.0f"
                   % (x - 8, s.R - lw - 20))
    return slide


def signposts(prs, brand, s, d):
    """Relay slide type 07: two columns, and the right one gets the orange
    rule - which is the correct reading, because the right column is what
    would push every date back."""
    slide = add_slide(prs, brand)
    s.header(slide, d.m, d.warn, "09. What would change this", "Signposts that move the dates",
             "Three things that would bring every horizon forward, and three that would "
             "push them back.", 10, display=d.disp_m)
    sides = (("Would bring the dates forward", FORWARD, "arrowup", s.INK_1000, s.INK_1000),
             ("Would push the dates back", BACK, "arrowdown", s.SIGNAL_500, s.SIGNAL_500))
    for i, (head, items, icon_name, rule_ink, label_ink) in enumerate(sides):
        x = s.L + i * (SP_COL_W + SP_GAP)
        rule(slide, x, SP_RULE_Y, SP_COL_W, s.RULE_HEAVY, rule_ink)
        icon(slide, brand.icon_dir, icon_name, "ink", x, SP_LABEL_Y - 3, 16)
        d.mono(slide, x + 24, SP_LABEL_Y, SP_COL_W - 24, 14, head, label_ink,
               label="column head %d" % i)
        for k, (title, desc) in enumerate(items):
            iy = SP_ITEM_Y[k]
            d.display(slide, x, iy, SP_COL_W, 26, title, s.T_LEAD, s.INK_1000,
                      "signpost head %d%d" % (i, k), ls=s.LS_CARD)
            d.fit.text(slide, x, iy + 28, SP_COL_W, 44, desc, s.T_CARD_DESC, s.GREY,
                       "signpost desc %d%d" % (i, k), ls=s.LS_BODY)
            if k < len(SP_HAIR_Y):
                d.hair(slide, x, SP_HAIR_Y[k], SP_COL_W)
    d.noteline(slide, SP_NOTE_Y, CLOSING_RULE, weight="heavy", size=s.T_LEAD, bold=True)
    return slide


# --- build -----------------------------------------------------------------

def build(template, out, mode, teleprompter=None):
    brand = load_brand("relay")
    s = brand.style()
    m = brand.metrics()
    warn = WarnRegister()
    d = Draw(brand, s, m, warn)
    prs = open_deck(template, brand)

    cover(prs, brand, s, d)
    how_to_read(prs, brand, s, d)
    horizon_map(prs, brand, s, d)
    for i, hz in enumerate(HORIZONS):
        horizon_slide(prs, brand, s, d, hz, 4 + i)
    matrix_slide(prs, brand, s, d)
    readiness(prs, brand, s, d)
    signposts(prs, brand, s, d)

    style = MarkerStyle(s.PAGE_X, s.PAGE_Y, s.PAGE_W, s.PAGE_H, s.PAGE_SIZE,
                        s.PAGE_COLOR, s.PAGE_FONT, PP_ALIGN.RIGHT)
    report = renumber(prs, style, skip=(1,))
    expected = [(p, p, "fixed") for p in range(2, 11)]
    if report != expected:
        raise SystemExit("renumber report %r, expected %r" % (report, expected))

    # The register gates the write: a dirty build must not leave a deck on
    # disk that looks finished. emit_notes comes after it for the same
    # reason - it is the step that writes the teleprompter file.
    warn.exit_if_dirty()

    refuse_in_place(out, template)
    emit_notes(prs, NOTES, mode, font=brand.sans, size_pt=s.T_BODY, gap_pt=6, title=TITLE,
               teleprompter=teleprompter, skip=(1,))
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


def count_shapes(prs):
    """Autoshapes plus freeforms, and pictures, the way assert_native.py counts."""
    auto = pics = 0
    for slide in prs.slides:
        for sh in iter_shapes(slide.shapes):
            if sh.shape_type in (MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.FREEFORM):
                auto += 1
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                pics += 1
    return auto, pics


AUTOSHAPES, PICTURES = 145, 32


def check(out, mode, teleprompter=None):
    """Reopen the package; assert what the mode asked for, and that the rest
    was NOT written - under --notes none the pane must be empty and no
    teleprompter file may exist."""
    prs = Presentation(str(out))
    if len(prs.slides) != 10:
        raise SystemExit("expected 10 slides, found %d" % len(prs.slides))
    got = read_notes(prs)
    if mode in ("pptx", "both"):
        if sorted(got) != list(range(1, 11)):
            raise SystemExit("notes did not round-trip: %r" % sorted(got))
    elif got != {}:
        raise SystemExit("--notes %s must leave the notes pane empty, found %r"
                         % (mode, sorted(got)))
    auto, pics = count_shapes(prs)
    if (auto, pics) != (AUTOSHAPES, PICTURES):
        raise SystemExit("shape arithmetic is off: %d autoshapes, %d pictures; the docstring "
                         "says %d and %d" % (auto, pics, AUTOSHAPES, PICTURES))
    if mode in ("teleprompter", "both"):
        html_text = teleprompter.read_text(encoding="utf-8")
        for needle in ('<section id="s10"', "Slide 10 [10]", "Total spoken time: 16 min",
                       'class="aside"'):
            if needle not in html_text:
                raise SystemExit("teleprompter lacks %r" % needle)
        if "Slide 1 [" in html_text:
            raise SystemExit("the cover must carry no printed number")
    elif teleprompter is not None and teleprompter.exists():
        raise SystemExit("--notes %s must not write a teleprompter, but %s exists (this run, "
                         "or a previous one at the same path)" % (mode, teleprompter))


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--notes", choices=NOTES_MODES, default="none",
                    help="which speaker-notes outputs to emit (default: none)")
    ap.add_argument("--teleprompter", type=Path,
                    help="where to write the teleprompter page; needed with "
                         "--notes teleprompter or both")
    args = ap.parse_args(argv)
    if args.notes in ("teleprompter", "both") and args.teleprompter is None:
        raise SystemExit("--notes %s writes a teleprompter: pass --teleprompter PATH"
                         % args.notes)
    return args


def main():
    args = parse_args()
    out = build(args.template, args.out, args.notes, args.teleprompter)
    check(out, args.notes, args.teleprompter)
    print("ai-horizon OK ->", out, "notes:", args.notes,
          *([args.teleprompter] if args.notes in ("teleprompter", "both") else []))


if __name__ == "__main__":
    main()
