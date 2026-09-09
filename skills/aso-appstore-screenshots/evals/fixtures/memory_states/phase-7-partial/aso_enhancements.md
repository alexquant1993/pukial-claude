---
name: ASO enhancement worksheet
description: Locked enhancement plan for eval-3 (phase-7-partial state). Per-slot panel_mode + brief + derived block.
type: project
---
# Enhancement worksheet

## Slot 1 — GIVE / WHAT YOU DON'T NEED  (source: img01.png, donation form)

### Analysis
- **Hero on screen**: Foto Principal photo card with the donated item.
- **Headline-visual link**: the photo card IS what you give.
- **Density**: medium
- **PET levers**: E (emotion via lifestyle imagery)
- **Story-arc role**: Hook
- **Justification**: Source thumbnail is too scrappy to lift literally; AI reinterpretation lifts perceived quality (§2 show-don't-tell).

### Brief

What we lift
  The "Foto Principal" photo card on the donation form.

How big
  About 1.5× larger than it appears on screen.

Where it sits
  Left side of the phone, upper third, bleeds past the left bezel by about a thumb's width.

Mode
  HERO (AI-painted)

Creative direction (used verbatim in the AI prompt)
  "Magazine-quality lifestyle photo of a donated item in a warm cozy living-room setting, soft pillows, natural window light, no people. Polished floating card with rounded corners, soft drop shadow, small 'Foto Principal' tag at bottom-left. Premium lifestyle photography vibe."

### Derived
```yaml
panel_mode: hero
anchor: left
breakout_zone: [130, 920, 600, 820]
source_rect: null
scale: null
overflow_px: 100
creative_direction: "Magazine-quality lifestyle photo of a donated item in a warm cozy living-room setting, soft pillows, natural window light, no people. Polished floating card with rounded corners, soft drop shadow, small 'Foto Principal' tag at bottom-left. Premium lifestyle photography vibe."
```

## Slot 2 — GET / FREE STUFF  (source: img02.png, home feed)

### Analysis
- **Hero on screen**: 4-card item grid.
- **Headline-visual link**: any of the FREE item cards proves the headline.
- **Density**: busy
- **PET levers**: P (offer)
- **Story-arc role**: Shift
- **Justification**: Source cards are already on-brand and readable; literal lift preserves the FREE chip + distance pixel-perfect.

### Brief

What we lift
  The top-left item card (FREE chip + distance label).

How big
  About 1.5× larger.

Where it sits
  Left side of the phone, upper third, bleeds past the left bezel by about a thumb's width.

Mode
  LITERAL (Pillow lifted-panel)

### Derived
```yaml
panel_mode: literal
anchor: left
breakout_zone: null
source_rect: [40, 220, 560, 520]
scale: 1.5
overflow_px: 100
creative_direction: null
```

## Slot 3 — SAVED / 7 TONS OF CO2  (source: img03.png, impact screen)

### Analysis
- **Hero on screen**: 735 kg CO₂ stat card.
- **Headline-visual link**: the stat IS the proof.
- **Density**: sparse
- **PET levers**: T (trust via specific number)
- **Story-arc role**: Proof
- **Justification**: Number must not drift. Literal lift keeps "735 kg" pixel-exact.

### Brief

What we lift
  The "735 kg de CO₂ no emitido" stat card.

How big
  About 1.5× larger.

Where it sits
  Right side of the phone, middle of the screen, bleeds past the right bezel by about a thumb's width.

Mode
  LITERAL (Pillow lifted-panel)

### Derived
```yaml
panel_mode: literal
anchor: right
breakout_zone: null
source_rect: [120, 950, 1050, 360]
scale: 1.5
overflow_px: 100
creative_direction: null
```

## Slot 4 — SWAP / WITH NEIGHBORS  (source: img04.png, requests)

### Analysis
- **Hero on screen**: swap-request rows.
- **Headline-visual link**: a request row proves the swap concept.
- **Density**: medium
- **PET levers**: P (feature)
- **Story-arc role**: Feature
- **Justification**: Row text ("handbag for sneakers" etc.) must not paraphrase.

### Brief

What we lift
  The "handbag for sneakers" swap-request row.

How big
  About 1.4× larger.

Where it sits
  Left side of the phone, lower third, bleeds past the left bezel by about a thumb's width.

Mode
  LITERAL (Pillow lifted-panel)

### Derived
```yaml
panel_mode: literal
anchor: left
breakout_zone: null
source_rect: [60, 1100, 1180, 260]
scale: 1.4
overflow_px: 100
creative_direction: null
```

## Slot 5 — FIND / FREE NEAR YOU  (source: img05.png, map)

### Analysis
- **Hero on screen**: full map.
- **Headline-visual link**: the map IS the message.
- **Density**: full-bleed visual
- **PET levers**: P (feature)
- **Story-arc role**: Feature
- **Justification**: Any breakout fights the map (§4 don't compete with the screen).

### Brief

What we lift
  Nothing — the map is the hero.

Mode
  CLEAN

### Derived
```yaml
panel_mode: clean
anchor: null
breakout_zone: null
source_rect: null
scale: null
overflow_px: null
creative_direction: null
```
