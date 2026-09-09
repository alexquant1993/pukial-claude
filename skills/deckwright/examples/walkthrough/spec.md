# SPEC - Walkthrough: one deck through the whole pipeline

**Date:** 2026-09-08
**Objective:** show every stage of the pipeline on a deck small enough to read in a minute.
**Audience and time budget:** whoever is adopting this repository; three minutes of speech.
**Status:** approved for build
**Design system:** relay
**HTML draft:** skipped: the spec's section 5 is the design, two slides
**Notes:** both
**Output:** pptx

---

## 1. Content constraints

Non-negotiable editorial rules. Each one is checked by
`examples/walkthrough/lint.toml`.

- No internal tracking codes (`D1-01` style) reach the deck.
- No client or person names; the only organisation named is the brand itself.
- Every content slide carries the copyright line and exactly one section kicker.
- Anything spoken only if asked lives in the notes, never on a slide.

## 2. Sources

| Artifact | Use |
|---|---|
| `references/00-pipeline.md`, the QA loop table | the four stages and the loop, and the three kinds of check |
| `references/00-pipeline.md` | the stage names as the repository states them |

## 3. Verified facts

Use EXACTLY these strings; do not invent figures. Every row is checked
verbatim against the built deck by `scripts/lint_deck.py`'s `exact` check
(whitespace-normalised). Append new rows below the line; never edit a
verified row in place.

| Fact | Exact string | Source |
|---|---|---|
| Shape of the method | `Four stages and one loop.` | design spec section 4, first line |
| Shape of the QA loop | `Three kinds of check: file, visual, content.` | design spec section 4, "The QA loop" |

## 4. Slide table

| # | Slide | Route | Source |
|---|---|---|---|
| S01 | Cover | B (built natively from this spec) | section 5 |
| S02 | The loop | B (built natively from this spec) | section 5 and the two facts above |

Routes: **A** = clone an approved slide and retext it in place (design
intact). **B** = design in HTML on the 1280x720 canvas, then port natively
with `deck_kit`. **C** = extract a slide from an existing deck and reframe it.

## 5. Content per slide

### S01 Cover

Title: "Walkthrough". Subtitle: "One deck through the whole pipeline". No
kicker, no copyright line, no page number (the cover is exempt).

### S02 The loop

Kicker: "01. THE LOOP". Title: "One deck, every stage". Body, two
paragraphs: "Four stages and one loop." and "Three kinds of check: file,
visual, content." One pill reading "Route B". Copyright line at the foot.
Page number 2, added by `renumber`.

## 6. Technical pipeline

PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/make_template.py --brand relay --out out/template.pptx
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python examples/walkthrough/build_walkthrough.py --template out/template.pptx --out out/walk/deck.pptx --notes both --teleprompter out/walk/teleprompter.html
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/lint_deck.py --deck out/walk/deck.pptx --rules examples/walkthrough/lint.toml --expect-checks 8
powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/walk/deck.pptx
powershell -NoProfile -File scripts/export_png.ps1 -Path out/walk/deck.pptx -Out out/png_walk -Expect 2
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py band --png-dir out/png_walk --box 0,836,1600,900 --expect 2 --out out/qa/band.png

## 7. Open flags and rulings

See `examples/walkthrough/ledger.md`.
