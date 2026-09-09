# Phase 5 — Enhancement Analysis

**Goal:** For each slot, examine the source screen and propose a **breakout brief** in plain English: what gets lifted, how big, where it sits, who paints it (Pillow or AI), and — for AI mode — a one-line creative direction. Show all briefs to the user. Lock once approved.

**Inputs:** `aso_benefits.md` (headlines), `aso_screenshot_pairings.md` (slot ↔ screen), `aso_visual_direction.md` (colors, fonts).

**Required reading before starting:**
- [`conversion-principles.md`](./conversion-principles.md) — universal principles + PET model
- [`enhancement-toolkit.md`](./enhancement-toolkit.md) — patterns + selection matrix

## Why this phase exists

Static "every slot gets a primary breakout" templates produce drift across slots and miss the conversion case-by-case. The right enhancement depends on what each specific (screen, headline) pair needs to say. Phase 5 forces the analyst to look at each slot, reason about what would actually convert, and pick deliberately.

## The three modes

Per slot, pick exactly one:

| Mode | Who paints the breakout | When to use |
|---|---|---|
| `hero` | **AI + Pillow** — AI paints a full-bleed scene photo (guided by `creative_direction`); Pillow builds the polaroid card around it (white inner margin, rounded outer corners, drop shadow, optional tag overlays) and composites onto the scaffold | Lifestyle / object / emotional UI element where a reinterpreted photo beats literal lift (e.g., a scrappy app thumbnail of a sofa). Raw scene is auto-saved to `scene.png` for $0-AI replication across locale/platform variants. |
| `literal` | **Pillow** — pre-renders the lifted UI panel as a deterministic crop+scale+shadow | Text or numbers that can't drift (e.g., "735 kg", "Cambio bolso por deportivas") |
| `clean` | Neither — no breakout | Screen IS the message (full map, full-bleed photo, single huge stat covering the screen) |

## Procedure

### Step 1 — Per-slot conversion analysis

For each of the N slots, answer in writing (one or two sentences each):

1. **Hero check**: most attention-grabbing element on this screen?
2. **Headline–visual link**: what visual on the screen is the literal proof of the headline? If nothing proves it, escalate to user.
3. **Density check**: sparse / medium / busy?
4. **PET levers**: which of P (Persuasion / benefit), E (Emotion), T (Trust / proof) does the headline target?
5. **Story-arc role**: Hook / Core A / Core B / Trust / Activation? (Slot 1 is always Hook.)

### Step 2 — Pick a mode

Apply in order:

1. Screen IS the message (full map / full-bleed photo) → **`clean`**.
2. Breakout content includes critical text or numbers that can't drift → **`literal`**.
3. The hero element is a lifestyle / object / emotional thing where AI reinterpretation lifts it from "scrappy app photo" to "magazine quality" → **`hero`**.
4. None of the above fit cleanly → **`clean`** (don't force it).

When in doubt, simpler beats overdesigned. ("§4 don't compete with the screen.")

### Step 3 — Compose the brief

For each non-clean slot, produce a brief. The skill **proposes** the location, size, and direction using the defaults below; the user approves or adjusts.

#### Defaults the skill uses to propose

**Hero zone (AI mode):**
- Width: 55–65% of the screen rectangle width
- Height: 30–40% of the screen rectangle height
- Anchor side: the side where the source element naturally sits on screen (left if it's on the left, right if right)
- Bleed past bezel: ~8% of canvas width on the anchored side
- Vertical position: roughly aligned with where the source element appears on screen (typically top 20–55% of the screen rect)

**Literal panel (Pillow mode):**
- Source rect: the bounding box of the UI element to lift (cropped from the source screenshot in source-image coordinates)
- Scale: 1.4–1.6× (hard cap **1.8×** — past that the panel dwarfs the phone)
- Anchor + bleed: same rules as hero

**Both modes** record their canvas-space rect as the `breakout_zone` in `scaffold.meta.json`. `compose.py` reserves that zone as empty space on the scaffold; `enhance_card.py` (hero mode) reads it to size the AI canvas and composite the painted card back in.

### Step 3.5 — Verify rects/zones visually (recommended)

Coordinates are easy to get wrong by 100+ px when eyeballing a 1290×2796 source. Before locking the brief, overlay the rect/zone onto the source so you catch off-by-one mistakes for free:

```bash
# For literal mode — overlay source_rect on the source screenshot:
python3 "$SKILL_DIR/scripts/preview_crop.py" \
  screenshots/source/ios/es/imgNN.png "x,y,w,h" /tmp/preview.png "slotN label"

# Read /tmp/preview.png to confirm the magenta box tightly bounds the intended UI element.
```

For hero mode the zone lives in canvas coordinates (not source coordinates), so verify *after* you scaffold instead — see [Phase 6 → Visualizing the breakout zone](./phase-6-scaffold.md).

If the box is misaligned, fix the rect in this worksheet before continuing.

### Step 4 — Write the worksheet

Save to `aso_enhancements.md` in memory. Per slot, two parts:

**1. Plain-English brief** (for human review).

```markdown
### Slot N — VERB DESCRIPTOR  (source: imgNN.png, [one-line screen description])

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

[ For HERO only: ]
Creative direction (used verbatim in the AI prompt)
  "[one-line vibe + subject + style]"
```

**2. Derived block** (consumed by `compose.py` and `enhance_card.py`).

```yaml
panel_mode: hero | literal | clean
device: iphone-6.9                       # canvas these rects were authored against
anchor: left | right | center | null     # 'center' added in v3.1; null for clean
breakout_zone: [x, y, w, h] | null       # HERO: canvas coords (analyst sets it). LITERAL: leave null — compose.py derives the actual zone from the painted panel and writes it to the sidecar. CLEAN: null.
source_rect: [x, y, w, h] | null         # source-image coords (literal only)
scale: 1.5 | null                        # literal only (cap 1.8)
overflow_px: 100                         # bleed past bezel (literal only)
corner_r: 24 | 50 | null                 # literal only — outer panel radius; bump to ~50 if the source card has natural rounded corners with whitespace around them
creative_direction: "..." | null         # hero only — required, validated at Step 5; describe the SCENE only (no card framing language — that's Pillow's job)
tags:                                    # hero only — optional Pillow overlays drawn on the photo
  - text: "Foto Principal"               # required
    position: bottom-center              # one of top/bottom × left/right/center
    bg_color: "#000000B0"                # hex; supports 8-digit alpha
    text_color: "#FFFFFF"                # default white
    font_size: 24                        # default 26
```

For platform/locale variants of the same hero slot, only `tags` typically
change (text translation); `creative_direction` can stay constant because
Phase 8 reuses the saved `scene.png` via `--reuse-scene-from`.

The `device` field is required so Phase 8 replication can recompute rects when the variant has a different canvas (e.g., iOS → Android).

The `derived` block is what Phase 6 (`compose.py`) and Phase 7 (`enhance_card.py`) actually read. The brief is for human review.

### Step 5 — Validate

Before presenting to the user, check each slot:

- **Hero mode requires `creative_direction`.** If `panel_mode: hero` and `creative_direction` is null/empty, the slot is invalid — re-author the brief or fall back to `literal` / `clean`. The Phase 7 `hero` prompt block interpolates `{creative_direction}` verbatim; an empty value produces a hollow prompt and the AI will paint something arbitrary or skip the panel entirely.
- **Literal mode requires `source_rect`, `anchor`, and `scale`.** Missing any of these means `compose.py` can't paint the panel.
- **`scale` is capped at 1.8×.** `compose.py` will reject larger values.

If any slot fails validation, fix it before Step 6.

### Step 6 — Present to user, lock

Show the briefs as a vertical list (not a table — the prose matters). Highlight the per-slot mode and ask: **"Approve as drafted, or edit which slots?"** When user approves, save `aso_enhancements.md` and link from `MEMORY.md`.

## Skipping the analysis

If the user says "just decide, you pick" — do the analysis silently, write the worksheet, and present the finished version for sign-off. Don't skip the reasoning; the worksheet is what Phase 7 prompts consume, so the rationale has to be in writing.

## Common mistakes

- **Picking `hero` because it looks cool** — only pick it when the source rect is too scrappy / abstract to lift literally. If the on-screen element is already premium, prefer `literal` so it stays on-brand.
- **Picking `literal` for a slot with critical text the source rect doesn't actually contain** — re-pair the slot or pick `clean`.
- **Two breakouts in one slot** — never. Pick one.
- **Skipping the headline–visual link question** — produces slots where the visual doesn't support the headline; users feel it even if they can't articulate it.
- **Treating slot 1 like the others** — slot 1 carries 2× weight; spend more thinking time on it.

## Output

Memory file: `aso_enhancements.md` (briefs + derived blocks).

## Gate

User has signed off on the per-slot briefs. Phase 6 (scaffold) and Phase 7 (AI enhancement) consume the derived blocks directly.

## AskUserQuestion gates (per slot)

### Step 1 — panel_mode per slot

```python
AskUserQuestion(questions=[{
    "question": "Slot N panel_mode: hero (AI paints a card), literal (Pillow lifts a UI panel), or clean (no breakout)?",
    "header": "Slot N mode",
    "multiSelect": False,
    "options": [
        {"label": "hero", "description": "AI paints a creative card per creative_direction. Use for editorial / hero moments."},
        {"label": "literal", "description": "Pillow lifts a literal UI element from the screen. Use when the proof is on-screen (numbers, badges)."},
        {"label": "clean", "description": "No breakout — the screen IS the message. Use for map / hero captures."}
    ]
}])
```

### Step 2 — confirm creative_direction (hero slots only)

After the user authors the free-text `creative_direction` string:

```python
AskUserQuestion(questions=[{
    "question": "Lock creative_direction for slot N: '{text}' ?",
    "header": "Creative direction",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Use this verbatim in the Phase 7 prompt."},
        {"label": "Revise", "description": "Edit the text — try again."}
    ]
}])
```
