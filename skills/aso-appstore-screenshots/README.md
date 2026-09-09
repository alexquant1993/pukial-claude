# ASO App Store Screenshots

An agent skill that generates high-converting App Store and Google Play screenshots through a transparent 9-phase pipeline. Works for any iOS or Android app — analyzes your codebase, identifies core benefits, pairs them with your screen captures, and produces polished store-ready images.

## What it does

1. **App discovery** — analyzes the codebase to identify the 3–5 benefits that drive downloads
2. **Headline authoring** — writes verb-led headlines per locale using the Solt framework (Pain → Shift → Proof → Feature × 2)
3. **Source pairing** — reviews your simulator/emulator captures, rates them, pairs each with a benefit
4. **Visual direction** — locks brand color, headline color, font, and background style
5. **Enhancement analysis** — per-slot conversion review picking one breakout mode (`hero` AI-painted card / `literal` Pillow lifted-panel / `clean` no breakout)
6. **Scaffold production** — Pillow renders the deterministic base (background, app UI inside the device frame, drop shadow, headline, and the lifted panel for `literal` mode)
7. **AI enhancement** — for `hero` slots only, `gpt-image-2` paints a full-bleed photoreal scene; Pillow frames it as a polaroid card (white inner margin + rounded corners + drop shadow + optional tag overlays) and composites onto the scaffold. The raw `scene.png` is saved so Phase 8 replications reuse it at $0 AI cost
8. **Replication** — repeats the locked formula across locales and platforms
9. **Showcase** — produces a side-by-side preview of approved finals

## Installation

This is a local, host-neutral agent skill. Install it in the active skills directory used by your agent host. When running the bundled scripts manually, set `ASO_SKILL_DIR` to the directory containing this `SKILL.md`.

### 1. Python dependencies

```bash
pip install -r "$ASO_SKILL_DIR/requirements.txt"
```

(That installs `Pillow` for the scaffold renderer and `openai` for the hero-card painter.)

### 2. Font

The skill needs a "black" / heavy headline font. macOS typically has SF Pro Display Black; on other platforms, install one and pass `--font-path` to `compose.py`. Default fallbacks (in order):

```
/Library/Fonts/SF-Pro-Display-Black.otf
/System/Library/Fonts/SFNS.ttf
/System/Library/Fonts/Supplemental/Arial Black.ttf
/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
C:/Windows/Fonts/Arial Black.ttf
```

### 3. OpenAI API key (only if any slot uses `hero` mode)

```bash
export OPENAI_API_KEY=sk-...
```

The hero-card painter calls `gpt-image-2`. `literal` and `clean` slots don't call the API at all — their scaffold IS the final.

### Cost estimate

Stage 1 (Pillow scaffold) is free and runs locally. Stage 2 (hero card) is the only cost.

A typical 5-slot deck with 2 `hero` slots: ~$0.19 per fire × 2 slots = ~$0.38 for the primary deck. Refire cost is the same per attempt. **Multi-locale / multi-platform replicas cost $0** — they reuse the primary deck's `scene.png` via `--reuse-scene-from` and re-render only the Pillow framing (tag translations, device frame swap, etc.). See OpenAI pricing for current `gpt-image-2` rates.

## Usage

From within your app's project directory:

```
/aso-appstore-screenshots
```

The skill walks you through each phase, gates on explicit user approval, and resumes across conversations from the project-local `.aso/` directory. It does not depend on a host-specific auto-memory feature.

## How it works

### Two-stage pipeline

**Stage 1 — Pillow scaffold (`compose.py`). Deterministic, free, fast.** Renders the entire screenshot in Pillow at the exact store canvas size: background (one of 8 styles), your app screenshot composited inside the photoreal device frame, drop shadow under the device, headline at the locked anchor, and (for `literal` mode) a lifted UI panel cropped + scaled + drop-shadowed onto the bezel. Writes a `scaffold.meta.json` sidecar recording the screen rect and the breakout zone.

**Stage 2 — Hero card (`enhance_card.py`). AI + Pillow, hero slots only.** For each `hero` slot, asks `gpt-image-2` to paint ONE full-bleed photoreal SCENE — no card framing, no labels, no UI chrome in the prompt. Pillow then builds the polaroid card around it: white inner margin, rounded outer corners, drop shadow, and optional tag overlays (e.g. "Foto Principal", "GRATIS", "4.3 km") drawn with the deck's locked font. The framed card is composited onto the scaffold at the breakout zone. The raw scene is auto-saved to `scene.png` so Phase 8 replicas can reuse it without paying for AI again.

`literal` and `clean` slots skip Stage 2 entirely. The scaffold IS the final.

### Output

Screenshots are saved to a `screenshots/` directory in your project:

```
screenshots/
├── source/                        ← your simulator/emulator captures
│   ├── ios/{en,es}/img0[1-5].png
│   └── android/{en,es}/img0[1-5].png
├── 0N-{slug}/                     ← per-slot working files
│   ├── scaffold.png               ← Pillow scaffold (deterministic)
│   ├── scaffold.meta.json         ← sidecar (panel_mode, breakout_zone)
│   ├── scene.png                  ← hero-mode only: raw AI photo (reused by Phase 8 — keep it)
│   ├── card.png                   ← hero-mode only: Pillow-framed polaroid card
│   └── final.png                  ← deliverable (= scaffold for literal/clean; = scaffold + card for hero)
├── final/                         ← deck-ready (after Phase 8 if multi-locale/platform)
└── showcase.png                   ← Phase 9 side-by-side preview
```

Default device: **iPhone 6.9" (1320 × 2868)** — Apple's primary required size. `compose.py --device` accepts `iphone-6.9` (default), `iphone-6.7`, `iphone-6.5`, or `android`.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill prompt — defines the 9-phase workflow |
| `CLAUDE.md` | Legacy authoring notes for the source plugin |
| `references/` | Per-phase procedures, the enhancement toolkit, prompt templates, memory schema, platform dimensions, provider setup |
| `scripts/compose.py` | Deterministic scaffold orchestrator (Pillow) |
| `scripts/bg_renderer.py` | 8 background styles |
| `scripts/frame_composite.py` | App UI + device frame + drop shadow composite |
| `scripts/headline_render.py` | Verb + descriptor typesetting |
| `scripts/lifted_panel.py` | Literal-mode lifted UI panel (crop + scale + shadow) |
| `scripts/overlay_zone.py` | QA overlay for screen_rect / breakout_zone |
| `scripts/enhance_card.py` | Hero-card pipeline: AI scene (gpt-image-2) + Pillow polaroid framing + tag overlays + drop-shadow composite. Supports `--reuse-scene-from` for $0 replication |
| `scripts/preview_crop.py` | Phase 5 helper for verifying source_rect |
| `scripts/showcase.py` | Phase 9 side-by-side composite |
| `assets/` | Photoreal device frame PNGs (iOS / Android) |

## License

MIT
