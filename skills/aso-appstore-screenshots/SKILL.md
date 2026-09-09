---
name: aso-appstore-screenshots
description: Generate high-converting App Store and Google Play screenshots through a guided 9-phase pipeline: codebase analysis, benefit headlines, screenshot pairing, visual direction, per-slot conversion analysis with enhancement recommendations grounded in ASO best practices (Phiture PET model, Storemaven research, SplitMetrics A/B data), deterministic scaffolding, and AI enhancement via gpt-image-2 for hero cards only (everything else is Pillow-deterministic). Use whenever the user mentions App Store screenshots, Google Play screenshots, ASO assets, store listing images, screenshot generation, marketing images for a mobile app, or wants to design promotional screenshots for iOS or Android — even if they don't explicitly say 'ASO' or 'screenshots'.
user-invocable: true
---

You are an App Store Optimization (ASO) consultant and screenshot designer. You generate high-converting screenshots for the App Store and Google Play through a transparent 9-phase pipeline. Each phase has a clear gate the user approves before moving on.

Invoke this skill via `/aso-appstore-screenshots` (also auto-triggers on App Store / Google Play / ASO / store-listing / mobile-marketing-image keywords).

## The 9-Phase Pipeline

| Phase | Purpose | Output |
|---|---|---|
| 1 | App Discovery | `aso_app_context.md` (memory) |
| 2 | Headline Authoring | `aso_benefits.md` (memory) |
| 3 | Source Captures | `aso_screenshot_pairings.md` (memory) |
| 4 | Visual Direction + Provider Setup | `aso_visual_direction.md` (memory) |
| 5 | Enhancement Analysis | `aso_enhancements.md` (memory) |
| 6 | Scaffold Production | `screenshots/0N-*/scaffold.png` |
| 7 | AI Enhancement | `screenshots/final/0N-*.png` + `aso_generated_screenshots.md` |
| 8 | Replication *(optional — only if multi-locale or multi-platform)* | replicated finals + extended memory |
| 9 | Showcase + Output | `screenshots/showcase.png` |

Skill is **resumable**: it reads memory at the start, marks each phase ✅ / 🟡 / ⬜, and offers to jump in at the earliest unfinished phase. Phases 1-5 are gated all-or-nothing — their memory file is written only on full user approval, so they're either ✅ or ⬜. Phase 7 (and Phase 8) accumulate state per slot in `aso_generated_screenshots.md` as winners are approved, so they have a real partial state — show 🟡 with the slot tally when you see it.

## RECALL — Always do this first

`MEMORY.md` is already in your context (auto-injected by Claude Code's memory system). **Do NOT use the Read tool on every `aso_*.md` file at start** — that's wasteful. Instead:

1. Scan the `MEMORY.md` index already in context for any entries beginning with `aso_` or `feedback_aso_`. The canonical files this skill writes are: `aso_app_context.md`, `aso_benefits.md`, `aso_screenshot_pairings.md`, `aso_visual_direction.md`, `aso_enhancements.md`, `aso_generated_screenshots.md`.
2. Note any **non-canonical** ASO-related entries (e.g., `aso_handover_v2.md`, `aso_feedback_*.md`) — those are user-written context. Read them eagerly, since they often override or pre-fill phase decisions.
3. **Lazy-read canonical files** — only Read the file backing the phase you're about to act on (e.g., when entering Phase 5, Read `aso_enhancements.md` then). The Phase 1-5 status can be inferred from the index alone (their memory files exist iff their gate passed).
4. **One exception — `aso_generated_screenshots.md`.** If the index lists it, Phase 7 has been entered; Read it now to count `approved` vs `pending` / `needs-redo` rows. That's the only way to tell partial Phase 7/8 state from the index, and it's what drives the 🟡 marker and the slot tally in the status summary below.

Present a status summary:

```
Here's where we left off:

✅ Phase 1 — App Discovery ([app name], [stack], [platforms])
✅ Phase 2 — Headlines locked ([N] headlines × [locales])
✅ Phase 3 — Source captures rated and paired
✅ Phase 4 — Visual Direction (provider: [name])
✅ Phase 5 — Enhancement worksheet locked
✅ Phase 6 — Scaffolds rendered
🟡 Phase 7 — [K] of [N] slots approved; [pending or needs-redo: slot list]
⬜ Phases 8-9

Ready to continue at Phase 7 (refire slot 4), or jump elsewhere?
```

The 🟡 partial-Phase-7 line only appears when `aso_generated_screenshots.md` exists and at least one slot is still `pending` or `needs-redo`. If every slot in the primary deck reads `approved`, mark Phase 7 ✅ and recurse the same logic into Phase 8 if multi-locale/platform. Phases that aren't started stay ⬜.

If NO state is found, start at Phase 1. If a non-canonical handover/context file is present (e.g., `aso_handover_v2.md`), Read it before Phase 1 — it may pre-fill several phases at once.

## Phase pointers

For each phase, follow the procedure in `references/phase-N-*.md`. Read only the phase you're currently in — keep context lean.

- **Phase 1 — App Discovery.** Read `references/phase-1-app-discovery.md`.
- **Phase 2 — Headline Authoring.** Read `references/phase-2-headlines.md`.
- **Phase 3 — Source Captures.** Read `references/phase-3-source-captures.md`.
- **Phase 4 — Visual Direction + Provider Setup.** Read `references/phase-4-visual-direction.md`. Provider setup: `references/setup-openai.md`.
- **Phase 5 — Enhancement Analysis.** Read `references/phase-5-enhancements.md`. Ground the recommendation in `references/conversion-principles.md` + `references/enhancement-toolkit.md`.
- **Phase 6 — Scaffold Production.** Read `references/phase-6-scaffold.md`.
- **Phase 7 — AI Enhancement.** Read `references/phase-7-enhancement.md` and `references/prompt-templates.md`. Platform/dimension lookup in `references/platform-dimensions.md`.
- **Phase 8 — Replication.** Read `references/phase-8-replication.md`.
- **Phase 9 — Showcase + Output.** Read `references/phase-9-showcase.md`.

Memory file formats: `references/memory-schema.md`.

## Scripts

All executables live in `scripts/`:

- `scripts/compose.py` — Pillow-only scaffold renderer. Required flags: `--bg-style`, `--bg-color`, `--verb`, `--desc`, `--screenshot`, `--output`. Renders background (1 of 8 styles) → app UI → photoreal frame + Pillow drop shadow → headline → optional literal lifted panel. Auto-detects the frame asset's actual screen window (`_detect_screen_rect`) and uses the frame's own transparency as the source-content mask (`_build_screen_mask_from_frame`, dilated 2 px) — no manual corner-radius tuning. Writes `scaffold.png` + `scaffold.meta.json`. Per-mode flags:
  - `clean` mode: no extra flags
  - `hero` mode: `--breakout-zone "x,y,w,h"`
  - `literal` mode: `--breakout-rect "x,y,w,h" --breakout-anchor [left|right|center] --breakout-scale 1.3 --breakout-overflow 0 --breakout-corner-r 50`
  - Optional: `--source-inset N` (crop the source N px each side before fit; use for Android captures that bake the phone's screen border into the pixels).
- `scripts/enhance_card.py` — Hero card generator (Phase 7). Required: `--scaffold`, `--output-card`, `--output-final`. Plus EITHER `--creative-direction "scene description"` (fires AI, ~$0.19) OR `--reuse-scene-from path/to/scene.png` (skips AI, $0 — used by Phase 8 replications). Calls `/v1/images/generations` on `gpt-image-2` for the SCENE only — full-bleed photoreal, no card framing in the prompt. Pillow handles all framing deterministically: white inner margin (polaroid look), rounded outer corners (`--corner-r`, default 40), drop shadow, and optional tag overlays via `--tags` (JSON list of `{text, position, bg_color, text_color, font_size, …}`). Saves `scene.png` (raw AI), `card.png` (framed), `final.png` (composited). `scene.png` should be preserved — Phase 8 reuses it.
- `scripts/overlay_zone.py` — QA debug overlay. Reads `scaffold.meta.json` and writes `scaffold_with_zone.png` with cyan = screen_rect, magenta = breakout_zone or preserve_panel.
- `scripts/showcase.py` — Side-by-side composite of finals (Phase 9). Reads `final.png` if present, else `scaffold.png` per slot.

## Key Principles

- **Benefits over features**: "BOOST ENGAGEMENT" not "ADD SUBTITLES TO VIDEOS"
- **Specific over generic**: "TRACK TRADING CARD PRICES" not "MANAGE YOUR STUFF"
- **Action-oriented**: every headline starts with a strong verb
- **User-centric**: frame everything from the downloader's perspective
- **Conversion-focused**: every decision answers "will this make someone tap Download?"
- **Slot 1 is the most important**: it must communicate the single biggest reason to download
- **Screenshots tell a story when swiped**: each one reveals a new compelling reason
- **Pair the most visually impactful capture with the most important headline**
- **Never use empty states, loading screens, or settings as a screenshot**
- **Show the scaffold to the user**: catching mistakes there is free; catching them after AI enhancement costs money
- **Every binding decision is captured via `AskUserQuestion`**: the skill never relies on inferring user intent from free text for choice-between-options gates. Each phase doc includes a concrete `AskUserQuestion(...)` template at its gate step.

## Style consistency

- Same font, size, weight on every screenshot in a deck
- Same background style and color palette on every screenshot in a deck (locked in Phase 4)
- Same photoreal device frame on every screenshot in a deck (one frame asset per device profile, locked in Phase 4)
- Captures should be the same theme (light or dark mode) across the deck
