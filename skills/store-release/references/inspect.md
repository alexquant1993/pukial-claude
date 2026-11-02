# Inspecting the app

Read these before asking the user anything. Every value found here is one question saved. Use plain
`grep`, `ls` and `[ -f path ]` (the user's shell may override `test`). Never open `android/key.properties`,
`~/.secure_credentials` or any `*.jks`, `*.p8`, `*service-account*.json`: check that they exist, nothing more.

| Need | Where to look | Notes |
|---|---|---|
| Android `application_id` | `android/app/build.gradle(.kts)`: `applicationId` | With flavors, take the production flavor's `applicationId` plus its `applicationIdSuffix`. Not the `namespace`. |
| iOS `bundle_id` | `ios/Runner.xcodeproj/project.pbxproj`: `PRODUCT_BUNDLE_IDENTIFIER` | Ignore the `.RunnerTests` lines. With flavors the id can live in `ios/Flutter/*.xcconfig` or per build configuration (`Release-production`). It can differ from the Android id (`com.acme.my_app` vs `com.acme.myApp`), so Sentry releases are named per platform. |
| iOS `team_id` | same file: `DEVELOPMENT_TEAM` | Ten characters. If missing, ask. |
| Build-time environment | `grep -rnE "appFlavor\|getFlavor\|Flavor\.\|String\.fromEnvironment" lib` | Mandatory, see below. `appFlavor` is only set by `--flavor`; without a native flavor it is null and apps usually fall back to development. |
| Flavors | `productFlavors` in the gradle file; `ios/Runner.xcodeproj/xcshareddata/xcschemes/*.xcscheme`; `lib/main_*.dart`; `Makefile`, `README.md`, `.vscode/launch.json` run commands | Release command looks like `flutter build appbundle --flavor production -t lib/main_production.dart`. No flavors means empty `flavor` and `target`. |
| fvm | `.fvmrc` or `.fvm/` | Yes: `command: fvm flutter`, `dart_command: fvm dart`. No: `flutter` and `dart`. If the Makefile already has `FLUTTER=`/`DART=` variables, mirror them. |
| Bundle path | Flutter's own rule | Flavor `production`: `build/app/outputs/bundle/productionRelease/app-production-release.aab`. No flavor: `build/app/outputs/bundle/release/app-release.aab`. |
| Sentry | `pubspec.yaml`: `sentry_flutter`, `sentry_dart_plugin`, a `sentry:` block (`org`, `project`) | The plugin may be missing: add it as a dev dependency (`<dart> pub add --dev sentry_dart_plugin`). Region: look for a `de.sentry.io` or `us.sentry.io` host in the block or in the DSN setup. If the app sets `options.release` or `options.dist` itself, the release name in `release.yml` must match it. |
| Google sign-in | `pubspec.yaml`: `google_sign_in`; Firebase Auth with Google | Yes: `required_resources: [default_web_client_id]`. Also list `ls android/app/src/main/res/raw/` and warn when an app-level `keep.xml` exists (see `lessons.md`, bundle check). |
| Other resources looked up by name | notification icon packages (`awesome_notifications`, `flutter_local_notifications`) | Add the drawable names they load by string to `required_resources`. |
| Release notes | `ls RELEASE_NOTES*.md CHANGELOG*.md`; top `## [x.y.z]` headings | One file per Play language. Language hints: `l10n.yaml`, `lib/l10n/*.arb`. Map to Play codes (`en-US`, `es-ES`, `es-419`). |
| Upload key | `[ -f android/key.properties ]`, `signingConfigs` in the gradle file | Existence only. Missing is fine for `release-check`, fatal for a real build. |
| Current version | `pubspec.yaml`: `version: x.y.z+n` | Must have both parts. |
| Branch | `git rev-parse --abbrev-ref HEAD`, `git symbolic-ref refs/remotes/origin/HEAD` | Default `release_branch` is the repo's default branch. |
| Tools | `command -v fastlane ruby keytool unzip curl` | Missing fastlane: `brew install fastlane`. Missing keytool: a JDK (Android Studio ships one). |
| Existing setup | `ls fastlane Gemfile`; `grep -n fastlane Makefile` | Never overwrite silently. See SKILL.md, "Existing fastlane". |

## Environment gate (mandatory)

An app that picks its environment at build time (Sentry DSN, backend, analytics and purchase keys, a DEV
banner) must select production in the release build. Read the match from the grep above:

- `appFlavor` / `getFlavor()`: which flavor names map to production (`'production' || 'prod'`), and what
  the `null`/empty fallback is. A fallback of development is the dangerous case.
- `String.fromEnvironment(...)` or `--dart-define`: whether the default is production, or whether the release
  build would have to pass a value (`flutter.extra_args`).
- Native side: `productFlavors` in gradle and a matching Xcode scheme and configurations for the flavor name.

Fine: no build-time choice, or a native production flavor that the app maps to production. Stop: the app
reads `appFlavor` and no production flavor exists (a release without `--flavor` gets the fallback), or a
dart-define default is not production and nothing would pass it. Then install nothing and follow SKILL.md,
step 2. `flutter-pukial-starter` is a stop case: no native flavors, only `lib/main.dart`, and a development
fallback in `lib/config/flavor.dart`.

## What the repo cannot tell

Ask only for these, all in one message, with the detected value as the default where there is one:

- Where to archive the symbols (a folder outside the repo, for example `~/release-symbols/<app>`).
- The Sentry org and project slugs, when they are not in `pubspec.yaml`.
- The Play languages and their notes files, when more than one language ships.
- Credential file names, when the user wants something other than `<app>-play-service-account.json`,
  `<app>-asc-api-key.json` and `.p8`, `<app>-sentry-auth-token` under `~/.secure_credentials/`.
- Which of Android and iOS ship.
- Whether the app already exists in Play Console and App Store Connect (see `console-setup.md`).
