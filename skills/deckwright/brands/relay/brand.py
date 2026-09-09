"""The Relay brand: the deckwright brand package built from
`brands/relay_design_system/`.

Relay is a technology consulting firm. The design system it ships was
written from a brief and flags three substitutions of its own - fonts,
logo and icons - in its `readme.md`. This package now inherits two of
them, not three.

**Fonts: fetched, not substituted.** Relay names Space Grotesk (display),
Public Sans (body) and JetBrains Mono (labels), and ships no binaries -
its `tokens/fonts.css` pulls all three from Google Fonts. All three are
under the SIL Open Font License 1.1, so `scripts/fetch_fonts.py --brand
relay` downloads them from the upstream release each family is published
from, verifies each file against the sha256 pinned in `fonts.toml`, and
writes the licence text alongside. They are the faces this brand measures
against and the faces it names in the PPTX. The earlier substitution -
Noto Sans standing in for all three, because none was installed - is
gone; `fonts/README.md` is the record of what it cost and why fetching
replaced it.

Six files, because `TextMetrics` addresses a family as a regular and a
bold and a variable TTF loads at one instance. The three families are
declared as three roles, and `style.py` puts each on the runs Relay's own
kit puts it on: display on titles, numerals and statements, sans on body
copy, mono on every kicker, footer label, table header and grade tag.

**Measurement factors, per face.** Calibrated once against an export. The
numbers this package started from were the repository's first brand's, and
they were that brand's faces (Noto Sans) rather than these; the calibration
below replaced them. Method, reproducible from the docstring alone:

  1. Build a deck that sets one string, S = "Handgloves 2050 quick brown
     fox", at 24 pt and again at 10 pt, once and then twice over, in each
     of the eight faces (the six above, plus Noto Sans Regular and Bold as
     a control). `wrap=False`, no tracking, one face per slide.
  2. Export it through `scripts/export_png.ps1`, which renders at 1600x900
     - a 1.25 scale on the 1280x720 canvas.
  3. In each PNG measure the horizontal ink extent of the once row and of
     the twice row. Their difference is the pen advance of S exactly: the
     first glyph's left side bearing and the last glyph's right side
     bearing appear in both and cancel. Divide by 1.25 for design pixels.
  4. R = that advance / `ImageFont.truetype(face, round(pt*96/72)).getlength(S)`
     - PowerPoint's advance over PIL's, like for like.

  OBSERVED, R at 24 pt and at 10 pt, regular and bold averaged:

     Space Grotesk    0.9951   1.0353
     Public Sans      0.9986   1.0277
     JetBrains Mono   1.0078   1.0000
     Noto Sans        1.0066   1.0487   <- the control

  R is near 1 at 24 pt for every face, which says what 1.12 never did:
  PowerPoint does not set glyphs ten percent looser than PIL measures
  them. 1.12 is headroom, and the 10 pt column says where most of it goes
  - PIL loads a face at an integer pixel size, so 10 pt is measured at 13
  px rather than 13.33 and comes out two to five percent narrow.

  The factors keep that headroom rather than re-deciding it. For each
  family, factor = 1.12 (or 1.07) x R_family / R_noto, taken at whichever
  of the two sizes gives the larger answer, then rounded to the two
  decimals the repository writes these in:

     Space Grotesk    width 1.1072 -> 1.11   wrap 1.0578 -> 1.06
     Public Sans      width 1.1112 -> 1.11   wrap 1.0616 -> 1.06
     JetBrains Mono   width 1.1214 -> 1.12   wrap 1.0713 -> 1.07

  Display and body landing on the same pair is the measurement, not a
  shortcut: Space Grotesk and Public Sans render within 0.4% of each other
  against PIL, and the two families differ by less than the rounding.
  JetBrains Mono is the one that needed its own number, and it needed the
  larger one.

**Rendering.** The factors above are what the builder measures with; what
PowerPoint draws depends on the faces Windows knows about. All three are
installed for the current user on the machine this was calibrated on. On
a machine where they are not, the build and its wrap simulation are still
correct - they read `fonts/` - but an export substitutes, and the PNGs
stop being evidence about line breaks.

**Logo.** Relay supplied none, and its own system drew none: the wordmark
guideline sets the word "Relay" in the display face at -0.045em.
`logo_primary.png` is that word, drawn by
`scripts/make_placeholder_logos.py` in Space Grotesk Bold now that the
display face is on disk, and it is a placeholder - recorded as one in
`assets.toml`. `logo_secondary` is not a second design but the same word
in the second ink Relay allows a mark to carry: the cover sits on
`#0A0A0A`, and an ink wordmark on an ink ground is an invisible footer
that no shape count would notice. Nothing in this brand calls
`primitives.lockup` - Relay puts one mark in the footer, not a two-mark
lockup in the header.

**Icons.** Lucide, which is Relay's own substitution, cropped from
`brands/relay/iconsheet.html` through `scripts/crop_icons.py --sheet
relay` in the one colour key Relay allows an icon to carry ("icons never
carry color of their own: they are ink, inverse, or the semantic color of
the message they sit in").
"""

from pathlib import Path

from deck_kit.brand import BrandSpec

HERE = Path(__file__).resolve().parent

BRAND = BrandSpec(
    name="relay",
    master_name="Relay Master",
    layout_name="Relay Content",
    background="inherited",
    # Body. Relay's --font-body, and the family a run with no role of its
    # own is set in.
    sans="Public Sans",
    serif=None,             # Relay has no serif role at all
    font_dir=HERE / "fonts",
    font_regular="PublicSans-Regular.ttf",
    font_bold="PublicSans-Bold.ttf",
    width_factor=1.11,
    wrap_factor=1.06,
    # Display. Titles, the cover line, the oversized numerals, the
    # statement on a horizon slide, and the wordmark.
    display="Space Grotesk",
    display_regular="SpaceGrotesk-Regular.ttf",
    display_bold="SpaceGrotesk-Bold.ttf",
    display_width_factor=1.11,
    display_wrap_factor=1.06,
    # Mono. Every kicker, footer label, page number, table header and grade
    # tag - which in Relay's kit is a lot of the slide.
    mono="JetBrains Mono",
    mono_regular="JetBrainsMono-Regular.ttf",
    mono_bold="JetBrainsMono-Bold.ttf",
    mono_width_factor=1.12,
    mono_wrap_factor=1.07,
    logo_primary=HERE / "logo_primary.png",
    logo_secondary=HERE / "logo_inverse.png",
    icon_dir=HERE / "icons",
    expects_embedded_fonts=0,
)
