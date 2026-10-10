---
name: ci-github-actions
description: >-
  Design, review and repair a project's GitHub Actions CI so it does not burn the account's
  Actions minutes or stall other repositories. Use it whenever you create or edit a file in
  .github/workflows/, when a workflow is slow or runs more often than it should, when GitHub warns
  that minutes or the spending budget ran out, when a scheduled (cron) workflow silently stops
  running, or when setting up a self-hosted runner. Triggers: "CI minutes", "GitHub Actions",
  "workflow", "out of minutes", "spending limit", "self-hosted runner", "CI is slow", "the cron
  stopped running". Not for debugging one failing test (that is ordinary debugging) or for CI
  systems other than GitHub Actions.
---

# GitHub Actions CI without burning the account

Actions minutes and the spending budget belong to the **account (user or organization), not the
repository**. When one repo exhausts them, GitHub stops **every** private workflow on the account,
including the scheduled ones that keep other products running. A typical failure: one product's CI
runs every commit twice and uses up the month's minutes. Then another product's cron jobs, which
publish content or send notifications, stop without any error in their own repo. And a real failure
on `main` goes unnoticed in the noise.

## Flow

1. **Measure before changing anything.** Run the diagnosis and read the output:
   `python3 -I scripts/diagnose_ci.py OWNER/REPO --runs 200`
   It shows runs per workflow, event, branch and result, commits tested more than once, and the
   slowest steps. If the account has several private repos, run it on each: the quota is the sum.
2. **If the minutes are already exhausted**, follow `references/emergency.md` first: restore what
   serves users, then fix the CI.
3. **Check the workflows against the rules** below. Each broken rule is one concrete change.
4. **Pin the rules with a test** that reads the YAML. A workflow without a test degrades again on
   the next edit. Template and example test in `references/workflow-template.md`.
5. **Check whether `main` is red** for a real reason, not the quota. Fix it with a test that would
   have caught it.
6. **Self-hosted runner** only if the CI still does not fit the plan after the rules, or if critical
   automations must not depend on the quota: `references/self-hosted-runner.md`.
7. **Document it in the repo:** a runbook with the measured numbers and the fallback switch.

## Rules

| # | Rule | Why |
|---|---|---|
| 1 | `push` only on the default branch; branches are tested through `pull_request` | `push` on every branch plus `pull_request` tests each commit twice, often 40 % or more of all minutes |
| 2 | `concurrency` with `cancel-in-progress` on PRs, grouped by PR number | After several quick pushes only the last one matters. Do not cancel on `main`, so every merge keeps its result |
| 3 | Two tiers: fast on every PR, full (E2E, Docker image, slow suites) on `main`, on demand, or with a label | E2E and image builds are often more than half the time and rarely need to run on every branch push |
| 4 | A docs path filter, **with re-included paths** | Docs-only changes should not start a 25-minute CI, **but** if a test reads a `.md` or another file under `docs/`, changing it must run the CI. A blind `paths-ignore: '**/*.md'` lets breakage through |
| 5 | A test that finds the docs paths the code and tests read, and checks the filter re-includes them | So nobody can break rule 4 silently by adding a new test |
| 6 | `timeout-minutes` on every job (≈2× its normal duration) | The default is 6 h: one hung job can eat a month's quota |
| 7 | Crons only as often as the product needs | Each run is billed rounded up to the minute per job: a 5-minute cron is ~8,600 min a month |
| 8 | Caches (`setup-node` with `cache`, etc.) and no unnecessary `apt-get` | Installing system packages can take 10–19 min when a mirror is slow |
| 9 | If the repo can be public, standard GitHub-hosted runners are free | The cheapest lever, when it applies |
| 10 | Automations that serve users (product crons) do not share a quota with heavy CI | Either the heavy CI moves to a self-hosted runner, or the product moves to another account or runner |

### Known pitfalls

- **Path filter order:** patterns apply in order; a `!` pattern excludes and a later positive one
  re-includes. When `paths` uses `!`, the first pattern must be positive (`'**'`).
- **Required checks and path filters:** if the CI job is a required status check in branch
  protection, a docs-only PR that the filter skips leaves the check "pending" forever and cannot
  merge. Either let a tiny always-running job report the required check, or make the filtering
  happen inside the job (a step that detects changed paths and exits early) instead of in `on:`.
- **Path filters also gate `labeled`:** adding the full-CI label to a docs-only PR starts nothing.
- **YAML anchors** (`&paths` / `*paths`): some parsers and older GitHub Enterprise Server versions
  reject them. Repeating the list and asserting in the test that `push` and `pull_request` match
  works everywhere.
- **`labeled` in `pull_request.types`:** adding *any* label restarts the workflow. Add
  `if: github.event.action != 'labeled' || github.event.label.name == '<label>'` and put
  `concurrency` **at job level**, so a discarded event does not cancel the run in progress.
- **Wall-clock minutes are not billed minutes:** wall-clock includes queue time, while billing
  rounds up per job and multiplies macOS and Windows minutes (see GitHub's current billing docs).
  The real number is in *Settings → Billing → Usage*.
- **A cron that stops for other reasons:** schedules run only from the default branch, and in public
  repos GitHub disables them after 60 days without repository activity. Rule those out before
  blaming the quota.
- **Registering a runner needs repo (or org) admin;** an account with push access gets 404 from
  the runners API.

## Do not

- Raise the budget as the fix: it buys time, it does not remove the cause. Spending is the owner's
  decision, never the agent's.
- Disable tests to save minutes. What you cut is **when** they run.
- Put a self-hosted runner on a production host or its Docker daemon: CI runs
  `docker compose down --volumes` and third-party code.
- Claim savings without saying they are a projection; measure at the end of the billing cycle.
