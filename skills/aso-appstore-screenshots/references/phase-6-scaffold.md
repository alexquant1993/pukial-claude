# Phase 6 — Scaffold Production

**Goal:** Render the Pillow-deterministic scaffold for each slot. For clean
and literal slots, this is the final deliverable. For hero slots, it is the
base over which Phase 7 will paint the AI card.

**Inputs:**
- `aso_visual_direction.md` — device, background style + colors, frame asset, fonts, text color
- `aso_enhancements.md` — per-slot `panel_mode` + `breakout_zone` (hero) or `source_rect` (literal)
- `aso_benefits.md` — headlines (verb + descriptor)
- Source captures at `screenshots/source/<platform>/<locale>/img0N.png`

## Procedure

Per slot, derive the `compose.py` flags from `aso_enhancements.md` and run:

```bash
SKILL="$HOME/.claude/skills/aso-appstore-screenshots"

python3 "$SKILL/scripts/compose.py" \
  --device iphone-6.9 \
  --bg-style plain --bg-color "#FFD7F0" \
  --verb "REGALA" --desc "LO QUE YA NO USAS" --text-color "#BC004B" \
  --font-path "$PROJECT/screenshots/fonts/Nunito-Black.ttf" \
  --desc-font-path "$PROJECT/screenshots/fonts/Nunito-Bold.ttf" \
  --screenshot "$PROJECT/screenshots/source/ios/es/img01.png" \
  --breakout-zone "60,950,760,820" \
  --output "$PROJECT/screenshots/es-ios/01-regala/scaffold.png"
```

Per-mode flag mapping:

| `panel_mode` | Flags to add |
|---|---|
| `clean` | (none — base flags only) |
| `hero` | `--breakout-zone "x,y,w,h"` (canvas coords) |
| `literal` | `--breakout-rect "x,y,w,h" --breakout-anchor [left\|right\|center] --breakout-scale 1.3 --breakout-overflow 0 --breakout-corner-r 50` |

Additional flags (all optional):

| Flag | Default | When to use |
|---|---|---|
| `--breakout-anchor center` | — | Source UI element is itself centered on screen; produces a symmetric lifted panel that bleeds past both bezels |
| `--breakout-corner-r N` | `24` | Bump to ~50 if the lifted source card has natural rounded corners with light whitespace around them — larger radius masks that whitespace away |
| `--source-inset N` | `0` | Crop N pixels from each side of the source before fit-to-fill. Use for Android captures that bake the phone's dark screen border into the pixels (causes visible double-curve at frame corners) |
| `--device-y N` | profile default | Override the phone's vertical position. **Use for hero slots** when the headline feels crowded against the device — the lifted card below the bezel adds visual mass that makes the default gap read as tight. Typical bump: +40–60 px. When you bump `--device-y` by N, also add N to the `--breakout-zone` Y so the hero card tracks the device. Literal/clean slots almost never need this — the lifted panel sits over the device and the default gap reads fine. |
| `--text-top N` | profile default | Override the y-coordinate where the headline starts. Use to nudge the headline up if extra room above is needed, or down for a top-heavy layout. |
| `--max-desc-lines N` | `2` | Cap the desc line count after word-wrap. The desc font auto-shrinks until it fits in N lines (down to a floor of ~6.5% of canvas width). Default 2 keeps long-locale phrases (e.g., Spanish "LO QUE NECESITAS GRATIS") from wrapping to 3+ lines and crowding the device frame. Bump to 3 only if you've intentionally written a long desc and accept the tighter layout. |

`compose.py` also auto-detects the frame asset's actual screen window
(via `_detect_screen_rect` flooding from the asset alpha) and uses the
frame's own transparency as the source mask (via
`_build_screen_mask_from_frame`, with a 2-px dilation). This eliminates
manual corner-radius guesswork and prevents the hairline pink-background
gap that earlier rounded_rectangle masks left around the phone curve.

Per-style background flag mapping:

| `bg-style` | Required flags |
|---|---|
| `plain` | `--bg-color "#X"` |
| `linear-vertical` | `--bg-color "#TOP" --bg-color-2 "#BOTTOM"` |
| `linear-diagonal` | `--bg-color "#A" --bg-color-2 "#B"` |
| `radial` | `--bg-color "#CENTER" --bg-color-2 "#EDGE"` |
| `vignette` | `--bg-color "#BASE" --bg-color-2 "#EDGE-DARK"` |
| `blob` | `--bg-color "#BASE" --bg-color-2 "#BLOB" --bg-blob-position [enum]` |
| `dual-blob` | `--bg-color "#BASE" --bg-color-2 "#GLOW-A" --bg-color-3 "#GLOW-B" --bg-blob-positions "upper-left,lower-right"` |
| `mesh-gradient` | `--bg-color "#BASE" --bg-color-2 "#A" --bg-color-3 "#B" --bg-color-4 "#C"` |

## Sidecar JSON shape

`compose.py` writes `scaffold.meta.json` next to each scaffold:

```json
{
  "device": "iphone-6.9",
  "canvas": [1320, 2868],
  "panel_mode": "hero | literal | clean",
  "breakout_zone": [x, y, w, h] | null,
  "preserve_panel": [x, y, w, h] | null,
  "screen_rect": [x, y, w, h],
  "headline_band": [x, y, w, h],
  "background": {"style": "plain", "colors": ["#FFD7F0"]}
}
```

The sidecar is used by Phase 7 (`enhance_card.py` reads `breakout_zone`) and
by `overlay_zone.py` for QA debug overlays.

## Sanity check (this is the gate)

Render scaffolds for all slots, then show every PNG to the user via `Read`.
Cheapest place to catch typos, wrong color, wrong rect, wrong breakout
position. Pillow is local and deterministic — regen costs nothing.

For `hero` slots, also generate the zone overlay to confirm placement:

```bash
python3 "$SKILL/scripts/overlay_zone.py" $PROJECT/screenshots/es-ios/01-regala/
```

Look at `scaffold_with_zone.png` — cyan rect = phone screen, magenta rect =
breakout zone. Confirm the zone Y aligns with where the AI card should sit.

## AskUserQuestion gate (per slot)

After rendering each scaffold and showing it to the user, use the
`AskUserQuestion` tool to lock the decision:

```python
AskUserQuestion(
    questions=[{
        "question": "Slot N ({verb} / {desc}): lock this scaffold, regenerate with tweaks, or change something upstream?",
        "header": "Slot N scaffold",
        "multiSelect": False,
        "options": [
            {
                "label": "Lock — proceed",
                "description": "Scaffold is ready. For clean/literal, it is the final. For hero, proceed to Phase 7."
            },
            {
                "label": "Regenerate with tweaks",
                "description": "Change a specific param (color, font size, breakout zone) and re-run compose.py."
            },
            {
                "label": "Go back to Phase 4 (visual direction)",
                "description": "Frame, background, or fonts need changing for the whole deck."
            }
        ]
    }]
)
```

Iterate until the scaffold is locked, then move to the next slot.

## Output

Per slot:
- `scaffold.png` — Pillow-rendered finished-looking image
- `scaffold.meta.json` — sidecar
- `scaffold_with_zone.png` — debug overlay (hero + literal modes only)

## Gate

User locks every scaffold via AskUserQuestion before proceeding to Phase 7
(if any hero slots) or Phase 8 (replication) / Phase 9 (showcase).
