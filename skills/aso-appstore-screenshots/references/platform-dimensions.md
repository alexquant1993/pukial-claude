# Platform Dimensions

App Store and Google Play accept specific portrait dimensions for screenshots.

## iOS — App Store Connect

App Store Connect rejects screenshots that don't match exactly.

| Display | Portrait dimensions | `--device` flag |
|---|---|---|
| iPhone 6.5" | 1242 × 2688 | `iphone-6.5` |
| iPhone 6.7" | 1290 × 2796 | `iphone-6.7` |
| iPhone 6.9" | 1320 × 2868 | `iphone-6.9` |

**Default:** iPhone 6.9" (1320 × 2868) — Apple's primary required size. Up to 10 screenshots per display size.

**Aspect ratio note:** Apple's portrait sizes are narrower than 9:16. gpt-image-2
generates at 1024×1536. Phase 7 ends with
a sips crop+resize loop that trims sides equally and resizes to the target.

## Android — Google Play Store

| Device | Portrait dimensions | `--device` flag |
|---|---|---|
| Phone | 1080 × 1920 | `android` |

**Default:** 1080 × 1920 (9:16, the skill's compose profile target).

**Play Console upload requirements (verbatim from Google):**
- 2–8 phone screenshots per listing.
- PNG or JPEG.
- Max 8 MB per file.
- Aspect ratio **16:9 or 9:16** (the skill renders 9:16 portrait).
- Each side between **320 px and 3,840 px**.

The earlier default of 1080 × 2400 (9:20 ≈ 2.22:1) violates the 16:9 / 9:16 requirement and is rejection-prone — stay at 9:16 or use a wider ratio.

## Crop+Resize Snippet

Used at the end of Phase 7. Adjust `TARGET_W` / `TARGET_H` per platform.

```bash
TARGET_W=1290 && TARGET_H=2796 && \
for INPUT in screenshots/01-*/v1.png screenshots/01-*/v2.png screenshots/01-*/v3.png; do
  OUTPUT="${INPUT%.png}-resized.png"
  cp "$INPUT" "$OUTPUT"
  W=$(sips -g pixelWidth "$OUTPUT" | tail -1 | awk '{print $2}')
  H=$(sips -g pixelHeight "$OUTPUT" | tail -1 | awk '{print $2}')
  CROP_W=$(python3 -c "print(round($H * $TARGET_W / $TARGET_H))")
  OFFSET_X=$(python3 -c "print(round(($W - $CROP_W) / 2))")
  sips --cropOffset 0 $OFFSET_X --cropToHeightWidth $H $CROP_W "$OUTPUT"
  sips -z $TARGET_H $TARGET_W "$OUTPUT"
done
```

## Validation

After resize, verify dimensions:

```bash
sips -g pixelWidth -g pixelHeight screenshots/01-*/v1-resized.png
```

Mismatch means crop math drifted — re-run from the beginning of the loop.
