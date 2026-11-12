---
name: store-release
description: >-
  Set up fastlane store releases in a Flutter app: install the Fastfile, `make release-android`,
  `make release-ios` and a read-only `make release-check` that build, upload to Google Play (internal,
  production, staged rollout) and TestFlight from the terminal, and upload Sentry debug symbols and the
  obfuscation map under the right release name. Use it whenever the user wants to set up or add
  fastlane, automate store uploads, release to Google Play or TestFlight from the terminal, stop
  uploading builds by hand in the consoles, upload Sentry symbols on release, or create a Play service
  account or App Store Connect API key for releasing, even if they do not name fastlane. Works for a
  new app from flutter-pukial-starter and for an existing Flutter app (flavors or not, Sentry or not).
  Not for running a release in an app that already has this setup (beyond explaining its commands), a
  single failed upload or store rejection, or general CI; those are ordinary debugging.
---

# Store release with fastlane

Install a release pipeline that works the same in every app: one **generic Fastfile** plus a
`fastlane/release.yml` that holds everything app-specific. The Fastfile is copied unchanged, so a fix
can be copied into every app later and a new app costs one yml plus the console setup. It generalizes a
setup running in production in a Flutter app.

Lanes: Android `release` (internal or production, staged rollout, promotes the build already on
internal), Android `rollout`, iOS `release` (TestFlight through an App Store Connect API key) and a
read-only `check`, exposed as `make release-check`. Sentry symbol upload and the Google sign-in resource
check switch off cleanly when the app does not use them.

## Ground rules

- **Secrets stay out of the repo and out of your context.** Credentials live in `~/.secure_credentials/`
  (`chmod 600`). The user creates and moves them. Never read, print or copy them or
  `android/key.properties`; refer to them by path and check existence with `[ -f path ]`.
- **Never run `release`, `rollout`, `fastlane android ...` or `fastlane ios ...`.** They publish to real
  stores. Store uploads are the user's to run. The only lane you run is `check`.
- **Inspect first, ask second.** Most values are in the repo; every question you can answer yourself
  wastes the user's time.

## Already installed?

If `fastlane/release.yml` and a generic `fastlane/Fastfile` (it reads `release.yml`) exist, do not
reinstall. Run `make release-check`, explain what it prints, and explain the commands in "Hand off". The
user runs any publishing. If they want a newer Fastfile, compare it with `assets/Fastfile`, show the
difference, keep their `release.yml`, and replace the Fastfile only after they agree.

## Workflow

### 1. Inspect the app

Read `references/inspect.md` and collect: Android applicationId, iOS bundle id and team id, flavors and
entry points, fvm, Sentry (dependencies, org, project, region, an existing `sentry:` block), Google
sign-in, release-notes files, whether `android/key.properties` exists (existence
only), the `pubspec.yaml` version, the release branch, and any fastlane files already there.

Also flag, before writing anything (detection and wording in `references/inspect.md`, "Flag before
installing"): placeholder app ids, a release build signed with the debug key, and a missing iOS export
compliance key. Each is permanent or blocks every upload, so tell the user and let them decide. Change
the app's code only if they agree.

### 2. Check how the app picks its environment (mandatory)

Many apps choose their backend, keys and banner at build time. If the release build does not select
production, the store gets a build wired to development, and nothing in the pipeline notices. Before
installing anything, search for it:

```bash
grep -rnE "appFlavor|getFlavor|Flavor\.|String\.fromEnvironment" lib | head -40
```

Then decide what the release build (the `flavor`, `target` and `extra_args` you would put in
`release.yml`) will select:

- **Fine**: the app has no build-time environment choice, or a native production flavor exists (gradle
  `productFlavors`, matching Xcode scheme) and the app maps it to production.
- **Stop**: the app reads `appFlavor` (or a `--dart-define`) and the release build would not select
  production, because there is no native production flavor or the fallback is development.

On **stop**, install nothing. Tell the user in plain words: "As it is, a store build of this app would
use the development settings (its keys, services and a DEV banner), because it only picks production when
built with a production flavor, and the project has none." Offer the two ways out:

1. Add native flavors (Android `productFlavors`, iOS schemes and configurations, an entry point if the app
   uses one per flavor), so `--flavor production` works.
2. Make the release build select production without flavors, for example a default that is production, or
   a `--dart-define` the app reads (`flutter.extra_args` carries it).

Change the app's code only if the user asks. Resume at step 3 once one is done.

`flutter-pukial-starter` is a stop case today: `lib/config/flavor.dart` reads `appFlavor` and falls back to
development, while the project has no native flavors and only `lib/main.dart`. A production mobile build of
the starter needs one of the two ways out first. Apps already scaffolded from it may have added flavors, so
look before assuming.

### 3. Ask only what the repo cannot tell

One message, defaults filled in, covering what `references/inspect.md` lists as unknowable: the final app
ids when the current ones are placeholders, where to archive the symbols, Sentry slugs, credential file
names, which platforms ship, whether the app already exists in both stores, and the **Play listing
languages**. The language codes in `android.notes` must match those enabled on the store listing, which the
repo cannot tell: show the notes files you found and the likely codes as a suggestion and ask. Never assume
a regional variant (`es-ES` versus `es-419`); a wrong code fails the upload. Write only the codes the user
confirmed. Leave a notes file whose code is unconfirmed commented out in `release.yml` with
`# confirm the Play language code`, instead of a guess. `make release-check` later compares the codes with
the real listing. If it is missing from a store, say that the first upload
needs the console (`references/console-setup.md`) and continue with the other parts.

### 4. Install

**Existing fastlane files first.** Look before copying: `ls fastlane`, read any `Fastfile` and `Appfile`
there, and check the `Makefile` for fastlane targets. If something exists, back it up (`Fastfile.bak`), show
the user the difference and ask. Their custom lanes can stay below the generic part only if they want that;
say it makes later copies of the generic Fastfile harder.

Copy from `assets/` (paths relative to the app root; create `fastlane/` if needed):

| Asset | Goes to | Notes |
|---|---|---|
| `Fastfile` | `fastlane/Fastfile` | Unchanged. App values belong in `release.yml`. |
| `Appfile` | `fastlane/Appfile` | Unchanged. It reads `release.yml` too. |
| `release.yml` | `fastlane/release.yml` | Fill every value from steps 1 to 3. Keep the comments. Commit it (no secrets). |
| `Makefile.snippet` | append to `Makefile` | Create one if missing. If it already has the targets or a `FASTLANE` variable, merge. |
| `gitignore.snippet` | append to `.gitignore` | Skip lines already there. |
| `README-releasing.md` | app `README.md`, section "Releasing" | Fill the `<PLACEHOLDERS>`; drop Sentry text when off and lines of a platform that is off. |
| `RELEASE_NOTES.md` | repo root | Only when the app has no notes file (format: `## [x.y.z]` sections). |

Decide each `release.yml` value like this:

- No flavor (after step 2 said fine): `flavor` and `target` empty, `aab` is
  `build/app/outputs/bundle/release/app-release.aab`.
- No Sentry: `sentry.enabled: false`, delete the other `sentry` keys and the `sentry_token` credential. With
  Sentry: `sentry_dart_plugin` must be a dev dependency (`<dart> pub add --dev sentry_dart_plugin`).
- If the app already has a `sentry:` block in `pubspec.yaml`, leave it. Tell the user that the values in
  `release.yml` (org, project, url, commits, ignore_missing, symbol paths) are passed on the command line
  and win over that block.
- Google sign-in: `required_resources: [default_web_client_id]`; otherwise leave the list empty.
- One platform only: set `platforms` to it and remove the other platform's block.
- `symbols_dir` outside the repo. `release_branch` is the repo's default branch.
- With a `Gemfile` for fastlane, prefix the Makefile's `FASTLANE` variable with `bundle exec`.

### 5. Console setup (the user does this)

Read `references/console-setup.md` and walk the user through what is not done yet: Google Cloud API and a
service account with no roles, the Play Console invite with exactly the needed permissions, the very first
AAB uploaded by hand, the App Store Connect Team key with App Manager (the `.p8` downloads once), the Sentry
token. One store at a time, wait for "done". The user creates the files and moves them to
`~/.secure_credentials/`; you never see their content.

### 6. Verify (read-only)

```bash
ruby -c fastlane/Fastfile
LC_ALL=en_US.UTF-8 FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_USAGE=YES fastlane lanes
```

Before `make release-check`, see which credential files from `release.yml` already exist (`[ -f path ]`,
never open them). The default names can match real keys the user made earlier, and the check would use
them without anyone noticing. If any exist, say in plain words: "release-check will use these keys to read
build numbers from Google Play, App Store Connect and Sentry. It is read-only and publishes nothing." Wait
for an OK, then run `make release-check`. If none exist, run it: it fails locally without any network.

Expect the lanes `check`, `android release`, `android rollout`, `ios release` (fewer when a platform is
off). `release-check` lists every problem at once (missing release.yml values, credentials, tools, the
Play and TestFlight build numbers, the Play listing languages against `android.notes`, the Sentry token,
notes over the Play limit) and prints warnings for
things a release needs fixed (git state, symbols inside the repo, flavor). It changes nothing.

Before step 5 is done it fails naming the missing files: report that as "waiting for the console setup",
not as a broken install. Never run another lane to "test" it.

### 7. Hand off

Tell the user, in plain words:

- Which files were created or changed, and that `fastlane/release.yml` is the only place to edit app values.
- That store uploads are theirs to run: `make release-check`, `make release-android TRACK=internal`,
  `make release-android TRACK=production ROLLOUT=20 CONFIRM=yes`, `make release-rollout PERCENT=100 CONFIRM=yes`,
  `make release-ios`.
- The routine: raise `version:` in `pubspec.yaml`, add the `## [<version>]` notes, commit and push to the
  release branch, `make release-check`, internal first, then production (which promotes the internal build).
- What staged rollout and managed publishing mean (`references/lessons.md`, "Rollout and publishing").
- What is left undone: credentials not created, an app missing from a store, a stop from step 2.

## Two apps from one repo (flavors)

When one Flutter repo ships two store apps (a store flavor and a development flavor), keep one Fastfile and
add a second settings file next to `release.yml`: `fastlane/release-<name>.yml`, e.g. `release-dev.yml`
with `flavor: development`, its own `application_id`, `bundle_id`, `aab` path and `symbols_dir`, and the
same credentials. The `RELEASE_CONFIG` environment variable names the file (a plain name like
`release-dev.yml`, nothing else is accepted); unset, the lanes read `release.yml` exactly as before. The
Makefile targets pass it through `CONFIG`: `make release-check CONFIG=release-dev.yml`,
`make release-android TRACK=internal CONFIG=release-dev.yml`. The app's own Makefile may add short aliases
(`release-android-dev`) and its own guards on top; the shared snippet stays generic.

## The rules the Fastfile enforces

`references/lessons.md` has the reasons; read it before changing a lane or when the user asks why.

- Play accepts a version code once: production promotes the build already on internal, otherwise the run
  fails early if the build number is not above Play's highest.
- fastlane turns `yes` and `true` into boolean `true` before the lane runs, so CONFIRM accepts both.
- The Sentry release is `<id>@<version>+<build>` with dist = build; symbols and the obfuscation map are
  uploaded; the token travels only in `SENTRY_AUTH_TOKEN` and is restored afterwards.
- The AAB is checked before upload for required resources and against the Android Debug signature.
- Notes come from `## [<version>]` sections; a language over the limit fails the run.
- Releases run from the release branch, clean and equal to origin.
- Symbols are archived per release under `<symbols_dir>/<version>+<build>/<android|ios>`.

## Files

- `assets/`: files to copy (`Fastfile`, `Appfile`, `release.yml`, snippets, README section, notes stub).
- `references/inspect.md`: what to detect, and what to ask.
- `references/console-setup.md`: the one-time Google, Apple and Sentry setup.
- `references/lessons.md`: why each rule exists.
- `evals/evals.json`: three test prompts.
