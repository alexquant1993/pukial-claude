# One-time console setup

The user does all of this in their own browser and moves the files themselves. Walk them through it
step by step, one platform at a time, and wait for "done" before the next. Do not read, print or copy
the credential files; `make release-check` is how you learn whether they work.

Credentials live in `~/.secure_credentials/` (create it with `mkdir -p` and `chmod 700`), one file per
secret, `chmod 600` each, never inside the repo. Use the file names from `release.yml` (`credentials`).
Tell the user to move the downloads there with `mv` and then `chmod 600`.

## Prerequisites per store

- **Google Play**: the app exists in Play Console and its **very first AAB was uploaded by hand** in the
  console (Testing, Internal testing, Create new release). Until then the API answers "Package not found",
  and an app that is still a draft only accepts draft releases, so the lanes cannot publish to it. After
  that first upload, fastlane takes over. Play App Signing is on, and the AAB is signed with an upload key
  (`android/key.properties` + keystore).
- **App Store Connect**: the app record exists with the same bundle id, and the Xcode project signs
  automatically with the team (a Release `flutter build ipa` works by hand once).

## Google Play (service account)

1. Google Cloud console: pick or create a project (any project, it only owns the service account).
2. APIs and services, Library: enable **Google Play Android Developer API**.
3. IAM and admin, Service accounts: create a service account. Give it **no roles** (access comes from
   Play Console, not from Google Cloud).
4. Open it, Keys, Add key, Create new key, **JSON**. The file downloads once. Save it as the `play_key`
   path from `release.yml`.
5. Play Console, **Users and permissions**, Invite new users: use the service account's email
   (`...@...iam.gserviceaccount.com`). Under App permissions add this app (and a second flavor's app, if the repo releases two) and tick exactly:
   - View app information (read-only)
   - Release apps to testing tracks
   - Manage testing tracks and edit tester lists
   - Release to production, exclude devices, and use Play App Signing
   The console words these slightly differently over time; match by meaning.
   Leave everything else off: no finance, no user management, no store listing.
6. The invite can take up to a few hours to reach the API. `make release-check` reads the track
   version codes, so it is the proof.

## App Store Connect (API key)

1. App Store Connect, **Users and Access**, Integrations, **App Store Connect API**, **Team Keys**.
   Only the Account Holder or an Admin can see it; the first time, request access.
2. Generate a key with **App Manager** access. Note the **Issuer ID** (top of the page) and the
   **Key ID**.
3. Download the `.p8`: Apple lets you do it **once**. Save it as the `asc_key_p8` path.
4. Create the `asc_key_info` file with exactly this content (the user types it, you do not need to see
   the values): `{"key_id": "XXXXXXXXXX", "issuer_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"}`.

## Sentry (auth token)

1. Create a **personal token** (User settings, Auth tokens) or an **internal integration** token (Settings,
   Developer settings, Custom integrations) with explicit scopes: `org:read`, `project:read`,
   `project:releases`, `project:write`. Organization auth tokens have fixed scopes chosen by Sentry, so
   you cannot tune them to the upload; prefer one of the other two.
2. Save it as the `sentry_token` path (the file holds only the token). Exporting `SENTRY_AUTH_TOKEN`
   also works and wins when set.
3. The org and project slugs are in the Sentry URL; the host (`sentry.io`, `de.sentry.io`) goes in
   `sentry.url` when it is not plain sentry.io.

## Afterwards

Run `make release-check`. A red line names the file or permission that is missing. Typical causes:
the Play invite has not propagated yet; the first AAB was never uploaded by hand (the API says "Package
not found"); `android.application_id` has a typo; the service account lacks one of the permissions above; the
Play API was not enabled in the same Google Cloud project that owns the service account; the ASC key
was created with a role below App Manager; the Sentry token lacks `project:read`.
