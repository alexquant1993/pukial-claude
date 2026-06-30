---
name: new-app
description: >
  Use this skill when the user wants to create a new app from this starter, scaffold a new
  Flutter project, port this starter to a new app, rename the starter, or start a fresh app
  based on flutter-pukial-starter. Trigger phrases: "create a new app", "scaffold a new app",
  "start a new app from this starter", "port this starter", "rename the starter".
---

# new-app Skill

You are an agent porting `flutter-pukial-starter` into a brand-new Flutter app. This skill
guides the full copy → rename → strip → verify process so every port is identical and no
step is missed.

---

## Phase 1 — Gather answers

Ask the user for the following (ask all at once, not one at a time):

1. **App name** — used in two forms:
   - *Package name* (snake_case, e.g. `my_expense_app`): goes in `pubspec.yaml`, import paths,
     Android namespace/applicationId.
   - *Display name* (e.g. `My Expense App`): shown in the app launcher, Android label, iOS
     CFBundleDisplayName.
   If only one name is provided, derive snake_case automatically and confirm.

2. **Destination path** — absolute path where the new app should be created
   (e.g. `/Users/you/projects/my_expense_app`). The folder must not yet exist.

3. **Org / bundle-ID prefix** — default `com.pukial`.
   The full Android applicationId will be `<org>.<package_name>`;
   the iOS bundle ID will be `<org>.<package_name_camelCase>`.

4. **Flavors** — dev + prod are always created. Add a **staging** flavor too? (yes/no, default no)

5. **Strip RevenueCat?** — RevenueCat (`lib/src/purchases/`) is the one strippable standalone
   integration. It lives in its own folder and is wired through a single provider + one init
   line in `main.dart`.
   - If **kept**: it no-ops silently on empty keys — just fill `.env.*` when ready.
   - If **stripped**: its folder, provider wiring, and env keys are removed; analyze confirms
     the result compiles clean.
   - **Sentry is always kept** — it is core infrastructure.
   - **Mixpanel is NOT offered here** — it lives inside the always-kept `monitoring/` folder and
     is silently disabled by leaving `MIXPANEL_TOKEN` empty (token-gated no-op). There is no
     folder to delete.
   - **Notifications are not included** in this starter (no local or push stack). When an app
     needs them, adapt a proven `awesome_notifications` + FCM implementation from your own
     reference app per-app, behind a service interface — it is not a strip option.

6. **Keep the `example` reference feature?** — default **keep**.
   `lib/src/features/example/` is the canonical data/domain/application/presentation pattern.
   A new agent (or developer) should read it before building the first real feature.
   Offer to remove it once the team is comfortable with the pattern.

7. **Firebase needed?** — report-only. This skill cannot wire Firebase mechanically, but if
   "yes", it will tailor the closing manual-steps report (e.g. `flutterfire configure`, adding
   `firebase_*` deps, placing `google-services.json`/`GoogleService-Info.plist`).

8. **`git init` the new app?** — yes/no, default yes.

---

## Phase 2 — Perform the copy

### 2a. Copy the starter

```bash
# Exclude: .git, .dart_tool, build/, .env.dev, .env.prod, .fvm/ (Flutter SDK binaries)
rsync -av --exclude='.git' --exclude='.dart_tool' --exclude='build' \
  --exclude='.env.dev' --exclude='.env.prod' --exclude='.fvm' \
  /path/to/flutter-pukial-starter/ <DEST>/
```

The `.fvmrc` and `pubspec.lock` ARE copied — this gives the new app the same pinned Flutter SDK
and exact package versions as the starter (reproducible from day one).

### 2b. Run the rename helper

```bash
cd <DEST>
# Run rename.sh from THIS skill's own directory — substitute the absolute path you were given as
# "Base directory for this skill" when this skill loaded (`.claude/skills/new-app/` for a repo-level
# copy, or the plugin install path under `pukial-flutter`). It operates on the current directory, so
# cwd must be <DEST> as above.
bash "<skill-dir>/rename.sh" <new_snake_package> "<New Display Name>" <org.prefix>
```

This rewrites:
- `pubspec.yaml` name + description
- All `package:flutter_pukial_starter/` → `package:<new_package>/` across `lib/` + `test/`
- `android/app/build.gradle.kts`: `namespace` + `applicationId` (both currently
  `com.pukial.flutter_pukial_starter`)
- `android/app/src/main/AndroidManifest.xml`: `android:label` (currently
  `flutter_pukial_starter`)
- `ios/Runner/Info.plist`: `CFBundleDisplayName` (currently `Flutter Pukial Starter`)
- `ios/Runner.xcodeproj/project.pbxproj`: `PRODUCT_BUNDLE_IDENTIFIER` (currently
  `com.pukial.flutterPukialStarter` for the Runner target; `…RunnerTests` for tests)

`rename.sh` echoes each change and exits non-zero on any failed/zero-match substitution, so
failures are loud. Inspect its output and fix any reported failures before proceeding.

### 2c. Scaffold `.env.*` from examples

```bash
cp .env.dev.example .env.dev
cp .env.prod.example .env.prod
```

All keys are empty — fill them per-app. The app boots cleanly with empty keys: Sentry, Mixpanel,
and RevenueCat each detect an empty key and skip initialization silently (§6.0 no-op contract).

---

## Phase 3 — Conditional strips

### 3a. Strip the `example` reference feature (if user said remove)

Default is KEEP. Only run these steps if the user explicitly chose to remove it.

```bash
rm -rf lib/src/features/example/
rm -rf test/src/features/example/
```

Also remove the three tagged wiring references (grep tag: `// Reference feature`):

1. **`lib/src/routing/app_router.dart`** — remove the import line:
   ```dart
   import 'package:flutter_pukial_starter/src/features/example/presentation/example_screen.dart'; // Reference feature — remove with features/example/
   ```
   And remove the nested route block tagged with the same comment:
   ```dart
   // Reference feature — remove with features/example/
   GoRoute(
     path: 'example',
     builder: (BuildContext context, GoRouterState state) =>
         const ExampleScreen(),
   ),
   ```
   After removing, also remove the now-empty `routes: <RouteBase>[...]` wrapper on the
   `/home` GoRoute if it becomes empty (leave it clean, no trailing comma issues).

2. **`lib/src/features/home/home_screen.dart`** — remove the button block tagged:
   ```dart
   // Reference feature — remove with features/example/
   OutlinedButton(
     onPressed: () => context.go('/home/example'),
     child: Text(context.loc.exampleTitle),
   ),
   ```
   Also remove the now-unused `import 'package:go_router/go_router.dart';` if `go_router`
   is no longer referenced in that file (check before removing).

**Note:** After import removal in `app_router.dart`, adjust the package prefix in the import
to match the new app's package name (the rename step already did this globally, but double-check
that the import you delete has the new package name, not the old one, to avoid a stale reference).

### 3b. Strip RevenueCat (if user said strip)

```bash
rm -rf lib/src/purchases/
rm -rf test/src/purchases/
```

Then make these code edits:

1. **`lib/src/app/app_startup.dart`** — remove the import and the init line:
   ```dart
   import 'package:<new_package>/src/purchases/purchases_providers.dart';
   // ...
   await ref.read(purchaseServiceProvider).init();
   ```

2. **`.env.dev`** and **`.env.prod`** — remove these two keys:
   ```
   REVENUECAT_ANDROID_KEY=
   REVENUECAT_IOS_KEY=
   ```

3. **`lib/config/env/env_dev.dart`** and **`env_prod.dart`** — remove the two RevenueCat
   `@EnviedField` entries:
   ```dart
   @EnviedField(varName: 'REVENUECAT_ANDROID_KEY', optional: true)
   static const String revenueCatAndroidKey = _EnvDev.revenueCatAndroidKey;
   @EnviedField(varName: 'REVENUECAT_IOS_KEY', optional: true)
   static const String revenueCatIosKey = _EnvDev.revenueCatIosKey;
   ```

4. **`lib/config/env/env_keys.dart`** — remove the two RevenueCat getters:
   ```dart
   static String get revenueCatAndroidKey => ...;
   static String get revenueCatIosKey => ...;
   ```

5. **`pubspec.yaml`** — remove the now-unused dependency so the stripped app
   carries no dead package:
   ```yaml
   purchases_flutter: ^9.6.2
   ```

After these edits run `make codegen` (regenerates the env `.g.dart` without the
RevenueCat fields) and `fvm flutter analyze` (must be zero issues).

### 3c. Add staging flavor (if user said yes)

Add `staging` to the `Flavor` enum in `lib/config/flavor.dart`:
```dart
enum Flavor {
  development('dev'),
  staging('stg'),
  production('prod');
  ...
}
```

Add `env_stg.dart` mirroring `env_dev.dart` (path `.env.stg`).
Update `EnvKeys` in `env_keys.dart` to handle `Flavor.staging`.
Copy `.env.dev.example` → `.env.stg.example` and add `.env.stg` to `.gitignore`.
Update `Makefile` if it has flavor-specific targets.

---

## Phase 4 — Self-verify

Run ALL of these; do not skip any:

```bash
cd <DEST>
fvm flutter pub get
fvm dart run build_runner build --delete-conflicting-outputs
fvm dart fix --apply   # REQUIRED: the package rename reorders imports alphabetically
                       # (e.g. package:<new>/ now sorts differently), which trips the
                       # strict `directives_ordering` lint in ~every file. dart fix
                       # auto-sorts them. Skipping this leaves dozens of analyze infos.
fvm flutter analyze
```

**If `fvm flutter analyze` reports any errors**, diagnose and fix them before reporting success.
Common causes after stripping:
- Leftover import of a deleted file.
- `routes: <RouteBase>[]` left with a trailing comma but no routes (remove the empty list).
- A generated `.g.dart` that references a deleted provider (re-run codegen after stripping).
- Unused import after removing the example button from `home_screen.dart`.

Never hand back a non-analyzing app. Fix forward.

---

## Phase 5 — Optional: git init

If the user said yes:

```bash
cd <DEST>
git init
git add -A
git commit -m "chore: scaffold <new_display_name> from flutter-pukial-starter"
```

---

## Phase 6 — Report remaining manual steps

Always report these at the end, regardless of what was stripped:

### Required before first run on a real device / CI

- **Fill `.env.dev` and `.env.prod`** with real keys:
  - `SENTRY_DSN` — from sentry.io project settings
  - `MIXPANEL_TOKEN` — from mixpanel.com (leave blank to disable analytics; no code change needed)
  - `APPSTORE_ID` — Apple App Store numeric ID (for force-update "open store" link)
  - `FORCE_UPDATE_MIN_VERSION_URL` — URL returning `{ "min_version": "1.0.0" }` JSON; leave
    blank on empty key → fail-open (app always boots, no blocking screen)
  - `REVENUECAT_ANDROID_KEY` / `REVENUECAT_IOS_KEY` — only if RevenueCat was kept

- **Re-run codegen** after filling env keys: `fvm dart run build_runner build --delete-conflicting-outputs`

### If Firebase = yes (as reported)

- Add `firebase_core` and other needed `firebase_*` deps to `pubspec.yaml`
- Run: `flutterfire configure` (installs FlutterFire CLI if missing: `dart pub global activate flutterfire_cli`)
- Place generated `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)
- Implement a real `AuthRepository` (see `lib/src/features/authentication/data/auth_repository.dart`) backed by
  `FirebaseAuth` and override `authRepositoryProvider`

### Always

- Replace the stub `FakeAuthRepository` with a real auth backend when you're ready (implement
  `AuthRepository`, override `authRepositoryProvider` in `ProviderScope` overrides or by
  editing `lib/src/features/authentication/data/auth_repository.dart`).
- Register your app in the RevenueCat dashboard and configure entitlements (if kept).
- Notifications: not included in the starter. Adapt a proven `awesome_notifications` + FCM
  setup from your own reference app per-app, behind your own service interface.
- Update `pubspec.yaml` `description` and `version` fields for your new app.
- Update `l10n/` ARB files: add your app's specific strings; the starter ships English + Spanish
  starter strings only.
- Replace the `appTitle` l10n string and the placeholder theme brand color
  (`lib/src/styles/app_theme.dart`) with your app's identity.
