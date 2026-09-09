# Phase 1 — App Discovery

**Goal:** Build a mental model of the app so headlines, pairings, and visuals are rooted in real product context.

**Inputs:** The user's project directory (assumed to be the current working directory).

## Procedure

1. **Detect platform(s).** Check for:
   - iOS: `.xcodeproj`, `.xcworkspace`, `Package.swift`, `ios/Runner.xcworkspace` (Flutter)
   - Android: `build.gradle`, `AndroidManifest.xml`, `android/app/build.gradle` (Flutter)
   - Both → cross-platform (Flutter, React Native, KMP)

2. **Explore the codebase.** Read:
   - UI files / view controllers / screens
   - Models and data structures (the domain)
   - Onboarding flow (what the app emphasizes first)
   - In-app purchase / subscription config (the premium offering)
   - `pubspec.yaml`, `Info.plist`, `AndroidManifest.xml`, `package.json` (app name, bundle ID)
   - README, marketing copy in code, `fastlane/metadata/` if present

3. **Ask the user clarifying questions** ONLY for what the code can't answer:
   - Target audience (age, interests, skill level)
   - Niche
   - #1 reason someone downloads
   - Main competitors and what users wish those apps did better
   - What best reviews say

   Do NOT ask questions the code already answers.

## Output

Write `aso_app_context.md` per the format in `memory-schema.md`. Add a one-line entry to `MEMORY.md`.

## AskUserQuestion gate

Once the app summary is drafted, present it to the user and lock with:

```python
AskUserQuestion(questions=[{
    "question": "Lock this app context summary, revise, or restart Phase 1?",
    "header": "App context",
    "multiSelect": False,
    "options": [
        {"label": "Lock", "description": "Write aso_app_context.md and proceed to Phase 2."},
        {"label": "Revise", "description": "Adjust specific lines without restarting."},
        {"label": "Restart Phase 1", "description": "The summary missed important context; gather more before drafting again."}
    ]
}])
```
