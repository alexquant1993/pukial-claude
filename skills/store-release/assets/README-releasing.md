### Releasing

Store builds go out through [fastlane](https://fastlane.tools) (`fastlane/Fastfile`; every app-specific
value is in `fastlane/release.yml`). Raise `version:` in `pubspec.yaml`, add a `## [<version>]` section
to the release notes file(s) (<PLAY_NOTES_LIMIT> characters at most each, Google Play's limit), commit
and push to <BRANCH>, then:

```bash
make release-check                                            # read-only: credentials and the build numbers in each store
make release-android TRACK=internal                           # Google Play internal testing
make release-android TRACK=production ROLLOUT=100 CONFIRM=yes # production (ROLLOUT in %, default <DEFAULT_ROLLOUT>)
make release-rollout PERCENT=100 CONFIRM=yes                  # change the production rollout later
make release-ios                                              # TestFlight
```

Each run stops before anything reaches a store if a check fails:

1. Checks: on <BRANCH>, no uncommitted changes, same as origin/<BRANCH>, release notes for the version, and a
   build number higher than the one already in the store.
2. Builds the release obfuscated, with the symbols in `<SYMBOLS_DIR>/<version>+<build>/<android|ios>`
   plus the obfuscation map.
3. Android only: checks that the bundle is signed with the upload key<REQUIRED_RESOURCES_CLAUSE>.
4. Uploads the symbols to Sentry under the release the app reports (`<ID>@<version>+<build>`), so crashes
   show readable stack traces and error names.
5. Uploads to the store. On iOS, send the TestFlight build for App Review in App Store Connect.

When the build is already on internal testing, the production run promotes that same build instead
(Google Play takes each build number once), so nothing is rebuilt. `SKIP_BUILD=true` reuses the last
build, for example to retry a failed upload. A production run below 100% is a staged rollout: only that
share of users (and new installs) get the new version until you raise it with `make release-rollout`.
If Play's managed publishing is on, approved changes wait until someone clicks Publish in Play Console.

One-time setup (`brew install fastlane`, then the keys below in `~/.secure_credentials`, never in the repo):

- **Google Play**: in Google Cloud, enable the Google Play Android Developer API, create a service
  account with no roles and download a JSON key for it. In Play Console, Users and permissions, invite
  the service account's email with these permissions for this app: view app information, release to testing
  tracks, manage testing tracks, release to production. Save the key as `<PLAY_KEY_FILE>`. The very first AAB of an app is uploaded by hand in Play Console; the API
  cannot see the app before that.
- **App Store Connect**: Users and Access, Integrations, App Store Connect API, Team Keys: generate a
  key with App Manager access. Save the `.p8` (it downloads only once) as `<P8_FILE>`, and its
  Key ID and the Issuer ID as `<ASC_INFO_FILE>`: `{"key_id": "...", "issuer_id": "..."}`.
- **Sentry**: save the auth token used by `sentry_dart_plugin` as
  `<SENTRY_TOKEN_FILE>`, or export `SENTRY_AUTH_TOKEN`, which wins when set.

Run `make release-check` after the setup: it reads the keys, the stores and Sentry and changes nothing.
