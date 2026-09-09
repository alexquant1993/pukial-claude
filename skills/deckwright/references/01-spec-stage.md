# Stage 1 - idea to binding spec

The stage that decides what the deck may say, before any pixel exists. Its
output is one markdown file that later stages are checked against, not a
briefing note that gets stale the moment a builder is written.

`templates/spec.md` is the skeleton. `examples/walkthrough/spec.md` is that
skeleton filled in for a real, two-slide deck this repository builds, lints
and exports on every gate run - read the two side by side.

## What a spec fixes before any pixel exists

Before section 1, unnumbered front matter: title, date, objective in one
sentence, audience and time budget, status
(`draft | approved for build | superseded by vN`), and then the four
intake answers, in this order and with this wording:

```
**Design system:** <path to a design system | brand name | brand name @ path outside the repository | default (brands/relay)>
**HTML draft:** <yes | skipped: reason>
**Notes:** <none | pptx | teleprompter | both>
**Output:** <html | pptx | both>
```

They are asked before any deck is started, one question per message
(`SKILL.md`, "Before any route: the intake"), and never assumed: the design
system after `scripts/discover.py` has listed what the machine holds, the
draft on by default with the reason recorded when it is skipped, the notes
off by default, the output `both` by default. The time budget is what the
speaker notes are later measured against. Pinned by
`tests/test_templates.py::test_the_spec_template_and_every_filled_spec_carries_the_intake_lines`.

**The design-system line offers no corporate master.** It used to read
`path to the corporate master`, and it invited an answer nothing could act
on: this pipeline starts from a design system and HTML examples, generates
its template, and verifies what it generated. What the line does offer is
the case an employer's brand always is - a brand package kept **outside**
this repository, reached through `DECKWRIGHT_BRANDS`, written as
`acme @ C:/work/brands` so the reader knows both which brand and where it
lives. `brands/<name>` alone means a package in this repository. Pinned by
`tests/test_templates.py::test_the_design_system_line_offers_no_pptx_master_route`.

**The output line decides how far the pipeline runs.** `html` stops after
stage 2: the drafts become the deck, `scripts/build_html_deck.py` turns them
into one navigable, printable stage page, and no Windows and no PowerPoint
are involved anywhere. `pptx` is the native, editable file and no HTML
deliverable. `both` is the default, because a deck usually has to be handed
over as a file somebody can edit as well as read. Pinned by
`tests/test_templates.py::test_the_output_line_offers_html_pptx_and_both`.

Then seven numbered sections, which are `templates/spec.md`'s seven `## `
headings in its own order:

1. **Content constraints** - the non-negotiable editorial rules, each one a
   sentence a reviewer can hold a slide up against. The walkthrough's are
   "no internal tracking codes reach the deck", "no client or person names",
   "every content slide carries the copyright line and exactly one section
   kicker", "anything spoken only if asked lives in the notes". Each of the
   four maps onto a check in `examples/walkthrough/lint.toml`, which is the
   point: a constraint nobody can check is a wish.
2. **Sources** - a table of artifact and what it is the source for. A fact
   with no row here is a fact with no source.
3. **Verified facts** - the `Fact | Exact string | Source` table. "Use
   EXACTLY these strings; do not invent figures." Rows are appended, never
   edited in place, so a figure that was verified once stays verified.
4. **Slide table** - `# | Slide | Route | Source`, one row per slide,
   carrying a technical route from the vocabulary below.
5. **Content per slide** - one `### SNN <title>` block per row of the slide
   table, holding closed copy rather than an outline: the kicker, the title,
   the body and every figure, written as they will appear.
6. **Technical pipeline** - the literal commands, one per line, that turn
   this spec into a file. `examples/walkthrough/spec.md` section 6 is six
   real command lines, and the gate runs the same six.
7. **Open flags and rulings** - in the ledger grammar, or a pointer at the
   deck's own ledger file.

By those numbers, sections 1 to 5 are the content contract; 6 and 7 are how
it gets built and what was decided along the way.

## The route vocabulary

Every row of the slide table carries a route, because "make this slide" is
three different jobs with three different risks.

**Route A - clone an approved slide and retext it.** The design is already
signed off and the only thing changing is words. Nothing is rebuilt: the
slide is copied inside the author's own file and its text is patched in
place through character-level run attribution, so mixed bold, colour and
spellcheck state survive. This is stage 4's machinery -
`references/04-integration.md#4-run-attribution` for the mechanism and
`references/04-integration.md#5-the-text-map` for finding the shape to patch.
Choose A whenever the layout is not in question; it is the cheapest route and
the only one that cannot regress a design nobody asked you to touch.

**Route B - HTML draft, then native port.** New design. Draft the slide as
one 1280x720 HTML file, argue about the layout in a browser where iteration
is free (`references/02-html-stage.md`), then port it to a Python builder
that reproduces the same geometry as real PPTX shapes
(`references/03-pptx-stage.md`). Geometry transfers 1:1; typography does not,
so the builder measures rather than autofits. Choose B when the slide does
not exist yet and its layout is genuinely open. The draft is disposable -
once the builder exists, the builder is the source of truth.

**Route C - extract and reframe.** The content exists in someone else's
deck and the slide itself is worth keeping. The slide is transplanted by
OOXML surgery, with its layout, master, media and relationships carried
across and their ids re-minted (`references/04-integration.md#6-the-transplant`),
and only then reframed. Choose C when rebuilding would lose something the
original carries - a chart, a diagram, a picture - and retexting is not
enough because the framing has to change.

## Exact figures are checked, not trusted

The `Exact string` column of section 3, Verified facts, is not decoration.
`scripts/lint_deck.py`'s `exact` check reads it - `exact_strings_from_spec`
finds the first markdown
table in the spec whose header row names `Exact string` and takes that
column, stripping backticks - and fails the deck if any of those strings is
not present verbatim, whitespace-normalised, on some slide.

The rules file points at the spec by relative path:

```toml
[exact]
spec = "spec.md"          # resolved against the rules file's own directory
```

The table is found by its column name, never by its section number, so
renumbering the spec's sections cannot silently turn the check into a no-op.
Pinned by `tests/test_lint_deck.py::test_exact_strings_come_from_the_spec_table`
and `tests/test_lint_deck.py::test_exact_figures_must_appear_verbatim_on_some_slide`,
and run on a real deck by the `walkthrough lint` gate step.

The consequence for the author is that the spec is load-bearing. A figure
retyped on a slide with a digit wrong fails the gate; a figure the spec never
declared exact is not checked at all.

## The governance loop, and what this repository does not duplicate

Briefs, implementer reports, reviews, re-reviews and the
`DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED` return contract come
from `superpowers:subagent-driven-development`. This repository does not ship
a second copy of them (design decision D1: one home per doctrine). What that
skill does not have, and what this file therefore keeps, is the deck-specific
half:

**The 35% rule.** Replacement copy more than 35% longer than the original run
text is shortened, never allowed to overflow, and every shortening is
reported to the author. A text box inherited from someone else's template
arrives with a width fitted to the old copy and, often enough, with word wrap
off, so "it will just wrap" is not true (catalogue items 12 and 13). The rule
is one of the six defaults in `templates/handoff.md` section 0, so it
travels with the deck rather than living only here.

**Fact-by-fact verification against a cited source.** Every claim on a slide
is checked against the source the spec names for it, and carries one of four
verdicts:

| Verdict | Meaning |
|---|---|
| **Exact** | the source says it, literally or by clear equivalence |
| **Inexact** | the source says otherwise |
| **Judgement** | a defensible reading of the evidence, not literal |
| **Untraceable** | no support in the sources at all |

Ties break toward **Judgement** over **Exact**: a claim that needed a step of
interpretation is not an exact quotation, and calling it one is how an
inference becomes a fact nobody re-checks. Separately, every error of fact
carries a severity - **high**, **medium** or **low** - graded by what it
breaks: a wrong figure in a recommendation is high, a wrong figure in a
supporting aside is low.

The design spec's own wording (section 4, stage 1) names only "exact" and
"untraceable" plus the severity grades. The two middle verdicts are the
source engagement's actual practice in its fact-by-fact review artifact, and
keeping them here is a declared extension of the spec, with a ruling in
`docs/decisions.md` under `## Phase 3`.

**A review checks the artifacts, never the report.** The reviewable objects
are the exported PNGs, the text dump and the shape ids - not the implementer's
account of them. Every finding carries three things: the problem, the
evidence (which PNG, which shape id), and the exact replacement string.
A review that cannot verify something says so, in its own "not verifiable
from the artifacts" section, rather than passing it in silence. A re-review
re-checks only the enumerated findings from the review it answers, and
nothing else.

**The ledger grammar.**

```
- Ruling: <decision> - <justification and source section> - cost if wrong: <recovery action>
```

The cost clause is mandatory, and it is not paperwork: it is what licenses
deciding without stopping to ask the author. A decision whose cost if wrong
is "rebuild one slide" can be taken alone; one whose cost is "the deck says
something false to a client" cannot. `docs/decisions.md` is the live example,
several hundred lines of it; `examples/walkthrough/ledger.md` is the minimal
one, two rulings for a two-slide deck. Pinned by
`tests/test_templates.py::test_the_walkthrough_ledger_uses_the_ruling_grammar`.

## The working agreement

`templates/handoff.md` section 0 ships six default rules, filled in rather
than left as placeholders, and marked as defaults the author can override
rather than law:

1. **Propose text changes in the conversation**, in a small number of
   alternatives, and let the author apply them; act on files only with an
   explicit go.
2. **Never overwrite the author's deck.** Read one path, write another. Their
   file is usually open in PowerPoint and locked, with a `~$` sidecar next to
   it (catalogue item 21); write to the work directory and say so.
3. **Reading order before touching anything:** the handoff, the spec, the
   ledger, then dump the deck's text and diff it against the last dump, then
   look at the current PNGs.
4. **One question per message, in prose**, with enough context to decide and
   the reasoning behind any recommendation.
5. **The 35% rule**, above.
6. **The intake before any deck:** run `scripts/discover.py`, then ask the
   four questions - design system, HTML draft, speaker notes, output - and
   record the answers in the spec's front matter before starting anything.

Stated once here and not repeated elsewhere in these references. Pinned by
`tests/test_templates.py::test_the_handoff_template_ships_section_zero_filled_in`,
which fails if section 0 arrives empty or full of angle-bracket placeholders.

## Speaker notes and the teleprompter

Notes are opt-in, and the default is none. The intake asks whether the
presenter wants them in the PPTX notes pane, on a teleprompter HTML page,
both, or neither, and the spec's `**Notes:**` line records the answer as
one of `none | pptx | teleprompter | both`. The builders take
`--notes {none,pptx,teleprompter,both}` (default `none`) and
`--teleprompter PATH`, the latter only when the mode includes the
teleprompter; both delegate to one library entry point,
`deck_kit.notes.emit_notes(prs, notes, mode, *, font, size_pt, gap_pt,
title, teleprompter=None, skip=(1,))`, which dispatches to the writer and
the emitter described below. The gate runs both example decks with
`--notes both`, so the feature keeps being proved on every run even though
a new deck starts without it.

Notes belong to the content stage, not to a stage of their own: what the
presenter says is spoken content the spec fixes, and its time budget is the
spec's time budget.

`src/deck_kit/notes.py` carries one `Note(position, title, text, minutes=0,
section="")` per **file position**, and nothing else. It deliberately does
not carry the printed page number or whether the slide is hidden - those are
properties of the deck, read from the presentation when the teleprompter is
emitted, never typed twice. `paragraphs()` splits the spoken text on blank
lines; a paragraph starting with `>` is an aside, spoken only if asked
(`is_aside`).

`write_notes(prs, notes, *, font, size_pt, gap_pt)` writes them into the
PPTX. The three keywords are required: the core library carries no
measurement defaults, and a note's size belongs to the brand's type scale.
It refuses a note list that does not cover every slide exactly once, naming
the out-of-range, duplicate or missing positions - a teleprompter with a gap
is a teleprompter the presenter discovers is missing, on stage. It reaches
each slide's notes body through `textedit.ensure_notes_body`, which is
catalogue item 11 (`references/06-gotchas.md`); it does not reimplement that
clone.

`teleprompter_html(notes, numbers, *, title, template=None)` fills
`templates/teleprompter.html` - one section per note, a nav strip, the total
spoken minutes, asides marked as asides, hidden slides marked hidden. Its
`numbers` argument is what `numbering(prs, skip=(1,))` returns:
`{position: (printed_number_or_None, hidden)}`, read straight from the deck.
`numbering` gets the printed numbers from `pagenums.visible_numbers`, the
same single counting rule `pagenums.renumber` writes with, so the
teleprompter and the footer cannot disagree - not even on the first deck that
hides a slide.

`examples/walkthrough/notes_data.py` is the note list for the walkthrough
deck, and `examples/walkthrough/build_walkthrough.py` generates both outputs
from it in one run (design decision D5: generated once, into both). Pinned by
`tests/test_notes.py` and by the `walkthrough` gate step, whose `check()`
reopens the saved PPTX and the emitted HTML and asserts the notes round-trip,
that slide 2 reads `Slide 2 [2]`, and that the cover carries no printed
number at all.
