# Conversion Principles

App-agnostic principles for App Store / Google Play screenshots that drive install conversion. Use these to reason about per-slot enhancement choices in Phase 5.

## Two anchor numbers

Lead every design decision with these two evidence-backed facts:

1. **~60% of App Store visitors decide from slot 1 alone, without scrolling.** ([Storemaven](https://www.storemaven.com/academy/app-store-statistics-revealed/))
2. **Creative A/B testing produces 19–26% average install CVR lift.** ([SplitMetrics](https://splitmetrics.com/blog/ab-testing/))

Implication: slot 1 carries roughly 2× the conversion weight of any other slot. Invest the most polish there. Other slots are for the ~40% who explore.

## The PET frame (Phiture)

Every slot must hit at least one of:

- **P — Persuasion**: a clear benefit the user gets (not a feature the app has)
- **E — Emotion**: a feeling — relief, delight, status, belonging, savings, safety
- **T — Trust**: proof — numbers, testimonials, real screens, real data

Slots that hit zero PET levers don't earn their place. Slot 1 should hit at least two. ([Phiture PET model](https://phiture.com/asostack/ios-15-our-flywheel-approach-to-screenshots/))

## The 8 principles

### 1. Slot 1 is a search-result ad creative, not a screenshot

iOS search results render the first portrait screenshot (or first 1–3 landscape screenshots) without a tap. ([SplitMetrics](https://splitmetrics.com/blog/app-store-screenshots-aso-guide/)) Slot 1 must communicate the single biggest reason to download in isolation. Do not assume context from slot 2+.

**Wins in slot 1**: short benefit headline (3–7 words) + visible UI proving the claim + bold high-contrast text. **Loses in slot 1**: logo + tagline only, "Welcome to X" splash, multi-feature collage, award badge as hero.

### 2. Show, don't tell

Real app UI beats stock imagery. Generic photos of people on phones are a documented trust killer. ([AppTweak](https://www.apptweak.com/en/aso-blog/how-to-optimize-your-app-screenshots)) When a screen has a hero element that is the literal proof of the headline (a chat bubble, a price, a stat), lift it — don't paraphrase it with a generic icon.

### 3. One message per slot

Every guide converges on this. ([Gummicube](https://www.gummicube.com/blog/are-landscape-or-portrait-screenshots-better-for-app-store-optimization), [AppTweak](https://www.apptweak.com/en/aso-blog/how-to-optimize-your-app-screenshots)) Multiple competing pop-outs, two stamps, or stamp + decorative motif + breakout in one slot all dilute conversion. Pick one focal enhancement.

### 4. Don't compete with the screen

If the screen IS the message — a full map, a big single number, a full-bleed photo — adding a pop-out or stamp fights it. Strip enhancements down to phone + shadow + headline. The screen is doing the work.

### 5. Specificity beats abstraction

"735 kg CO₂ not emitted" wins over a leaf icon. "1M users" wins over a community sticker. Real numbers and real items earn trust; generic symbols feel like marketing. The exception: stamps for binary value claims (FREE / NEW / 0€) where the abstraction *is* the message.

### 6. One focal point per slot

Eye flow on a portrait screenshot is **headline → hero → bottom edge**. The enhancement (pop-out, stamp, callout) must land on this path, not cross it. If you have two candidate enhancements, pick the one that sits on the eye path; drop the other.

### 7. Color contrast is non-negotiable

WCAG **4.5:1** for body text, **3:1** for large text — necessary but not sufficient. ([ScreenMagic](https://appscreenmagic.com/guides/app-store-screenshot-background-ideas)) Test legibility at thumbnail size (~100 px wide in search results). A green leaf on warm pink technically passes contrast but reads busy — drop it.

### 8. Style consistency across the deck

Same font stack, background system, device frame, text anchor position across all slots. Vary the dominant *content* (different screens, different colors inside the screen) — never the *frame*. ([AppTweak](https://www.apptweak.com/en/aso-blog/how-to-optimize-your-app-screenshots)) Drift between slots reads as amateur and breaks scannability.

## Story arc — the 5-slot template

Distilled from AIDA, three-act, and Phiture frameworks:

1. **Hook**: top benefit + hero UI (highest investment)
2. **Core feature A**: the single thing the app does best
3. **Core feature B**: the differentiator vs. category leaders
4. **Trust / proof**: testimonial, rating count, big number, security badge — within Apple/Google rules (no superlatives, no fake stars, no "#1")
5. **Activation / closing benefit**: the long-term outcome (community, savings, ongoing value)

This is a default, not a law. Marketplaces, social, and lifestyle apps benefit from a **panoramic spread** across slots 1–3 (one composition split across portrait slots) — the Wallapop case study showed +26% CVR lift from this. ([Storemaven](https://www.storemaven.com/aso-case-study-storemaven-increased-wallapops-app-install-conversion-rates/))

## Visitor segments to design for

From Storemaven's published behavior data:

- **~60% Decisive** — install or bounce based on slot 1 alone
- **~30% Explorers** — scroll through slots, may compare with competitors
- **~10% Engaged Explorers** — read description, watch video, scroll to bottom

Slots 1 = Decisives. Slots 2–5 = Explorers. Description + video = Engaged Explorers. Allocate polish accordingly.

## Anti-patterns (documented)

- **Text overload** — AppTweak audit: 37% of apps overuse text; 40% have messy captions. ([AppTweak](https://www.apptweak.com/en/aso-blog/most-common-aso-mistakes-how-to-avoid-them))
- **Vague slot 1** — logo + tagline with no UI, "Welcome" splash
- **Low contrast / tiny fonts** — fail the thumbnail test
- **Fake CTAs / store chrome** — "Install now," fake star ratings, fake App Store buttons. Apple and Google both reject. ([Google Play Console Help](https://support.google.com/googleplay/android-developer/answer/9866151), [Apple Marketing Resources](https://developer.apple.com/app-store/marketing/guidelines/))
- **Superlative claims** — "#1", "best ever", competitor name-checks. Apple disallows.
- **Real user data / PII** in mockups — use fictional account data
- **Outdated device chrome** — iPhone with home button on a 2026 listing reads cheap
- **Drift across slots** — different fonts, gradients, scales between slots
- **Multiple competing pop-outs** in one slot
- **Decorative motifs that compete with UI** for attention

## Localization

- **Spanish runs ~25–30% longer** than English on the same copy
- **German runs ~35% longer**, with single words up to 75% longer ("Settings" → "Einstellungen") ([Shotlingo](https://shotlingo.com/blog/german-app-store-screenshots-35-percent-longer))

Design implications:

- Reserve **30–50% horizontal padding** on text containers
- Design for the **longest target language first** (German or Finnish among common locales)
- Prefer **sentence case** to title case (German capitalises all nouns)
- Avoid **auto-shrink to fit** — produces visibly smaller text in localized versions, breaks deck rhythm
- **Localize visuals**, not just text — currency, people, in-app screen content

## Compliance constraints

- **App Store**: up to 10 screenshots per device size. ([Apple Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/))
- **Google Play**: up to 8 screenshots, text overlays should occupy **≤20%** of the canvas. ([Google Play Console Help](https://support.google.com/googleplay/android-developer/answer/9866151))
- Both stores require localized screenshots per market when the app is localized.

## Quick decision check

Before locking any slot's design, answer:

1. Which PET lever does this slot hit?
2. Does slot 1 work in isolation (Decisive segment)?
3. Is there ONE focal enhancement, not two?
4. Does the enhancement sit on the eye flow path?
5. Would a thumbnail viewer at 100 px still get the message?
6. Will the headline still fit at +30% length in Spanish, +35% in German?
7. Any Apple/Google policy violations (fake CTAs, superlatives, fake stars)?

If any answer is "no," redesign before generating.
