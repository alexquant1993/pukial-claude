---
title: Pukial Flutter Architecture Standard
version: 2026-06-27
source: reference-app audit (2026-06-27) + flutter-pukial-starter resolved conventions
---

# Pukial Flutter Architecture Standard

The single, self-contained standard every Pukial Flutter app is held to. `/ship-check` reads this
file; it does **not** read any app's `AGENTS.md`, so the standard is identical across all apps.

The cleanly grep-able TIER-1 rules also exist as machine-readable data in the sibling
[`tier1-rules.yaml`](tier1-rules.yaml), which the Stage 0.5 sweep loads. **Keep the two in sync:**
when you add or change a TIER-1 rule here, edit `tier1-rules.yaml` too.

## Enforcement tiers

| Tier | Meaning | Enforced by | Blocks? |
|---|---|---|---|
| **TIER 1** | Mechanical, unambiguous | deterministic grep (Stage 0.5) where line-grep-able; otherwise the conformance agent as a checklist | yes, when in-diff |
| **TIER 2** | Structural, needs judgment | LLM conformance agent (Stage 1) over the diff | yes, when in-diff (by severity) |
| **TIER 3** | Maturity-dependent | LLM conformance agent, advisory | never |

> **Maturity guard:** a young app or spike is **never failed** for a TIER-3 pattern, nor for
> pre-existing drift surfaced outside its current changes. TIER 3 and existing-drift items are
> always advisory notes.

---

## TIER 1 — mechanical (always enforce; blocks when in-diff)

Each rule notes whether it is **grep** (in `tier1-rules.yaml`) or **agent-checklist** (verified by
the conformance agent because absence/intent isn't line-grep-able).

### T1.1 Named routes only — no hardcoded path strings · *grep* `no-hardcoded-route-path`
Routes are an `AppRoute` enum; navigation uses `context.goNamed(AppRoute.x.name)` /
`pushNamed(...)`. Never a literal path string in a navigation call.
- ❌ `context.go('/home')` · `context.goNamed('/post')` · `context.push('/login')`
- ✅ `context.goNamed(AppRoute.home.name)`

### T1.2 Asset paths via `AppImages` — no inline literals · *grep* `no-inline-asset-literal`
Every asset path is a `static const String` on `AppImages`. No `'assets/...'` string literal
anywhere except `app_images.dart`.
- ❌ `Image.asset('assets/logos/logo.png')`
- ✅ `Image.asset(AppImages.logo)`
- *Absence note (agent-checklist):* "no `AppImages` class exists yet" cannot be grepped to a
  `file:line`, so it is reported only in the advisory existing-drift baseline — it nudges, it does
  not gate.

### T1.3 Spacing via `Sizes` / gap widgets — no magic numbers · *grep* `magic-number-edgeinsets`, `magic-number-sizedbox`
Use `Sizes.pX`, `gapW*`, `gapH*`. No numeric literal in the argument of
`EdgeInsets.{all,symmetric,only,fromLTRB}` or `SizedBox(width:/height:)`.
- ❌ `EdgeInsets.all(12)` · `SizedBox(width: 8)`
- ✅ `EdgeInsets.all(Sizes.p12)` · `gapW8`
- **Documented boundary:** the grep keys *only* on those literal-arg constructors.
  `BorderRadius.circular(8)`, `Radius`, `Offset`, elevation, and font sizes are **out of scope**
  (TIER-3 taste), to keep the rule false-positive-free.

### T1.4 Breakpoints via `Breakpoint.*` · *grep* `hardcoded-breakpoint`
Responsive thresholds use `Breakpoint.tablet` / `Breakpoint.desktop`, never a raw 3-digit width
literal in a `MediaQuery` width comparison.
- ❌ `MediaQuery.sizeOf(context).width > 600`
- ✅ `MediaQuery.sizeOf(context).width > Breakpoint.tablet`

### T1.5 Absolute imports only — no relative `../` · *grep* `relative-import`
- ❌ `import '../../utils/x.dart';`
- ✅ `import 'package:<app>/src/utils/x.dart';`

### T1.6 No raw `throw Exception(...)` in feature code · *grep* `raw-throw-exception`
App errors extend the sealed `AppException` hierarchy with `getMessage(loc)`. Feature code must not
throw a bare `Exception`/`Error`.
- ❌ `throw Exception('not found')`
- ✅ `throw const PostNotFoundException()` (extends `AppException`)
- *Hierarchy completeness is an agent-checklist item* (the sealed base may legitimately be a known
  skeleton gap; the grep only flags *new* raw throws).

### T1.7 `@freezed` domain models · *agent-checklist*
Every model in a `domain/` folder is `@freezed` (+ `json_serializable` when serialized) and the
`domain/` layer imports only domain + exceptions. Absence of the annotation isn't reliably
line-grep-able, so the conformance agent verifies it deterministically as a checklist item.

### T1.8 Riverpod codegen annotations · *agent-checklist*
Every provider uses `@riverpod` / `@Riverpod(keepAlive: true)` (no hand-written
`Provider(...)`/`StateNotifierProvider`).

### T1.9 Env secrets obfuscated + fail-open · *agent-checklist*
`@EnviedField` secrets are `obfuscate: true`; every optional integration no-ops on an empty key
(the fail-open contract).

### T1.10 Test path mirroring · *agent-checklist* (advisory)
A test file lives at `test/<same path as lib>/<name>_test.dart`. Not a line-grep (it's a
path-structure check), so it is **not** in `tier1-rules.yaml`; the conformance agent notes
misplaced tests opportunistically. Missing tests themselves are maturity-scaled — see TIER 3.

---

## TIER 2 — structural (LLM-judged over the diff; blocks by severity when in-diff)

### T2.1 Localization — no hardcoded user-facing strings
All user-facing text via `context.loc.<key>`, present in **both** `app_en.arb` + `app_es.arb`.
LLM-judged (not grep): distinguishing `Text('Total')` from `Text(context.loc.total)`,
`Text(amount)`, `Semantics(label:)`, `Key('…')`, or a debug/map-key string needs intent reading.

### T2.2 Layering & the repository-vs-service rule
`domain ← data ← application ← presentation`, one-way. A single-repository action → the controller
calls the repo **directly** (no pass-through service). A multi-repository or genuine use-case action
→ a **`Service`** in `application/`. A class wrapping one SDK/API/DB is a **Repository**; never name
an SDK-wrapper a "Service." `data/` never imports `application/`; `application/` never imports
`presentation/`.

### T2.3 Repositories: interface + `Fake*` + provider
A repository is an interface with a `Fake*` impl in the same folder and a `@riverpod` provider,
wrapping **one** data source and returning domain models. A new repository ships with its `Fake*`
and a provider-override test. (Trivial single-SDK wrappers with no fake-injection need may stay
concrete until a second concern appears — mirrors the starter's `paywall` exception.)

### T2.4 Presentation read-path vs write-path
- **Read:** a function provider returning `Stream`/`Future`, rendered via `AsyncValueWidget`.
- **Write:** a `@riverpod class` controller exposing `AsyncValue<void>`; `state = AsyncLoading()` →
  `state = await AsyncValue.guard(...)`; error surfaced via
  `ref.listen(p, (_, s) => s.showAlertDialogOnError(context))`.
- Validation lives in the service/controller, **not** the widget.

### T2.5 Routing organization
`GoRoute` / `StatefulShellBranch` definitions live in `routing/routes/` + `routing/branches/`
(function-returning), not inline in `app_router.dart`. 2+ related route params → a typed param class
with `fromMap`/`toMap`.

### T2.6 Analytics via the facade
Analytics go through the `AnalyticsFacade`; never a direct SDK call (`Mixpanel.track(...)`) in
feature code.

---

## TIER 3 — advisory only (never blocks)

- `onExit` route guards on unsaved-form pages; global `redirect()` flow gating; deep-link parser.
- Better Comments `// *` on **new** code (init steps, gotchas); no mass retrofit.
- Exhaustive unit tests for money / pace / state-machine logic; exception-mapping tests. Test
  coverage expectations scale with app maturity — a spike is not failed for missing tests on
  trivial code.
- Theme-extension / `colorScheme` adoption instead of `Color(0x…)` / `Colors.*` literals.
- `ScreenUtils` / `ScreenSize` for responsive logic instead of scattered `Platform.is*` checks.

---

## Suppression

Any TIER-1 grep finding can be suppressed with an inline `// ship-check:ignore <rule-id>` on the
offending line or the line directly above it (e.g. `// ship-check:ignore magic-number-sizedbox`).
Suppressions are **counted in the report** so they can't hide silently; they do not block.
