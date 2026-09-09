# Phase 8 — Replication

**Goal:** Replicate the locked formula across remaining (locale × platform) combinations.

**Inputs:** All locked memory files from Phases 1-5. Approved primary deck from Phase 7.

## When this phase runs

Only when `aso_app_context.md` declares multiple platforms OR `aso_benefits.md`
has multiple locales. Otherwise skip to Phase 9.

## Procedure

For each remaining (locale, platform) combination:

1. **Confirm with user** that the formula is locked: bg + text + font + provider
   + enhancement worksheet + headlines per locale.

2. **Adjust device flag** for Android variants: `--device android` and target
   dimensions 1080×2400.

3. **Recompute coordinates per slot** *(only if the new variant has a different
   `device` than the primary deck — i.e., iOS → Android, or different iPhone
   profile)*. Both rect families need attention:

   **`breakout_zone` (hero mode)** — canvas-relative. Scale proportionally:
   ```
   new_zone = (
       old_x * (new_canvas_w / old_canvas_w),
       old_y * (new_canvas_h / old_canvas_h),
       old_w * (new_canvas_w / old_canvas_w),
       old_h * (new_canvas_h / old_canvas_h),
   )
   ```
   Round to ints. Sanity-check that `new_x + new_w` is still inside the
   new canvas width.

   **`source_rect` (literal mode)** — captured against the iOS source image.
   The Android source capture is a *different image* with different dimensions,
   so the rect doesn't transfer. **Re-pick** the rect against the new locale's
   capture — same UI element, freshly bounded. Update the slot's
   `derived.source_rect` and `derived.device`.

   If the variant only changes locale (same device profile), no recompute is
   needed; the existing rects still apply because the source captures share
   dimensions across locales for the same platform.

4. **Run Phase 6** (scaffold) for the new variant. Use the locale-specific
   captures from `screenshots/source/{platform}/{locale}/imgNN.png`.

   **Android-only caveats:**
   - Android source captures may bake the phone's own rounded screen border
     into the pixels. If you see a thin dark band hugging the phone's screen
     curve in the rendered scaffold, pass `--source-inset 12` (or similar)
     to crop the source before fit-to-fill.
   - The literal-mode `--breakout-corner-r` should be smaller on Android
     (~35) than on iOS (~50) because Android panels are scaled down to fit
     the 1080×2400 canvas, and the same absolute radius reads as
     over-rounded on the smaller panel.
   - Source layouts may differ slightly between platforms (different
     padding, dividers in different places). Always **re-pick `source_rect`
     against the new platform's captures** rather than trusting the iOS
     rect; verify by self-inspecting the cropped top and bottom of the
     lifted panel.

5. **Show scaffold thumbnails** to user. Sanity check the recomputed rects
   landed correctly.

6. **Run Phase 7 with scene reuse** ($0 AI cost). The primary deck's
   `scene.png` for each hero slot is reused across all replicas — only the
   Pillow framing re-renders, with translated tags for English variants:

   ```bash
   python3 "$SKILL/scripts/enhance_card.py" \
     --scaffold "$SLOT/scaffold.png" \
     --reuse-scene-from "$PROJECT/screenshots/es-ios/01-regala/scene.png" \
     --output-card "$SLOT/card.png" \
     --output-final "$SLOT/final.png" \
     --tag-font-path "$PROJECT/screenshots/fonts/Nunito-Bold.ttf" \
     --tags '[{"text":"Main Photo","position":"bottom-center","bg_color":"#000000B0","font_size":24}]'
   ```

   `--reuse-scene-from` skips the OpenAI call. `--creative-direction` is
   not required when reusing a scene. Pillow re-frames the card with new
   `--tags`, fits to the variant's `breakout_zone` (Android cards are
   smaller than iOS cards because the canvas is smaller), and composites
   onto the variant's scaffold.

   Tag translations to map across locales:

   | es tag | en equivalent |
   |---|---|
   | `Foto Principal` | `Main Photo` |
   | `GRATIS` | `FREE` |
   | distance pills (`4.3 km`) | stay the same |

7. **User reviews and approves** slot-by-slot. Re-fires for a variant
   should re-use the scene (not the AI) unless the scene itself is the
   problem.

8. **Save** to `screenshots/{locale}-{platform}/0N-<verb>/final.png`
   (hero slots) or `…/scaffold.png` (literal/clean slots — the scaffold IS
   the final).

## Output

Final files for all variants. Extend `aso_generated_screenshots.md` with one
section per variant.

After every slot in a replicated deck is user-approved, run the same
`{deck}/final/` promotion step described in Phase 7. Each replica gets its
own flat upload folder at `screenshots/{locale}-{platform}/final/0N-<verb>.png`.

## Gate

User approves each variant. Replicas can be produced in any order — the formula
doesn't change between them.

## AskUserQuestion gate

Once the primary deck (e.g., es-iOS) is locked, ask which decks to replicate:

```python
AskUserQuestion(questions=[{
    "question": "Which decks should we replicate now? Pick all that apply.",
    "header": "Replicate decks",
    "multiSelect": True,
    "options": [
        {"label": "en-iOS", "description": "English headlines, iOS source captures."},
        {"label": "es-Android", "description": "Spanish headlines, Android source captures."},
        {"label": "en-Android", "description": "English headlines, Android source captures."}
    ]
}])
```

Then per replicated slot, the Phase 6/7 gate templates from those phase
docs apply.
