# Phase 2 — Headline Authoring

**Goal:** Lock 3–5 benefit headlines per locale, structured around the Solt/Teodora ASO framework.

**Inputs:** `aso_app_context.md` from Phase 1.

## The Solt framework

Five-slot deck, in swipe order:

| # | Slot | Purpose |
|---|---|---|
| 1 | Pain | Surfaces the problem the user has today |
| 2 | Shift | Names the payoff — what changes after install |
| 3 | Proof | Credibility moment — number, social proof, outcome |
| 4 | Feature | Unique mechanic / killer feature |
| 5 | Feature | Second feature, often delivers on slot 2's promise |

For 3–4 slot decks, drop slot 5 first, then slot 1.

## Drafting rules

1. **Lead with an action verb** — TRACK, GIVE, BUILD, FIND, SAVE, BOOST, etc.
2. **Frame what the user gets**, not what the app does technically.
3. **Be specific** — "TRACK TRADING CARD PRICES" not "MANAGE COLLECTION".
4. **Answer the unspoken question**: "Why download this instead of scrolling past?"
5. **Keep desc short enough to wrap to ≤2 lines at base size.** Phase 6's renderer auto-shrinks the desc font to fit `--max-desc-lines` (default 2), so long phrases get visibly smaller. Aim for ≤4 short words in the descriptor; check the longest-locale rendering early. Long phrases like ES "LO QUE NECESITAS GRATIS" sit on the edge and force a font-size drop.

## Procedure

1. **Draft natively in each target locale.** Don't auto-translate. For es-ES,
   prefer warm everyday verbs (REGALA over DONA, CONSIGUE over OBTÉN).

2. **Present to user** with reasoning per headline:

```
Here are the proposed headlines:

1. [VERB] / [DESCRIPTOR] — [why this slot, why this verb]
2. ...
```

3. **Iterate** until the user confirms. Push back politely if they pick generic
   over specific.

## Output

Write `.aso/aso_benefits.md` per `memory-schema.md`. Add a one-line entry to `.aso/MEMORY.md`.

## User approval gate (per slot)

For each of the 5 slots' verb + descriptor pairs:

```python
USER_INPUT_GATE(questions=[{
    "question": "Slot N headline '{verb} / {desc}': approve, revise wording, or pick a different framework slot?",
    "header": "Slot N headline",
    "multiSelect": False,
    "options": [
        {"label": "Approve", "description": "Lock this verb + descriptor."},
        {"label": "Revise wording", "description": "Tweak verb or descriptor; keep the framework slot."},
        {"label": "Different framework slot", "description": "Try a different role in the Solt framework (Pain → Shift → Proof → Feature×2)."}
    ]
}])
```
