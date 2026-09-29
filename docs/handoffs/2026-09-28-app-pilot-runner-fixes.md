# Handoff: app-pilot runner fixes (from the Waki QA run)

Written 2026-09-28. Waki's Phase 0 QA used app-pilot 0.5.0 for about a hundred
flow runs on iOS and Android. These fixes come from that run. Every file:line
below was checked against this repo's `skills/app-pilot/runner/src/` (identical
to the installed 0.5.0 cache at the time of writing).

**Do all four, bump the version, verify on Waki, commit.** No design decisions
are open; if something below turns out wrong in the code, stop and say so.

## 1. A low-confidence "failed" verdict must hand off, not end the run

**Where:** `runner/src/loop.mjs:174-178`.

```js
if (action.kind === 'verdict') {
  log(line()); await trace(entry);
  if (action.status === 'passed') { result = handoff('uncertain_pass', …); break; }
  result = { status: action.status, reason: action.id, confidence: decision.confidence };
  break;
}
if (action.kind === 'handoff' || !clear) { … handoff('uncertain', …) }   // line 180
```

The verdict branch runs before the confidence gate (`clear`, line 150:
`confidence >= POLICY.act || (confidence >= POLICY.actWithMargin && margin >= POLICY.margin)`).
A low-confidence *pass* already becomes a handoff, but a low-confidence *fail*
ends the run as `failed`. It's also inconsistent: `passed` always goes to
`uncertain_pass`, even when `clear`.

**Evidence (Waki):**
- `language-en` / `language-es` on Android ended FAILED at confidence 0.22,
  0.25, 0.32 and 0.35, while screenshots showed the language had switched
  correctly.
- Cause: right after the confirm dialog closed, the screen was still being
  redrawn, and Jev's near-random pick between `wait` and `done_fail` decided
  the outcome.
- 4 reproductions: 2 `done_fail` (terminal) and 2 `wait` (recoverable).

**Change:** a `failed` verdict that isn't `clear` returns
`handoff('uncertain_fail', { snapshotFile, actions, decision })`. A `clear`
fail stays `failed`. Leave the `passed` handling as it is.

**Test:** extract the verdict decision into a small pure function (e.g.
`verdictOutcome(action, decision, policy)` returning `failed`,
`uncertain_fail` or `uncertain_pass`) and unit-test it:
- fail at 0.30 → `uncertain_fail`;
- fail at 0.90 → `failed`;
- fail at 0.50 with margin 0.30 → `failed` (the margin rule);
- pass at any confidence → `uncertain_pass`.

## 2. A resumed run that passes must still save its recording

**Where:** `runner/src/cli.mjs:117`.

```js
if (passed && !resume && (!replay || state.replayed < state.path.length - 1)) { /* write paths/… */ }
```

A run that needed a single handoff and `--resume` never writes
`paths/<flow>-<platform>-<locale>.json`. That's intended nowhere in the docs;
it just happens. On Waki, `create-post`, `profile-edit-restore`,
`favourite-toggle` (iOS) and every step of the 7-step request/chat chain
passed after one small nudge, but none of them could ever replay.

**Change:** when a resumed run passes, write the recording from the combined
steps: the original run's steps (from the run dir) plus the steps after the
resume. The host agent's manual action at the handoff isn't a runner step, so
mark it in the file (e.g. a `{ kind: 'handoff', note }` step or a top-level
`partial: true` with the gap's index). On replay, stop at the gap and hand
back to Jev from there. Keep the current "no rewrite when the replay covered
everything" rule.

**Test:** a unit test for the function that builds the recording from
(original steps, resumed steps, note): it produces the expected JSON with the
gap marked. A replay test: a path with a gap replays up to the gap, then
reports `diverged` / Jev takes over.

## 3. Language-changing flows need recordings per starting language

**Where:** `runner/src/cli.mjs:104`.

```js
// Paths are per language because they match controls by their visible labels ("Search" vs "Buscar").
const pathFile = join(dirname(mapPath), 'paths', `${flow.id}-${platform}-${locale}.json`);
```

`locale` is the requested `--locale`, which defaults to the first entry in
`app.locales` (line 95). For a flow that *changes* the app language, the
labels on the way depend on the language the app is in when it *starts*, and
that varies. Waki's `language-en-android-es.json` was recorded from Spanish
(labels "Cuenta" / "Configuración" / "Idioma"). When the app started in
English ("You" / "Settings" / "Language"), replay diverged at step 1 every time.

**Change:**
- Let a map flow declare `languageFlow: true` (or reuse the skill's existing
  language-flow notion if there is one; check `references/app-map.md`).
- For such flows, detect the UI language from the first observation, e.g. by
  matching the tab labels against `app.locales` or by asking Jev once.
- Key the recording as `${flow.id}-${platform}-from-${startLocale}.json`.
- Replay only a recording whose start language matches.
- Other flows keep the current key.

**Test:** a unit test for the key function (a language flow gets a `from-`
key, a normal flow keeps its key). Then verify on Waki: `language-es` from
English and from Spanish each record once, then replay their own recording.

## 4. `doctor` should detect stale agent-device sessions

When a runner or host session dies, its `agent-device` session (e.g.
`requester-android`, `owner-ios1`) keeps the device. The next
`app-pilot run` fails with `Device is already in use by session "<name>"`. On
Waki that happened three times, and each time it needed a manual
`agent-device session list` and `close --session <name>`.

**Change:** in `doctor`, list the sessions with `agent-device session list`
(the binary is in `runner/node_modules/.bin/`). For each one that holds a
device from the map, print it with the exact close command. Add a
`--close-stale` flag that closes them. Only offer this for sessions holding
the map's devices.

**Test:** a unit test for the function that picks sessions to report, given
`session list` JSON plus the map's devices.

## Docs (SKILL.md / references)

Add three short notes. These are documentation only, not code:
- **One folder per map:** recordings, screenshots and discovery files live
  next to the map file (`dirname(mapPath)` in `cli.mjs:104-105` and
  `explore.mjs:126`). Two maps for the same app (e.g. production and dev)
  therefore need separate folders, or they overwrite each other's recordings.
  Waki's dev map lives in `.app-pilot/dev/app-map.yaml`.
- **Photo pickers aren't supported:** Jev doesn't offer iOS photo-picker cells
  as targets, and the Android system picker
  (`com.google.android.photopicker`) is refused as "another app". Flows that
  pick a photo need a handoff at that step. With fix 2, the rest of the flow
  can still be recorded.
- **Language flows:** they should be written to work from either starting
  language and pass right away if the target is already selected. Point to
  Waki's `language-es` / `language-en` in its dev map as the example.

## Observation from the final verification (context, not a separate fix)

After Waki fixed its own language-switch delay, a re-check ran 10 language
runs on Android and iOS: no FAILED verdicts, and Android passed 4 of 5 without
help. On iOS, whenever the Spanish "Idioma" screen was already in the correct
state (Español checked), Jev's confidence stalled around 0.35-0.54, so every
such run ended `needs_help` / `uncertain_pass`, even though the screenshots
showed the correct state. So no iOS `language-es` recording was ever written.
Two likely causes:
- the lingering UMP consent node that iOS keeps in the accessibility tree
  ("system-surface-host");
- the "already done, nothing to tap" case.

Fix 2 would at least let those resumed passes record. While you're in
`loop.mjs`, check how the "already in target state" case reaches the
`goalMet` 0.9 bar.

## Out of scope

- Waiting for a second screen change after a dialog closes. Waki's delay
  turned out to be the app itself, fixed there.
- Replay matching by `identifier`.
- Photo-picker automation itself.

## Tests, version, verification

- The runner has no test script yet. Add `"test": "node --test"` to
  `runner/package.json`, with tests next to the sources (e.g.
  `src/*.test.mjs`) using `node:test` and `node:assert/strict`. No new
  dependencies. Keep `npm run check` passing.
- Bump `0.5.0` → `0.5.1` in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`, and add a line to the README if it lists
  versions.
- **Live check on Waki:**
  - Worktree: `~/.herdr/worktrees/waki/worktree-silver-river-fd87`, map
    `.app-pilot/dev/app-map.yaml`.
  - Devices: Android `emulator-5554` (requester), iOS sim
    `59C44B1A-5C27-4DD7-8D6E-FB5734B177B0` (owner). Both have the dev app
    `io.wakiapp.waki.dev` installed and signed in.
  - Run the source runner directly:
    `node ~/Documents/01_projects/pukial-claude/skills/app-pilot/runner/src/cli.mjs …`,
    or the `runner/app-pilot` wrapper, which finds Node ≥ 22.12.
  - Run `language-es` and `language-en` from both starting languages on
    Android: no terminal FAILED on a correct switch, and each start language
    gets its own recording.
  - Leave the app in Spanish afterwards.
  - Don't commit anything in the Waki repo from this session. If the new
    recordings are worth keeping, say so, and the Waki session will commit
    them.
- Commit in this repo with conventional messages, one per fix, e.g.
  `fix(app-pilot): hand off low-confidence failed verdicts`.
