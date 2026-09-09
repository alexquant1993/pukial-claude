# Setting up OpenAI gpt-image-2

The skill calls `/v1/images/generations` (NOT `/edits`) to generate the
**scene photo** for hero cards. Pillow handles all card framing
downstream — there is no chroma-key step. The model is always
`gpt-image-2`.

## Prerequisites

1. OpenAI account with billing enabled (gpt-image-2 is a paid model).
2. API key from https://platform.openai.com/api-keys.
3. Python SDK: `pip3 install openai pillow`.

## Auth

Export the key in your shell before running Phase 7:

```bash
export OPENAI_API_KEY=sk-...
```

The skill never writes this key to disk. To skip the AI call entirely
(replicating a previously-generated scene), pass `--reuse-scene-from
path/to/scene.png` to `enhance_card.py` — no key needed.

## API parameters used

```python
client.images.generate(
    model="gpt-image-2",
    prompt=<built-by-enhance_card.build_prompt>,
    size=f"{w}x{h}",   # scaled so short side ≥ 1024 px, mult-16
    quality="high",
    n=1,
)
```

The script targets the photo aspect (`card_w - 2*inner_margin` ×
`card_h - 2*inner_margin`) but scales the request up so the short side
meets gpt-image-2's minimum pixel budget (~1024 px), then downscales the
response back to the photo dimensions before Pillow composites the card.

**Not sent:** `background`, `mask`, input image, `input_fidelity`. Pure
generation, not edit.

## Cost

Approximate per-call cost at hero-card photo sizes (~1024–1500 short side
at high quality): **~$0.19 per fire**. A primary deck with 2 hero slots
costs ~$0.38. Refire cost is the same per attempt.

**Phase 8 replications cost $0** when `--reuse-scene-from` is used to
reuse a `scene.png` from the primary deck. Always preserve `scene.png`
files — they are auto-saved alongside `card.png`.

## Failure modes

| Failure | Cause | Fix |
|---|---|---|
| `400 invalid_value` — "Requested resolution is below the current minimum pixel budget" | Computed photo dims short side < 1024 px | `_api_size_for_photo` should scale up; verify the breakout zone is sane (>200×200) |
| `400 invalid_request_error: size` | Width or height not multiple of 16 | `_round_up_to_mult` should handle; check inner_margin isn't producing odd dims |
| AI paints a card frame / white border / label inside the scene | Prompt drift: `creative_direction` used UI-element vocabulary | Rewrite as a photo brief; remove "card", "frame", "label", "polaroid". See [prompt-templates.md](./prompt-templates.md) → "Writing creative_direction for the new pipeline" |
| Scene looks staged / glossy / magazine-y | Direction leaned aspirational | Add "lived-in", "honest", "casual smartphone photo", "no professional staging" |
| Scene subject doesn't match the slot | Direction was vague about subject + setting | Be specific: subject, setting, lighting, what NOT to include in frame |
| OPENAI_API_KEY not set | Env var missing | `export OPENAI_API_KEY=sk-...` — OR use `--reuse-scene-from` to skip the AI |
| Safety classifier blocks mid-batch | Recent user pushback on AI costs flagged subsequent calls as contradicting | Re-confirm with user before refiring; surface the cost explicitly |
