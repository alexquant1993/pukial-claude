# Phase 7 — Hero card (AI, hero slots only)

**Goal:** For each `hero` slot, generate a polished hero card. The AI paints
a full-bleed photoreal scene; Pillow handles all card framing
deterministically (white polaroid margin, rounded outer corners, drop
shadow, optional tag overlays). No chroma-key. `clean` and `literal` slots
skip this phase entirely — their `scaffold.png` is already the final.

**Inputs:**
- `scaffold.png` + `scaffold.meta.json` (Phase 6) — sidecar's
  `breakout_zone` tells `enhance_card.py` the target card dimensions
- `creative_direction` string from `aso_enhancements.md` — **scene-only**
  description (no card framing language; framing is Pillow's job)
- Optional `tags` list from `aso_enhancements.md` — text overlays drawn on
  the photo (e.g. `"Foto Principal"`, `"GRATIS"`, `"4.3 km"`)
- `OPENAI_API_KEY` env var (skipped when `--reuse-scene-from` is set)

See [prompt-templates.md](./prompt-templates.md) for the prompt shape.

## Procedure

ONE variant at a time (per `feedback_aso_thorough_on_drift` memory):

```bash
# ASO_SKILL_DIR is the installed directory containing this skill's SKILL.md.
SKILL="${ASO_SKILL_DIR:?Set ASO_SKILL_DIR to the installed skill directory}"
SLOT="$PROJECT/screenshots/es-ios/01-regala"

python3 "$SKILL/scripts/enhance_card.py" \
  --scaffold "$SLOT/scaffold.png" \
  --creative-direction "A casual iPhone photo of a red velvet sofa in a sunlit Madrid apartment, lived-in, no people." \
  --output-card "$SLOT/card.png" \
  --output-final "$SLOT/final.png" \
  --tag-font-path "$PROJECT/screenshots/fonts/Nunito-Bold.ttf" \
  --tags '[{"text":"Foto Principal","position":"bottom-center","bg_color":"#000000B0","font_size":24}]'
```

The script also writes `scene.png` alongside `card.png` — the raw AI scene
before Pillow framing. **Always keep `scene.png`** — it powers $0-AI
replication in Phase 8.

## How it works

1. `enhance_card.py` reads the sidecar, verifies `panel_mode == "hero"`,
   and reads `breakout_zone` to get the target card `(w, h)`.
2. Computes the photo area inside the polaroid margin: `(w - 2 *
   inner_margin) × (h - 2 * inner_margin)`. Default `inner_margin = 25`.
3. Computes the API request size: scales the photo aspect up so the short
   side ≥ 1024 px (`gpt-image-2`'s minimum pixel budget), rounded to mult-16.
4. Builds the prompt with `build_prompt(scene_description)` — see
   [prompt-templates.md](./prompt-templates.md). The prompt asks for a
   full-bleed photoreal scene with **no card framing, border, corners, or
   labels**. All of that is Pillow's job.
5. Calls `client.images.generate(model="gpt-image-2", prompt=..., size=...,
   quality="high", n=1)`. The opaque response is saved to `scene.png`.
6. `render_card(scene, ...)`:
   - Creates a white card surface at `(card_w, card_h)`
   - Resizes the AI scene to fit the photo area and pastes it inside the
     inner margin, with rounded inner corners (`corner_r - 14`)
   - Draws each tag overlay (capsule + text) on the photo area
   - Applies the outer rounded-corner mask (`corner_r`, default 40)
7. `composite_card_with_shadow(scaffold, card, position=(zone_x, zone_y))`
   shadow-renders the card silhouette beneath the card, then alpha-composites
   the card onto the scaffold at the breakout zone.

## Tags

Tags are passed as a JSON list via `--tags`. Each entry supports:

| field | default | notes |
|---|---|---|
| `text` | (required) | The label to draw |
| `position` | `"bottom-center"` | One of `top-left`, `top-right`, `top-center`, `bottom-left`, `bottom-right`, `bottom-center` |
| `bg_color` | `"#000000B0"` | Hex; supports 8-digit with alpha (`#RRGGBBAA`) |
| `text_color` | `"#FFFFFF"` | Hex |
| `font_size` | `26` | Px |
| `font_path` | (`--tag-font-path` default) | Per-tag font override |
| `edge_margin` | `18` | Distance from the photo edge in px |
| `padding_h` | `16` | Horizontal capsule padding |
| `padding_v` | `9` | Vertical capsule padding |
| `corner_r` | `20` | Capsule corner radius |

Common patterns:

- **Photo label**: `{"text":"Foto Principal","position":"bottom-center","bg_color":"#000000B0"}`
- **Free chip (iOS-feed style)**: `{"text":"GRATIS","position":"bottom-left","bg_color":"#22A55F"}`
- **Distance pill**: `{"text":"4.3 km","position":"bottom-right","bg_color":"#000000B0"}`

## Outputs

Per slot:
- `scene.png` — raw AI scene (no framing). **Keep for Phase 8 reuse.**
- `card.png` — Pillow-framed card with rounded corners, margin, tags
- `final.png` — scaffold + card composited with drop shadow

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| AI paints a card frame, white border, or label inside the scene | `creative_direction` reads like a UI element instead of a scene | Rewrite the direction as a photo brief — "A casual iPhone photo of…" Avoid words like "card", "frame", "label", "polaroid" |
| Scene looks staged / magazine-y, not realistic | Direction too aspirational | Add "lived-in", "honest", "no professional staging", "soft natural daylight" |
| Tag text wraps or overflows the card edge | Font size too big, or tag text too long for `padding_h` | Reduce `font_size`, or shorten the text |
| API returns `400` "below minimum pixel budget" | Computed photo dims < 1024 short side, scale-up logic broken | Verify the breakout zone is reasonable (>200×200 px) and that `_api_size_for_photo` is rounding correctly |

## User approval gate (per card)

After each fire, show the user `card.png` and `final.png` with the host's available image viewer or preview mechanism. Then:

```python
USER_INPUT_GATE(
    questions=[{
        "question": "Slot N hero card: lock as winner, refire scene, or change framing?",
        "header": "Slot N card",
        "multiSelect": False,
        "options": [
            {
                "label": "Lock — proceed",
                "description": "card.png and final.png are good; scene.png saved for Phase 8 reuse."
            },
            {
                "label": "Refire with adjusted scene",
                "description": "Tweak `creative_direction` in `aso_enhancements.md` and re-run enhance_card.py for this slot."
            },
            {
                "label": "Adjust framing",
                "description": "Change inner margin, corner radius, tag style/position, or breakout zone."
            }
        ]
    }]
)
```

## Iterate

If the user wants changes, identify the smallest delta:

- **Wrong scene mood** → tweak `creative_direction`, refire (`gpt-image-2` is
  non-deterministic, so even an unchanged prompt gives a fresh draw)
- **Tag wrong text/position/color** → just re-run with updated `--tags`; no
  AI call needed if `scene.png` exists (pass `--reuse-scene-from
  scene.png`)
- **Card dimensions wrong** → update `breakout_zone` in
  `aso_enhancements.md`, regen scaffold (Phase 6), then either refire or
  reuse scene with the new card size

ONE variant per refire, not three. Per the feedback memory: single variants
during iteration.

## Save winner

Already saved automatically — `card.png` + `final.png` overwrite previous
attempts. **`scene.png` also persists** — do not delete it; Phase 8 reuses
it across locale/platform replications at $0 AI cost.

Update `aso_generated_screenshots.md` per Phase 7 schema (see
[memory-schema.md](./memory-schema.md)) once user locks the slot.

## Gate

User locks every hero card via the user-input gate. After all hero slots
approved, proceed to Phase 8 (replication) if multi-locale/platform;
otherwise Phase 9 (showcase).

## Promote approved finals to `{deck}/final/`

Once every slot in the primary deck is user-approved, gather the
per-slot deliverables into a single flat folder for upload:

```bash
DECK="screenshots/{locale}-{platform}"  # e.g. screenshots/es-ios
mkdir -p "$DECK/final"
for slot in "$DECK"/0*/; do
  slot_name=$(basename "$slot")
  # Hero slots have final.png; literal/clean slots have scaffold.png that == final.
  src="$slot/final.png"; [ -f "$src" ] || src="$slot/scaffold.png"
  cp "$src" "$DECK/final/${slot_name}.png"
done
```

Result: `screenshots/{locale}-{platform}/final/0N-<verb>.png` — these are
the files to upload to App Store Connect / Play Console. The per-slot
folders remain as the working / regen source.
