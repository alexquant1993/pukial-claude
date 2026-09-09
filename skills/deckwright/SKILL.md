---
name: deckwright
description: Turn an idea into a slide deck: a binding spec, HTML drafts drawn on a design system, then a native, editable PowerPoint file - or ship the HTML deck itself and print it to PDF - with a QA loop that proves the deliverable says what the spec said. Use this skill whenever someone wants a deck, slides, a presentation, a PPTX or an HTML deck built, rebuilt, restyled or checked: building slides on a company or client design system or brand, drafting a slide in HTML before any Python, retexting an approved deck without breaking its formatting, transplanting generated slides into a file a human keeps editing by hand, adding speaker notes or a teleprompter, diagnosing a deck PowerPoint wants to repair, or running lint, visual and file-integrity QA before it goes to a client. Use it even when the request is only "make me some slides" and names no tool or format. Not for merely reading a deck somebody sent: summarising or extracting from a .pptx needs no skill.
---

# deckwright

One body of documentation, routed by task. Each route names what it needs
up front and the reference sections it crosses. Read `README.md` for the
map and `references/00-pipeline.md` for the whole pipeline end to end.

**Every `python <script>` in this file is shorthand** for the invocation
`README.md` requires, which is the only one that resolves this repository's
dependencies:

```
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python <script>
```

Copy-pasting a bare `python scripts/...` fails on a machine without those
packages in the ambient interpreter, which is most machines.

**Brand packages live in `brands/`, or wherever `DECKWRIGHT_BRANDS` points.**
Everything reads that variable - `discover.py`, `fetch_fonts.py`,
`make_template.py`, `lint_deck.py` and the library itself - and it is how an
employer's brand is kept **outside** this repository, which the provenance
rule in `README.md` makes the normal case rather than the exception.

## Requirements

Four things, and the third is the one people assume is optional:

| Requirement | Level | Without it |
|---|---|---|
| Python with `python-pptx` | **required** | nothing builds a `.pptx`, so `Output: pptx` and `both` are unreachable |
| Python with `Pillow` | **required** | the builder cannot measure text, `compose_qa.py` cannot crop, and a capture's size cannot be verified |
| A browser `scripts/capture_drafts.py` can drive: Python Playwright, or **any** Chromium-family binary - the one the Playwright MCP server leaves under `%LOCALAPPDATA%\ms-playwright` counts, and `DECKWRIGHT_BROWSER` points at one anywhere | **required** | **this agent cannot see its own drafts.** The layout goes unreviewed and the quality of the deck falls |
| Windows with PowerPoint, reached through COM | optional | no doubled-open integrity check and no PNG export, so a `pptx` deliverable ships unverified. An `Output: html` deck needs none of it ([the platform matrix](references/00-pipeline.md#platform-matrix)) |

**Seeing the drafts is a requirement of this skill, not a nicety.** An agent
that cannot screenshot a draft cannot judge it, and a deck whose layouts
nobody looked at is the failure this whole stage exists to prevent. A
capture that cannot happen is a hard stop, not a skipped step.

`python scripts/doctor.py` checks all four and prints one line each -
`REQUIRED`/`OPTIONAL`, present or missing, and for anything missing the
consequence and the remedy. It exits non-zero when a REQUIRED item is
missing.

## Before any route: the intake

**Step 0, before question 1: run `python scripts/doctor.py`.** If it exits
non-zero, stop and show the user its output: the missing item is cheaper to
fix now than after a spec is agreed and ten drafts are written.

**This pipeline always starts from a design system and HTML examples.** There
is no route that adopts somebody's corporate `.pptx` master as the identity:
a real one arrives with four unnamed slide masters and a hundred layouts, and
the template contract's one rule is by name, never by index. A template is
**generated** from the design system (`scripts/make_template.py`) and
`scripts/inspect_template.py` verifies what was generated.

Four questions, asked before any deck is started, one question per message
in prose (working-agreement rule 4, `templates/handoff.md` section 0), each
answer recorded on its own line of the spec's front matter, after
**Status:** and in this order. Never assume an answer.

1. **Design system.** Run `python scripts/discover.py` (`--root PATH`,
   `--brands PATH`, `--design-system PATH`, `--json`). It prints one
   recommendation line **first and last**, and between them: the design
   system the user pointed at, the brand packages under the brands dir, the
   design systems on disk that no brand package has been built from, the
   candidate masters as inventory, and every `tokens.css`. A downloaded
   system rarely arrives in this repository's shape - one had a `tokens/`
   directory rather than a `tokens.css`, the next a `colors_and_type.css`
   beside a README - so the report names what each one holds and prefers the
   outermost match, never a sample kit nested inside a system.

   The answer is one of three: **a design system the user points at**, given
   as a path (`--design-system PATH`, which the report verifies and
   recommends); **one discovery found**, which the "Set up a brand" route
   turns into a brand package; or **the default, `brands/relay`**, when they
   have none of their own. A brand package that already exists is the same
   answer arrived at earlier. Recorded as
   `**Design system:** <path to a design system | brand name | brand name @ path outside the repository | default (brands/relay)>`.

   A design system of the user's own outranks `brands/relay` in the
   recommendation: "the repository ships one brand" is not a fact about the
   user's identity. `brands/relay` is the only brand package in this
   repository, so on this tree with nothing else found the report says
   "use brand relay".

   The report also names, per brand, every face the brand's `fonts.toml`
   declares that is not in `brands/<name>/fonts/`. **Fetch them before
   measuring anything**: `python scripts/fetch_fonts.py --brand <name>`. A
   builder measures against the file on disk, so a missing face fails the
   build mid-deck, after the template is already written - and the older
   answer, substituting whatever face the repository already had, is how a
   brand ends up arguing in a README for type it never wanted. OFL faces
   only; a proprietary face is pointed at in `brand.py` and never fetched.
2. **HTML draft.** On by default for every slide being designed rather than
   retexted - route B in the spec's slide table
   ([the route vocabulary](references/01-spec-stage.md#the-route-vocabulary)) -
   because the draft is what makes a deck visually rich
   ([the HTML stage](references/02-html-stage.md)). `templates/slide.html`
   and `templates/slide.css` are the skeleton a draft starts from. The user
   may opt out; then the spec says why. **Opting out also decides question
   4:** the stage page is built out of the drafts, so a deck with no drafts
   can only ship as `pptx`. If they lean towards an HTML deliverable, say
   that here rather than discovering it two questions later. Recorded as
   `**HTML draft:** <yes | skipped: reason>`.
3. **Speaker notes.** Off by default. Ask whether they want notes in the
   PPTX notes pane, a teleprompter HTML page, both, or neither. The builders
   take `--notes {none,pptx,teleprompter,both}` (default `none`) and
   `--teleprompter PATH` only when the mode includes the teleprompter; the
   library entry point is `deck_kit.notes.emit_notes` ([speaker notes and the
   teleprompter](references/01-spec-stage.md#speaker-notes-and-the-teleprompter)).
   Recorded as `**Notes:** <none | pptx | teleprompter | both>`.
4. **Output.** The PPTX is optional. Offer all three explicitly: `html` -
   the drafts become the deck, built into one navigable, printable stage
   page by `scripts/build_html_deck.py` and shipped as that
   ([the HTML stage](references/02-html-stage.md)); `pptx` - the native,
   editable PowerPoint file and no HTML deliverable; or `both`, which is the
   default and what a deck that has to be handed over and then edited by
   hand needs. `html` needs no Windows and no PowerPoint at all
   ([the platform matrix](references/00-pipeline.md#platform-matrix)). Both `html` and `both` are
   built from question 2's drafts, so a spec that skipped the draft has only
   `pptx` left - which is why `examples/walkthrough/spec.md` says `pptx` and
   `examples/ai-horizon/spec.md` says `both`. Recorded as
   `**Output:** <html | pptx | both>`.

## Build a new slide

**Needs:** Python, `python-pptx`, `Pillow`, the brand's TrueType files, and a browser for the draft. `Output: html` needs neither `python-pptx` nor a template - Python and a browser are the whole of it.

1. Fix the content first: [the spec](references/01-spec-stage.md#what-a-spec-fixes-before-any-pixel-exists). Copy `templates/spec.md`, put the four intake answers in its front matter, and give every slide being designed from scratch route **B** in the slide table.
2. Draft on the 1280x720 canvas, by default: [the HTML stage](references/02-html-stage.md). `templates/slide.html` is the skeleton; serve it with `python scripts/preview.py serve --root .` from a root high enough that its `@import` resolves, which is the repository root and not the draft's own directory. Only a spec whose front matter says `HTML draft: skipped: <reason>` goes straight to step 4 - with no drafts there is nothing for step 3 to build, which is why such a spec's `Output:` can only be `pptx`.

   **Capture every draft and look at it** - `python scripts/capture_drafts.py --drafts <dir> --out <dir> --root . --expect N`, then open the PNGs ([capturing](references/02-html-stage.md#capturing)). A draft nobody looked at is a layout that only reads right in the author's head. If the capture is unavailable, **stop**: show the user `scripts/doctor.py`'s message, ask them to fix one of the three remedies, and keep trying the remaining routes meanwhile - a different browser path through `DECKWRIGHT_BROWSER`, the harness's own MCP browser tools if it has any, the user installing Playwright. Never skip the look and go on to step 4, and never present a deck whose drafts nobody looked at as finished. **A capture that fell back to a route other than Python Playwright is a ruling for the spec's ledger** - cost if wrong: the drafts were judged through a different renderer than the reference one; `capture_drafts.py` prints the line to record.
3. **If `Output: html`, stop here and ship the stage page.** `python scripts/build_html_deck.py --drafts <dir> --out <dir> --expect-slides N` writes `<out>/index.html`; QA it as [an HTML deck](references/05-qa.md#the-html-deck) - lint the drafts directory against the deck's own rules file (`templates/lint.toml` is the skeleton, and `--expect-checks` is one lower on drafts than on a `.pptx`), capture and compose - and print it to PDF from the browser. There is no step 4 for this output. `examples/ai-horizon/run_html.ps1` is the whole loop as a script.
4. Port natively, measuring instead of autofitting: [the PPTX stage](references/03-pptx-stage.md). Open the builder with the docstring `templates/builder-docstring.md` describes, including the literal command that runs it. `Output: both` delivers the stage page from step 3 as well, from the same drafts.
5. Prove it: [native shapes, not images](references/05-qa.md#native-shapes-not-images).

## Integrate a version into the author's deck

**Needs:** Python; Windows with PowerPoint for the integrity check.

1. Read the handoff, the spec and the ledger; then [dump and diff the text](references/05-qa.md#text-dump-and-diff) before anything else.
2. [The versioned build pattern](references/04-integration.md#2-the-versioned-build-pattern), [run attribution](references/04-integration.md#4-run-attribution) or [the text map](references/04-integration.md#5-the-text-map), [the transplant](references/04-integration.md#6-the-transplant), [page numbers](references/04-integration.md#7-page-numbers), [fonts](references/04-integration.md#8-fonts).
3. [Speaker notes and the teleprompter](references/01-spec-stage.md#speaker-notes-and-the-teleprompter), generated once.
4. Every intermediate through [the doubled COM open](references/05-qa.md#file-integrity-through-com).

## Diagnose a deck that will not open

**Needs:** Windows with PowerPoint; Python for the package tools.

1. [File integrity through COM](references/05-qa.md#file-integrity-through-com) - which pass failed, and with what.
2. [The failure catalogue](references/06-gotchas.md): dangling animation targets (item 8), dropped notes and comments (item 6), a reused part name (item 9), a font list spliced in the wrong place (item 2).
3. `scripts/diff_package.py` against the last good version; `dangling_refs` from `deck_kit.merge` ([what can go wrong](references/04-integration.md#9-what-can-go-wrong)).

## Set up a brand

**Needs:** Python; the brand's TrueType files (OFL-licensed may be committed; proprietary faces are pointed at, never committed). Network access for `fetch_fonts.py`, once.

The input is a design system - a path the user gave, or one `discover.py`
found. Never a corporate `.pptx`: this route **generates** the template and
then verifies it. Put the package in `brands/<name>/`, or outside this
repository and point `DECKWRIGHT_BRANDS` at its parent, which is what an
employer's brand needs.

1. **Get the faces first.** Declare each one in `brands/<name>/fonts.toml` - family, role (`display` | `sans` | `mono`), weight, filename, URL, licence - and run `python scripts/fetch_fonts.py --brand <name>`. It prints the sha256 of each download; paste those into the manifest and re-run, and every run after that verifies. OFL only: a proprietary face is named in `brand.py` and never copied in. Nothing below can be calibrated until the files are there.
2. [The template contract](references/03-pptx-stage.md#the-template-contract) - `brand.py` by name never by index, then `make_template.py` to generate the template and `inspect_template.py` to verify what it generated, clause by clause. An empty `master_name` is refused: it binds to whichever master comes first, which is an index in a name's clothing.
3. Palette, type scale and measurement factors in `style.py` ([what the builder measures with](references/03-pptx-stage.md#no-autofit-the-builder-measures)); icons through [the icon pipeline](references/02-html-stage.md#the-icon-pipeline). The factors are **per face**: calibrate each family once against an export and record the numbers in the brand's docstring.
4. Record every binary's provenance in `assets.toml` and check it with `python scripts/lint_deck.py --brand <name>`, which runs [the `[assets]` check](references/05-qa.md#content-lint) alone - no deck and no rules file, both of which are two stages away. A fetched face appears in both manifests - `fonts.toml` says what to fetch, `assets.toml` says what is committed.

`brands/relay` is this route run on a real downloaded system, and
[what adopting Relay actually took](references/02-html-stage.md#what-adopting-relay-actually-took) is the
account: what the intake missed, how 1920x1080 geometry and a foreign type
scale were converted, which substitutions could not be closed, and what the
component vocabulary could not express.

## Run QA

**Needs:** Windows with PowerPoint for integrity and export; Python alone for lint and the text tools.

1. [Three kinds of check, kept distinct](references/05-qa.md#three-kinds-of-check-kept-distinct).
2. [File integrity](references/05-qa.md#file-integrity-through-com), [PNG export](references/05-qa.md#png-export), [visual QA by composition](references/05-qa.md#visual-qa-by-composition), [content lint](references/05-qa.md#content-lint) - whose rules file starts from `templates/lint.toml`, and whose `--expect-checks N` is what stops a check that stopped running from passing in silence.
3. An `html` deliverable gets its own loop, on the drafts rather than on a package: [the HTML deck](references/05-qa.md#the-html-deck).
4. [Without Windows](references/05-qa.md#without-windows): what is lost, and what still runs.
