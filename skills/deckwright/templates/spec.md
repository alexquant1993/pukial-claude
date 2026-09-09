# SPEC - <deck title>

**Date:** <YYYY-MM-DD>
**Objective:** <one sentence: what the audience should decide or believe after this deck>
**Audience and time budget:** <who is in the room, how many minutes of speech>
**Status:** <draft | approved for build | superseded by vN>
**Design system:** <path to a design system | brand name | brand name @ path outside the repository | default (brands/relay)>
**HTML draft:** <yes | skipped: reason>
**Notes:** <none | pptx | teleprompter | both>
**Output:** <html | pptx | both>

---

## 1. Content constraints

Non-negotiable editorial rules, in the deck's own language. Each one is a
sentence a reviewer can check a slide against.

- <rule, e.g. "No internal tracking codes reach the client">
- <rule, e.g. "Every content slide carries the copyright line">

## 2. Sources

| Artifact | Use |
|---|---|
| `<path or citation>` | <what it is the source for> |

## 3. Verified facts

Use EXACTLY these strings; do not invent figures. Every row is checked
verbatim against the built deck by `scripts/lint_deck.py`'s `exact` check
(whitespace-normalised). Append new rows below the line; never edit a
verified row in place.

| Fact | Exact string | Source |
|---|---|---|
| <what the figure is> | `<the string as it must appear on the slide>` | <source, with page or slide> |

## 4. Slide table

| # | Slide | Route | Source |
|---|---|---|---|
| S01 | <title> | <A, B or C> | <where its content comes from> |

Routes: **A** = clone an approved slide and retext it in place (design
intact). **B** = design in HTML on the 1280x720 canvas, then port natively
with `deck_kit`. **C** = extract a slide from an existing deck and reframe it.

## 5. Content per slide

### S01 <title>

<kicker, title, body copy, and every figure - closed copy, not an outline>

## 6. Technical pipeline

<the literal commands: template, builders, versioned build, QA - one per line>

## 7. Open flags and rulings

- Ruling: <decision> - <justification and source section> - cost if wrong: <recovery action>
