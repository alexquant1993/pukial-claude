# Builder docstring skeleton

Every builder script - anything that opens a template and draws a slide, or
runs one stage of the integration pipeline - opens with a docstring that
makes it readable a month later without opening the HTML draft it came from
or rerunning it to see what it does. That docstring is the entire mechanism;
there is no other place this information lives.

A builder's opening docstring names:

1. **The source HTML file it was ported from** (stage 3 builders) or **what
   it exists to exercise** (stage 4 step wrappers, which have no HTML
   source).
2. **The deliberate deltas from that source** - what changed on the way from
   the draft to the native build, and why, so a reader comparing the two
   does not mistake an intentional change for drift.
3. **The geometry and type contract it works under** - 1 CSS pixel is 9525
   EMU, type is re-derived through the brand's scale rather than mapped
   px-to-pt, that kind of statement, when it is not already obvious from
   what the builder imports.
4. **The literal command that runs it**, exactly as typed, including
   `PYTHONIOENCODING=utf-8` and the full `uv run` invocation with every
   `--with` flag it needs. Not "run it like the other builders" - the exact
   line, because that is what someone actually pastes into a terminal.

## Skeleton

```python
"""<One line: what this builder produces.>

Ported from <source>.html. <What the source is, if not obvious.>

Deltas from the draft: <what changed on the way to native shapes, and why -
or "none" if the port is faithful.>

Run: PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx \
       --with pillow python <path/to/this_builder.py> \
       --template out/template.pptx --out out/<name>.pptx
"""
```

For a stage-4 integration script with no HTML source - a version driver or an
out-of-process step wrapper - the first two sections become what the script
exists to prove or exercise, in place of a source file and a delta list. The
command line and the geometry/type note still apply wherever they are not
vacuous.

## Worked examples, from the builders that carry this pattern today

**`examples/ai-horizon/build_ai_horizon.py`** - a stage-3 builder ported
from ten HTML drafts, with a stated delta list and a shape-arithmetic block
`check()` re-derives against the saved package:

> Ten slides on `brands/relay`, ported from the ten HTML drafts in
> `examples/ai-horizon/drafts/` (route B for every slide), which were
> authored FIRST [...] Geometry transfers 1:1 from those files: every
> coordinate below is the number the draft carries inline.
>
> Deltas from the drafts: none of substance. Two things the drafts express
> differently because CSS can and DrawingML cannot [...]

**`examples/kit-furniture/build_furniture.py`** - a stage-3 builder whose
docstring states *why the slide exists*, not only what it draws, because its
whole purpose is coverage the other example does not reach:

> Covers `footer()` and `lockup()`, the conic raster path (the maturity
> balls, and with them the content-keyed asset cache), a native linear
> gradient, and a freeform curve with an arrowhead.
>
> The AI horizon deck draws its own bottom furniture and has no curves and
> no conic fill, so without this slide three pieces of the kit would ship
> untested.

**`examples/integration/build_host.py`** and **`build_donor.py`** - stage-4
builders with no single HTML source; their opening section states what
synthetic condition each slide plants and why the round trip needs it,
which is the equivalent of "deltas from the draft" when there is no draft:

> It carries, deliberately, everything Phase 2 has to survive: a paragraph
> split into three runs with the middle one bold [...]; all three
> page-number marker flavours across three slides; a slide with no marker at
> all, as a machine-built slide arrives; an animation targeting one shape,
> so the deletion guard has something to guard.

**`examples/integration/version.py`** - the driver itself, not a slide
builder, but the same discipline applies: its docstring states what it is
(`"This is the gate: it is the whole of stage 4 run end to end..."`) and
carries the exact command line before a single import.

## What this is not

This is not a template for the module-level docstrings inside
`src/deck_kit/` - those document a mechanism (a function, a module), not a
build. It applies to anything that is *run* to produce a `.pptx`, or to run
one out-of-process stage of the integration pipeline.
