# Memory Schema

The skill writes one memory file per completed phase to
`~/.claude/projects/<project-id>/memory/`.
Each file uses the standard frontmatter format from Claude's auto-memory system.

After saving, also add a one-line entry to `MEMORY.md` (the index).

## Files

| File | Phase | Stable across sessions? |
|---|---|---|
| `aso_app_context.md` | 1 | yes |
| `aso_benefits.md` | 2 | yes |
| `aso_screenshot_pairings.md` | 3 | yes |
| `aso_visual_direction.md` | 4 | yes |
| `aso_enhancements.md` | 5 | yes |
| `aso_generated_screenshots.md` | 7-8 | grows over time |

## Format — `aso_app_context.md`

```markdown
---
name: ASO app context for [APP_NAME]
description: App description, audience, niche, competitors, and key differentiators for ASO screenshot generation.
type: project
---
# [APP_NAME]

- **Platforms**: iOS / Android / both
- **One-liner**: [what the app does in 12 words]
- **Target audience**: [demographics + interests]
- **Niche**: [category]
- **Competitors**: [main competitors]
- **Key differentiators**: [bullet list]
- **Brand vibe**: [tone — playful / serious / minimal / etc]
```

## Format — `aso_benefits.md`

```markdown
---
name: ASO benefit headlines for [APP_NAME]
description: Confirmed App Store / Google Play screenshot benefit headlines per locale, target audience, and brand context.
type: project
---
# [APP_NAME] — App Store & Google Play screenshot benefits

## Target locales
- [locale 1] (e.g. `en-US`)
- [locale 2] (e.g. `es-ES`)

## Headlines (Solt framework: Pain → Shift → Proof → Feature × 2)

| # | [Locale 1 headline] | [Locale 2 headline] | Solt slot |
|---|---|---|---|
| 1 | VERB / DESCRIPTOR | VERB / DESCRIPTOR | Pain |
| 2 | ... | ... | Shift |
| 3 | ... | ... | Proof |
| 4 | ... | ... | Feature |
| 5 | ... | ... | Feature |
```

## Format — `aso_screenshot_pairings.md`

```markdown
---
name: ASO source captures + pairings
description: Per-screenshot rating + benefit-to-screenshot pairings.
type: project
---
# Source captures + pairings

## Pairings

| Slot | Source filename | Headline | Rating | Notes |
|---|---|---|---|---|
| 1 | `screenshots/source/ios/en/img01.png` | [headline 1] | Great | [what it shows] |
| ... | | | | |
```

## Format — `aso_visual_direction.md`

```markdown
---
name: Visual direction
description: Locked visual cues for the deck (device, frame, background, fonts, colors)
type: project
---
# Visual direction

```yaml
device: iphone-6.9 | iphone-6.7 | iphone-6.5 | android
frame_asset: bundled-default | project-override:<relative-path-from-project>
background:
  style: plain | linear-vertical | linear-diagonal | radial | vignette | blob | dual-blob | mesh-gradient
  color: "#XXXXXX"
  color_2: "#XXXXXX" | null
  color_3: "#XXXXXX" | null
  color_4: "#XXXXXX" | null
  blob_position: upper-left | upper-right | lower-left | lower-right | center | null
  blob_positions: "<pos>,<pos>" | null
fonts:
  verb: <path-to-ttf-or-otf>
  desc: <path-to-ttf-or-otf>
text_color: "#XXXXXX"
```
```

## Format — `aso_enhancements.md`

Output of Phase 5. Per-slot conversion analysis + breakout brief (plain English, for human review) + derived block (machine-readable, consumed by `compose.py` and `enhance_card.py`).

```markdown
---
name: ASO enhancement worksheet for [APP_NAME]
description: Per-slot conversion analysis plus a plain-English breakout brief and a machine-readable derived block (panel_mode, breakout_zone, source_rect, scale, anchor, creative_direction).
type: project
---
# Enhancement worksheet

## Slot 1 — [VERB] [DESCRIPTOR]  (source: imgNN.png, [one-line screen description])

### Analysis
- **Hero on screen**: [most attention-grabbing element]
- **Headline-visual link**: [what visual proves the headline]
- **Density**: sparse | medium | busy
- **PET levers**: P | E | T (or combinations)
- **Story-arc role**: Hook | Core A | Core B | Trust | Activation
- **Justification**: [one sentence — why this mode pick, citing a principle from `conversion-principles.md`]

### Brief (for human review)

What we lift
  [the UI element being lifted, in plain language]

How big
  About 1.5× larger than it appears on screen.

Where it sits
  [Anchor side] of the phone, roughly aligned with where the element naturally
  appears on screen ([upper / middle / lower] third). Bleeds past the
  [left/right] bezel by about a thumb's width.

Mode
  HERO (AI-painted) | LITERAL (Pillow lifted-panel) | CLEAN

[ HERO mode only: ]
Creative direction (used verbatim in the AI prompt)
  "[one-line vibe + subject + style]"

### Derived (consumed by compose.py + enhance_card.py)
```yaml
panel_mode: hero | literal | clean
device: iphone-6.9 | iphone-6.7 | iphone-6.5 | android   # canvas these rects were authored against
anchor: left | right | center | null      # 'center' added in v3.1; null for clean
breakout_zone: [x, y, w, h] | null  # canvas coords — hero only (literal leaves null; compose.py auto-derives and writes the actual zone to the sidecar)
source_rect: [x, y, w, h] | null    # source-image coords (literal only)
scale: 1.5 | null                   # literal only (cap 1.8)
overflow_px: 100                    # bleed past bezel (literal only)
corner_r: 24 | 50 | null            # literal only — outer panel radius; bump to ~50 if source card has natural rounded corners with whitespace
creative_direction: "..." | null    # hero only — SCENE description only (no card framing language)
tags:                               # hero only — optional Pillow overlays on the photo (Phase 7 --tags)
  - text: "Foto Principal"
    position: bottom-center         # one of top/bottom × left/right/center
    bg_color: "#000000B0"
    text_color: "#FFFFFF"
    font_size: 24
```

## Slot 2 — ...
```

### Schema notes

- `panel_mode` is the single source of truth — Phase 6 picks `compose.py` flags from it; Phase 7 picks the prompt enhancement block from it.
- `device` records the canvas profile the rects were authored against. Required for Phase 8 replication: when generating an Android variant from an iOS-authored worksheet, both `breakout_zone` and `source_rect` need recomputation (different canvas dims and a different source capture). Without `device` the recompute is impossible.
- `breakout_zone` is in canvas coordinates. **Hero mode**: the analyst sets it in the worksheet; `enhance_card.py` reads `breakout_zone` and `panel_mode` from the sidecar (the only fields it uses) — it requires `panel_mode == "hero"` and a non-null `breakout_zone`, then sizes the AI canvas to that zone (+ shadow padding) and composites the painted card back into the same zone. **Literal mode**: leave null in the worksheet — `compose.py` auto-derives the zone from the painted panel's canvas bbox and writes it to the sidecar.
- `source_rect` is in source-image coordinates (the screenshot's own coords). Only `literal` mode needs it because Pillow crops from the source image. Source rects are device- and locale-specific — they don't transfer across captures.
- `creative_direction` is used **verbatim** in the AI prompt — write it as a single, concrete, vibe-led sentence describing the **scene only** (subject + setting + lighting + restraint cue like "no people, no faces, lived-in"). Do NOT use card-framing vocabulary ("card", "frame", "label", "polaroid", "rounded corners") — Pillow handles that. It is the per-slot reproducibility lever; do not over-specify geometry. Raw AI output is saved to `scene.png` and reused across Phase 8 variants via `--reuse-scene-from`.
- `tags` (hero only) is an optional list of Pillow overlays drawn on the photo (not in the white margin). Each tag is rendered as a capsule with text. For locale variants, only the `text` typically changes (e.g. es `Foto Principal` → en `Main Photo`, es `GRATIS` → en `FREE`); geometry stays constant so the variant cards look like the same deck.
- The deck-wide `background motif` field has been retired. The BACKGROUND prompt block is now a single vibe-led version that lets the AI elevate the scaffold's color within its own family.

## Format — `aso_generated_screenshots.md`

```markdown
---
name: ASO generated screenshots
description: Final approved screenshot paths and deck status across locales/platforms.
type: project
---
# Generated screenshots

## Primary deck: [locale] / [platform]

| Slot | Final path | Version chosen | Status |
|---|---|---|---|
| 1 | `screenshots/final/01-give.png` | v2 | approved |
| ... | | | | |

## Replicas

| Locale | Platform | Status |
|---|---|---|
| es-ES | iOS | approved |
| en-US | Android | pending |
```
