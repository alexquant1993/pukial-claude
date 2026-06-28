#!/usr/bin/env bash
# rename.sh — Rename flutter-pukial-starter into a new app.
#
# Usage:
#   bash rename.sh <new_snake_package> "<New Display Name>" <org.prefix> [dest_dir]
#
# Arguments:
#   new_snake_package  — snake_case package name, e.g. my_expense_app
#   New Display Name   — quoted human-readable name, e.g. "My Expense App"
#   org.prefix         — reverse-domain org, e.g. com.pukial or com.acme
#   dest_dir           — (optional) directory to operate on; defaults to $PWD
#
# What it changes:
#   pubspec.yaml              name field
#   lib/ + test/              package:flutter_pukial_starter/ → package:<new_pkg>/
#   android/app/build.gradle.kts   namespace + applicationId
#   android/.../AndroidManifest.xml  android:label
#   android/.../MainActivity.kt      package decl + on-disk kotlin/ dir path
#   ios/Runner/Info.plist            CFBundleDisplayName + CFBundleName
#   ios/Runner.xcodeproj/project.pbxproj  PRODUCT_BUNDLE_IDENTIFIER (Runner + RunnerTests)
#   web/manifest.json                name + short_name
#   web/index.html                   <title> + apple-mobile-web-app-title
#   lib/src/localization/*.arb       appTitle
#
# Exits non-zero on any failed or zero-match substitution so failures are loud.

set -euo pipefail

# ── arguments ───────────────────────────────────────────────────────────────
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <new_snake_package> \"<New Display Name>\" <org.prefix> [dest_dir]" >&2
  exit 1
fi

NEW_PKG="$1"           # e.g. my_expense_app
NEW_DISPLAY="$2"       # e.g. "My Expense App"
ORG="$3"               # e.g. com.pukial
DEST="${4:-$PWD}"

# Guard: the display name flows into sed replacements (Info.plist, web/, .arb).
# '|' is the sed delimiter; '&' expands to the matched text; '\' escapes — any
# of the three would corrupt the substitution, so reject them loudly up front.
if [[ "$NEW_DISPLAY" == *'|'* || "$NEW_DISPLAY" == *'&'* || "$NEW_DISPLAY" == *'\'* ]]; then
  echo "ERROR: display name must not contain '|', '&', or '\\' (they break sed substitution). Please choose a name without those characters." >&2
  exit 1
fi

# ── constants (what we're replacing) ────────────────────────────────────────
OLD_PKG="flutter_pukial_starter"
OLD_DISPLAY="Flutter Pukial Starter"
OLD_BUNDLE_NAME="flutter_pukial_starter"
OLD_ORG="com.pukial"
OLD_ARB_TITLE="Pukial Starter"   # appTitle value in the .arb files
OLD_ANDROID_ID="com.pukial.flutter_pukial_starter"
OLD_IOS_ID="com.pukial.flutterPukialStarter"
OLD_IOS_TESTS_ID="com.pukial.flutterPukialStarter.RunnerTests"

# Derive camelCase from snake_case for iOS bundle ID:
#   my_expense_app → myExpenseApp
to_camel_case() {
  local s="$1"
  # lower-case the whole thing, then capitalise each segment after _
  echo "$s" | awk -F_ '{
    printf $1;
    for (i=2; i<=NF; i++) {
      printf toupper(substr($i,1,1)) substr($i,2);
    }
    print ""
  }'
}

NEW_PKG_CAMEL=$(to_camel_case "$NEW_PKG")
NEW_ANDROID_ID="${ORG}.${NEW_PKG}"
NEW_IOS_ID="${ORG}.${NEW_PKG_CAMEL}"
NEW_IOS_TESTS_ID="${ORG}.${NEW_PKG_CAMEL}.RunnerTests"

echo "━━━ rename.sh ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Working dir:    $DEST"
echo "  Package:        $OLD_PKG  →  $NEW_PKG"
echo "  Display name:   $OLD_DISPLAY  →  $NEW_DISPLAY"
echo "  Org:            $OLD_ORG  →  $ORG"
echo "  Android ID:     $OLD_ANDROID_ID  →  $NEW_ANDROID_ID"
echo "  iOS bundle:     $OLD_IOS_ID  →  $NEW_IOS_ID"
echo "  iOS tests:      $OLD_IOS_TESTS_ID  →  $NEW_IOS_TESTS_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── helper: sed in-place, portably (macOS BSD sed / GNU sed) ─────────────────
# Usage: sed_inplace <file> <old_pattern> <new_value>
sed_inplace() {
  local file="$1" pattern="$2" replacement="$3"
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|${pattern}|${replacement}|g" "$file"
  else
    sed -i "s|${pattern}|${replacement}|g" "$file"
  fi
}

# ── helper: verify at least one match was made ───────────────────────────────
assert_changed() {
  local file="$1" pattern="$2"
  if ! grep -q "$pattern" "$file"; then
    echo "ERROR: expected to find '$pattern' in $file after substitution — check the file." >&2
    exit 1
  fi
}

# ── helper: verify a pattern is NOT present (was successfully removed) ───────
assert_absent() {
  local file="$1" pattern="$2"
  if grep -q "$pattern" "$file"; then
    echo "ERROR: '$pattern' still present in $file after substitution." >&2
    exit 1
  fi
}

# ════════════════════════════════════════════════════════════════════════════
# 1. pubspec.yaml — name field
# ════════════════════════════════════════════════════════════════════════════
PUBSPEC="$DEST/pubspec.yaml"
echo "[1/10] pubspec.yaml — name: $OLD_PKG  →  $NEW_PKG"
sed_inplace "$PUBSPEC" "^name: ${OLD_PKG}$" "name: ${NEW_PKG}"
assert_changed "$PUBSPEC" "^name: ${NEW_PKG}"
assert_absent  "$PUBSPEC" "^name: ${OLD_PKG}"

# ════════════════════════════════════════════════════════════════════════════
# 2. Dart imports — package:flutter_pukial_starter/ → package:<new>/
# ════════════════════════════════════════════════════════════════════════════
echo "[2/10] Dart imports in lib/ + test/"
IMPORT_OLD="package:${OLD_PKG}/"
IMPORT_NEW="package:${NEW_PKG}/"

# Count occurrences before.
# NOTE: `|| true` is required — under `set -o pipefail`, grep exits 1 when it
# finds no matches, which would otherwise kill the script (zero matches is a
# valid state we want to handle ourselves below, not crash on).
BEFORE=$({ grep -r --include="*.dart" -l "$IMPORT_OLD" "$DEST/lib" "$DEST/test" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$BEFORE" -eq 0 ]]; then
  echo "ERROR: no Dart files contain '$IMPORT_OLD' — was the package already renamed?" >&2
  exit 1
fi
echo "  Found $BEFORE file(s) with old import prefix."

# Replace across lib/ and test/
while IFS= read -r f; do
  sed_inplace "$f" "$IMPORT_OLD" "$IMPORT_NEW"
done < <(grep -r --include="*.dart" -l "$IMPORT_OLD" "$DEST/lib" "$DEST/test" 2>/dev/null)

# Verify none remain (grep finds nothing on success → `|| true` avoids pipefail death).
AFTER=$({ grep -r --include="*.dart" -l "$IMPORT_OLD" "$DEST/lib" "$DEST/test" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$AFTER" -gt 0 ]]; then
  echo "ERROR: $AFTER file(s) still contain '$IMPORT_OLD' after substitution." >&2
  exit 1
fi
echo "  Import prefix updated in $BEFORE file(s)."

# ════════════════════════════════════════════════════════════════════════════
# 3. Android: namespace + applicationId in build.gradle.kts
# ════════════════════════════════════════════════════════════════════════════
GRADLE="$DEST/android/app/build.gradle.kts"
echo "[3/10] Android build.gradle.kts — namespace + applicationId"
sed_inplace "$GRADLE" "namespace = \"${OLD_ANDROID_ID}\"" "namespace = \"${NEW_ANDROID_ID}\""
assert_changed "$GRADLE" "namespace = \"${NEW_ANDROID_ID}\""
sed_inplace "$GRADLE" "applicationId = \"${OLD_ANDROID_ID}\"" "applicationId = \"${NEW_ANDROID_ID}\""
assert_changed "$GRADLE" "applicationId = \"${NEW_ANDROID_ID}\""
assert_absent  "$GRADLE" "${OLD_ANDROID_ID}"

# ════════════════════════════════════════════════════════════════════════════
# 4. Android: app label in AndroidManifest.xml
# ════════════════════════════════════════════════════════════════════════════
MANIFEST="$DEST/android/app/src/main/AndroidManifest.xml"
echo "[4/10] AndroidManifest.xml — android:label"
sed_inplace "$MANIFEST" "android:label=\"${OLD_PKG}\"" "android:label=\"${NEW_PKG}\""
assert_changed "$MANIFEST" "android:label=\"${NEW_PKG}\""
assert_absent  "$MANIFEST" "android:label=\"${OLD_PKG}\""

# ════════════════════════════════════════════════════════════════════════════
# 5. iOS: CFBundleDisplayName + CFBundleName in Info.plist
# ════════════════════════════════════════════════════════════════════════════
INFOPLIST="$DEST/ios/Runner/Info.plist"
echo "[5/10] ios/Runner/Info.plist — CFBundleDisplayName + CFBundleName"
sed_inplace "$INFOPLIST" "<string>${OLD_DISPLAY}</string>" "<string>${NEW_DISPLAY}</string>"
assert_changed "$INFOPLIST" "<string>${NEW_DISPLAY}</string>"
assert_absent  "$INFOPLIST" "<string>${OLD_DISPLAY}</string>"
# CFBundleName: shown in iOS share sheet / Siri (was not updated before)
sed_inplace "$INFOPLIST" "<string>${OLD_BUNDLE_NAME}</string>" "<string>${NEW_PKG}</string>"
assert_changed "$INFOPLIST" "<string>${NEW_PKG}</string>"
assert_absent  "$INFOPLIST" "<string>${OLD_BUNDLE_NAME}</string>"

# ════════════════════════════════════════════════════════════════════════════
# 6. iOS: PRODUCT_BUNDLE_IDENTIFIER in project.pbxproj (Runner target)
# ════════════════════════════════════════════════════════════════════════════
PBXPROJ="$DEST/ios/Runner.xcodeproj/project.pbxproj"
echo "[6/10] project.pbxproj — PRODUCT_BUNDLE_IDENTIFIER (Runner)"
# Replace Runner tests ID first (it's the longer string — avoids partial match)
sed_inplace "$PBXPROJ" "PRODUCT_BUNDLE_IDENTIFIER = ${OLD_IOS_TESTS_ID};" \
                        "PRODUCT_BUNDLE_IDENTIFIER = ${NEW_IOS_TESTS_ID};"
assert_changed "$PBXPROJ" "PRODUCT_BUNDLE_IDENTIFIER = ${NEW_IOS_TESTS_ID};"
# Then replace the main Runner ID
sed_inplace "$PBXPROJ" "PRODUCT_BUNDLE_IDENTIFIER = ${OLD_IOS_ID};" \
                        "PRODUCT_BUNDLE_IDENTIFIER = ${NEW_IOS_ID};"
assert_changed "$PBXPROJ" "PRODUCT_BUNDLE_IDENTIFIER = ${NEW_IOS_ID};"
assert_absent  "$PBXPROJ" "PRODUCT_BUNDLE_IDENTIFIER = ${OLD_IOS_ID};"

# ════════════════════════════════════════════════════════════════════════════
# 7. pubspec.yaml — description (best-effort: update if it still says "Pukial")
# ════════════════════════════════════════════════════════════════════════════
echo "[7/10] pubspec.yaml — description (best-effort)"
# Replace the starter description with a placeholder the dev should fill in
NEW_DESC="${NEW_DISPLAY} — Flutter app."
if grep -q "^description:" "$PUBSPEC"; then
  sed_inplace "$PUBSPEC" "^description:.*" "description: \"${NEW_DESC}\""
  echo "  description → \"${NEW_DESC}\" (update as needed)"
else
  echo "  WARNING: no 'description:' line found in pubspec.yaml — skipping."
fi

# ════════════════════════════════════════════════════════════════════════════
# 8. Web: title in manifest.json + index.html (PWA / browser tab name)
# ════════════════════════════════════════════════════════════════════════════
MANIFEST_JSON="$DEST/web/manifest.json"
INDEX_HTML="$DEST/web/index.html"
echo "[8/10] web/ — manifest.json name/short_name + index.html title"
# manifest.json: "name" and "short_name" both hold the old package string.
sed_inplace "$MANIFEST_JSON" "\"${OLD_PKG}\"" "\"${NEW_DISPLAY}\""
assert_changed "$MANIFEST_JSON" "\"${NEW_DISPLAY}\""
assert_absent  "$MANIFEST_JSON" "\"${OLD_PKG}\""
# index.html: <title> + apple-mobile-web-app-title both hold the bare old package
# string (the only occurrences; flutter_bootstrap.js etc. are untouched).
sed_inplace "$INDEX_HTML" "${OLD_PKG}" "${NEW_DISPLAY}"
assert_changed "$INDEX_HTML" "${NEW_DISPLAY}"
assert_absent  "$INDEX_HTML" "${OLD_PKG}"

# ════════════════════════════════════════════════════════════════════════════
# 9. Localization: appTitle in the .arb files (shown in-app)
# ════════════════════════════════════════════════════════════════════════════
echo "[9/10] lib/src/localization/*.arb — appTitle"
ARB_OLD=$({ grep -rl "\"appTitle\": \"${OLD_ARB_TITLE}\"" "$DEST/lib/src/localization" 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$ARB_OLD" -eq 0 ]]; then
  echo "ERROR: no .arb file contains appTitle \"${OLD_ARB_TITLE}\" — already renamed?" >&2
  exit 1
fi
while IFS= read -r f; do
  sed_inplace "$f" "\"appTitle\": \"${OLD_ARB_TITLE}\"" "\"appTitle\": \"${NEW_DISPLAY}\""
done < <(grep -rl "\"appTitle\": \"${OLD_ARB_TITLE}\"" "$DEST/lib/src/localization" 2>/dev/null)
echo "  appTitle → \"${NEW_DISPLAY}\" in $ARB_OLD file(s)."

# ════════════════════════════════════════════════════════════════════════════
# 10. Android: Kotlin package declaration + on-disk directory path
# ════════════════════════════════════════════════════════════════════════════
echo "[10/10] android MainActivity.kt — package decl + kotlin/ dir path"
KOTLIN_ROOT="$DEST/android/app/src/main/kotlin"
OLD_KOTLIN_DIR="$KOTLIN_ROOT/$(echo "$OLD_ANDROID_ID" | tr '.' '/')"
NEW_KOTLIN_DIR="$KOTLIN_ROOT/$(echo "$NEW_ANDROID_ID" | tr '.' '/')"
OLD_MAIN_ACTIVITY="$OLD_KOTLIN_DIR/MainActivity.kt"
if [[ ! -f "$OLD_MAIN_ACTIVITY" ]]; then
  echo "ERROR: expected $OLD_MAIN_ACTIVITY — kotlin layout changed?" >&2
  exit 1
fi
# Rewrite the package declaration first (file still at its old path).
sed_inplace "$OLD_MAIN_ACTIVITY" "package ${OLD_ANDROID_ID}" "package ${NEW_ANDROID_ID}"
assert_changed "$OLD_MAIN_ACTIVITY" "package ${NEW_ANDROID_ID}"
# Move the directory to match the new package, then prune empty old ancestors.
if [[ "$OLD_KOTLIN_DIR" != "$NEW_KOTLIN_DIR" ]]; then
  mkdir -p "$(dirname "$NEW_KOTLIN_DIR")"
  mv "$OLD_KOTLIN_DIR" "$NEW_KOTLIN_DIR"
  find "$KOTLIN_ROOT" -type d -empty -delete
  echo "  moved kotlin/ → ${NEW_KOTLIN_DIR#$DEST/}"
else
  echo "  package path unchanged — dir move skipped."
fi
assert_changed "$NEW_KOTLIN_DIR/MainActivity.kt" "package ${NEW_ANDROID_ID}"

echo ""
echo "✓ rename.sh complete — all targets updated."
echo ""
echo "Next steps:"
echo "  1. cd $DEST"
echo "  2. fvm flutter pub get"
echo "  3. fvm flutter gen-l10n   # regenerates app_localizations_*.dart with the new appTitle"
echo "  4. fvm dart run build_runner build --delete-conflicting-outputs"
echo "  5. fvm flutter analyze   # should be zero issues"
