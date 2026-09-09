---
name: ship-check
description: >
  Use when a development effort on a Pukial Flutter app is finished and should be verified against
  the company architecture standard before commit/PR. Runs a verification gate, a deterministic
  TIER-1 conformance sweep, and parallel LLM review (architecture + bugs), then reports findings and
  offers an opt-in fix loop. Trigger phrases: "ship-check", "review my work", "run the gate",
  "is this ready to ship", "check this against our standards".
---

# ship-check Skill

Post-development review pipeline. Verifies a finished change against the **Pukial Flutter
Architecture Standard** ([`flutter-architecture-standard.md`](flutter-architecture-standard.md)),
reports findings, and applies fixes only on opt-in. Design rationale lives in the
`flutter-pukial-starter` repo (starter-internal, not shipped with this plugin):
`docs/superpowers/specs/2026-06-27-ship-check-review-pipeline-design.md` and its refinement
`docs/superpowers/specs/2026-06-28-ship-check-pipeline-refinement-design.md`.

**Two scopes, one principle — review the WORKING TREE vs a base, never commit-to-commit.** The
effort may be uncommitted, and the fix loop edits the working tree without committing, so the review
range is `git diff --unified=0 $BASE_SHA` (no `..HEAD`).

Create one todo per stage below and work them in order.

## Stage 0 — Verification gate (deterministic)

Run from the app repo root. Stop the *LLM* stages if this fails (but still run Stage 0.5 — it's
static).

1. `make analyze` — must exit zero. 
2. `make test` — must pass. *(A `--skip-tests` invocation may skip this; if so, **stamp "tests
   skipped" in the final report**. Default is to run them.)*
3. **Codegen freshness** — only meaningful if generated files are committed (the starter commits
   them; if an app gitignores `*.g.dart`/`*.freezed.dart`, skip with a note):
   - Confirm the generated files are clean in git. Run `make codegen`. Assert
     `git diff --quiet -- '*.g.dart' '*.freezed.dart'`. If non-empty → generated output is stale;
     report it. Then **revert** any regenerated files (`git checkout -- <generated>`) so the review
     reads the developer's real diff.
   - **Inside the fix loop only:** do NOT treat regeneration as a failure — run `make codegen` after
     the fix agent and fold the regenerated files into the accepted change (a conformance fix may
     legitimately touch a `@riverpod`/`@freezed`/`Fake*` input). Strict freshness applies to the
     **first** Stage 0 pass only.

## Stage 0.5 — TIER-1 grep sweep (deterministic, whole-repo, partitioned)

Runs even if Stage 0 failed (near-zero cost, static).

```bash
# Run sweep.py from THIS skill's own directory — substitute the absolute path you were given as
# "Base directory for this skill" when this skill loaded. That is `.claude/skills/ship-check/` for a
# repo-level copy, or the plugin install path when installed via the `pukial` plugin. The
# templates and {STANDARD_PATH} (= <skill-dir>/flutter-architecture-standard.md) live there too.
python3 "<skill-dir>/sweep.py" --root . --json /tmp/ship-check-sweep.json
```

The script resolves `BASE_SHA` (fallback chain `merge-base with origin/main → merge-base with main →
HEAD~1 → none`), greps every rule in `tier1-rules.yaml` over the working tree, honors
`// ship-check:ignore <rule-id>`, and partitions hits into **in-diff (actionable)** vs
**existing-drift (advisory, never blocks)**. Read the JSON for the structured findings. Exit code 1 =
in-diff Critical/Important present.

**The JSON's `base_sha` is the canonical base for the whole run.** Read it once and reuse it
everywhere downstream — fill `{BASE_SHA}` in the Stage 1 & 2 templates with it, and use it for Stage
2's diff range. Do not let any later stage re-resolve its own base; a single shared base is what keeps
the "one base, base→working-tree" invariant true across the deterministic sweep and the LLM stages.

## Stages 1 & 2 — LLM review (parallel, diff-scoped, read-only)

Skip if Stage 0 failed (fix the gate first). Dispatch **both subagents in one message** so they run
concurrently. Both review **base → working tree**.

- **Stage 1 — Architecture conformance.** Dispatch a `general-purpose` subagent using the filled
  [`conformance-agent.md`](conformance-agent.md) template (placeholders: `{STANDARD_PATH}`,
  `{ROOT}`, `{BASE_SHA}`). It returns TIER 2/3 findings only (TIER 1 is already covered by Stage
  0.5).
- **Stage 2 — Code review.** Dispatch the `feature-dev:code-reviewer` agent for bugs, logic errors,
  and security issues. **Tell it the range explicitly** — review the **base → working tree** diff
  (`git -C {ROOT} diff {BASE_SHA}`, no `..HEAD`, using the canonical `base_sha` above) so it sees the
  uncommitted work this skill exists to catch. The generic agent otherwise defaults to the
  branch/commit diff and would miss uncommitted changes.

## Consolidate → report (always first, nothing changed yet)

Merge Stage 0 result + Stage 0.5 + Stages 1–2 into ONE report with two sections:

- **YOUR CHANGES** (actionable): grouped **Critical / Important / Minor**, each `file:line` + rule +
  one-line fix. Includes Stage 0.5 in-diff hits + Stage 1/2 findings + gate status.
- **EXISTING DRIFT** (advisory, never blocks): Stage 0.5 pre-existing baseline (per-rule counts +
  locations) — a punch-list, not a failure.

Also print: the base SHA + how it resolved, the standard-doc `version` and a **staleness note** if
this app's copy predates the starter's, the suppression count, and (if used) the tests-skipped stamp.

**Tier policy:** TIER-1 in-diff → Critical/Important. TIER 2 → Important/Minor by judgment. TIER 3
and all existing-drift → advisory, never block.

## Triage the findings — you are the author receiving review

Before offering any fix, **invoke `superpowers:receiving-code-review`** and triage every actionable
finding. You (the orchestrator) are the development session that wrote this code — the one party with
the implementation context to judge a finding correctly. Sort each into one bucket:

- **accept** — real finding; it goes to the fix loop.
- **push-back** — the reviewer misread intentional design; reject it *with one-line reasoning*.
- **needs-investigation** — can't decide yet.

**Visibility (integrity guard) — graduated by severity.** You are a Claude session triaging another
Claude's review, so a silent dismissal can't be allowed to hide:

- **Critical push-back → stop and get an explicit human OK** before going further ("the session
  rejected a CRITICAL finding for reason X — confirm or override"). Until acknowledged, that Critical
  is an **unresolved blocker**.
- **Important / Minor push-backs and all needs-investigation → surface in the report** with the
  one-line reasoning. The human reads the report before opting into fixes, so they land at the
  decision point without a confirm prompt.

A finding is **unresolved** if it is an accepted-but-unfixed blocker, an open Critical push-back
awaiting human OK, or a needs-investigation item. Unresolved Critical/Important findings gate Stage 3.

## Opt-in fix (default: report only)

Ask the developer whether to apply fixes. Two independently-selectable tracks:

1. **Conformance/correctness fixes** — for the **accepted** findings only. On opt-in, run the
   **bounded self-healing loop** (max **5** iterations):
   - Dispatch a fix subagent as a **pure applier**: it mechanically applies the accepted findings.
     Triage already happened above, so it does **not** re-litigate validity — it may only report an
     accepted finding that proves impossible to apply cleanly.
   - Re-run Stage 0 gate (loop-tolerant codegen) + Stage 0.5 in-diff sweep + Stages 1–2.
   - **Re-triage emergent findings.** If a re-run surfaces a finding that wasn't in the triaged set
     (a fix introduced it), the orchestrator triages it *then* — same `receiving-code-review`
     discipline and graduated visibility — before the next apply pass. Triage is **per-iteration**,
     not a one-time gate; without this, a fix-introduced finding could never be accepted and the loop
     would spin to the cap without healing what it discovered.
   - Repeat until clean or the cap. **State how many iterations ran and why it stopped** (clean vs
     cap, with residual findings). *(Cost: each iteration is a fresh parallel Stage 1+2 — up to 5×
     the first-pass review cost in the worst case; this is why the loop is opt-in.)*
2. **Simplifier pass (Stage 3)** — see below. Offered **only if no Critical/Important finding is
   unresolved**, on a separate opt-in (a developer may want the fixes without the restyle).

## Stage 3 — Pukial-simplifier (opt-in, recommend-only, settled tree)

Offer this **only when no Critical/Important finding is unresolved** (restyling unfinished code is
premature) and the developer opts in. It runs over the **settled tree** — after the fix loop
converges, or on an already-clean change.

- Dispatch a `general-purpose` subagent with the filled [`simplifier-agent.md`](simplifier-agent.md)
  template (placeholders: `{STANDARD_PATH}`, `{ROOT}`, `{BASE_SHA}`). It is **recommend-only** — it
  returns intra-layer taste recommendations (dedup, naming, dead code, boilerplate→shared-helper) and
  **never edits**. Structural/boundary findings are Stage 1's, never Stage 3's.
- Fold its recommendations into an **"optional polish"** section for the developer to adopt and
  adapt — take some, modify one, reject another.
- **Adoption re-gates (the gate is the trust boundary, not the agent).** When the developer adopts
  recommendations, those edits write the tree, so re-run Stage 0 (`make analyze` / `make test`)
  **plus a mandatory Stage 0.5 in-diff sweep** over the adopted edits — `make analyze` / `make test`
  do **not** catch the TIER-1 grep rules, so the sweep is the only thing that catches a re-introduced
  `AppRoute` / `AppImages` / `Sizes` literal, a relative import, or a stripped `context.loc`. A new
  in-diff TIER-1 hit means the adoption crossed a line: revert or repair that edit and note it.

## Notes

- **Subagent model — select explicitly per stage by capability tier; do NOT silently inherit.**
  Follows superpowers `subagent-driven-development` § Model Selection: an omitted model inherits the
  session's model (often the most capable and most expensive), which wastes cost. Choose by tier at
  dispatch — don't hardcode a version id (it ages badly):
  - **Stage 1 · conformance** — architecture judgment over the diff → a **capable** model; scale up
    for large or subtle diffs. This is the judgment that justifies the gate.
  - **Stage 2 · code review** — the `feature-dev:code-reviewer` agent **pins its own model** in its
    frontmatter; omit the `model` arg so its pin stands — nothing to choose.
  - **Fix loop agent** — **standard** model for real fixes; a **cheap** tier is fine when the
    accepted findings are mechanical transcription (e.g. the `AppRoute`/`AppImages` refactor).
  - **Stage 3 · simplifier** — dispatched as a filled `simplifier-agent.md` to a **general-purpose**
    subagent, so it **pins nothing**; select a tier explicitly. Taste judgment over settled code
    wants a **capable** model — keep a mid-tier floor so suggestions aren't shallow.
  - *Turn count beats token price:* keep a **mid-tier floor** for the conformance reviewer and fix
    agent — the cheapest tiers take 2–3× the turns on multi-step work. Stages 0/0.5 are
    deterministic (model-independent).
- Requires `python3` (standard library only; PyYAML used if present, else a built-in reader).
- This skill enforces the existing standard; it does not redesign architecture. To change a rule,
  edit `flutter-architecture-standard.md` **and** `tier1-rules.yaml` (keep versions in sync).
