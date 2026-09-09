# ASO skill v3 — Pillow-first pivot

- **Date:** 2026-05-13
- **Status:** Design locked, pending user spec review before implementation planning
- **Supersedes:** v2 (mask-based gpt-image-2 full-canvas edit) — every fix attempt traded one problem for another. v3 inverts the architecture.

## Why pivot

v2 asked one AI call to do five jobs at once (render photoreal chassis, drop shadow, hero card, background polish, plus preserve the screen UI and headline). Every reliability fix — masking the headline, re-pasting preserved pixels, fidelity flags — created a new failure mode. The right structural move is to shrink the AI's job to the one thing only it can do: paint the hero card creatively.

Everything else (phone frame, drop shadow, headline, background, app UI) is deterministic and lives in Pillow.

## Pipeline shape — two stages

### Stage 1 — Scaffold (Pillow, runs for every slot)

Produces a finished-looking image deterministically:

1. Background rendered per chosen style (one of 8 — see below)
2. App UI screenshot fit into the screen area (fit-to-width, bleeds past canvas bottom)
3. Photoreal phone frame PNG composited on top (chassis covers bezels, transparent inside lets UI show through)
4. Drop shadow under the phone (Pillow Gaussian blur of frame alpha; 0/+24 px offset, 60 px blur, 18% black)
5. Headline drawn on top of the background, above the phone
6. For `literal` mode: lifted UI panel composited beside the phone with its own Pillow shadow

The scaffold is **shippable on its own** for `clean` and `literal` slots, and shippable as a no-breakout option for `hero` slots.

### Stage 2 — Hero card (gpt-image-2, runs only for `hero` slots)

Generates a transparent PNG of the card + its own shadow on a small canvas (zone size + 60 px shadow padding), then Pillow alpha-composites it onto the scaffold at the breakout zone position.

The AI never sees: the headline text, the app UI, the phone chassis, or the canvas background. It can't drift any of them.

## Frame asset strategy — app-agnostic

The skill ships two photoreal frame PNGs as bundled defaults:

| File | Source | Notes |
|---|---|---|
| `assets/iphone-6.9-frame.png` | iPhone 17 Pro Max Deep Blue from Apple Design Resources | 490×1000, RGBA, transparent screen + outside |
| `assets/android-frame.png` | Cleaned Pixel-style silver, photoreal | 486×1024, RGBA, transparent screen + outside (alpha gradient on screen edge for clean compositing) |

**Per-project override:** when running the skill from a project, `compose.py` checks for `screenshots/assets/<frame-name>.png` first; falls back to the bundled default if not present. This lets any other app drop in its own frame PNG (different model, different finish, Galaxy instead of Pixel) without touching the skill.

Phase 4 (Visual Direction) records `frame_asset: bundled-default | project-override:<path>` in `aso_visual_direction.md`.

## Background style menu — 8 styles, all Pillow-deterministic

| Style | What it is | Flags |
|---|---|---|
| `plain` | One flat color edge-to-edge | `--bg-color "#X"` |
| `linear-vertical` | Vertical gradient, top → bottom | `--bg-color "#TOP"` `--bg-color-2 "#BOTTOM"` |
| `linear-diagonal` | 45° gradient, top-left → bottom-right | `--bg-color "#A"` `--bg-color-2 "#B"` |
| `radial` | Center glow → edges fade | `--bg-color "#CENTER"` `--bg-color-2 "#EDGE"` |
| `vignette` | Bright center, darker edges (focus effect) | `--bg-color "#BASE"` `--bg-color-2 "#EDGE-DARK"` |
| `blob` | One large soft glow off-center, base color elsewhere | `--bg-color "#BASE"` `--bg-color-2 "#BLOB"` `--bg-blob-position [upper-left\|upper-right\|lower-left\|lower-right\|center]` |
| `dual-blob` | Two glows of different colors at different positions | `--bg-color "#BASE"` `--bg-color-2 "#GLOW-A"` `--bg-color-3 "#GLOW-B"` `--bg-blob-positions "upper-left,lower-right"` |
| `mesh-gradient` | 3 soft glows blending (Stripe / Linear / Apple Music aesthetic) | `--bg-color "#BASE"` `--bg-color-2 "#A"` `--bg-color-3 "#B"` `--bg-color-4 "#C"` |

Hardcoded defaults:
- Linear angles: vertical and 45° only
- Radial: center = canvas center, radius = half-diagonal
- Blob: radius = 60% of canvas height, Gaussian falloff
- Mesh: 3 blobs distributed evenly across canvas, soft Gaussian blend

Background is rendered FIRST in `compose.py`; everything else (UI, frame, headline) layers on top. Headlines always sit above the background regardless of style.

### Memory format — `aso_visual_direction.md`

```yaml
background:
  style: plain | linear-vertical | linear-diagonal | radial | vignette | blob | dual-blob | mesh-gradient
  color: "#FFD7F0"
  color_2: "#FFC4E8"        # styles 2-8
  color_3: "#FFE8F4"        # dual-blob, mesh-gradient
  color_4: "#FFB8DC"        # mesh-gradient only
  blob_position: upper-left              # blob only
  blob_positions: upper-left,lower-right # dual-blob only

frame_asset: bundled-default      # or: project-override:screenshots/assets/iphone-6.9-frame.png
```

## Phase 6 / Phase 7 contract

### Phase 6 — Scaffold (Pillow, always)

**Inputs:** memory (visual direction, enhancements), source captures, headlines.

**Per-slot output:**

- `scaffold.png` — Pillow-rendered finished-looking image
- `scaffold.meta.json` — minimal sidecar:

```json
{
  "device": "iphone-6.9",
  "canvas": [1320, 2868],
  "panel_mode": "hero | literal | clean",
  "breakout_zone": [x, y, w, h] | null,
  "screen_rect": [x, y, w, h],
  "background": {"style": "plain", "colors": ["#FFD7F0"]}
}
```

- `scaffold_with_zone.png` — debug overlay (cyan = screen_rect, magenta = breakout/panel zone) for hero + literal modes

**Gate:** per-slot AskUserQuestion — lock / regenerate with tweaks / go back upstream.

### Phase 7 — Hero card (gpt-image-2, hero slots only)

For `clean` and `literal` slots, Phase 7 is skipped entirely.

**Inputs:** `scaffold.png`, `scaffold.meta.json` (for breakout_zone), `creative_direction` string from `aso_enhancements.md`.

**Per-slot output:**

- `card.png` — AI output, transparent canvas, card + its own shadow (savable standalone)
- `final.png` — scaffold + card composited at breakout_zone position

**Iteration:** ONE variant at a time (per existing `feedback_aso_thorough_on_drift` memory rule).

**Gate:** per-slot AskUserQuestion — lock as winner / refire with adjusted prompt / change the breakout zone.

### File matrix per slot

| panel_mode | scaffold.png | scaffold.meta.json | scaffold_with_zone.png | card.png | final.png |
|---|:---:|:---:|:---:|:---:|:---:|
| `clean` | ✓ | ✓ | — | — | — |
| `literal` | ✓ | ✓ | ✓ | — | — |
| `hero` | ✓ | ✓ | ✓ | ✓ if Phase 7 runs | ✓ if Phase 7 runs |

### Phase 9 (Showcase)

Reads each slot's "best available" file: `final.png` if it exists, else `scaffold.png`.

## Hero card prompt template

```
TRANSPARENT BACKGROUND. Paint ONE polished card filling the canvas edge-to-edge.

CARD CONTENT:
{creative_direction}

SHADOW: soft drop shadow beneath the card, blurred, falling down and slightly outward.

DO NOT: paint anything outside the card itself. No extra cards, no surrounding text or labels, no decorative borders, no fake UI badges. The card is the only thing on the canvas.
```

Wrapper: ~50 words. Total with `creative_direction` (typically 60-100 words): ~110-150 words. Far shorter than v2's 600+.

## AI call — `/v1/images/generations`, not `/edits`

```python
response = client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size=f"{w}x{h}",
    background="transparent",
    quality="high",
    n=1,
)
```

- No input image, no mask, no fidelity flag
- Canvas size: breakout_zone w + 60 px shadow padding both sides, h + 60 px shadow padding both sides, rounded up to multiple of 16
- Smaller canvas than full scaffold → cheaper (~$0.04/call vs ~$0.19) and faster

## Compositing card → final

```python
scaffold = Image.open('scaffold.png').convert('RGBA')
card = Image.open('card.png').convert('RGBA')  # transparent
scaffold.alpha_composite(card, (zx - shadow_pad, zy - shadow_pad))
scaffold.convert('RGB').save('final.png')
```

The card's AI-painted shadow lands naturally on both phone-screen pixels and canvas pixels via alpha-composite.

## AskUserQuestion as the universal gate

Every binding decision in the skill uses `AskUserQuestion`. Free text is reserved for content the user authors (headlines, creative direction, hex colors).

| Phase | Gate format |
|---|---|
| 1 — App Discovery | Single-select: confirm/revise/restart app context summary |
| 2 — Headlines | Per-slot single-select: approve / revise / different framework slot |
| 3 — Source Captures | Per-slot single-select: right fit / swap file / re-shoot |
| 4 — Visual Direction | Sequence of single-selects: frame source, model, finish, bg style, bg colors (per color slot), fonts, text color |
| 5 — Enhancements | Per-slot single-select for `panel_mode`; free text for `creative_direction`; confirm with AskUserQuestion |
| 6 — Scaffold | Per-slot single-select: lock / regen with tweaks / change upstream |
| 7 — Hero card | Per-card single-select: lock / refire / change breakout zone |
| 8 — Replication | Multi-select: which locales / platforms to extend to |
| 9 — Showcase | Single-select: ship / regen ordering / revise a slot |

Each phase doc includes a concrete `AskUserQuestion(...)` template at the gate step. The model running the skill copies the shape and fills in slot-specific values.

## Migration plan

### Skill files — rewritten or replaced

| File | Action |
|---|---|
| `scripts/compose.py` | Rewrite for photoreal-frame pipeline + 8 bg styles + Pillow drop shadow under phone |
| `scripts/enhance_openai.py` → `scripts/enhance_card.py` | Gut to ~80 lines: build prompt, call `images.generate`, crop padding, composite onto scaffold |
| `references/prompt-templates.md` | Shrink to just the hero card wrapper + creative_direction interpolation; drop mode-aware blocks for clean/literal (no AI involvement for those) |
| `references/phase-6-scaffold.md` | Rewrite for new pipeline + 8 bg styles + AskUserQuestion gate template |
| `references/phase-7-enhancement.md` | Rewrite for hero-only AI call + AskUserQuestion gate template |
| `references/phase-{1..5,8,9}-*.md` | Light updates: each gets an AskUserQuestion gate template at the gate step |
| `SKILL.md` | Update to reference the simpler 2-stage pipeline, AskUserQuestion gate pattern, new asset paths |

### Skill files — added

| File | Source |
|---|---|
| `assets/iphone-6.9-frame.png` | iPhone 17 Pro Max Deep Blue from Apple Design Resources |
| `assets/android-frame.png` | Cleaned Pixel-style silver from `main_clean.png` |
| `docs/specs/2026-05-13-pillow-first-pivot-design.md` | This document |

### Skill files — deleted

- `assets/device_frame.png` and `assets/device_frame_android.png` — legacy placeholder outlines
- `references/setup-nano-banana.md` — Nano Banana out of v3 scope entirely
- All mask-build logic, re-paste logic, `input_fidelity` gating, and safe-size resize/padding from the v2 enhance_openai.py — gone with the rewrite

### Memory files — Phase 1-5 outputs carry over

| File | Change |
|---|---|
| `aso_app_context.md` | Unchanged |
| `aso_benefits.md` | Unchanged |
| `aso_screenshot_pairings.md` | Unchanged |
| `aso_visual_direction.md` | Adds `background:` block + `frame_asset:` field |
| `aso_enhancements.md` | Unchanged (breakout_zone, source_rect, creative_direction all still relevant) |
| `aso_generated_screenshots.md` | Fresh start — old v2 entries irrelevant |

### Existing Waki outputs

Per user direction: leave on disk; v3 overwrites as we regenerate. Not a priority.

## Out of scope for v3 (explicit non-goals)

- Nano Banana support (dropped entirely)
- gpt-image-1 support (gpt-image-2 only)
- Web/desktop platform support (iOS + Android only)
- AI-painted backgrounds, AI-painted chassis, AI-painted shadows (all Pillow)
- Multi-variant AI fires per slot during iteration (one at a time, per existing memory feedback)
- Re-paste safety nets, mask-based pixel preservation, `input_fidelity` flags (none apply when AI only paints onto transparent canvas)

## Open items (none load-bearing for plan-writing)

- Confirm exact rendering implementation for `mesh-gradient` (3 Gaussian blobs vs 4? distribution pattern?) — finalize during implementation
- `linear-diagonal` direction: locked to top-left → bottom-right; if other angles wanted later, add `--bg-angle` flag

## Implementation plan

To be written by the `writing-plans` skill in the next step. Spec is ready for user review before that handoff.
