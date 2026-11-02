# Why the Fastfile does what it does

Each rule below cost a real release a failed upload, a broken feature or unreadable crashes. The
Fastfile enforces them, so do not "simplify" a lane without reading the reason first. Contents:
Google Play build numbers, CONFIRM, Sentry, bundle check, release notes, preconditions, rollout and
publishing, symbols archive, iOS.

## Google Play takes each version code once

Play rejects an upload whose version code it has seen, on any track, even if that release was never
published. So building again for production fails, and bumping the number would ship a different
binary from the one testers approved. The production lane therefore:

1. Reads the version codes of every track in `android.tracks`.
2. If the local build number is on `internal`, **promotes that build** (`track_promote_to` with
   `version_code`): no new build, the tested bits go to production.
3. Otherwise fails early when the build number is not above the highest on Play, before spending ten
   minutes building. The message says to raise it in `pubspec.yaml`.

A track that was never used can fail to read: the lane skips it with a warning, and stops only when
every track fails. Then the message lists each track's error and says what to check: the package id,
the very first AAB uploaded by hand in Play Console (the API cannot see an app before that), and the
service account's invite and permissions.

Only the tracks in `android.tracks` are read. A custom or closed testing track must be added there, or
its version codes are not seen and the highest-code check can miss them, so Play rejects the upload late.

## CONFIRM accepts `true` and "yes"

`make release-android CONFIRM=yes` becomes `confirm:yes`, and fastlane turns the strings "yes" and
"true" into the boolean `true` before the lane sees them. A check against the string "yes" alone
refuses a valid confirmation. The lane accepts both. Production steps need this explicit word so a
typo or a shell history replay cannot reach users.

## Sentry: the release name must equal what the app reports

`sentry_flutter` names the release `<package id>@<version>+<build>` with `dist` = the build number,
where the package id is the Android applicationId or the iOS bundle id. `sentry_dart_plugin` defaults
to `<pubspec name>@...`, so the symbols land on a release no crash ever uses and stack traces stay
obfuscated. The lane passes `release` and `dist` explicitly, per platform (the ids can differ).

Obfuscated Dart stack traces need two things, and the lane uploads both:

- the debug symbols from `--split-debug-info=<dir>` (`symbols_path`);
- the obfuscation map from `--extra-gen-snapshot-options=--save-obfuscation-map=<file>`
  (`dart_symbol_map_path`), which turns scrambled class and error names back into real ones.

The plugin settings are passed explicitly as `--sentry-define`, so they win over a `sentry:` block in
`pubspec.yaml` and new apps do not depend on plugin defaults. `commits` is `false` by default: `auto`
errors when the Sentry org has no linked repository, and is fine once one is linked. Everything the
upload needs (org, project, the plugin in `pubspec.yaml`, the token) is checked before the build starts,
not after ten minutes of compiling.

The token goes in only through the `SENTRY_AUTH_TOKEN` environment variable. Given as plugin config,
the plugin echoes `--auth-token <value>` in its command line and the secret lands in terminal
scrollback and CI logs. The lane sets the variable for the upload and restores the previous value
afterwards, so nothing leaks into later steps. If `sentry.enabled` is false the whole step is skipped.

If an app overrides `options.release` or `options.dist` in code, the Fastfile's names must follow it;
otherwise leave the SDK defaults.

## The bundle check before upload

Two failures happen only in store builds, so they are caught on the finished AAB:

- **Shrunk resources.** The release resource shrinker removes resources it thinks are unused. Some are
  looked up by name at runtime (Google sign-in's `default_web_client_id`, notification icons). A plugin
  keeps its own with a `res/raw/keep.xml`; an app-level `android/app/src/main/res/raw/keep.xml` **replaces**
  it, because resources merge by file name. In one app the shrinker then removed
  `default_web_client_id` and Google sign-in broke only in store builds. The lane unzips
  `base/resources.pb` from the AAB and greps each name in `android.required_resources`. Name an
  app-level keep file anything but `keep.xml` (for example `app_keep.xml`).
- **Wrong signature.** A build signed with the debug key is rejected by Play, late and with a vague
  message. The lane runs `keytool -printcert -jarfile` and refuses an AAB signed by `CN=Android Debug`
  or with no signer, which usually means `android/key.properties` was missing.

## Release notes

Notes come from the `## [<version>]` section of the files in `android.notes` (one per Play language)
and `ios.notes_file`. A missing section fails the run, because shipping with empty notes is easy to
miss. Play limits each language to 500 characters, so a language over `notes_limit` is caught before the upload: the lane
fails with the file, version and length. The text is written to `build/fastlane/play-metadata/<lang>/changelogs/<build>.txt`,
the layout the Play upload reads.

## Preconditions

A release runs from `release_branch`, with a clean tracked tree (untracked files are allowed), equal to
`origin/<branch>` after a fetch. What reaches a store must be what teammates can check out; a release
from a dirty tree cannot be reproduced and a crash cannot be matched to a commit.

## Rollout and publishing

- `default_rollout` (20) applies to production when ROLLOUT is not given. At 100 the release is
  `completed`; below, `inProgress` (a staged rollout).
- In a staged rollout, existing users and new installs both get the new version only within that
  percentage; the rest get the previous release until the percentage is raised. Raise it with
  `make release-rollout PERCENT=<n> CONFIRM=yes`, up to 100.
- If **managed publishing** is on in Play Console, an approved release is held until someone clicks
  Publish there. A green lane means "accepted by Play", not "live".
- Review by Google can take hours to days; `release-check` shows what is on each track.

## Symbols archive

Debug symbols and the obfuscation map are the only way to read an old obfuscated crash, and a rebuild
does not reproduce them. They are archived per release under
`<symbols_dir>/<version>+<build>/<android|ios>`, outside the repo and outside `build/` (which
`flutter clean` wipes). Back that folder up.

## iOS

The lane uploads to TestFlight through an App Store Connect API key (no Apple ID password, no 2FA
prompt) and does not wait for Apple's processing (`skip_waiting_for_build_processing`), because that
can take half an hour; the build appears in TestFlight when ready. Sending it for App Review is done
in App Store Connect. The build number is checked per version against TestFlight, the same early
failure as on Play.

## CONFIRM from the environment

`CONFIRM=yes` exported in a shell would confirm every production run without typing it. The Makefile only
passes `confirm:` when CONFIRM was given on the make command line (`$(origin CONFIRM)`), so an exported
value is ignored.

## Environment selection

`flutter build` without `--flavor` leaves `appFlavor` null. An app that maps null to development ships a
store build with development keys and banner. The Fastfile cannot know every app's scheme, so the skill
checks it at setup (SKILL.md, step 2), and `check` and the release lanes warn when `flutter.flavor` is
empty and the code reads `appFlavor`.

## Before the first build

- **Ask before the first `check`.** Default credential names can match real keys already on the machine,
  and `check` reads Play, App Store Connect and Sentry with them. The skill lists which files exist and waits
  for an OK first.
- **Play language codes.** Notes are uploaded per listing language, and a code that is not enabled on the
  listing fails the upload, after the long build. `es-ES` and `es-419` are different, a guess went wrong in
  a real run, so the user confirms the codes and `check` compares them with the listing read from Play. `android release` repeats the comparison before the build on the upload path (not when promoting, which sends no notes): a missing code fails the lane, an unreadable listing only warns.
- **Placeholder ids.** An application id or bundle id cannot change after the first upload, so a template
  id (`com.example.*`, the starter's) is replaced first.
- **Export compliance.** Without `ITSAppUsesNonExemptEncryption` each TestFlight build waits for a manual
  "Missing Compliance" answer. It is a legal declaration, so only the user decides its value.
- **Debug signing.** Flutter's template signs release with the debug key. The skill flags it at setup and
  `check` warns, and the AAB signer check stays as the last line of defence.

## `release-check` is read-only

It reads files, version codes, the listing languages, the TestFlight build number and (with a request) the
Sentry project. The listing is read through a Play edit that is opened only to read and always deleted,
never committed (`download_from_play_store` would also download every screenshot). It never builds,
uploads, promotes, fetches or edits anything, so it is safe to run during setup and before
every release. It lists all the problems it finds, not only the first, and exits non-zero when something
blocks a release. Git state, symbols inside the repo and flavor are warnings, because they are fixed
right before releasing.
