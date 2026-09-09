# deckwright

A portable pipeline for taking a consulting deck from an idea to a native,
editable PowerPoint file: the spec discipline that fixes content before
design, the HTML stage used to iterate on layout, the measurement-driven
Python builders that reproduce that layout as real PPTX shapes, and the QA
loop that proves the result opens cleanly.

The output is **real shapes**, not a screenshot of a browser. Anyone can open
the deck and edit the text.

**It always starts from a design system.** The intake's first question offers
a design system you point at, one `scripts/discover.py` found on your
machine, or the default `brands/relay`. There is no route that adopts a
corporate `.pptx` master as the identity: the template is *generated* from
the design system and `scripts/inspect_template.py` verifies what was
generated. A real corporate master arrives with unnamed slide masters and a
hundred layouts, and the template contract's one rule is by name, never by
index.

**The PowerPoint file is optional.** The spec's `**Output:**` line says
`html`, `pptx` or `both` (the default). `html` stops after the HTML stage:
`scripts/build_html_deck.py` turns the drafts into one navigable, printable
stage page, which is the deliverable and prints to PDF from the browser. That
route needs no Windows and no PowerPoint at any point.

**Brand packages live in `brands/`, or wherever `DECKWRIGHT_BRANDS` points.**
Every script and the library itself read that variable, and it is how an
employer's brand is kept outside this repository - which the provenance rule
below makes the normal case.

## The gate

```
powershell -NoProfile -File scripts/gate.ps1
```

All three phases are in, and one gate runs everything they promise: the unit
tests, then the four files that pin the safety checks (`test_fonts.py`,
`test_new_version.py`, `test_deck.py`, `test_textedit.py`) again under
`python -O` so those checks are proved to survive it, the template generator
and its contract verifier, the kit-furniture
builder, the native-shape assertion, two consecutive PowerPoint opens per
deck, and a PNG export - then the Phase 2 round trip: generate a second
master from the same brand's contract (`make_template.py --variant donor`),
put it through the contract verifier and the doubled open as well, build a
synthetic host on one master and a synthetic donor on the other, transplant
slides from the donor into the host with one hidden, retext a paragraph with
mixed bold through the
run-attribution path and verify the bold survives, renumber all three
page-number marker flavours, re-embed fonts, and check every intermediate
`stepN_*.pptx` plus the final file with the doubled COM open - then the Phase
3 walkthrough: build a two-slide deck with speaker notes written into both
the PPTX and the teleprompter, lint it against its own spec with all eight
checks running, dump its text, export its PNGs, and compose a footer band and
a page-marker zoom whose content is asserted row by row - then the AI horizon
deck: ten slides in `brands/relay`, by way of `examples/ai-horizon/run.ps1`,
which generates that brand's template and puts it through the contract
verifier and the doubled open before building on it, then runs the same loop
- build with notes, exact shape counts, eight lint checks, an exact text
dump, the doubled open again, the export, and three composed strips asserted
row by row - and finally the same deck as an **HTML deliverable**, by way of
`examples/ai-horizon/run_html.ps1`: the ten drafts built into one stage page,
asserted to carry ten slides, no external resource and a print rule; the
drafts directory linted with seven of the eight checks, `notes_only` skipped
with a reason because drafts carry no notes; then ten captures - taken by
whatever Chromium-family browser the machine holds, since an offline `uv`
cannot fetch Playwright - and their composed strips, asserted row by row
like the PPTX deck's. Nothing there is allowed to skip: an agent that cannot
screenshot its drafts cannot judge them, so a machine with no browser at all
fails that step rather than passing it quietly. `python scripts/doctor.py`
says which requirements this machine has before a deck is started.
Every step runs on `brands/relay`, which is the repository's only brand.
It runs on committed inputs, so anyone can re-run it. It needs no network:
the brand's six type faces are fetched once, by hand, and committed.

The gate fails, deliberately, if any build reports a single overflow warning.

## Map

```
SKILL.md             the router: five task routes into the references
references/          the know-how
  00-pipeline.md       the four stages, the QA loop, the platform matrix
  01-spec-stage.md     stage 1: what a spec fixes, the route vocabulary,
                       exact figures, the governance loop, speaker notes
  02-html-stage.md     the 1280x720 draft, serving, capture, the icon pipeline
  03-pptx-stage.md     the template contract, geometry vs typography,
                       measurement, the raster boundary, the vocabulary
  04-integration.md    stage 4: versioned builds, run attribution, the text
                       map, the transplant, page numbers, fonts
  05-qa.md             the QA loop: integrity, PNG export, composition,
                       content lint, the text dump, what needs Windows
  06-gotchas.md        the failure catalogue, Symptom/Cause/Fix/Pinned by
src/deck_kit/        the library - holds no colour values and no brand knowledge
  notes.py             speaker notes: the model, the PPTX writer, the
                       teleprompter emitter
brands/relay/        THE ONLY BRAND, and the default design system. A real
                     system adopted: Relay's ink/signal palette, its 1.26 type
                     scale scaled from 1920x1080, its radius and rule scale,
                     its tracking, its three type families, its wordmark and
                     its Lucide icons. Every example, every test and every
                     gate step builds on it
  fonts.toml           the six faces it declares, each with a URL, a pinned
                       sha256 and a licence; scripts/fetch_fonts.py reads it
                     The two synthetic fixture brands that used to sit beside
                     it, brands/example and brands/example2, were deleted on
                     2026-09-09. The one thing only they could do - give the
                     Phase 2 transplant two DIFFERENT slide masters - is now
                     make_template.py --variant, which builds a second master
                     from this brand's own contract
scripts/             generators, verifiers, QA tools, the gate
  doctor.py            the intake's step 0: python-pptx, Pillow and a browser
                       REQUIRED, PowerPoint OPTIONAL, with the consequence
                       and the remedy for anything missing
  discover.py          the intake's first question: takes --design-system PATH,
                       lists brand packages, the design systems on disk
                       (outermost match, never a kit nested inside one),
                       candidate masters as grouped inventory and every
                       tokens.css, says which declared faces are missing on
                       disk, and prints one recommendation first and last
  fetch_fonts.py       fetch a brand's declared faces, OFL only, hash-pinned
  build_html_deck.py   the HTML deliverable: a drafts directory becomes one
                       navigable, printable, self-contained stage page
  capture_drafts.py    one sNN.png per draft, at the size the PPTX export
                       writes, so composition QA runs on an HTML deck too.
                       Playwright, then any Chromium-family binary, then a
                       loud failure - never a quiet skip
  lint_deck.py         content lint: eight TOML-driven checks over a deck -
                       a .pptx, or a directory of drafts
  compose_qa.py        visual QA: band, zoom and ink over the exported PNGs
examples/            one real deck, plus the gate's coverage of the kit and
                     of Phase 2. All of it builds on brands/relay
  integration/         build_host.py, build_donor.py, version.py - the
                       versioned build driver run end to end. The host is on
                       the brand's master and the donor on its donor variant
  kit-furniture/       the kit's freeforms, gradients and rasters. Deliberately
                       off-brand: it draws a gradient and spends five signal
                       labels, both of which Relay's own rules forbid, because
                       what it proves is the kit and not a Relay slide
  walkthrough/         one two-slide deck through every Phase 3 tool: the
                       filled spec, ledger, handoff, notes and lint rules
  ai-horizon/          THE REAL DECK: ten slides in brands/relay, drafted in
                       HTML first and then ported - an inverse cover, oversized
                       numerals, a year rail, a hairline table and no gradient
                       anywhere; run.ps1 is its spec section 6. Its S09 is the
                       kit's own matrix, pills and legend, which used to live
                       in a second example directory, examples/capability-matrix,
                       deleted on 2026-09-09 because that coverage was the only
                       reason it existed. run_html.ps1 is the same deck as an
                       HTML deliverable: the stage page, the lint on the
                       drafts directory, the captures and the composition
templates/           the icon sheet, the builder-docstring skeleton
  spec.md              the binding spec skeleton, stage 1
  lint.toml            the content-lint rules skeleton, every table annotated
  handoff.md           the session handoff skeleton, section 0 filled in
  teleprompter.html    the speaker-notes page the emitter fills
evals/               how the skill itself is tested, in skill-creator's own
                     schemas. evals.json is four task cases with the
                     expectations a grader checks; trigger-eval.json is
                     twenty queries, half of which must NOT load this skill,
                     for measuring the front-matter description
docs/decisions.md    the reconciliation ledger: every ruling the references
                     cite, with its cost if wrong. The design spec, the
                     implementation plans, the session handoffs and the skill
                     audits that produced this repository are internal
                     history and are not shipped with it.
tests/
```

## Requirements

Python 3.11+, `python-pptx`, `Pillow`. The build and the tests are
cross-platform; the integrity check and the PNG export need Windows with
PowerPoint, driven through COM. `references/00-pipeline.md` has the full
platform matrix and says what is lost without it. An **`Output: html`** deck
needs none of that: Python alone builds and lints it, and a browser looks at
it and prints it.

```
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python <script>
```

## Starting a new deck

0. Run `python scripts/doctor.py` and fix anything it calls REQUIRED - a
   missing browser costs a deck its whole draft review. Then run
   `python scripts/discover.py` (add `--design-system PATH` if you know
   which one) and answer the four intake questions (`SKILL.md`, "Before any
   route: the intake"): which design system, whether to draft in HTML,
   whether the deck carries speaker notes, and what it ships as - `html`,
   `pptx` or `both`. The answers go into the spec's front matter.
1. With no design system of your own, build on `brands/relay`, the default
   and currently the only brand in the repository.
   With one, copy `brands/relay/` to `brands/<yours>/` - or to a directory
   outside this repository with `DECKWRIGHT_BRANDS` pointing at its parent,
   which is what an employer's brand needs - and change the numbers.
   `brands/relay/` is itself the worked example, derived from a downloaded
   system that had no `brand.py`, no `tokens.css` and no master;
   `references/02-html-stage.md` says what it took. Declare your faces in
   `fonts.toml` and run
   `python scripts/fetch_fonts.py --brand <yours>` before measuring anything -
   OFL faces are fetched and committed, proprietary ones are named in
   `brand.py` and never copied in. Generate the template with
   `make_template.py` and verify it with `inspect_template.py`; do not try to
   adopt an existing corporate master, which the pipeline has no route for.
2. Draft the slide as one 1280x720 HTML file; this is the default, and the
   spec records the reason when it is skipped. Serve it with
   `scripts/preview.py serve` from a root high enough that its `@import`
   resolves. Then capture every draft with `scripts/capture_drafts.py` and
   **look at the pictures**; that is what the draft is for.
3. If the output is `html`, build the stage page with
   `scripts/build_html_deck.py --drafts <dir> --out <dir>` and ship that -
   there is no step 4. Otherwise port the draft to a builder; geometry
   transfers 1:1, type does not. `both` does the two.
4. Run the gate.

## Provenance

Extracted as method from a consulting engagement. No client content and no
employer brand asset is present. `brands/relay/`'s wordmark is a placeholder
drawn by `scripts/make_placeholder_logos.py`, because Relay's own system
supplied no mark and drew none; its six type faces are all under the SIL Open
Font License 1.1 and each ships its licence text in `brands/relay/fonts/`.
The two synthetic fixture brands that carried the repository's other
placeholder marks were deleted on 2026-09-09.

`brands/relay/` was derived from a downloaded design system. **That system is
not in this repository** - it was a third-party download, and what is
committed is the derivation, not the input. Files that name
`brands/relay_design_system/` are citing where a number came from, not a path
you will find here.
