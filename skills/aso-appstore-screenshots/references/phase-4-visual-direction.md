# Phase 4 — Visual Direction

**Goal:** Lock the visual cues that stay constant across the entire deck:
device profile, frame asset, background style + colors, fonts, text color.
Persist to `aso_visual_direction.md`.

**Inputs:** `aso_app_context.md` (brand cues, vibe), `aso_benefits.md` (the
headlines whose typography we're choosing).

## Procedure — driven by sequential `AskUserQuestion` calls

The skill walks the user through binding decisions one at a time. Each
decision is an `AskUserQuestion` call. Free-text input is reserved for hex
colors and asset paths.

### Decision 1 — Device profile

```python
AskUserQuestion(questions=[{
    "question": "Which device size profile? (Determines canvas dimensions and which frame asset is used.)",
    "header": "Device",
    "multiSelect": False,
    "options": [
        {"label": "iphone-6.9 (Recommended)", "description": "1320×2868, Apple's primary required size for App Store Connect."},
        {"label": "iphone-6.7", "description": "1290×2796."},
        {"label": "iphone-6.5", "description": "1242×2688."},
        {"label": "android", "description": "1080×2400, Google Play Store."},
    ],
}])
```

### Decision 2 — Frame asset source

```python
AskUserQuestion(questions=[{
    "question": "Use the skill's bundled photoreal frame, or a project-local override?",
    "header": "Frame source",
    "multiSelect": False,
    "options": [
        {"label": "Bundled default (Recommended)", "description": "iPhone 17 Pro Max Deep Blue (Apple Design Resources) for iOS; Pixel-style silver for Android."},
        {"label": "Project override", "description": "Drop a custom frame PNG at screenshots/assets/{frame_file}; compose.py picks it up automatically."},
    ],
}])
```

### Decision 3 — Background style

```python
AskUserQuestion(questions=[{
    "question": "Which background style? (Same style applied to every slot in the deck.)",
    "header": "BG style",
    "multiSelect": False,
    "options": [
        {"label": "plain", "description": "One flat color edge-to-edge."},
        {"label": "linear-vertical", "description": "Vertical gradient, top color → bottom color."},
        {"label": "linear-diagonal", "description": "45° gradient, top-left → bottom-right."},
        {"label": "radial", "description": "Center color glow fades to edge color."},
        {"label": "vignette", "description": "Bright center, darker edges — focus on the phone."},
        {"label": "blob", "description": "One large soft glow at a named position over a base color."},
        {"label": "dual-blob", "description": "Two glows of different colors at named positions."},
        {"label": "mesh-gradient", "description": "Three soft glows blending (Stripe / Apple Music aesthetic)."},
    ],
}])
```

### Decision 4 — Colors (free-text per style)

Ask the user for the hex colors required by the chosen style. Style → colors
needed (per [phase-6-scaffold.md](./phase-6-scaffold.md) flag mapping):

| Style | Colors |
|---|---|
| `plain` | 1 hex |
| `linear-vertical`, `linear-diagonal`, `radial`, `vignette` | 2 hex |
| `blob` | 2 hex + blob_position enum |
| `dual-blob` | 3 hex + blob_positions enum-pair |
| `mesh-gradient` | 4 hex |

When the user is undecided between colors, render Slot 1's scaffold with
the user's top 2-3 choices (Pillow is cheap) and show all variants — pick
the winner via another `AskUserQuestion`.

### Decision 5 — Fonts

```python
AskUserQuestion(questions=[{
    "question": "Verb font (line 1) — must be a heavy/black weight for ASO impact",
    "header": "Verb font",
    "multiSelect": False,
    "options": [
        {"label": "Bundled default (Nunito Black)", "description": "Strong sans-serif, premium feel. Recommended for most decks."},
        {"label": "Project-supplied font", "description": "Provide path to a .ttf or .otf file at screenshots/fonts/."},
        {"label": "System default", "description": "Falls back to SF Pro Display Black or Arial Black."},
    ],
}])
```

Then similarly for descriptor font (typically Bold, not Black).

### Decision 6 — Text color

Free-text hex (e.g., `#BC004B`). Confirm with `AskUserQuestion`:

```python
AskUserQuestion(questions=[{
    "question": "Lock text color {color} for all headlines in the deck?",
    "header": "Text color",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Use this color across all slots."},
        {"label": "Try a different hex", "description": "Free-text another hex value."},
    ],
}])
```

## Persistence — `aso_visual_direction.md`

Once all decisions are locked, write to memory:

```yaml
---
name: Visual direction
description: Locked visual cues for the deck
type: project
---
device: iphone-6.9
frame_asset: bundled-default          # or: project-override:screenshots/assets/iphone-6.9-frame.png
background:
  style: plain
  color: "#FFD7F0"
  color_2: null
  color_3: null
  color_4: null
  blob_position: null
  blob_positions: null
fonts:
  verb: "screenshots/fonts/Nunito-Black.ttf"
  desc: "screenshots/fonts/Nunito-Bold.ttf"
text_color: "#BC004B"
```

## Gate

All decisions locked via AskUserQuestion. Phase 4 memory file written.
Proceed to Phase 5 (Enhancement Analysis).
