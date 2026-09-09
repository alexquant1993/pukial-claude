# Stage 2 - the HTML draft

## What the draft is for

One HTML file per slide, on the same 1280x720 canvas the builder works on, so
every coordinate transfers unchanged. The draft exists to argue about layout
cheaply and to let an agent see its own output before any Python is written.

**The draft is the default for every route-B slide.** A slide that skips it
is the exception, and the user is the one who opts out: the spec records the
decision in its front matter as `HTML draft: skipped: <reason>`, next to the
design-system line, so a reader of the spec knows the layout was never seen
before it was built. The reason matters because the draft is what makes a
deck visually rich - a builder written straight from prose tends to reach
for the header furniture and a text box, and the ai-horizon deck, built
without drafts, is the evidence: its ledger says the horizon map is the one
slide where a draft would have paid for itself, and the drafts in
`examples/ai-horizon/drafts/` were authored afterwards to close that gap.

**The draft is disposable - unless the deck's output is `html`.** Once its
layout is approved, the builder becomes
the source of truth and the HTML stops being maintained. Say so in the file,
as every file in `examples/ai-horizon/drafts/` does. The alternative - keeping the HTML as the
master and exporting from it - does not survive the moment a human edits the
PPTX by hand, which is the moment every real deck reaches.

That last sentence is the whole argument, and it has an exception: a deck
that is **never** ported has no PPTX for a human to edit, so nothing goes
stale. When the spec's `**Output:**` line says `html`, the drafts are the
deck and the disposability note comes out of the files. See
[The stage page](#the-stage-page) below.

The engagement this repository comes from learned that the hard way: its HTML
slides went stale and its handoff eventually had to declare, in writing, that
the builder was the source of truth.

## The default design system

A draft needs a design system to be drawn in, and most users arrive without
one. `brands/relay` is the design system used when the user has none: a real
system, adopted from a download, with a palette, a type scale, a grid, line
spacings, tracking, header furniture, three type families, a wordmark and
icons. The spec's front matter says `Design system: default (brands/relay)`
when that is the case, and `templates/slide.css` imports its tokens.

**It is also the only one.** The repository used to carry two synthetic
fixture brands next to it, so that the gate had two slide masters and the
unit tests had a brand to load that was not the real one. Both are gone: the
second master is now a variant of Relay's own contract
(`scripts/make_template.py --brand relay --variant donor`), and every test
loads `relay`. `scripts/discover.py` therefore has no brand to skip - a
brand package on disk is a candidate - and its recommendation on this tree
is "use brand relay" because relay is the only one.

The mirror rule below is still written as a rule about brands rather than
about one brand: `tests/test_html_stage.py` parametrizes over a list read
from the brands directory, so a second brand that ships both halves is held
to it without the test being edited.

A design system has two halves that mirror each other one to one:

| Half | Files | Used by |
|---|---|---|
| HTML | `brands/<name>/tokens.css` (the numbers) and `templates/components.css` (the vocabulary styled with them) | the draft, through `templates/slide.css` or the brand's own `slide.css` |
| PPTX | `brands/<name>/style.py` (the numbers and `header()`) and `deck_kit.components` / `deck_kit.primitives` (the vocabulary) | the builder |

Every name in one half has its counterpart in the other: `BLUE` is
`--blue`, `T_CAPTION` is `--t-caption`, `LS_CARD` is `--ls-card`,
`ROW_LABEL_W` is `--row-label-w`, and `components.draw_pill` is `.pill`.
`tests/test_html_stage.py` pins the mirror: every `T_*` in `style.py` has a
`--t-*` token, and every token the vocabulary uses is defined.

The one thing that does not mirror is the type size itself. The CSS px is
the design size; `style.py` holds the point size the builder re-derives at
roughly px x 0.76 and then floors to the spec's minimums
(`references/03-pptx-stage.md`, "Typography does not"). `--t-body: 14px` is
`T_BODY = 11.0`, and a line that fits at 14 px in the draft can wrap at 11 pt
in the export. That is expected; the builder measures and warns.

**To swap in a brand of your own:** copy `brands/relay/` to
`brands/<yours>/`, change the numbers in both halves - the hex values and px
in `tokens.css`, the `RGBColor` and pt values in `style.py` - and keep every
name. The vocabulary in `components.css` and `deck_kit` reads the names,
never the values, so it carries over unchanged; then give the brand its own
`slide.css` (or point `templates/slide.css`'s `@import` at the new tokens),
declare the brand's faces in `fonts.toml` and run
`python scripts/fetch_fonts.py --brand <yours>` to put them under `fonts/`
(the `@font-face` rules in `tokens.css` and `brand.py`'s per-role
`*_regular` and `*_bold` fields name them), calibrate a width and wrap
factor **per family** against an export, regenerate the icons through the
pipeline below, and run `tests/test_style.py`, which walks EVERY brand's
`T_*` against the floors.

**Three type roles, not one.** A design system usually names a display face,
a body face and a mono face, and `BrandSpec` carries all three: `sans`,
`display` and `mono`, each with its own two files and its own two
measurement factors, reached through `brand.metrics(role)` and
`brand.family(role)`. A brand that names only a sans keeps working
unchanged - `metrics("display")` hands back the sans metrics, which is what
a one-family brand means by its display face. The factors are per family
because they calibrate a face: `brands/relay`'s docstring carries the
measurement that produced 1.11 / 1.06 for Space Grotesk, 1.11 / 1.06 for
Public Sans and 1.12 / 1.07 for JetBrains Mono, and the method that got
them.

### What adopting Relay actually took

`brands/relay/` is that procedure run for real, on a system downloaded into
`brands/relay_design_system/` and read there without being edited. It is
worth reading before the next one, because the sentence above understates
four things.

**The intake did not recognise it.** Relay has no `brand.py`, no PPTX master
and no `tokens.css` - its tokens are a `tokens/` directory of eight CSS
files - so `scripts/discover.py` reported "no design system found" and
recommended the default brand while Relay sat unread on disk. `discover.py`
now takes three shapes as evidence (a `tokens/` directory of CSS, a
`styles.css` beside a readme or a `SKILL.md`, a `_ds_manifest.json`) and
recommends setting a brand up from what it finds.

**Geometry scaled, type was re-derived, and neither was one number.** Relay's
own slide kit is 1920x1080 and this canvas is 1280x720, so lengths scale by
2/3: its 120 px page padding became `L = 80` and its 24 px gutter
`COL_GAP = 16`. Rules did **not** scale - a 2 px hairline at 2/3 is 1.33 px,
which renders as a fuzzy 1 or 2 - so 1 / 1.5 / 2 / 3 came straight from the
system's `tokens/spacing.css`. Type was picked from Relay's own 1.26-ratio
scale at the smaller canvas and then put through px x 0.76 and the floors.
Relay carries a floor of its own, "nothing on a slide goes below 24px",
which is 12.2 pt here; this repository's 8-to-11 floors won, because Relay's
rule is written for a reference deck whose densest slide is a five-row
table. That disagreement is the ruling in `docs/decisions.md`, and it is the
one every adoption will have.

**Three substitutions arrived already declared, and none of them closed.**
Relay's own readme flags fonts, logo and icons as substitutions, and this
package inherits all three:

| Substitution | What Relay says | What `brands/relay` does |
| --- | --- | --- |
| fonts | Space Grotesk, Public Sans, JetBrains Mono, no binaries - loaded from Google Fonts | NOT substituted any more: all three are OFL 1.1, so `scripts/fetch_fonts.py --brand relay` downloads them from each family's upstream release, verifies them against the sha256 pinned in `fonts.toml` and writes the licence alongside. Six files, because `TextMetrics` addresses a family as a regular and a bold |
| mono | eyebrows, footers and table headers in JetBrains Mono at +0.12em | kept: `MONO` is JetBrains Mono, and the labels are set uppercase at `TRACK_MONO`. The tracking is what reads as a label at 8 to 10 pt |
| logo | none supplied and none drawn; the wordmark guideline sets the word in the display face at -0.045em | that word, drawn to PNG by `scripts/make_placeholder_logos.py`, in ink and in paper, both recorded as PLACEHOLDER in `assets.toml` |
| icons | Lucide, already Relay's substitution | kept: `brands/relay/iconsheet.html` inlines the paths from `assets/icons/` and `scripts/crop_icons.py --sheet relay` slices them |

`brands/relay/fonts/README.md` records what was looked for and where, so the
next reader does not repeat the search.

**Tracking turned out to be load-bearing, and the kit could not express it.**
A system whose display type is set at -0.035em and whose labels are set at
+0.12em is a different system without it, so `primitives.settext` grew a
`spc` argument (points, written as OOXML `a:rPr/@spc` in hundredths) and
`metrics.width`/`lines` grew the same, added after the padding factor rather
than multiplied by it. Measuring a mono label untracked understates it by
about a fifth, which is an overflow nothing would have reported.

**Two things did not carry over at all.** `deck_kit.components` -
`matrix_frame`, `explain_box`, `loop_line`, `flow_pills`, `chip` - hard-codes
radius 6, 7 or 8, and Relay's radius is 0 for a surface and 2 for a control;
and the kit's bands are gradients, which Relay forbids outright. The Relay
builder therefore draws with `deck_kit.primitives` and a local `Draw` class
instead, one method per class in `brands/relay/slide.css`. That is a real
cost of the adoption and it is written down as a ruling in
`examples/ai-horizon/ledger.md` rather than hidden in the builder.

**The substitution that did not have to happen.** The first version of this
brand set all three roles in Noto Sans, because none of Space Grotesk,
Public Sans or JetBrains Mono was installed on the machine and `uv --offline`
could fetch nothing. Every one of the three is OFL, and the network was
reachable the whole time; nobody looked. `scripts/fetch_fonts.py` exists so
the next adoption asks the question in the intake instead - it reads the
brand's `fonts.toml`, downloads what is missing, verifies a pinned sha256
and writes the licence text alongside, and refuses anything that is not OFL
1.1.

## The skeleton

`templates/slide.html` and `templates/slide.css` are the starting point.
`slide.css` reaches the brand's tokens through a relative `@import` of
`brands/relay/tokens.css` - the default design system - then imports
`templates/components.css`. That first import is the reason the serving
section matters, and it is the line to change when drafting against another
brand. The skeleton shows
one instance of each major class, so the vocabulary is visible in the file a
draft starts from; delete what the slide does not use.

## The component vocabulary in CSS

One class per `deck_kit` component or primitive, each carrying the geometry
contract the builder uses. A draft written with these classes ports 1:1: the
inline `left/top/width/height` on an element are the numbers the named
function takes. Everything is positioned absolutely inside `.slide`, in px;
inside a `.grid` or a `.card`, children are positioned from the parent's
corner instead (the builder's `x + 14` becomes `left: 14px`).

| Class | `deck_kit` function | Geometry contract |
|---|---|---|
| `.card` | `primitives.rrect(fill=WHITE, line=CELL_BD, lw=0.75, rad=8)` | white ground, cell border, radius 8; `.card--blue/--amber/--line/--muted` are the border colours a builder passes as `line` |
| `.band` | `primitives.rrect(fill=BLUE, rad=8)` + `xmlfill.grad([(0, BLUE_DARK, a), (100, BLUE, a)], ang=0)` | left-to-right gradient, white ink; `.band--faded` sets `--band-alpha` (.56, override inline), `.band--headline` fades 100 to 82, `.band--column` is one colour 100 to 70 (`.band--amber` for AMB_LEG) |
| `.band-label`, `.band-title` | `textbox(..., T_COL_HEAD, upper=True, anchor=MIDDLE)` / `textbox(..., T_TITLE, ls=LS_TITLE, anchor=MIDDLE)` | the text inside a band; the band's padding is the builder's inset |
| `.chip` | `primitives.chip(x, y, w, h=20, text, T_META, fg, fill, border, lw=.75)` | height 20 (`.chip--tall` 22), radius half the height, width = measured text + 22; `.chip--inverse/--amber/--panel/--outline` are the (fg, fill, border) triples |
| `.pill`, `.pill .sub` | `components.draw_pill(x, y, w, h, pill, font, T_PILL, T_PILL_SUB)` | height 23, 32 with a sublabel; radius 7; width = measured title + 20; bold title centred, sublabel below at 1.05; `.pill--amber/--panel/--outline` are the `PillStyle`s |
| `.pill--bar` | `PillStyle(bar=...)` | a 3 px bar inset 10, 6 above the foot, plus 4 px of height |
| `.flow`, `.flow--left` | `components.flow_pills(slide, cell, pills, ...)` | pills wrap inside the cell, 6 apart, rows 3 apart, 6 inset a side, centred both ways or `align="left"` |
| `.matrix` | `components.matrix_frame(slide, top, row_h, cols, rows, geom, ...)` | the row-label gutter (`--row-label-w`) then `--cols` equal columns with `--col-gap` between, which is `geometry.columns()`; header 32 tall with a 2 px BLUE rule, rows `--row-h` tall with 8 between |
| `.col-head`, `.col-sub` | the header textboxes inside `matrix_frame` | `T_COL_HEAD` bold upper BLUE in 16 px, `T_COL_SUB` GREY in 12 px |
| `.row-label` | the row label and icon inside `matrix_frame` | 18 px icon at left + 44, `T_ROW_LABEL` bold upper BLUE right-aligned 6 short of the gutter |
| `.cell`, `.cell--empty` | the cell background inside `matrix_frame` | `rrect(WHITE, line=CELL_BD, .75, rad 8)` with `alpha_fill(WHITE, 42)`; the empty cell is dashed and unfilled with a centred "-" |
| `.explain`, `.explain .head`, `.explain .desc` | `components.explain_box(slide, cell, title, desc, ...)` | the element is the cell; the white box is inset 6 with a BLUE 1.2 border, radius 8; text at +16, +8, anchored middle: `T_CAPTION` bold NAVY then `T_CARD_DESC` GREY |
| `.loop-line` | `components.loop_line(slide, y, runs, geom, ..., h=24)` | full band width, 24 tall, WHITE at alpha 72, LINE border, radius 6, text at left + 16, no wrap |
| `.legend`, `.legend-row` | `rrect(WHITE, line=LINE, .75, rad 5)` + `settext(runs, T_LEGEND)` / `chip(...)` + `textbox(x + cw + 8, y, tw, 20, T_CAPTION)` | an 18 px box right-aligned to the band; a chip then a caption on one 20 px line |
| `.numcircle` | `primitives.numcircle(x, y, sz=22, n, BLUE, WHITE, T_CAPTION)` | a 22 px circle, the number centred |
| `.rule`, `.rule--blue`, `.rule--v` | `primitives.rule(x, y, w, h, color)` | a 1 px LINE hairline; height inline when it is not 1 |
| `.rail` | `primitives.rule(x, y, w, 3, BLUE)` | the 3 px year rail |
| `.tick` | `rule(x - .5, y - 6, 1.5, 15, BLUE)` + `textbox(x - 24, y + 12, 48, 14, T_META, MUTED, CENTER)` | a 1.5 x 15 tick centred on x with its label 18 below the tick's top |
| `.milestone`, `.milestone--above`, `.milestone--below` | `numcircle` + `rule` (the connector) + `rrect(card_x, card_y, 150, 74, WHITE, line, 1.0, rad 6)` | a zero-size anchor at the circle's centre; the 150x74 card sits with its foot 26 above the rail or its head 40 below, joined by a 1 px LINE connector |
| `.cover-title`, `.cover-sub`, `.cover-note` | `textbox(L, 250, W, 100, T_COVER)`, `textbox(L, 360, W, 40, T_SUB, MUTED)`, `textbox(L, 400, W, 20, T_META, MUTED)` | the cover's three lines |
| `.grid` | `col_w = (W - (n - 1) * gap) / n`, the arithmetic every builder does by hand | equal columns with `--gap` (default `--col-gap`) between; children fill a column each |
| `.text`, `.text--head`, `.text--body`, `.text--body-bold`, `.text--caption`, `.text--mid` | `primitives.textbox(x, y, w, h, runs, T_*, ...)` | free text at a textbox's coordinates, typed by the `T_*` the builder would pass; `--mid` is `anchor=MSO_ANCHOR.MIDDLE` |
| `.ink-blue`, `.ink-navy`, `.ink-grey`, `.ink-muted`, `.ink-amber`, `.ink-amb-leg`, `.ink-white` | the third element of a run tuple, `(text, bold, colour)` | a per-run colour |

The header furniture - `.tagline`, `.kicker`, `.title`, `.sub`, `.lockup`,
`.foot`, `.page` - stays in `slide.css` and ports to `style.header()`.

Two things have no CSS counterpart, deliberately. The `flow_pills` ladder
(9.5 to 9.0 to 8.5 pt) is the only autoshrink in the kit and it is a
builder decision; if pills do not fit the draft, they will not fit the
export. And the warning register: the draft shows an overrun, the builder
refuses it.

**The worked example** is `examples/ai-horizon/drafts/`: ten drafts for
ten slides, authored **before** the builder, which is the stage done in the
right order. Each carries the coordinates
`examples/ai-horizon/build_ai_horizon.py` passes to `deck_kit`. Put a
draft's capture beside `out/ai-horizon/png/sNN.png` and the layouts
coincide; the copy wraps differently where a point size is wider than the
px it came from, which is the type rule doing what it says.

Its classes come from `brands/relay/slide.css` rather than from
`templates/slide.css`, because Relay's header is a rule, a mono kicker and a
display heading, and its mark is in the footer - brand rules belong in the
brand's own CSS, and `components.css` stays brand-neutral.
`tests/test_html_stage.py` holds the drafts to the rules: only classes a
stylesheet defines, no `<script>`, no inline `<style>`, a stated
disposability, and every `src` pointing at a committed file in the brand
package.

## Serving

```
uv run --offline --no-project python scripts/preview.py serve --root . --port 8123
```

**Serve from a root high enough that every relative `@import` resolves.** A
CSS `@import` resolves against the importing stylesheet's own URL, not against
the served root. A slide stylesheet that reaches its design tokens through
`../../` will, when the server is rooted at the slide directory, have that
path normalised back past the root: the import 404s and every custom property
is left undefined.

The symptom is a **silently unstyled slide**, not an error. Nothing in the
console says "your tokens are missing"; the page simply renders with browser
defaults and looks subtly wrong in a way that is easy to blame on the CSS.

A draft that lives in `examples/<deck>/drafts/` links the skeleton's
stylesheet relatively, `../../../templates/slide.css`, and is served from
the repository root, where that path and both `@import`s resolve.

**Two trees is the normal case, and it raises the root.** A brand package
kept outside this repository - which `DECKWRIGHT_BRANDS` exists for, and
which the provenance rule makes the usual arrangement for an employer's
brand - has its `slide.css` in one tree and `templates/components.css` in
another, so the brand's stylesheet reaches the shared vocabulary through
something like `../../../../deckwright/templates/components.css` and the
server has to be rooted at the directory that contains **both** trees. That
is the rule above working as intended, not a workaround; it is worth saying
out loud because the root that follows from it is higher than anyone
expects.

**`serve` proves the root before it announces one.** It fetches one file it
knows is under the root and compares the bytes, and it refuses a port
another process is already holding instead of binding alongside it. An
earlier version set `SO_REUSEADDR`, which on Windows let a second server
bind a port a stale one still held: the new server printed
`serving <the new root>` and answered 404 to everything, and the printed
line was the only evidence, and it was false. Pinned by
`tests/test_preview.py::test_a_busy_port_is_refused_rather_than_hijacked`.

## Capturing

**Looking at the draft is the point of the draft.** The one bug this stage
exists to catch is a layout that only reads right in the author's head, and
nothing catches it but a picture. So a capture is a requirement of this
pipeline, not a convenience: an agent that cannot screenshot its drafts
cannot judge them, and the deck is worse for it. `scripts/doctor.py` reports
the browser as REQUIRED for that reason, and `SKILL.md`'s intake runs the
doctor before its first question.

For the whole deck at once - which is the normal case:

```
python scripts/capture_drafts.py --drafts examples/ai-horizon/drafts \
    --out out/ai-horizon/png_html --root . --expect 10
```

It writes one `sNN.png` per draft at the 1600x900 the PPTX export writes,
serving the tree itself on a free port, so composition QA runs on an HTML
deck exactly as it does on a PowerPoint one (`05-qa.md#the-html-deck`). It
tries three things in order and says which one it used:

1. **Python Playwright**, the reference renderer, when it is importable.
2. **A Chromium-family browser binary driven directly**, which needs no
   Python package: `--headless=new --screenshot=<png>` against the served
   URL. It searches the ms-playwright builds under `%LOCALAPPDATA%` (the
   Playwright MCP server installs these, so a machine that has never run
   `pip install playwright` often still holds a Chromium), then Google
   Chrome, then Microsoft Edge. `DECKWRIGHT_BROWSER=<path>` overrides the
   search. Each capture gets 60 seconds and one retry, and the retry is the
   one that adds a throwaway `--user-data-dir` - which is what a browser the
   user has open needs, and what the ms-playwright Chromium hangs on, so it
   is the retry rather than the default. A binary that hangs fails over to
   the next rather than hanging the run. Pinned by
   `tests/test_capture_drafts.py::test_a_browser_that_hangs_times_out_and_the_next_one_captures`
   and `tests/test_capture_drafts.py::test_the_browser_search_order_is_the_measured_one`.
3. **Nothing** - and then it exits non-zero with `CAPTURE UNAVAILABLE`, the
   three remedies, and the real diagnostics for every route it tried. It
   used to print a cheerful skip and exit 0, which is how ten drafts nobody
   had looked at reached a stage page.

Every PNG is verified against `1280x720 x scale` before it is counted: a
browser that ignored the device scale writes a plausible image that every
crop box in `05-qa.md` then misses by a quarter. Pinned by
`tests/test_capture_drafts.py::test_a_capture_of_the_wrong_size_is_refused`.

**The font race, and why `--virtual-time-budget` is in the command.** A
browser's `--screenshot` fires on the load event, and the load event does
not wait for web fonts. A `@font-face` still inside its block period renders
its text **invisibly**, so the capture comes out with every rule, box and
icon exactly in place and not one word on it - a slide that looks like a
design decision rather than a failure. It was found by looking at a capture
of `s06-toward-2050.html` and it is the reason this section exists.
Measured on the machine this was written for: one blank in eight without
the flag, none in twenty with it. The Playwright route awaits
`document.fonts.ready` for the same reason. **A capture with no text on it
is this bug, not the draft's**; re-run before editing anything.

**A capture taken through any route other than Python Playwright is a ruling
for the deck's ledger**, and the script prints the line to record: the
drafts were judged through a different renderer than the reference one.

For one page rather than a deck - the icon sheet, say - `preview.py capture`
is the single-shot version:

```
uv run --no-project --with playwright python scripts/preview.py capture \
  http://127.0.0.1:8123/examples/ai-horizon/drafts/s09-readiness.html \
  --out out/s09.png --width 1280 --height 720
```

**Note the missing `--offline`**: that is the one command in these
references that needs the network, once, because `--offline` cannot fetch
Playwright and Playwright then has a browser to download of its own.

Single pages are captured at **scale 1** so the DOM geometry read back is
unscaled. If a capture tool renders at a device scale factor, the pixel
coordinates you measure will not be the pixel coordinates the builder needs.

**The last resort, after the doctor and after all three routes:** any
browser that can be driven to a 1280x720 viewport and asked for a
screenshot does the same job - the cropper and the composer do not care
which tool produced the image. `capture_drafts.py` prints the URL and the
filename for every slide under its failure message, so it can be done by
hand. It is last because doing it by hand for ten slides is how the look
gets skipped.

## The stage page

When the spec's `**Output:**` line says `html` or `both`, the drafts are
built into one deliverable:

```
python scripts/build_html_deck.py --drafts examples/ai-horizon/drafts \
    --out out/ai-horizon/html --title "AI horizon" --expect-slides 10
```

It writes `<out>/index.html` and nothing else: every draft **embedded** in
slide order at 1280x720, one visible at a time and scaled to the window,
arrow keys, Home and End, click - the left third goes back - a `N / M`
counter, and a print stylesheet that puts one slide on one 13.333in x 7.5in
page, which is 1280x720 CSS px at 96dpi and PowerPoint's own 16:9 sheet. So
"print to PDF" from the browser yields a PDF deck, with no PowerPoint in the
chain.

Three things about it are decisions rather than details:

**Embedded, not iframed.** An iframe would keep each draft's own document
intact, which is tidier and would need no URL rewriting. Browsers print an
iframe as one clipped box or not at all, and printing is half of what this
page is for.

**Every URL is rewritten, and a remote one is refused.** The stage page
lives in the output directory, so a draft's `../../../brands/relay/slide.css`
means nothing from there; each `href` and `src` is resolved against the
draft's own directory and re-expressed relative to the output. An absolute
`http://`, `https://` or protocol-relative URL is refused with a sentence
saying why: **no external network resource reaches the page**, because a
deck that fetches a font from a CDN renders differently on the client's
machine and not at all offline.

**The drafts' own comments are dropped.** A draft's comment is a note to its
author - "DISPOSABLE, the builder is the source of truth" - and the stage
page is the deliverable, not the workshop.

Slides are ordered by the number in `sNN-`, read as a number: `s10` sorts
before `s02` as a string, and a deck in the wrong order is one nobody
notices is wrong until the meeting. Two drafts claiming the same number are
refused rather than silently ordered. `--expect-slides N` is exact, because
a glob that matched four drafts of ten builds a four-slide deck that looks
exactly like a successful build. Pinned by
`tests/test_build_html_deck.py`; `examples/ai-horizon/run_html.ps1` is the
whole HTML loop as a script and the gate runs it.

## The icon pipeline

The builders place rasterised PNGs, not SVG, because python-pptx cannot draw a
multi-path stroked icon as a native shape. The pipeline is three steps:

1. **Author the sheet.** `templates/iconsheet.html` inlines the chosen icon
   paths in a fixed `LIST` order and lays them out on a grid. Cells are 160 px
   and the icons are placed at 13 to 18 px, so the oversample runs from about
   nine times up to twelve - which is what keeps them crisp in PDF and print.
   The shipped sheet uses Lucide outline icons (ISC licence); swap them for
   whatever set the brand uses.
2. **Capture it.** Any browser, any device scale. The cropper derives cell size
   from the screenshot's own dimensions, so it does not care.
3. **Crop it.** `scripts/crop_icons.py --sheet <name>` slices the grid into
   `ic_<name>_<colorkey>.png` under the brand's `icons/`. `--sheet` has no
   default: the filenames it writes end in the sheet's colour key, so
   cropping one sheet under another sheet's entry writes plausible names
   that nothing resolves.

**The `LIST` order is the only contract between the sheet and the cropper**,
and both files carry a `MUST match` comment saying so. That comment is the
entire safety mechanism. In the one sheet-and-cropper pair of the source
engagement where it was dropped, the names drifted inline into the cropper -
which is exactly what the comment exists to prevent.

The icons are **committed**, not regenerated when the gate runs. That is what
makes the gate hermetic: it needs Python and PowerPoint, never a browser.

## Placing an icon

`deck_kit.primitives.icon` **raises** when the file is missing. The
engagement's version returned silently, so a typo in a name or a colour key
rendered nothing at all and the build still reported success.

In a draft the same icon is an `<img>` pointing at the committed PNG,
`brands/<name>/icons/ic_<name>_<colorkey>.png` - `brands/relay/icons/
ic_zap_ink.png`, say - at the size the builder will pass; `.row-label img`
in `examples/ai-horizon/drafts/s09-readiness.html` is the worked case. The colour key is the brand's, named as
`ICON_KEY` in its `style.py`: `deck_kit.components.matrix_frame` reads it
rather than hardcoding one, which it used to do.
