# Hero card prompt template

Phase 7 (hero-mode slots only). `enhance_card.py` asks `gpt-image-2` to
paint ONE photoreal scene that fills the entire AI canvas edge-to-edge.
**No card framing, border, rounded corners, or text labels are requested
from the AI** — Pillow handles all of that downstream, deterministically.

The AI returns an opaque image (gpt-image-2 doesn't support transparent
output). That image becomes the photo content of a polaroid-style card:
Pillow resizes it into the photo area inside a white inner margin, applies
a rounded outer mask, draws any tag overlays, and composites it onto the
scaffold with a drop shadow.

## The prompt

```
A magazine-quality photoreal scene that fills the entire canvas edge-to-edge. The image must be ONE coherent photograph — no card frame, no white border, no rounded corners, no drop shadow, no UI chrome, no text overlays, no labels, no decorative elements, no collage. Just the photograph.

SCENE:
{scene_description}

Fill the full image with the scene. No whitespace, no padding, no margins, no vignette.
```

## How it's assembled

`enhance_card.build_prompt(scene_description)` substitutes the per-slot
`creative_direction` string from `aso_enhancements.md` into the
`{scene_description}` placeholder.

Wrapper alone: ~80 words. Total with a typical scene description (40–80
words): ~120–160 words.

## What the AI never sees

- The card framing (white margin, rounded corners, drop shadow — all Pillow)
- Tag overlays like "Foto Principal" or "GRATIS" (Pillow draws them)
- The headline text (Pillow renders it on the scaffold)
- The phone chassis (Pillow composites the frame PNG)
- The app UI inside the screen
- The canvas background

The AI sees only the scene brief and an empty canvas. The card aesthetic
is the same on every refire because Pillow owns it.

## API call

```python
response = client.images.generate(
    model="gpt-image-2",
    prompt=prompt,
    size=f"{w}x{h}",   # photo area, scaled so short side ≥ 1024 px, mult-16
    quality="high",
    n=1,
)
```

`gpt-image-2` requires a minimum pixel budget (~1024 short side). The
script scales the requested size up proportionally to clear that minimum
and resizes the response back down before framing.

No `background` parameter, no mask, no input image, no `input_fidelity`.

## Writing `creative_direction` for the new pipeline

**Describe the scene, not the card.** Words like "card", "frame",
"polaroid", "rounded corners", "drop shadow", "label", "badge",
"thumbnail" tend to push the AI back toward UI-element framing — which
Pillow already handles and will conflict with.

What works:

- **Format hint**: "A casual smartphone photo (iPhone, natural lighting,
  no professional staging)…"
- **Subject**: explicit, photo-able (a single sofa, one coat on a hanger).
- **Setting**: real-world location ("a real Madrid apartment hallway", "a
  sunlit living room").
- **Mood**: "lived-in", "honest", "gently used", "well-loved" — leans the
  model away from glossy / staged.
- **Lighting**: "soft daylight from a nearby window", "bright daylight from
  a window on the left". Specifies direction + intensity.
- **What to avoid in frame**: "no people, no faces, no clutter".

What to avoid:

- "Polished editorial card with rounded corners and a label" — pulls the AI
  toward drawing card framing, which conflicts with Pillow's framing.
- "Magazine-quality, professionally lit, styled" — produces glossy stock
  imagery that looks fake for a peer-to-peer donation app.

## Tags (Pillow, not AI)

Tag overlays go in the `--tags` JSON flag, NOT in the prompt. The AI
won't draw them reliably. See `phase-7-enhancement.md` for the tag schema.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| AI paints a frame / border / label inside the scene | Scene description used UI-element vocabulary | Rewrite as a photo brief; remove "card", "frame", "label" |
| Scene looks staged / glossy | Description leaned magazine-y | Add "lived-in", "honest", "no professional staging", "soft natural daylight" |
| API returns `400 invalid_value` for size | Computed photo dims < 1024 px short side | Verify the breakout zone is sane (>200×200) and `_api_size_for_photo` is rounding correctly |
| Scene content doesn't match the slot's headline | Direction was vague about the subject | Be explicit about subject + setting |
