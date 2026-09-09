# pukial-claude

A **Claude Code marketplace and plugin** carrying the skills the Pukial team uses,
so every project gets them with one install and one-command updates instead of
copy-paste drift. The skills span more than one domain: a slide-deck pipeline,
a Flutter toolkit, and whatever comes next.

This repo is **both a marketplace** (`pukial`) **and a single plugin**
(`pukial`), carrying every skill. Each skill lives in its own directory under
`skills/` with a `SKILL.md` that says when it triggers and what it needs.

## Skills

| Skill | Domain | What it does | Needs |
|---|---|---|---|
| `deckwright` | Slides | Turns an idea into a slide deck: a binding spec, HTML drafts drawn on a design system (the bundled `relay` brand or your own), then a native editable PowerPoint file or a printable HTML deck, with a QA loop that proves the file opens and says what the spec said. Its intake asks about the design system, the HTML draft, speaker notes and the output before anything is built. | Python with `python-pptx` and `Pillow`; a browser the capture script can drive; Windows with PowerPoint only for the PPTX integrity and export steps. `skills/deckwright/README.md` has the map and the gate. |
| `ship-check` | Flutter | Post-development architecture gate for Pukial Flutter apps: deterministic verification and a TIER-1 grep sweep, parallel fresh-eyes review (architecture and bugs), author triage, an opt-in fix loop, and a recommend-only simplifier pass. | A repo started from `flutter-pukial-starter`: its `Makefile` targets, `.env` and FVM pin. A copy of the architecture standard ships with the skill. |
| `new-app` | Flutter | Scaffolds a new `com.pukial` Flutter app from `flutter-pukial-starter` (rename, ids, keys). | A checkout of the starter. |
| `aso-appstore-screenshots` | ASO / Marketing | Produces App Store and Google Play screenshot decks through a gated nine-phase pipeline, deterministic Pillow scaffolds, optional AI hero cards, and multi-platform or locale replication. | Python with `Pillow`; `openai` and `OPENAI_API_KEY` only for AI hero cards. |

Invoke a skill by asking for what it does ("build me a deck", "run ship-check",
"scaffold a new app") or by its slash name. Each `SKILL.md` lists its trigger
phrases.

## Install

```text
/plugin marketplace add alexquant1993/pukial-claude     # or your fork/org path
/plugin install pukial@pukial
```

> Installing from a local clone instead of GitHub:
> `/plugin marketplace add /path/to/pukial-claude`

### Migrating from `pukial-flutter` (before v0.3.0)

The plugin was published as `pukial-flutter` through v0.2.0, back when the only
skills were the Flutter ones. As of **v0.3.0 it is `pukial`**, because the
plugin now spans domains.

The plugin id is the identity key, so this rename does **not** carry over on
`/plugin update` — the old id simply stops existing in the marketplace. Migrate
once, by hand:

```text
/plugin uninstall pukial-flutter@pukial
/plugin marketplace update pukial
/plugin install pukial@pukial
```

Then check `enabledPlugins` in `~/.claude/settings.json`: drop any leftover
`"pukial-flutter@pukial"` entry, and make sure `"pukial@pukial": true` is there.
If you installed the plugin at **project** scope anywhere, repeat the uninstall
and install in each of those projects.

Skill invocation names change with the id: `pukial-flutter:ship-check` becomes
`pukial:ship-check`, and likewise for `new-app` and `deckwright`. Fix any saved
prompts, aliases or scripts that spell the old form.

### Keeping up to date

Updates are **not** automatic by default. A marketplace only refreshes on demand,
so an install can sit months behind without any signal:

```text
/plugin marketplace update pukial     # refresh the catalog
/plugin update                        # then pull new plugin versions
```

To have it refresh on its own, set `autoUpdate` on the marketplace entry in your
own `~/.claude/settings.json` — this is a per-machine setting, so it cannot be
turned on for you from this repo and each teammate has to do it once:

```json
{
  "extraKnownMarketplaces": {
    "pukial": {
      "source": { "source": "github", "repo": "alexquant1993/pukial-claude" },
      "autoUpdate": true
    }
  }
}
```

## What the plugin does and does not carry

The plugin distributes **skill logic**: instructions, references, scripts and
the fixtures a skill needs to prove itself. It does not carry per-repo
infrastructure. The Flutter skills expect a repo started from
`flutter-pukial-starter` (Makefile, env, FVM pin, the `dart-format` hook, which
is deliberately not bundled here so it does not double-fire). `deckwright` is
self-contained: it brings its own default design system, fonts under the SIL
Open Font License, and a gate you can run on the skill directory itself.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with front matter (`name`, `description` that
   says when to trigger and when not to) and keep the router short; put the
   know-how in files next to it.
2. Bundle only what the skill needs to run: scripts with a `Run:` line, templates
   that are filled in enough to copy, no client or employer material, no
   proprietary fonts or marks.
3. Add a row to the table above and, if the skill has requirements, say them in
   the Needs column.
4. Bump the version (below).

## Versioning

Bump `version` in `.claude-plugin/plugin.json` **and** the matching entry in
`.claude-plugin/marketplace.json` together, then tag the commit. Teammates pick
it up with `/plugin update` — see [Keeping up to date](#keeping-up-to-date),
since that step is manual unless they have opted into `autoUpdate`.

Never change the plugin `name` in a routine bump. It is the identity key behind
every teammate's install record and enabled-plugin entry, so renaming it forces
the manual migration documented above.

## License

MIT - see [LICENSE](LICENSE). Bundled third-party assets carry their own
licences next to them (the fonts under `skills/deckwright/brands/relay/fonts/`
are SIL OFL 1.1).
