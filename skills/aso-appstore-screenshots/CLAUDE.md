# CLAUDE.md

This file provides guidance to Claude Code when working in **this skill's repository** (the skill author's perspective). For the skill's user-facing flow, see `SKILL.md`.

## What this is

A Claude Code skill (`aso-appstore-screenshots`) that guides users through creating high-converting App Store and Google Play screenshots through a 9-phase pipeline. State persists across sessions via auto-memory.

## Architecture (v3 — Pillow-first)

```
SKILL.md                    — entry point, 9-phase table, RECALL rules, pointers into references/
references/
  conversion-principles.md  — universal ASO principles (Phiture PET, Storemaven, SplitMetrics)
  enhancement-toolkit.md    — 3 breakout modes (hero / literal / clean) + when-to-use rules
  phase-N-*.md              — procedure for each of the 9 phases
  prompt-templates.md       — hero-card scene prompt wrapper (Phase 7)
  memory-schema.md          — auto-memory file formats
  platform-dimensions.md    — store target sizes
  setup-openai.md           — OpenAI gpt-image-2 provider setup
scripts/
  compose.py                — Pillow scaffold orchestrator. Renders background, app UI inside frame, photoreal device frame, Pillow drop shadow, headline band, and (literal mode) lifted panel. Writes scaffold.png + scaffold.meta.json.
  bg_renderer.py            — 8 background styles (plain, linear-vertical, linear-diagonal, radial, vignette, blob, dual-blob, mesh-gradient).
  frame_composite.py        — Composites the app UI inside the device frame PNG and adds a Pillow drop shadow.
  headline_render.py        — Verb + descriptor typesetting at locked anchor.
  lifted_panel.py           — Literal-mode panel: crop → scale → rounded corners → shadow, anchored to the bezel.
  overlay_zone.py           — QA overlay (cyan = screen_rect, magenta = breakout_zone or preserve_panel).
  enhance_card.py           — Hero-card generator (Phase 7, hero slots only). Calls gpt-image-2 for a full-bleed photoreal SCENE; Pillow renders the polaroid card (white margin + rounded corners + drop shadow + tag overlays) and composites onto the scaffold. Auto-saves scene.png for $0 Phase-8 replication. Supports --reuse-scene-from to skip AI.
  preview_crop.py           — Phase 5 helper: overlay source_rect on the source capture before locking the brief.
  showcase.py               — Phase 9 side-by-side composite of finals.
assets/
  iphone-6.9-frame.png      — photoreal iPhone frame PNG used by frame_composite.py
  android-frame.png         — photoreal Android frame PNG
evals/                      — eval fixtures + assertions
```

## Two-stage generation

**Stage 1 — Scaffold (`compose.py`).** Deterministic, fully Pillow-rendered, free, fast. Default canvas: 1320×2868 (iPhone 6.9", Apple's primary required size). Renders, in order:
1. Background (one of 8 styles, per `aso_visual_direction.md`).
2. App UI screenshot composited inside the device frame.
3. Photoreal device frame PNG + Pillow drop shadow under the device.
4. Headline band (verb + descriptor at the locked anchor).
5. Optional breakout, depending on `panel_mode`:
   - `literal`: Pillow paints a lifted UI panel (cropped from the source, scaled, anchored, drop-shadowed).
   - `hero`: no paint — only records `breakout_zone` in the sidecar, leaving that region of the scaffold as reserved space for Stage 2 to fill.
   - `clean`: no breakout. The scaffold IS the final.

For `literal` and `clean` slots, `scaffold.png` is already the deliverable. Phase 7 is skipped for those slots.

**Stage 2 — Hero card (`enhance_card.py`, hero slots only).** Optional, AI + Pillow. Asks `gpt-image-2` to paint ONE full-bleed photoreal SCENE (no card framing in the prompt) sized to the photo area inside the polaroid margin. Pillow then `render_card()` wraps the scene in a white inner margin, applies rounded outer corners, draws optional tag overlays (e.g. "Foto Principal", "GRATIS"), and `composite_card_with_shadow()` drops it onto the scaffold at `breakout_zone` with a Pillow-rendered shadow. Saves `scene.png` (raw AI), `card.png` (framed), `final.png` (composited).

`enhance_card.py` reads two fields from `scaffold.meta.json`: `panel_mode` (must be `"hero"`) and `breakout_zone`. Either `--creative-direction "scene description"` triggers an AI call (~$0.19), or `--reuse-scene-from path/to/scene.png` skips the AI entirely ($0). No chroma-key, no mask, no input image. `gpt-image-2` doesn't accept `background="transparent"`; we don't need it — Pillow's rounded mask on the framed card creates the transparency we need.

This split keeps every text-bearing element drift-free (it's all Pillow) and confines the AI to painting a photo — no UI elements, no labels, no card framing. The AI cannot drift outside the photo region because Pillow physically clips it.

## Key implementation details

- **Frame-alpha source mask** (`_build_screen_mask_from_frame`): flood-fills the frame asset's transparency from a known-interior seed point and uses that as the source-content mask (dilated by 2 px via `ImageFilter.MaxFilter(5)`). Eliminates corner-radius guesswork — source content tracks the frame's actual screen-window curve, no double-curve mismatch, no hairline pink-bg gap at the anti-aliased frame edge.
- **Auto-detected screen rect** (`_detect_screen_rect`): off-center column scan finds the screen body even when a centered notch / Dynamic Island would break a center-column scan. The detected rect overrides any `bezel`/`bezel_top` values in the device profile.
- **`iphone-6.9` profile** has asymmetric bezels: `bezel=55` (sides), `bezel_top=157` (top, accounts for notch area). Fallback only — `_detect_screen_rect` typically wins.
- **`android` profile**: `screen_corner_r=80` retained as fallback in case detection fails. Use `--source-inset 12` for Android source captures that bake in the phone's dark screen border.
- **Polaroid card sizing** (`render_card`): photo area = `(card_w - 2 * inner_margin) × (card_h - 2 * inner_margin)` with `inner_margin=25` default. AI request size scales the photo aspect up so short side ≥ 1024 px (gpt-image-2's minimum pixel budget), then downscales the response before framing.
- **Tag overlays** are passed as JSON via `--tags` and rendered on the photo area (not the white margin). Supports `top|bottom`-`left|right|center` positions, hex bg/text colors with optional alpha, per-tag font override.
- **`scene.png` persistence**: always saved alongside `card.png`. Phase 8 replicas reuse it via `--reuse-scene-from` at $0 AI cost; tag text translations (e.g. "Foto Principal" → "Main Photo") happen at framing time, not generation time.
- **Device profiles scale proportionally**: typography, padding, and breakout placements derive from canvas width so all profiles produce visually consistent output.

## When making changes

- **Scripts are the implementation; references are the contract.** If you change a flag in `compose.py`, update `references/phase-6-scaffold.md` and `references/enhancement-toolkit.md` in the same change.
- **Phase 5 / Phase 7 contract**: the worksheet schema in `references/memory-schema.md` is the wire format between phases. `enhance_card.py` reads only `panel_mode` and `breakout_zone` from the sidecar — any new field needs a corresponding consumer.
- **gpt-image-2 contract** lives in `scripts/enhance_card.py`. The prompt wrapper is `PROMPT_WRAPPER` (scene-only, no card framing language); the API call is `client.images.generate(...)` in `enhance()`. Pillow framing lives in `render_card()` and `composite_card_with_shadow()`. Treat the file as the source of truth and propagate changes into `references/prompt-templates.md`, `references/phase-7-enhancement.md`, and `references/setup-openai.md`.
- **Always save `scene.png`**. Never delete it. Phase 8 depends on it.

## Running compose.py

```bash
# Required: pip install Pillow
# Required: a font file (e.g., Nunito-Black.ttf passed via --font-path)

python3 scripts/compose.py \
  --bg "#FFD7F0" \
  --verb "GIVE" \
  --desc "WHAT YOU DON'T NEED" \
  --screenshot path/to/source.png \
  --device iphone-6.9 \
  --text-color "#BC004B" \
  --font-path path/to/Nunito-Black.ttf \
  --desc-font-path path/to/Nunito-Bold.ttf \
  --breakout-rect "55,420,440,410" \
  --breakout-anchor left \
  --output output.png
```

Devices: `iphone-6.9` (default, 1320×2868 — Apple's primary required size), `iphone-6.7` (1290×2796), `iphone-6.5` (1242×2688), `android` (1080×2400).

## Running enhance_card.py

```bash
export OPENAI_API_KEY=sk-...
python3 scripts/enhance_card.py \
  --scaffold path/to/scaffold.png \
  --creative-direction "A polished editorial photo card with rounded corners (~24px radius), photographing a sage-green velvet sofa against a soft pink backdrop, late-afternoon light, magazine quality." \
  --output-card path/to/card.png \
  --output-final path/to/final.png
```

Requires `scaffold.meta.json` next to `scaffold.png` with `panel_mode == "hero"` and a non-null `breakout_zone`.
