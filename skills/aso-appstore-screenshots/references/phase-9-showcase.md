# Phase 9 — Showcase + Output

**Goal:** Generate a side-by-side showcase composite + summarize all final paths.

**Inputs:** Approved finals from Phase 7 (and Phase 8 if applicable).

## Run showcase

All slots from each approved deck. Phase 7 (and Phase 8) have already
promoted approved finals into `screenshots/{locale}-{platform}/final/`,
so the showcase just globs that folder. One showcase per deck.

```bash
# ASO_SKILL_DIR is the installed directory containing this skill's SKILL.md.
SKILL_DIR="${ASO_SKILL_DIR:?Set ASO_SKILL_DIR to the installed skill directory}"
DECK=screenshots/es-ios   # repeat per deck: en-ios, es-android, en-android
python3 "$SKILL_DIR/scripts/showcase.py" \
  --screenshots "$DECK"/final/0[1-5]-*.png \
  --output "screenshots/showcase-$(basename $DECK).png"
```

For single-platform single-locale projects, replace `--screenshots "$DECK"/final/0[1-5]-*.png` with a single flat folder; the output stays
`screenshots/showcase.png`.

`--cols` defaults to "all in one row" — fine for 1-3 screenshots; for 5-slot decks pass `--cols 3` (3+2) or `--cols 4` (4+1).

`--github` is optional and defaults to none. Pass it only if the user wants their
GitHub link displayed: `--github "github.com/their-handle"`.

## Show the showcase

Inspect the showcase image with the host's available image viewer and present it to the user.

## Final summary

Print a tree of all final paths grouped by locale and platform:

```
screenshots/
├── es-ios/final/
│   ├── 01-regala.png
│   ├── 02-consigue.png
│   ├── 03-ahorramos.png
│   ├── 04-intercambia.png
│   └── 05-encuentra.png
├── en-ios/final/
│   └── ...
├── es-android/final/
│   └── ...
└── en-android/final/
    └── ...
```

These are the files to upload to App Store Connect / Play Console.

## Output

`screenshots/showcase.png` + final tree printed to user.

## Gate

User confirms showcase looks right. End of pipeline.

## User approval gate

After rendering the showcase composite:

```python
USER_INPUT_GATE(questions=[{
    "question": "Showcase composite: ship it, regenerate with different ordering, or revise an underlying slot?",
    "header": "Showcase",
    "multiSelect": False,
    "options": [
        {"label": "Ship it", "description": "Save as final showcase.png; deck is done."},
        {"label": "Regenerate with different ordering", "description": "Swap slot order; re-composite."},
        {"label": "Revise an underlying slot", "description": "Go back to Phase 6 or 7 for the offending slot."}
    ]
}])
```
