# Vendored source

This skill is a frozen copy — not a live git checkout.

- **Upstream:** https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots
- **Vendored from:** https://github.com/Skipperlla/claude-skill-aso-appstore-screenshots
- **Branch:** `add-android-support`
- **Commit:** `8f233726e846f03e80c03cb4a2fc7f914846851c`
- **Vendored on:** 2026-04-25
- **Why this fork:** Upstream `main` is iOS-only. This branch is the source of upstream PR #6, which adds Google Play (Android, 1080×2400) device support via a `--device` flag. PR is open and unmerged as of vendor date.

## Updating later

If upstream PR #6 merges or improves, re-clone the relevant branch into a temp dir, diff against this folder, and apply the deltas you want. Don't reintroduce a `.git` directory here.

## Local modifications

If you tweak the skill, log changes below so future-you can tell vendor code from local edits.

### 2026-04-26 — `compose.py` font fallback
Replaced the hardcoded `FONT_PATH = "/Library/Fonts/SF-Pro-Display-Black.otf"` with a `_resolve_font_path()` helper that walks a candidate list (SF Pro Display Black → SFNS → Arial Black → DejaVu → Windows Arial Black). Reason: SF Pro Display Black is not installed by default on macOS — Apple ships it via developer downloads. Arial Black is universal and looks acceptable for ASO scaffolds.

### 2026-04-26 — Required external patch: `nano-banana-mcp` model name
The aso-appstore-screenshots skill expects the nano-banana-mcp MCP server. Version 1.0.3 hardcodes `model: "gemini-2.5-flash-image-preview"` which Google renamed to `gemini-2.5-flash-image` after preview ended.

**Patch applied:** in `$(npm root -g)/nano-banana-mcp/dist/index.js`, replaced both occurrences of `gemini-2.5-flash-image-preview` with `gemini-2.5-flash-image`.

**Re-apply if nano-banana-mcp is updated:**
```bash
sed -i.bak 's/gemini-2.5-flash-image-preview/gemini-2.5-flash-image/g' \
  "$(npm root -g)/nano-banana-mcp/dist/index.js"
```

Watch for an upstream fix at https://www.npmjs.com/package/nano-banana-mcp — once a >1.0.3 release lands, drop this patch.

### 2026-05-03 — v2 rewrite (9-phase pipeline + provider choice)

Major restructure following spec at `~/Documents/01_projects/waki/docs/superpowers/specs/2026-05-03-aso-skill-v2-design.md` and plan at `~/Documents/01_projects/waki/docs/superpowers/plans/2026-05-03-aso-skill-v2-implementation.md`.

**Layout changes:**
- SKILL.md trimmed from 588 lines → 94 (orchestrator only).
- 14 reference files added under `references/` (one per phase + setup + prompts + memory schema + dimensions).
- Scripts moved into `scripts/` subdir; `compose.py` patched to resolve assets via parent dir (`SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`).
- `generate_frame.py` deleted (was dead code).
- `assets/selftest/` added with stub PNGs for `enhance_openai.py --selftest`.
- `evals/` added with 3 workflow assertion test cases + fixtures (mock app codebase, mock screenshots, three memory states).

**New script:**
- `scripts/enhance_openai.py` — OpenAI Images Edit wrapper (`gpt-image-2`, 1024×1536) with auto-generated screen-preserving mask. Imports `DEVICE_PROFILES` from sibling `compose.py`. Supports `--selftest` for verification (~$0.02). 6 unit tests passing covering mask generation and API wrapper.

**Behavior changes:**
- Provider choice (Nano Banana / OpenAI GPT Image) added in Phase 4; setup verification gates progression.
- Breakout worksheet phase added (Phase 5) — eliminates the v1 placeholder problem where prompts shipped with `[PRIMARY BREAKOUT — describe ...]` unfilled.
- Scaffold thumbnails are now shown to the user (Phase 6 gate) — the v1 instruction to hide them is removed.
- Subsequent-screenshot two-image style template reference dropped — caused content bleed in v1.
- Prompt templates restructured into bucketed sections (PRESERVE / RENDER / ADD / DO NOT) and split per (provider × platform).
- "Screen as sacred zone" rule added to all prompts; OpenAI provider also enforces it via mask.
- Replication phase formalized (Phase 8) for multi-locale / multi-platform decks.

**Rollback:**
- v1 archived as `~/.claude/skills/aso-appstore-screenshots-v1/` (separate skill name with archived description so it doesn't compete with v2 for triggering). Delete that directory after v2 is confirmed stable in real use.

### 2026-05-06 — Phase 5 conversion-driven enhancement analysis + scaffold sidecar + stamp impl

Replaced the static "breakout worksheet" Phase 5 with a research-grounded conversion analysis loop. Closes the audit findings that the worksheet template forced every slot into "primary breakout + secondary sticker" regardless of what the screen needed.

**New references:**
- `references/conversion-principles.md` — 8 universal ASO principles with anchor numbers (Storemaven 60% don't scroll past slot 1; SplitMetrics 19–26% avg CVR lift from creative A/B). Phiture PET model as spine. Localization rules (Spanish +25–30%, German +35%). Apple/Google policy guardrails (no fake CTAs, no superlatives, no fake stars).
- `references/enhancement-toolkit.md` — 7 patterns (lifted-panel, stamp, number-callout, decorative motif, real-context overlay, quote-card, clean) with when-to-use / when-to-avoid / implementation method. Pattern selection matrix.
- `references/phase-5-enhancements.md` — analytical procedure: per-slot 5-question analysis (hero, headline-visual link, density, PET, story-arc role) → toolkit pick → user signoff. Replaces `phase-5-breakout-worksheet.md` (deleted).

**Modular prompt templates:**
- `references/prompt-templates.md` rewritten as 7 composable blocks (preamble, role, preserve, device, enhancement, background, do-not). Enhancement block varies per slot from the toolkit. `number-callout` is a semantic alias for `lifted-panel` — same prompt language, same render path.

**Phase 5 → 6 → 7 contract:**
- `aso_breakouts.md` memory file renamed to `aso_enhancements.md` with new schema in `references/memory-schema.md`.
- `compose.py` writes a `scaffold.meta.json` sidecar containing canvas-space rects of any pre-rendered enhancement (lifted panel, stamp). `enhance_openai.py` auto-loads the sidecar and adds those rects to the mask. Eliminates the manual coordinate arithmetic between phases.

**Script changes:**
- `compose.py`: `--breakout-rect/--breakout-anchor/--breakout-scale/--breakout-overflow` (lifted panels), `--stamp-text/--stamp-color/--stamp-position/--stamp-rotation/--stamp-font-path` (stamps), sidecar JSON emission, `+500` bleed comment.
- `enhance_openai.py`: tuple-form image upload (locks model to `gpt-image-2`), headline-band auto-extension in mask (`y=0..device_y`), 1024×1536 stretch round-trip with output un-stretch back to scaffold canvas size, repeatable `--preserve-rect`, sidecar auto-discovery.
- `showcase.py`: multi-row layout via `--cols` (5-slot decks read better as 3+2 than as 5-wide), multi-OS font resolver matching `compose.py`.

**Doc consistency:**
- `phase-6-scaffold.md` now demonstrates `--breakout-rect` and `--stamp-text` examples per enhancement type.
- `phase-7-enhancement.md` clarifies that `--preserve-rect` is auto-loaded from the sidecar; explicit flag only needed for non-scaffolded rects.
- `prompt-templates.md` collapses `number-callout` into `lifted-panel` (rendered identically).
- `setup-nano-banana.md` adds an "MCP not loaded" troubleshooting block.
- `CLAUDE.md` rewritten from v1 era to reflect current architecture.

**Quote-card status:** marked roadmap. Until a `--quote-text/--quote-attribution` flag lands, Phase 5 must pick `stamp` or `clean` instead.

### 2026-05-13 — v3 Pillow-first pivot (chroma-key → polaroid framing)

Replaced the AI-paints-entire-card pipeline with: AI paints scene only, Pillow handles all framing. See spec/plan in `docs/`. Net change:

**Renamed / deleted:**
- `scripts/enhance_openai.py` (Images-Edit mask-based wrapper) → deleted. Replaced by `scripts/enhance_card.py` (Images-Generate, scene-only). The `assets/selftest/` stubs are now unused.

**`scripts/enhance_card.py` behavior:**
- Calls `/v1/images/generations` (not `/edits`) with no mask.
- Prompt asks for ONE polished card centered on a flat-white canvas.
- Pillow `_remove_white_background()` chroma-keys the white to alpha after the response, preserving the drop shadow as graduated alpha.

### 2026-05-16 — v3.1 Polaroid framing + scene reuse + frame-alpha mask

Iteration during a real Waki deck run (4 buckets × 5 slots). Replaced the chroma-key pipeline entirely; chroma-key reliably ate into card edges where AI-painted content was near-white.

**`scripts/enhance_card.py` rewritten:**
- AI prompt is now SCENE-ONLY ("a magazine-quality photoreal scene that fills the entire canvas, no card frame, no borders, no labels…"). No chroma-key.
- New `render_card(scene, …)` builds a polaroid card around the AI scene: white inner margin (`--inner-margin`, default 25), rounded outer corners (`--corner-r`, default 40), optional tag overlays via `--tags` JSON (each `{text, position, bg_color, text_color, font_size, …}`, positions = top/bottom × left/right/center).
- `composite_card_with_shadow(scaffold, card, position)` renders the drop shadow from the card's alpha silhouette (no more "shadow baked into AI output").
- New `--reuse-scene-from path/to/scene.png` skips the API call entirely. Used by Phase 8 replications for $0 AI cost.
- `scene.png` (raw AI output, no framing) is **always saved** alongside `card.png`. Preserve it.
- API request size scales up to ≥ 1024 px short side (gpt-image-2 minimum pixel budget) and downscales the response before framing.
- All chroma-key code (`_remove_white_background`, fill_threshold/white_cutoff constants) removed.

**`scripts/compose.py` upgrades:**
- `_detect_screen_rect(frame_path)` — auto-detects the frame asset's screen window via an off-center column scan (skips centered notches / Dynamic Islands). Overrides bezel-based screen rect.
- `_build_screen_mask_from_frame(...)` — flood-fills the frame's transparent region from a seed point and dilates by 2 px (`ImageFilter.MaxFilter(5)`) to use as the source-content mask. Replaces the old `rounded_rectangle` mask; tracks the frame's actual screen-window curve precisely. Kills double-curve mismatch and hairline pink-bg gap.
- `iphone-6.9` profile now has asymmetric bezels: `bezel=55` (sides), `bezel_top=157` (top, accounts for notch area).
- `android` profile: `screen_corner_r=80` retained as fallback (auto-detect normally wins).
- New CLI flag `--source-inset N`: crops N px each side of the source before fit-to-fill. Use for Android captures that bake the phone's screen border into the pixels.
- New CLI flag `--breakout-corner-r N`: tunes the lifted panel's outer corner radius (default 24). Bump to ~50 if the lifted source card has natural rounded corners with whitespace around them.

**`scripts/lifted_panel.py` upgrades:**
- New anchor: `center` (was `left | right`). Centers the panel horizontally with bleed on both bezels — used when the source UI element is itself centered on screen.
- `corner_r` is now a parameter (was hardcoded constant), threaded through `--breakout-corner-r`.

**Doc updates:** `references/phase-5-enhancements.md`, `references/phase-6-scaffold.md`, `references/phase-7-enhancement.md`, `references/phase-8-replication.md`, `references/prompt-templates.md`, `references/setup-openai.md`, `references/enhancement-toolkit.md`, `SKILL.md`, `CLAUDE.md`, `README.md` all updated to reflect the new pipeline.

**Deprecated:** `--selftest` references in this file are now stale (the script no longer exists). `assets/selftest/` is dead weight; safe to delete in a future cleanup.
