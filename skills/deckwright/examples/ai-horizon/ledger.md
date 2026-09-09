# Ledger - AI and humanity, 2026 to 2050 and beyond (Relay)

Every ruling here is a design decision this deck took, in `brands/relay`'s
own vocabulary rather than in the kit's default furniture. The kit's
furniture - radius 8 cards, gradient bands, colour-scaled statuses - came
from the fixture brand the repository used to carry, and this deck departs
from all of it; each departure is a ruling below.

- Ruling: nine of the ten slides draw with `deck_kit.primitives` and a local
  `Draw` class rather than `deck_kit.components` - `matrix_frame`,
  `explain_box`, `loop_line`, `flow_pills` and `chip` all defaulted to radius
  6, 7 or 8, and Relay's `tokens/radius.css` says "sharp by default, radius is
  a rounding of last resort, never a style", with 0 for a surface and 2 for a
  control - `brands/relay_design_system/tokens/radius.css` and its readme,
  "Borders, radii, elevation" - cost if wrong: the Relay vocabulary is one
  class rather than five functions; move `Draw`'s methods into
  `deck_kit.components` behind a radius parameter when a second Relay-shaped
  deck needs them. S09 is the exception and the next ruling says why.

- Ruling: the four confidence grades are a monochrome ink ramp - solid
  `ink-1000`, solid `ink-600`, a hairline `ink-300` outline, a faint
  `ink-200` outline - rather than the example brand's blue/amber/panel/muted
  scale, because Relay's readme says "orange is never a status color" and
  its status ramp is green/amber/red, which would read as good-to-bad;
  confidence is not goodness - the readme, "Colors" - cost if wrong: the
  grades are harder to tell apart at a glance; give the two strongest a
  `volt-500` edge, which is the one colour Relay licenses for data.

- Ruling: the kicker is `ink-500` on every white slide and the one orange
  element is chosen per slide - the nearest horizon, the live milestone, the
  year the forecast lands on, the column that would push the dates back.
  Relay's own kit sets `.k mute` on all seven of its white slide types and
  keeps signal for the content that earns it - `ui_kits/slides/03, 05, 06,
  07, 09, 10, 11` - cost if wrong: the deck reads quieter than the brand;
  one line in `style.header` puts the kicker back in signal.

- Ruling: the inverse cover is painted per slide as one full-bleed `rrect`
  rather than by a second layout in the template, so `make_template.py` and
  the template contract are unchanged. Relay's own kit does exactly this,
  with `data-theme="dark"` on the section element; and python-pptx cannot
  add a layout, so a second one would mean cloning a `p:sldLayout` part and
  re-minting its relationships - the class of surgery the gate's doubled COM
  open exists to catch - `brands/relay/style.py` module docstring - cost if
  wrong: one autoshape per dark slide and a background a hand-editor can
  select; make the layout and add a `layout_name` list to `BrandSpec`.

- Ruling: S03's seven milestones do NOT alternate above and below the rail,
  as `examples/ai-horizon`'s do. Two milestones sit exactly on a tick (2040
  and 2045), so a card below the rail would need a connector running through
  that year's label. The rail keeps the proportion and carries the numbered
  markers; seven equal columns under a 3 px rule carry the words, which is
  Relay's 09-timeline - spec section 5, S03 - cost if wrong: the reader
  matches a column to a marker by number rather than by position; put the
  cards back on the rail and move the tick labels above it.

- Ruling: the cover title is written as two explicit paragraphs breaking
  after the comma, not as one wrapped box. Greedy wrap cannot produce that
  break at any size - "2026 to 2050 and beyond" is wider than "AI and
  humanity, 2026", so any width that fits line two pulls "2026" onto line
  one - `build_ai_horizon.py`, `cover()` - cost if wrong: an edited
  title breaks in the wrong place and nothing warns; the measurement still
  refuses a line wider than the box.

- Ruling: S02's three forecast lines sit in fixed 40 px slots rather than at
  measured heights. Stacking measured heights reserves two lines for a line
  the renderer sets in one - the 1.12 width factor is deliberately generous -
  and the four columns then step down at four different rhythms, which reads
  as a bug - the export at `out/ai-horizon/png/s02.png` - cost if
  wrong: a longer line clips; `Fit.text` warns HEIGHT on the slot and the
  build exits non-zero.

- Ruling: the type scale does NOT honour Relay's own floor, "nothing on a
  slide goes below 24px", which is 16 px and 12.2 pt at this canvas. That
  rule is written for a fourteen-slide reference deck whose densest slide is
  a five-row table; this deck puts three domain cells and five tags on one
  slide. The repository's floors govern instead, and `tests/test_style.py`
  now walks every brand against them - `brands/relay/style.py` docstring and
  `docs/decisions.md` - cost if wrong: the mono labels read small in a large
  room; raise `T_COL_SUB`, `T_FOOT` and `T_META` and re-fit two slides.

- Ruling: the mono role - eyebrows, footers, table headers, source notes -
  is set in Noto Sans uppercase at +0.12em rather than in a monospaced face,
  because none of Relay's three named faces and no OFL mono is on this
  machine, and a proprietary Windows face may be pointed at but not
  committed - `brands/relay/fonts/README.md` - cost if wrong: the labels
  lose the monospaced texture; drop JetBrains Mono into `fonts/`, add a
  second `TextMetrics` and set the label runs in it.

- Ruling: `notes_data.py` is imported from `examples/ai-horizon/` rather
  than copied. The spoken content is the same deck in a different design
  system, and a second copy would drift the moment one of them was edited -
  `build_ai_horizon.py`, the import block - cost if wrong: editing the
  ai-horizon notes silently changes this deck's teleprompter; both builders'
  `check()` reopen the package and assert the notes round-trip.

- Ruling: S09 alone draws with `deck_kit.components` - `matrix_frame`,
  `flow_pills`, `Pill`, `PillStyle` and `draw_pill` - because those pieces had
  exactly one caller in the repository, `examples/capability-matrix`, an
  example from another engagement kept alive for no reason but that coverage.
  A slide that belongs to this deck's argument covers them better than a
  second example directory nobody reads, and the readiness matrix is the
  argument's missing half: the other nine slides say what will happen, this
  one says what it rests on - `docs/decisions.md`, "Session 2026-09-09 - one
  deck" - cost if wrong: one slide in the deck is drawn in a second
  vocabulary, and a reader tracing a coordinate has two places to look; move
  the matrix into `Draw` and let the kit's components go untested by any deck.

- Ruling: the kit's radii became parameters rather than the slide accepting
  the kit's defaults. `draw_pill` and `flow_pills` take `rad` (default 7) and
  `matrix_frame` takes `cell_rad` (default 8); S09 passes `s.RAD_CONTROL` and
  `s.RAD_SURFACE`, so its cells are square and its pills are 2 px controls.
  A radius is a design-system value and `src/deck_kit` holds no brand
  knowledge - the same argument that moved the icon colour key and the frame
  accent out of the kit - `src/deck_kit/components.py` and
  `tests/test_components.py::test_draw_pill_takes_the_brands_control_radius`,
  `::test_matrix_frame_takes_the_brands_surface_radius` - cost if wrong: two
  more parameters on two kit functions; drop them and the slide draws lozenges
  on a system whose readme forbids them.

- Ruling: the pills carry Relay's semantic STATUS colours - amber for partial
  today, red for absent today - where the four confidence grades are a
  monochrome ink ramp. The two are different claims: a grade is not goodness
  and a green-to-red ramp would misread it, but "this capability does not
  exist yet" IS a bad state and amber-to-red is what Relay's status ramp is
  for - the readme, "Colors", and the second ruling above - cost if wrong: the
  deck carries two colour languages on two slides and a reader may take the
  matrix's red as a grade; the legend names both states in words, which is
  what the exact strings pin.

- Ruling: the enablers strip and the legend share ONE bottom row rather than
  a row each. The strip measures 305 px from the first column and the legend
  302 px back from the right edge, so they cannot collide inside 1120; two
  rows would push the last one past `CONTENT_BOTTOM` at any row height that
  fits a two-pill cell - `build_ai_horizon.py`, `RD_STRIP_Y` and its
  derivation comment - cost if wrong: longer enabler titles run into the
  legend with nothing to stop them; the strip measures itself and warns
  OVERFLOW past the legend's left edge, so the build exits non-zero.

- Ruling: the four row icons take the nearest mark Relay ships rather than
  the mark the row would choose. The brand carries six - activity, terminal,
  users, zap and two arrows - so "skills and people" is drawn with `activity`
  and "data and compute" with `zap`, which is the same compromise the deleted
  matrix example recorded when its own two icons stopped existing -
  `brands/relay/icons/` - cost if wrong: two rows carry a mark that reads
  approximately; add the glyphs to `templates/iconsheet.html`, re-capture the
  sheet and re-crop, which is a browser step the gate deliberately does not
  take.

- Ruling: the empty cell is a claim, not a hole. "Data & compute" in the
  2040s is drawn as the dashed, unfilled cell with a centred dash because by
  then the compute question is answered and the row asks for nothing new;
  the speaker note says so, so a reader who reads it as a missing entry is
  corrected out loud - spec section 5, S09, and `notes_data.py` note 9 - cost
  if wrong: the slide looks unfinished to anyone who does not hear the note;
  put a plain pill reading "nothing new" in the cell and lose the one dashed
  cell the kit's `empty=` argument is drawn for.

- Ruling: this deck's HTML captures were taken with the ms-playwright
  `chrome-headless-shell` on the machine of record, not with Python
  Playwright. Playwright is not importable there - an offline `uv` cannot
  fetch it and PyPI is behind a corporate TLS interceptor - so
  `scripts/capture_drafts.py` fell through to the browser-binary route, and
  the route it landed on is printed by the run and recorded here because
  `SKILL.md` says a fallback route is a ruling. The full-browser
  `chromium-1217/chrome.exe` is tried first and fails fast on this machine
  (exit 0, no file, ~1.2 s per attempt) when another Chromium already holds
  the default profile - cost if wrong: the drafts were judged through a
  different renderer than the reference one, so a difference that is
  Chromium-build-specific would not be seen. The composition strips over
  those captures are asserted row by row by
  `examples/ai-horizon/run_html.ps1`, which is what limits the exposure.
