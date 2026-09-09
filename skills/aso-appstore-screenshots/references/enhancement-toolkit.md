# Enhancement Toolkit

Three breakout modes paired with how they're rendered. For every slot, Phase 5 picks **at most one** mode. More than one focal pattern dilutes conversion (see [conversion-principles.md](./conversion-principles.md) §3, §6).

## How patterns are implemented

Each mode below maps to one of:

- **Deterministic** (Pillow / `compose.py`) — text or specific UI cutouts that must not drift; baked directly into the scaffold. Pillow also renders the background, app UI, device frame, drop shadow, headline band, and (for `literal` mode) the lifted panel. AI never touches the scaffold.
- **AI prompt** (`gpt-image-2`) — used in v3+ for one thing only: painting a full-bleed photoreal scene for `hero` slots. Pillow then frames that scene into a polaroid-style card (white inner margin, rounded outer corners, drop shadow, optional tag overlays) and composites it onto the scaffold. AI does NOT render device frames, shadows, card framing, text labels, or backgrounds.

Always prefer deterministic when a pattern involves text, exact numbers, or specific UI that must replicate across the deck without drift.

---

## 1. `hero` — AI-painted breakout

`compose.py` reserves the `breakout_zone` as empty space on the scaffold. `enhance_card.py` asks AI to paint a full-bleed scene photo for that zone (no card framing in the prompt), then Pillow builds the polaroid card around the photo: white inner margin, rounded outer corners, drop shadow, optional tag overlays (`Foto Principal`, `GRATIS`, distance pills). The framed card is composited onto the scaffold to produce `final.png`. The raw scene is also saved to `scene.png` so Phase 8 replications can reuse it at $0 AI cost.

**When to use**
- The slot's benefit lives in a UI element whose source-rect content is too **scrappy / abstract / placeholder-y** to lift literally — a small thumbnail, a tile in a noisy grid, an item card with poor lighting.
- The headline targets the E (Emotion) lever and a magazine-quality reinterpretation of the subject converts better than a faithful crop of the app UI.
- Lifestyle / object / consumer-emotional categories where premium presentation lifts perceived quality.

**When to avoid**
- The breakout content includes specific text or numbers that can't drift (use `literal` instead).
- The screen IS already premium and lifting it literally would convey the message faithfully (use `literal`).
- The screen IS the message (full map, full-bleed photo) — no breakout helps.

**Implementation**: scene-only AI prompt + Pillow framing. `compose.py --breakout-zone "x,y,w,h"` reserves the zone on the scaffold and records it in `scaffold.meta.json`. `enhance_card.py` requests a full-bleed scene sized to the photo area (zone minus inner_margin), saves it as `scene.png`, then renders the polaroid card around it and composites onto the scaffold. See [`prompt-templates.md`](./prompt-templates.md) for the scene prompt and [`phase-7-enhancement.md`](./phase-7-enhancement.md) for the tag schema.

**Reproducibility lever**: the locked `creative_direction` line + `scene.png`. Same scene file + new tag list = a fully deterministic refresh (for tag-text translations, locale variants) without an AI call.

**Conversion principle**: §2 (show, don't tell), PET-E (emotion).

---

## 2. `literal` — deterministic UI panel (Pillow lifted lift)

A real card or row from the screen, scaled up, pasted by Pillow so it crosses the device bezel. Casts a soft shadow. Fully deterministic — AI never touches it (literal-mode slots skip Phase 7 entirely).

**When to use**
- The slot's benefit lives inside a single visible UI component AND the component IS the literal proof of the headline — a stat number, a request row text, a price tag, a notification.
- The breakout content includes specific text or numbers that **cannot drift** (e.g., "735 kg", "Cambio bolso por deportivas").
- The component on screen is already premium / readable / on-brand and a faithful enlargement conveys the message.

**When to avoid**
- The source rect content is scrappy or placeholder-y — use `hero` so AI can reinterpret.
- The screen is already busy (4-card grid, dense feed) — pop-out adds visual noise.
- More than one panel competes for the role — pick one, drop the rest.
- The screen IS the message (full map, full-bleed photo) — pop-out fights the screen.
- The component contains user-specific PII that shouldn't be enlarged.

**Implementation**: deterministic. `compose.py --breakout-rect "x,y,w,h" --breakout-anchor [left|right|center] --breakout-scale 1.3 --breakout-overflow 0 --breakout-corner-r 50`. The `center` anchor (added in v3.1) centers the panel horizontally with bleed on both bezels — useful when the source element is itself centered on screen. `--breakout-corner-r` tunes the panel's outer corner radius (default 24); bump it to ~50 to mask away whitespace around a source card's natural rounded corners. The painted panel's canvas bbox is recorded in `scaffold.meta.json`. The scaffold IS the final — `literal` slots skip Phase 7.

**Subsumes**: the old `number-callout` pattern. A number callout is a `literal` lift whose rect is a number on screen rather than a card. Rendering is identical.

**Conversion principle**: §2 (show, don't tell), §5 (specificity), PET-T (trust via numbers when the rect is a stat).

---

## 3. `clean` — no breakout

Phone + headline + Pillow-rendered background + Pillow-rendered device frame and drop shadow. No floating panels, no AI. The scaffold IS the final.

**When to use**
- The screen IS the hero (full map, full-bleed photo, big single number covering the screen).
- Slot 1 of premium / productivity / B2B apps where calm reads as competent.
- Mid-deck breather between two visually loud slots.
- High-density app categories where "clean" is the differentiator.

**When to avoid**
- High-competition consumer categories (games, social, e-commerce) where attention is scarce — clean reads as forgettable.
- When the headline alone doesn't carry the message — clean exposes weak copy.

**Implementation**: phone + headline + background only. No breakout flags. Pillow renders everything; no AI call is made.

**Conversion principle**: §4 (don't compete with the screen), §8 (consistency via restraint).

---

## Pattern selection matrix

| Slot type | Default mode | Alternates |
|---|---|---|
| Slot 1 hook with hero UI element, source rect is scrappy | `hero` | — |
| Slot 1 hook with hero UI element, source rect already premium | `literal` | `hero` |
| Slot 1 with strong full-screen visual (map, photo, big stat covering the screen) | `clean` | — |
| Stat / proof slot with a real number on screen | `literal` (number must not drift) | — |
| Workflow / step slot | `literal` lift of one step | `clean` |
| Differentiator slot vs. competitor with a unique on-screen feature | `literal` lift of that feature | `hero` if the feature is best shown as a lifestyle card |
| Lifestyle / emotion / community slot with object content | `hero` | — |
| Full-bleed map / photo / big stat | `clean` | — |

This is a starting point, not a law. The Phase 5 analyst always chooses based on the specific (screen, headline) pairing — see decision rules in [`phase-5-enhancements.md`](./phase-5-enhancements.md) Step 2.

## What every slot gets regardless

- Photoreal device frame (Pillow, from the bundled frame PNG)
- Soft drop shadow under device (Pillow)
- Background per the locked style + colors (Pillow, one of 8 styles)
- Headline at locked anchor position (Pillow, deterministic)

## What no slot ever gets

- Fake App Store / Play Store badges
- Fake star ratings
- "Install now" / "Try now" CTAs
- Superlative claims ("#1", "best", "world's only")
- Competitor name-checks
- Real user PII / personal data in screens
- Outdated device chrome (home-button iPhone, etc.)
- Multiple competing focal patterns in one slot
- Light beams, lens flares, harsh radial glows, sparkle bursts on the background
- 3D / chrome / gloss / glow halos / outlines / gradients on the headline letters

---

## Retired patterns (reference only)

The following patterns from earlier toolkit versions are no longer first-class:

- **stamp** — folded into `literal` when the binary claim already lives on screen as a UI element; otherwise prefer `clean` over a stamp. AI-rendered stamps in v1 drifted on text and rotation.
- **number-callout** — alias for `literal` (same rendering, same mask).
- **quote-card** — never reached production; required a deterministic text renderer that doesn't exist. AI-rendered quotes drift.
- **real-context-overlay** — AI-painted background with a hand / environment behind the device. Removed because it competed with the breakout for the AI's painting budget. The new BACKGROUND block lets AI add restrained ambient depth in the side margins, which covers most of the same ground without the competition.
- **decorative motif (dots / swirls / sparkles)** — replaced by the single vibe-led BACKGROUND block. Motifs added geometry constraints without lifting conversion.
