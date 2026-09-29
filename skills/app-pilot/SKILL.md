---
name: app-pilot
description: >-
  Drive a real iOS or Android app to run QA flows and capture store/website-quality screenshots,
  fast and cheaply: TypeSafe's Jev picks each step from the accessibility tree (~0.3s, ~$0.0001),
  recorded paths replay with no model at all, and Claude only steps in for the hard cases.
  Use when the user wants app screenshots refreshed, the main flows of an app smoke-tested,
  an app "walked through" on a simulator/emulator, an accessibility gap report, or says
  "app-pilot", "run the flows", "retake the screenshots", "QA the app", or wants every screen of an app
  mapped or reviewed ("explore the app", "full review", "what screens does it have").
---

# app-pilot

Three tiers, cheapest first. Code owns every fact it can see; models only choose.

| Tier         | Who decides                         | Cost per step                              | When                                                     |
| ------------ | ----------------------------------- | ------------------------------------------ | -------------------------------------------------------- |
| Replay       | recorded path (`.app-pilot/paths/`) | 0 model calls, ~1s (iOS) / ~0.5s (Android) | Every run once a flow has passed                         |
| Jev          | TypeSafe System One model           | ~0.25–1.5s, ~$0.0001                       | New flows, and from the first step a replay cannot match |
| Claude (you) | reasoning + vision                  | seconds                                    | Handoffs (exit code 4), onboarding, screenshot review    |

The runner is in `runner/` (Node ≥ 22.12, MIT deps: agent-device, @typesafe-ai/sdk, yaml).
Per-app data lives in the app's repo under `.app-pilot/`, never in this plugin.

## 0. Setup (once per machine)

Call the runner through its wrapper, `runner/app-pilot` (below: `app-pilot`). It finds a Node ≥ 22.12 and installs
its own dependencies on first use and after plugin updates.

1. `app-pilot setup` creates `~/.config/app-pilot/.env` (chmod 600) for `TYPESAFE_API_KEY=…` plus any account
   variables the app map references (`APP_EMAIL=…`). Secrets never go in a repo or the chat: give the user
   `! open -e ~/.config/app-pilot/.env`.
2. `app-pilot doctor [<app-map.yaml>]` must end with "Ready." before anything else. It checks the key, the OCR helper,
   booted simulators/emulators, the app installed on each, the map's variables, agent-device sessions left holding
   the app's devices by a dead run or agent (they make the next run fail with "Device is already in use by session";
   it prints each close command, and `--close-stale` closes them: not while a run waits on a handoff in one), and
   warns (`!`) about what only slows runs down: a Flutter debug build on Android (use a profile build), an emulator
   under 4 GB RAM, and on macOS a missing idb.
3. Optional on macOS, a big iOS speed-up: taps through idb (a few ms) instead of XCTest (~0.5 s). It needs
   `brew install facebook/fb/idb-companion`, which requires `brew trust --formula facebook/fb/idb-companion`, a
   system-level change that is the user's decision: ask first. Then
   `python3 -m venv ~/.cache/app-pilot/idb-venv && ~/.cache/app-pilot/idb-venv/bin/pip install fb-idb`.
4. Nothing else to configure: Android emulator animations are switched off for each run and restored after it;
   physical phones are used only when named with `--udid`/`--serial`.

## 1. Intake (every request)

Do not start driving the app straight away. Settle what to run, then run only that.

1. **Discover**, without asking what the repo can tell you: platforms (`app.platforms`, booted devices from
   `doctor`), languages (`app.locales`), the main journeys (routes, tabs, existing flows in the map, the saved
   explore map), and the accounts the flows need.
2. **Offer one menu** and let the user pick:
   - the main journey only;
   - every tab (a quick visual pass);
   - a full review of every screen, via explore (section 2);
   - something custom;

   crossed with platforms × languages and the purpose (store screenshots, website images, QA, an accessibility
   report). Give each option an estimated time and cost from the numbers in this file (explore ≈ 2.5 s per new
   screen on one device, ≈ 1.5 s with two, both platforms in parallel; a refresh of an explored app ≈ 15 s; Jev ≈
   $0.0001 per call).
3. **Production data is the user's call.** If the only accounts are real ones, say so and get a yes before running
   flows that sign in. Explore and read-only flows never write; anything a flow creates is listed and deleted after.
4. **Order**: a login flow first when the others assume a signed-in app, then the rest.
5. **Agent mode** (no user to answer, e.g. a scheduled or delegated run): never wait for the menu. Use safe
   defaults: read-only flows and explore only, every booted platform, the first locale, test accounts only.

## 2. Explore: map the app (read-only)

```bash
app-pilot explore .app-pilot/app-map.yaml --platforms ios,android [--locale en] [--depth 3] [--fresh] [--devices 2]
```

It browses like a person and writes `.app-pilot/discovery-<platform>-<locale>.json`: every distinct screen (title,
section, texts, controls, how it was reached), the links between them, external links, and the accessibility gaps.
Both platforms run at the same time. Measured on a Flutter app (~35 screens per platform, depth 3): ~80 s per
platform on one device, 45-55 s with `--devices 2`; ~15 s for a refresh.

- **Several devices per platform** (`--devices N`, or `--udid a,b` / `--serial a,b`): up to N booted simulators or
  emulators that have the app installed (and are signed in, if the app needs it) share one map. Each device takes
  whole sections (tabs, sub-tabs included) from a common queue; one that runs out takes untried controls over from
  another. Each device needs its own memory (an Android emulator ~4-9 GB on the host): on a machine that swaps, more
  devices make the run slower, not faster. A second simulator is `xcrun simctl create` + `simctl install` of the
  same build + the app map's login flow (`simctl clone` can fail on protected files); a second emulator is a copy of
  the AVD folder (`cp -c` on APFS) started with `-port 5556`. Ask before creating or booting devices.
- **Refresh by default.** The discovery file keeps the map. The next run checks each section's top screen again,
  asks Jev only about controls it has not judged before, and explores only what is new; the summary lists
  `newScreens` and `missing` section tops. `--fresh` explores everything again (after a large redesign).
- **Safety rules (never relaxed):** it types nothing; it never taps outward or confirming words (post, send, pay,
  delete, follow, share, log out, OK, allow, consent, link…, English and Spanish) nor switches, checkboxes or
  sliders, and Jev vetoes any control that "would change a setting, a preference, a consent choice or saved data";
  it records dialogs without answering them, with one exception: the "leave this page?" dialog its own back raised
  on a form it never typed into, which it answers with Exit/Discard; it detects when a tap opened another app (a
  browser) and comes back without acting there.
- **Navigation:** tab bars, the app's own back and close controls, iOS sheets swiped down, the system back last
  (never on a top-level Android screen, where it closes the app), and a relaunch only when no known route is left
  (reported under `relaunches`). A sheet or dialog is closed before heading to another section.
- **Start:** always a fresh start of the app (a running app keeps each tab's inner pages in memory). On Android a
  running app restarts in a new task (its navigation starts over in ~1 s instead of a cold start); if anything but
  the app is in front after that, a cold launch, and explore stops rather than tap another app.
- `APP_PILOT_DEBUG=1` logs each back rung (⤺), reopen (↺), relaunch reason (↻), external link (↗), and why a control
  was skipped. Use it before changing the runner.

## 3. Onboard an app (you, once per app)

Goal: write `<app-repo>/.app-pilot/app-map.yaml`. Read `references/app-map.md` first; its authoring
rules come from real failures and are not optional.

1. Learn the app's main journeys from its source (routes, tabs, main screens) if available, and from an explore
   run's discovery file (titles, texts and controls of every screen).
2. Walk each journey yourself with the agent-device CLI (`agent-device open <id> --platform ios`,
   `snapshot -i`, `press`, `screenshot`) and note the exact text visible on each target screen.
3. Write one flow per journey: a goal with explicit constraints, the inputs it types, and capture
   points whose `when` names **text that is on that screen**.
4. Run each flow with Jev (section 4). Fix the map from what the runs teach you, not the runner.

## 4. Run flows

From the app repo:

```bash
app-pilot run .app-pilot/app-map.yaml <flow> --platform ios [--udid <udid>]
app-pilot run .app-pilot/app-map.yaml <flow> --platform android [--serial <serial>]
app-pilot run-all .app-pilot/app-map.yaml [--flows a,b] [--platforms ios,android] [--locales es,en]
```

- `--locale <tag>` picks the app language for the run (default: the first of `app.locales`). iOS gets
  it as a launch argument; Android 13+ as a per-app language. Apps with their own in-app language
  setting ignore both: give them `language-<tag>` flows and run one before a locale batch.
- A passing run records `.app-pilot/paths/<flow>-<platform>-<locale>.json`; later runs replay it and
  only call Jev where the app has changed, plus one final "goal met" check. `--explore` ignores it.
  A run that passed after a handoff and `--resume` records too, with the handoff kept as a gap
  (`partial: true`): a replay stops there and Jev carries on; a later clean pass rewrites it without the gap.
  Language flows (see `references/app-map.md`) are keyed by the language the app starts in instead:
  `<flow>-<platform>-from-<start>.json`, so each starting language replays its own recording.
- **One folder per map.** Recordings, screenshots and discovery files live next to the map file. Two maps
  for one app (e.g. production and dev) need separate folders (`.app-pilot/dev/app-map.yaml`), or they
  overwrite each other's recordings.
- **Photo pickers are not supported.** Jev is not offered iOS photo-picker cells, and the Android system
  picker (`com.google.android.photopicker`) is refused as another app. A flow that picks a photo needs a
  handoff at that step; the rest of it still records and replays.
- **Output is only finished work:** a passing run copies its captures to
  `.app-pilot/screenshots/<platform>-<locale>/<flow>-<capture>.png` (replacing the previous version)
  and updates `screenshots/manifest.json`. Everything else (snapshots, frames, trace) lives in the OS
  temp dir (`$TMPDIR/app-pilot/<app>/`): deleted when a run passes, kept for the newest 5 failed runs
  (the summary's `runDir`). `--keep` keeps a passing run's files for debugging.
- Exit codes: 0 passed · 1 failed (the app contradicts the goal: report it as a bug) · 2 incomplete ·
  3 error · 4 needs_help.
- Run flows one at a time per device; each platform uses the session `app-pilot-<platform>`.

## 5. Handle a handoff (exit code 4)

Read `state.json` → `handoff` and follow `references/handoff.md`. In short:

| `handoff.reason`                                 | What you do                                                                                                                                                                                                 |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `uncertain`, `jev_requested_help`, `no_progress` | Look at the screen (`agent-device screenshot … --session app-pilot-<platform>`), do the one right step with the CLI in that session, then resume: `… run … --resume <runDir> --note '<action> -> <effect>'` |
| `uncertain_pass`, `uncertain_fail`               | Jev chose PASSED, or chose FAILED without a clear margin (often a screen still redrawing). Look at the screen: if it is right, resume with a note like `'Looked: the goal is shown -> no change'`; if it is still settling, resume so Jev looks again; if the app is really wrong, report the bug.                                     |
| `missing_captures`                               | The goal was reached but a capture's `when` never matched. Compare it with `state.handoff.missing[].lastProbability` and the screen text; reword it with on-screen text, rerun.                             |
| `action_failed`                                  | The app refused an action twice. Check for an overlay/permission prompt; clear it and resume.                                                                                                               |
| `unreadable_screen`                              | No accessibility tree. Screenshot it; if it is a game/canvas screen, the flow needs a different path.                                                                                                       |

If the same handoff repeats across runs, fix the map (clearer goal, a `labels` entry) rather than
handling it by hand every time.

## 6. Review and ship screenshots (you)

1. Read the new files in `.app-pilot/screenshots/<platform>-<locale>/` and judge them like a designer: loaded content (no spinners,
   no placeholder avatars), realistic data, no cut-off text, correct locale.
2. Reject and rerun rather than retouch. iOS screenshots are 1290×2796 (the App Store's 6.9" size) with a
   normalized status bar. Android ones are the emulator's native size; Google Play wants the long side at most twice
   the short one, so tall captures (e.g. 1280×2856) need framing or cropping before upload.
3. Export to the destination the user names (e.g. `sips -s format webp` for a website, or hand the
   PNGs to `aso-appstore-screenshots` for store listings).

## 7. Report

End with: flows run × platform, pass/fail, median step time, Jev calls and cost (from the summary),
screenshots produced, bugs found (exit 1 runs), and the accessibility gaps (`unlabeledControls`,
plus fields named only by inferred captions). Unlabeled controls are real accessibility defects in the
app; list them as a fix list for the app's developers.

## What the runner does so you do not have to

- Uses the raw accessibility tree (Flutter text inputs, unlabeled controls) and hides layers that are
  in the tree but not drawn (e.g. a consent web view), by checking element text against on-device OCR.
- Waits for real content after launch, polls until the screen settles after each action, and treats a
  pressed control that vanished (spinner) as "busy", all without model calls.
- Types fast into empty fields, verifies the text landed, and falls back to a verified fill.
- Offers only what a person could tap: not the page left under a pushed one, not groups whose frame is zero, the
  whole window, or centred on another control (Flutter on iOS reports such groups), and it treats "Tab 2 of 3"
  labels and labeled picture tiles as the controls they are.
- Goes back with the app's own back or close control (a native iOS back button is described as one), never with a
  blind tap, and stops before tapping or typing in another app.
- Offers one option per control, adds context to repeated labels ("♡ in 'Vintage lamp'"), names fields
  from their captions, and never offers keyboard keys (it has submit/dismiss actions instead).
- Acts only on a clear winner (confidence ≥ 0.7, or ≥ 0.45 with a 0.25 margin); passes on a calibrated
  "goal met" yes/no; re-observes before leaving a screen that is probably a pending capture.
