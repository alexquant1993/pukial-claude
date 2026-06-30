# pukial-claude

A **Claude Code plugin** distributing the Pukial Flutter toolkit so the whole team gets it in
every project, with one-command updates instead of copy-paste drift.

This repo is **both a marketplace and a single plugin** (`pukial-flutter`).

## What's in the plugin

| Skill | What it does |
|---|---|
| `ship-check` | Post-development architecture gate for Pukial Flutter apps: deterministic verification + TIER-1 grep sweep, parallel fresh-eyes review (architecture + bugs), author triage, opt-in fix loop, and a recommend-only simplifier pass. |
| `new-app` | Scaffolds a new `com.pukial` Flutter app from the `flutter-pukial-starter` (rename, ids, keys). |

This plugin is **skills-only**. The `dart-format` PostToolUse hook is intentionally *not* bundled —
it is FVM-pinned, repo-bound infrastructure, so it lives in the `flutter-pukial-starter` (and is
inherited by any app scaffolded from it). Bundling it here would double-fire it on starter-derived
apps.

## Install (teammates)

```text
/plugin marketplace add alexquant1993/pukial-claude     # or your fork/org path
/plugin install pukial-flutter@pukial
```

Then in any project: invoke `/ship-check` or `/new-app`. Update everywhere with `/plugin update`.

> Installing from a local clone instead of GitHub:
> `/plugin marketplace add /Users/<you>/Documents/01_projects/pukial-claude`

## Prerequisite — the skills need a Pukial Flutter repo

The plugin distributes the **skill logic**; it does **not** carry the per-repo scaffolding the skills
depend on:

- `ship-check` runs `make analyze` / `make test` / `make codegen` and reads
  `flutter-architecture-standard.md`. The `Makefile` targets, `.env` setup, and FVM pin come from the
  **`flutter-pukial-starter`** (and are inherited by any app scaffolded from it). A copy of the
  standard ships in the plugin so the reviewer always has one; an app may keep its own repo-level
  copy and `ship-check`'s staleness note will compare versions.
- `new-app` operates on a checkout of the starter.

So the team flow is: **install the plugin once** (skills everywhere) **+ start apps from the starter**
(per-repo Makefile/standard/settings). The plugin handles distribution + versioning; the starter
handles per-repo wiring.

## Versioning

Bump `version` in `.claude-plugin/plugin.json` **and** the matching entry in
`.claude-plugin/marketplace.json` together, then tag the commit. Teammates pick it up with
`/plugin update`.

## License

MIT — see [LICENSE](LICENSE).
