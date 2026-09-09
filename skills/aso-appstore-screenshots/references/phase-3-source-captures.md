# Phase 3 — Source Captures

**Goal:** Collect simulator/emulator screenshots, rate each, pair to headlines.

**Inputs:** `aso_benefits.md` from Phase 2. User-provided captures.

## Conventions

For multi-locale or multi-platform decks, captures should live at:

```
screenshots/source/{ios,android}/{en,es,...}/img0[1-N].png
```

Same `imgNN.png` filename across locales/platforms maps to the same headline slot —
makes Phase 8 replication trivial.

## Rating rubric

For every capture, assign **Great / Usable / Retake** with explicit reasoning:

- **Great**: rich content, clear UI, visually striking at thumbnail size.
- **Usable**: works but has minor flaws (sparse content, distracting status bar).
- **Retake**: empty state, debug UI, settings page, login screen, dark/light mismatch.

## Common Retake triggers

- Empty states / "no results" / placeholder data
- Lists with 1-2 items when they should look full
- Console logs, debug overlays, dev-mode indicators
- Status bar clutter (low battery, carrier name, unusual time)
- Settings pages, onboarding screens
- Mixed dark/light mode across the deck

## Retake coaching

For any Retake, give specific guidance:

- Which screen to navigate to
- What state the data should be in (e.g., "5-6 items in the list, realistic names")
- Light vs dark mode (pick one for the whole deck)
- Status bar tips:
  - **iOS**: Simulator → Features → Status Bar → override to full signal, full battery, time 9:41
  - **Android**: `adb shell settings put global sysui_demo_allowed 1 && adb shell am broadcast -a com.android.systemui.demo -e command clock -e hhmm 0941`

## Pairing rules

- Pair only Great or Usable captures.
- Match relevance: a "TRACK PRICES" headline needs a screen showing prices.
- Prefer visually striking captures for slots 1 and 5 (first and last impression).
- Don't reuse the same capture for multiple slots if avoidable.

## Output

Write `aso_screenshot_pairings.md` per `memory-schema.md`. Include the rating + assessment for every capture (even Retakes — the user may come back to fix them).

## AskUserQuestion gate (per slot pairing)

For each of the 5 slots' paired source capture:

```python
AskUserQuestion(questions=[{
    "question": "Slot N source img0N.png: right fit for this headline, swap to a different file, or re-shoot?",
    "header": "Slot N source",
    "multiSelect": False,
    "options": [
        {"label": "Right fit", "description": "This capture conveys the slot's benefit visually. Lock the pairing."},
        {"label": "Swap to different file", "description": "Try a different existing capture (img0M.png or alt)."},
        {"label": "Re-shoot", "description": "No existing capture works; take a new one before locking."}
    ]
}])
```
