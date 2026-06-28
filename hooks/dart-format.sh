#!/bin/bash
# PostToolUse hook: auto-fix and format .dart files after Edit/Write.
# Mirrors on-save behavior (dart fix + dart format). Uses FVM-pinned SDK.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Skip if no file path or not a .dart file.
[[ -z "$FILE_PATH" ]] && exit 0
[[ ! "$FILE_PATH" =~ \.dart$ ]] && exit 0

# Skip generated files — they should not be modified.
[[ "$FILE_PATH" =~ \.g\.dart$ ]] && exit 0
[[ "$FILE_PATH" =~ \.freezed\.dart$ ]] && exit 0

fvm dart fix --apply "$FILE_PATH" 2>/dev/null || true
fvm dart format "$FILE_PATH" 2>/dev/null || true

exit 0
