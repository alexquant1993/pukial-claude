# Stage 3 - building the PPTX natively

The output is real, editable shapes. Not a screenshot, not a picture of a
deck. That is the whole point of the stage, and `scripts/assert_native.py`
enforces it by refusing any slide-sized picture.

## The template contract

Builders do not construct a deck from nothing. They open a template and purge
its slides, so every generated slide inherits the master, the layout and the
background without the builder drawing any of it.

What a template must provide is declared as data in `brands/<name>/brand.py`:

| Clause | Why |
|---|---|
| canvas size, and the slide size in EMU it implies | the 1:1 mapping depends on it |
| master **by name** | see below |
| layout **by name** | see below |
| background: inherited from the layout, or drawn per slide | the builder must not draw what the layout already supplies |
| font family names and the TrueType directory used for measurement | measurement needs real files, embedding needs the names |
| logo assets and lockup proportions | the header furniture |
| embedded-font expectation | **reported, never asserted** |

**By name, never by index.** The source engagement hardcoded
`slide_masters[3].slide_layouts[0]`. That is true of exactly one file and is
the least portable line in the toolkit; `BrandSpec` raises a `TypeError` if
you try to pass an index.

**An empty name is an index in disguise, and it is refused too.** A real
corporate template arrives with its slide masters called `''` - one that
prompted this had four of them, and a hundred layouts with names repeated
across masters and once within one. Writing `master_name = ""` into
`brand.py` used to pass `__post_init__`, then pass `inspect_template.py`'s
`spec.master_name in names` clause, while `deck._layout` bound to whichever
unnamed master python-pptx yielded first. That is a binding by position
wearing a name, and it passed the contract verifier. `BrandSpec` now raises
a `ValueError` naming the remedy, and `inspect_template.py` prints the same
remedy under the failed clause:

```
FAIL master 'Relay Master'          found: '', '', '', ''
     remedy: this deck's slide masters carry no usable names. Name the
     master in PowerPoint's Slide Master view (View > Slide Master, rename),
     or generate a template with make_template.py --brand relay. ...
```

Pinned by `tests/test_brand.py::test_brand_spec_rejects_an_empty_name` and
`tests/test_template.py::test_inspect_names_the_remedy_for_an_unnamed_master`.

Two tools share this one schema, which is what makes it a contract rather than
a description:

```
python scripts/make_template.py   --brand relay --out out/template.pptx
python scripts/inspect_template.py --brand relay out/template.pptx

# a SECOND master from the same contract, for the Phase 2 transplant: the
# master and layout names get " (donor)" appended and the ground is painted
# in the brand's PANEL, so the merge crosses two masters rather than merging
# a template with itself
python scripts/make_template.py   --brand relay --variant donor --out out/template2.pptx
python scripts/inspect_template.py --brand relay --variant donor out/template2.pptx
```

`inspect_template.py` reports every clause and then exits non-zero if any of
them failed - all of them, not just the first, so one run tells you
everything there is to fix.

**It verifies a generated template; it is not a route for adopting somebody
else's.** The template is generated from the design system the intake chose,
and this is what proves the generated file satisfies the contract before
anything is built on it - which is why the gate and every example run it on
their own output, immediately after `make_template.py`. Pointing it at a
corporate deck still reports honestly, and what it usually reports is the
unnamed-master case above; the answer to that is to generate, not to edit
somebody's artifact. `SKILL.md`'s intake offers a design system the user
points at, one `discover.py` found, or the default - and no master.

Note that python-pptx cannot add a shape to a layout, so `make_template.py`
builds the background on a scratch slide and moves its element into the
layout's shape tree.

## Geometry transfers exactly

1 CSS pixel is 9525 EMU at 96 dpi. Worked through:

```
1280 x 9525 = 12192000 EMU = 13.333 in
 720 x 9525 =  6858000 EMU =  7.5   in
```

So a 1280x720 draft maps 1:1 onto a 16:9 slide and **every coordinate in the
HTML transfers unchanged**. `deck_kit.geometry.px()` is the only conversion
you need, and `columns()` holds the derived-column formula that every builder
in the source repository re-declared for itself.

## Typography does not

Mapping `font-size: 11px` to 11 pt leaves body copy near 8 pt and labels near
5 pt on a projected slide. The rule is **type re-derived at roughly px x 0.76
and then floored**:

| Kind | Floor |
|---|---|
| body copy | 11 pt |
| captions, including pill sublabels | 9.5 pt |
| box titles | 11 pt |
| column headers | 12 pt |
| metadata: copyright, page numbers | 9 pt |
| all-caps micro-labels | the only type allowed below 9 pt, down to 8 |

Sizes live in named `T_*` constants in the brand's `style.py`, never inline
and never as arithmetic on another constant. `ALL_CAPS_MICRO` in the brand
names the constants licensed to sit below 9 pt, and
`tests/test_style.py::test_every_type_size_honours_the_floors` walks every
other `T_*` against the floors - naming a handful of constants by hand let
every violator through, which is how mixed-case copy ended up at 7.2 pt.

Line spacing follows a small scale: 1.0 for single-line labels, 1.04 to 1.06
for titles, 1.1 to 1.15 for card titles, 1.2 to 1.34 for body prose.

### Tracking, when the brand has any

Some design systems are half tracking. Relay's display type is set at -0.035
to -0.045em and its mono labels at +0.12em, and a deck built without that is
not that system - so `settext`, `textbox` and `add_para` take `spc`, a
letter-spacing **in points**, and write it as OOXML `a:rPr/@spc`, which is in
hundredths of a point. Points, because every other size in the kit is points
and a caller reaching for the XML has two chances to get the unit wrong.
Zero writes no attribute at all, so a brand with no tracking produces exactly
the runs it did before. Pinned by
`tests/test_primitives.py::test_settext_writes_letter_spacing_in_hundredths_of_a_point`
and `tests/test_primitives.py::test_no_spc_attribute_is_written_when_tracking_is_zero`.

**Measure with the same `spc` you write with.** `TextMetrics.width` and
`.lines` take it too, and add it *after* the padding factor rather than
multiplying by it: the factor calibrates how much looser PowerPoint sets
glyphs than PIL measures them, while tracking is an exact number of points
the renderer inserts after every character. Scaling it would make a tightly
tracked display line measure narrower than it is drawn. A mono label at
+0.12em measured untracked is about a fifth narrower than it renders, which
is an overflow the register never sees. Pinned by
`tests/test_metrics.py::test_tracking_is_added_after_the_padding_factor_not_multiplied_by_it`
and `tests/test_metrics.py::test_tracking_reaches_the_wrap_simulator`.

The amount is the brand's: `brands/relay/style.py` holds `TRACK_DISPLAY`,
`TRACK_MONO` and the rest as em, and `track(size_pt, em)` turns one into the
points both halves take. The core holds none of them.

## No autofit. The builder measures.

`MSO_AUTO_SIZE` must never be imported, and `tests/test_metrics.py` fails the
build if it is - but that check is necessary and nowhere near sufficient.
python-pptx's `add_textbox()` emits `<a:spAutoFit/>` by default, so autofit
reaches a deck without anyone importing anything. `settext` strips it from
every text frame it writes, and `scripts/assert_native.py` fails the build if
a single `spAutoFit` or `normAutofit` survives into a slide part. **Doctrines
are checked against the artifact, not against the source.**

All fitting happens offline in `deck_kit.metrics` against the brand's TrueType
files:

| Factor | Value in `brands/relay` (sans role) | Why |
|---|---|---|
| points to CSS pixels | 96/72 = 1.3333 | load the face at canvas scale |
| width padding | 1.11 | headroom over what PIL measures |
| wrap simulation | 1.06 | a smaller padding, used only when counting lines |

The factors are **the brand's**, not the library's, and **one pair per type
family** rather than one pair per brand. `BrandSpec` carries `width_factor`
and `wrap_factor` for the sans role and `display_*` / `mono_*` for the other
two; `brand.metrics(role)` builds the right `TextMetrics` and `TextMetrics`
itself takes the numbers as parameters and has no defaults, so a brand that
forgets them fails loudly rather than inheriting another brand's.

**Calibrate against an export, not against a belief.** The method, and the
numbers it produced for `brands/relay`'s three families, are in
`brands/relay/brand.py`'s docstring: set one string once and then twice over
in each face, export through `export_png.ps1`, and take the difference of
the two ink extents - which is the pen advance exactly, because the first
glyph's left side bearing and the last glyph's right side bearing appear in
both and cancel. Against PIL's `getlength` for the same string, that ratio
came out within a percent of 1 at 24 pt for every face measured, which is
worth knowing: 1.12 is not "PowerPoint sets ten percent looser", it is
headroom, and most of what it covers is PIL loading a face at an integer
pixel size (10 pt is measured at 13 px, not 13.33, and comes out two to five
percent narrow).

Wrapping is a greedy simulator that measures **every word at its own weight**.
Measuring a mixed-weight string as a single weight under-counts lines.

Vertical centring is measure-then-place: compute the block height from the
measured parts, then derive the top. The only autoshrink in the kit is an
explicit short ladder of candidate sizes in `flow_pills`.

## The warning register is a gate, not a report

Every fit check appends to a `WarnRegister`, tagged `OVERFLOW`, `WRAP` or
`HEIGHT`, deduplicated and sorted on output - the same overflow fires once per
cell, and an undeduplicated dump is unreadable.

**A clean build prints `no warnings` and exits zero; a dirty one exits
non-zero.** In the source engagement this was a *reported* gate: the builders
printed the line and the task reports cited it, but nothing ever exited
non-zero. Here `WarnRegister.exit_if_dirty()` makes it real.

Check both dimensions, twice over. A pill wider than its cell wraps onto a row
of its own and still fits vertically, so a height-only check reports a clean
build while the text runs past the cell edge - `flow_pills` checks width
separately, and the source repository did not. The ladder itself also has to
consider width: stepping down on height alone leaves a pill drawn at a size
that does not fit horizontally when the next rung would have fitted, which is
a build failure with its own fix one rung away.

Warnings are tagged by what went wrong: `OVERFLOW` for width, `HEIGHT` for a
stack that does not fit, `WRAP` for copy that takes more lines than the design
budgeted. Name the cell in the message - the register is a set, so two cells
overflowing by the same amount otherwise collapse into one entry.

## The raster boundary

PNG is allowed in exactly two places:

- **conic fills**, because DrawingML has no angular gradient - the maturity
  balls and partial-state status marks, pre-rendered with Pillow;
- **multi-path stroked icons**, for the same reason.

Everything else stays native. Linear gradients are `a:gradFill` XML written on
the shape by `deck_kit.xmlfill.grad`. Curves, rails and connectors go through
`deck_kit.paths`, which parses the SVG `d` attribute from the draft and hands
the points to python-pptx's own `shapes.build_freeform(..., scale=EMU)` so the
whole path stays in CSS pixels.

`grad` takes 3-tuple stops carrying alpha and a **required** angle. The
engagement had two arities, two parameter names and two different defaults, 0
and 90, so merging the copies by name silently rotated gradients.

## The vocabulary

| Layer | Where | Examples |
|---|---|---|
| primitives | `deck_kit.primitives` | `rrect`, `oval`, `rule`, `textbox`, `settext`, `add_para`, `chip`, `numcircle`, `tri`, `icon`, `ball`, `lockup`, `footer` |
| fills | `deck_kit.xmlfill` | `alpha_fill`, `grad`, `dashed` |
| paths | `deck_kit.paths` | `bezier_points`, `polyline`, `arrow_head` |
| components | `deck_kit.components` | `Pill`, `PillStyle`, `pill_w`, `draw_pill`, `flow_pills`, `matrix_frame`, `explain_box`, `loop_line` |
| slide furniture | `brands/<name>/style.py` | `header`, `footer`, the palette, the type scale, the grid, the tracking |

**Which of them land in `assert_native.py --autoshapes`:** `rrect`, `rule`,
`oval`, `chip`, `numcircle` and `tri` are auto-shapes and are counted;
`textbox` is a text box and is not; `icon` and `ball` place pictures,
counted by `--min-pictures` / `--max-pictures`; `polyline` and `arrow_head`
are freeforms, counted by `--min-freeforms`. Two are compound: `lockup` is
two pictures **and** the hairline between them, and `footer` is one rule and
two text boxes. `rule` is the
one that surprises people, because it is an `rrect`: every 1 px hairline and
every 3 px accent rule is an auto-shape, and on a Relay deck the hairlines
can be most of the count. That is what makes an exact `--autoshapes N`
strict rather than arbitrary, and it is why the number is derived in the
builder's docstring before the deck is built.

A brand is free to draw with `primitives` alone. `components` is a
vocabulary, not a contract: several of its functions assume a gradient band,
which came from the fixture brand the repository used to carry rather than
from the kit itself. `brands/relay` is square by rule - radius 0 for a
surface, 2 for a control - and forbids gradients outright, so
`examples/ai-horizon/build_ai_horizon.py` carries a local `Draw` class, one
method per class in `brands/relay/slide.css`, and draws nine of its ten
slides with it. That is a legitimate shape for a builder; what is not
legitimate is putting the radius into the core - which is why the radius is
a parameter now: `draw_pill(rad=)`, `flow_pills(rad=)` and
`matrix_frame(cell_rad=)` default to the kit's 7 and 8, and that deck's S09
passes the brand's `RAD_CONTROL` and `RAD_SURFACE`. `accent=` and `icon_key=`
came out of the core the same way.

`settext` writes **only the first paragraph**; `add_para` appends the rest.
That is deliberate and is why both exist.

One example call, from `examples/ai-horizon/build_ai_horizon.py`'s
`readiness()`:

```python
cells = matrix_frame(slide, top=182, row_h=86, cols=RD_COLS, rows=RD_ROWS,
                     geom=style.GEOM, style=style, font=style.SANS,
                     icon_dir=brand.icon_dir, empty={(0, 2)},
                     accent=style.NAVY, cell_rad=style.RAD_SURFACE)
flow_pills(slide, cells[(0, 0)], pills, metrics, style.SANS, warn,
           ladder=(style.T_PILL, 9.5, 9.0), rad=style.RAD_CONTROL)
```

## The builder docstring

Each builder opens with a docstring naming the source HTML file, recording the
deliberate deltas from it, stating the geometry and type contract, and giving
the literal command that runs it. That docstring is what makes a builder
readable a month later. Every builder in `examples/` carries one.
