# Vendored source

This skill is a frozen, reviewed copy — not a live checkout.

- **Upstream:** https://github.com/morluto/rea (`.agents/skills/reverse-engineer-anything/`)
- **Commit:** `569ef4159db73931717825302b323fae7aa91bbf` (2026-10-14), skill metadata version `42`
- **Matching npm package:** `rea-agents@6.5.0` (SLSA provenance from `morluto/rea`
  `.github/workflows/release.yml`, GitHub-hosted runner; no install scripts)
- **Vendored on:** 2026-10-14
- **License:** MIT, copyright (c) 2026 morluto — see `LICENSE-UPSTREAM`.

The skill is instructions only. Its tools come from the REA MCP server
(`rea-agents` on npm), which each person registers on their own machine.

## Security review (2026-10-14)

- skills.sh audits: Gen Agent Trust Hub Pass, Socket Pass, Snyk Pass.
- Skill files (SKILL.md + 6 references): no hidden Unicode, no credential access,
  no exfiltration, no hook/settings edits; it asks for approval before setup writes
  configuration and does a `--dry-run` first.
- `rea-agents` source: no analytics/telemetry SDKs; external URLs in `src` are test
  placeholders; no `postinstall`/`preinstall` scripts.
- Residual risks: upstream text uses unpinned `rea-agents@latest` with `npx -y`;
  single npm maintainer; runtime workflows execute the target. Mitigated by the
  Pukial rules at the top of `SKILL.md`.

## Local modifications

### 2026-10-14 — Pukial security rules (Spanish section at the top of SKILL.md)
Pin `rea-agents@6.5.0`; setup only after dry-run and approval, with `--skill=false`
and project-scoped MCP registration preferred; authorized targets only; live
execution needs approval; suspicious samples never run on the Mac.
The upstream body and `references/` are unchanged.

## Updating later

Clone upstream into a temp dir, diff `.agents/skills/reverse-engineer-anything/`
against this folder (ignoring the Pukial section, `VENDORED.md` and
`LICENSE-UPSTREAM`), re-review, check the new npm version's provenance, and bump the
pinned version in rule 1 together with the commit above.
