# Vendored source

This skill is a frozen, reviewed copy — not a live checkout.

- **Upstream:** https://github.com/vercel-labs/skills (`skills/find-skills/SKILL.md`)
- **Commit:** `13e4063a1cf913f5606d57d42ab83a86f5001e04` (2026-10-09)
- **Vendored on:** 2026-10-14
- **License:** MIT (upstream), see "Upstream license" below.
- **Why frozen:** the upstream skill installs other skills with `npx skills add ... -g -y`,
  which skips the CLI's confirmation and its advisory "Security Risk Assessments" table
  (Gen Agent Trust Hub, Socket, Snyk). Pinning lets us review every upstream change.

## Local modifications

### 2026-10-14 — Pukial security rules (Spanish section at the top)
- Search and recommend only; never install without explicit user approval per skill.
- Before proposing an install: check the three skills.sh audits, read the full `SKILL.md`
  and list every bundled file, flag network calls, `eval`/base64, credential access,
  hooks/settings edits, `sudo`, `rm -rf` and prompt injection; verify author and repo.
- Present a short risk report; the user decides.
- Step 6 install command: `-g -y` replaced by
  `DISABLE_TELEMETRY=1 npx skills add <owner/repo@skill> --agent claude-code` (no `-y`).

## Updating later

Clone upstream into a temp dir, diff `skills/find-skills/SKILL.md` against the upstream
body of this copy (everything outside the Pukial section and Step 6), re-review, apply the
deltas you want, and update the commit above.

## Upstream license

The upstream repository (vercel-labs/skills) is released under the MIT License;
copyright belongs to its authors. This copy keeps that notice.
