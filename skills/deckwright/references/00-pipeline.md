# The pipeline, end to end

Four stages and a QA loop, all three phases of this repository in: Phase 1
built stages 2 and 3 and the parts of the loop a greenfield deck needs, Phase
2 built stage 4, and Phase 3 built stage 1's templates, the speaker notes and
the teleprompter, and the rest of the QA loop.

## Stage 1 - idea to binding spec

Before any pixel exists, a spec fixes what may be said: verified facts each
carried with its source, non-negotiable editorial rules, the audience and the
time budget, and a slide-by-slide table whose rows carry a technical route -
**A** clone an approved slide and retext it, **B** design in HTML then port
natively, **C** extract from an existing deck and reframe. Its front matter
also records the four intake answers - the design system, whether the HTML
draft is on, the notes mode, and the **Output:** the deck ships as (`html`,
`pptx` or `both`) - asked before any deck is started
(`SKILL.md`, "Before any route: the intake").

**The design system is the input, always.** No stage adopts a corporate
`.pptx` master as the identity. The intake's first question offers a design
system the user points at, one `scripts/discover.py` found, or the default
`brands/relay`, and stage 3's template is **generated** from whichever was
chosen - `scripts/inspect_template.py` verifies what was generated rather
than admitting somebody else's file. A real corporate master arrives with
unnamed slide masters and a hundred layouts repeated across them, and the
template contract's one rule is by name, never by index.

Speaker notes belong to this
stage too, and they are opt-in: the default is none, and the spec's
`**Notes:**` line picks one of `pptx` (the PPTX notes pane), `teleprompter`
(an HTML page) or `both`, all from one `Note` per slide position in the same
run (`src/deck_kit/notes.py`, `templates/teleprompter.html`; the builders'
`--notes` flag, `01-spec-stage.md`).

`templates/spec.md` is the skeleton and `examples/walkthrough/spec.md` is it
filled in for a deck this repository actually builds. See
`01-spec-stage.md` for what each section is for, the route vocabulary, how
the spec's `Exact string` column becomes a check the gate runs, and the
governance loop this repository keeps rather than duplicates.

## Stage 2 - spec to HTML draft

One file per slide on a fixed 1280x720 canvas, served and screenshotted so the
layout can be argued about before any Python is written. The draft is on by
default for every route-B slide, because it is what makes a deck visually
rich; a spec that skips it says why on its `**HTML draft:**` line. It is
drawn against the design system the intake chose - `brands/relay`, the
default, when the user has none of their own - through the brand's
`tokens.css`. The draft is disposable: once approved, the builder becomes
the source of truth. This stage also owns the icon pipeline, because the
builders consume rasterised icons rather than SVG. See `02-html-stage.md`.

**When `Output: html`, this stage is the last one.** The drafts stop being
disposable sketches and become the deliverable:
`scripts/build_html_deck.py --drafts <dir> --out <dir>` writes one
navigable, printable stage page carrying every slide in order, and the deck
is shipped as that page or printed from it to PDF. Stage 3 and stage 4 do
not run, and neither Windows nor PowerPoint is needed anywhere. See
`02-html-stage.md` for the page and `05-qa.md#the-html-deck` for its QA.

## Stage 3 - HTML to native PPTX

**Skipped when `Output: html`.** A template deck is opened and its slides
purged, so generated slides inherit
its master, layout and background. Geometry transfers 1:1; typography does
not. Nothing relies on PowerPoint to fit text. See `03-pptx-stage.md`.

## Stage 4 - integration into a deck edited by hand

The author edits the PPTX between versions, so a generated deck is never the
deliverable and the author's file is never overwritten. `scripts/new_version.py`
drives a numbered, resumable pipeline - copy the author's file, assert it is
the file the build was written against, patch text in place through
character-level run attribution, delete the positions being replaced,
transplant generated slides by OOXML surgery, renumber pages, re-embed
fonts - with every step written to disk as `stepN_<name>.pptx` and the last
two stages running as separate subprocesses so a crash inside zip surgery
cannot corrupt an in-memory `Presentation`. See `04-integration.md`.

## The QA loop

Three kinds of check, kept distinct:

| Check | Tool | Phase |
|---|---|---|
| File integrity - open twice, repair prompt is a failure | `scripts/check_pptx.ps1` | 1 |
| Editable shapes, not a picture of a deck | `scripts/assert_native.py` | 1 |
| Rendered review | `scripts/export_png.ps1` | 1 |
| Visual composition - crop the same strip across every slide | `scripts/compose_qa.py` | 3 |
| Content lint - typos, internal codes, required boilerplate, verbatim figures | `scripts/lint_deck.py` | 3 |
| Text dump and diff against the author's last version | `scripts/dump_text.py` plus `scripts/diff_package.py` | 2 |
| Shape ids for a text map, walked through groups | `scripts/inspect_shapes.py` | 2 |
| Round trip - transplant, retext, renumber, re-embed, doubled COM | `examples/integration/version.py`, via `scripts/gate.ps1` | 2 |
| The HTML deck - stage page, lint on drafts, captures, composition | `scripts/build_html_deck.py`, `scripts/lint_deck.py --deck <drafts dir>`, `scripts/capture_drafts.py` | 3 |

Everything the gate runs is in `scripts/gate.ps1`, which is the single entry
point: `powershell -NoProfile -File scripts/gate.ps1`.

## Platform matrix

| Stage | Needs | Portable |
|---|---|---|
| 1, spec and governance | an editor | yes |
| 2, HTML draft and icons | a static server and a browser | yes |
| 2b, the HTML deck (`Output: html`) | Python alone; a browser to look at it or print it | yes |
| 3, native build | Python, `python-pptx`, `Pillow`, TrueType files | yes |
| 4, integration | same as stage 3 | yes |
| QA, file integrity and PNG export | **Windows with PowerPoint, through COM** | no |
| QA, visual composition of a PPTX | Python and `Pillow` - but its input is the COM export | no, in practice |
| QA, capturing the drafts | Python, `Pillow`, and **a browser: Python Playwright or any Chromium-family binary** | yes, and required rather than optional |
| QA, composition of an HTML deck | Python and `Pillow`, on the captures above | yes |
| QA, content lint (a package or a drafts directory) | Python | yes |

`scripts/doctor.py` reports each of those as REQUIRED or OPTIONAL on the
machine it is run on, with the consequence of anything missing. `SKILL.md`'s
intake runs it at step 0.

Without Windows and PowerPoint you lose rendered PNG review, the repeated-open
integrity check and the hidden-slide report. Composition is portable code with
a non-portable input: `compose_qa.py` needs only `Pillow`, but the `sNN.png`
files it composes come from `export_png.ps1`. Everything else runs anywhere;
`05-qa.md` says what still runs, in full.

**An `Output: html` deck needs no Windows and no PowerPoint at all.** Every
row it touches is portable: the spec, the drafts, the stage page, the lint.
Its captures come from `capture_drafts.py` rather than from COM, so even
composition crosses the line. That is the whole reason the output is a
question the intake asks: a user who wants only the HTML deck should not
need a Windows machine to get one.

**What it does need is a browser, and that is not negotiable.** The capture
row is REQUIRED, not optional: an agent that cannot screenshot its drafts
cannot judge them, and a deck whose layouts nobody looked at is exactly what
the draft stage exists to prevent. `capture_drafts.py` therefore tries
Python Playwright, then every Chromium-family binary it can find, and then
fails with `CAPTURE UNAVAILABLE` and three remedies - it does not print a
skip and let the gate stay green, which is what it used to do. Pinned by
`tests/test_capture_drafts.py::test_no_route_at_all_fails_loudly_and_says_what_to_do`.

## Running anything

```
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python <script>
```

`PYTHONIOENCODING` is not decoration: builders print non-ASCII and the Windows
console encoding will otherwise raise mid-report. The `--no-project` form is
explained in `docs/decisions.md`.
