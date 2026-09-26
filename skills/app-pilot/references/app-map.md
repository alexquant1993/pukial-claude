# Writing `.app-pilot/app-map.yaml`

Jev is text-only and reads instructions literally. It sees the accessibility tree as text, never pixels.
Every rule below comes from a run that failed without it.

## Schema

```yaml
app:
  name: Swapshop # the examples below are for an imaginary second-hand marketplace app
  ids: { ios: com.example.swapshop, android: com.example.swapshop } # bundle id / package per platform
  locales: [es, en]
  platforms: [ios, android]
  languageFlow: language-{locale} # optional: apps with an in-app language setting (see Languages)

inputs: # values typed into fields; ${VAR} reads ~/.config/app-pilot/.env
  email: { value: "${APP_EMAIL}", hint: account email }
  password: { value: "${APP_PASSWORD}", secret: true, hint: account password }
  query: { value: lamp, hint: search text }

labels: # optional: names for unlabeled icons, keyed "<context>|<position>"
  "Vintage desk lamp|top-right": Favourite

flows:
  - id: search-item
    goal: >-
      Starting from the home feed, open the Search tab, type "lamp" into the search field and
      submit the search, then open the first item in the results. Finish when that item's detail
      page is showing. Do not contact the owner, do not favourite, do not request the item.
    inputs: [query] # only these inputs are offered as things to type
    capture:
      - id: search-results
        when: a list or grid of item results for the search "lamp".
      - id: item-detail
        when: a single item's detail page, showing the item title, the owner's name and a Request this Item button.
        threshold: 0.85 # default
    maxSteps: 15
    scope: null # optional agent-device snapshot scope for very crowded screens
```

## Authoring rules

1. **Describe captures with text that is on the screen.** "with its photo" scored 0.59 because a photo
   has no text; "showing the item title, the owner's name and a Request this Item button" scored 0.96.
   Name labels, buttons and headings; never colours, images or layout.
2. **Describe the real state, including empty ones.** "the Inbox listing conversations" failed on an
   empty inbox (0.59); "with its Received, Sent and Messages tabs (the list may be empty)" passed (0.93).
   Look at the screen before you write the criterion.
3. **Say what not to do.** Onboarding offered "Skip" (guest mode) next to "Continue with Email" and Jev
   split 51/49 until the goal said "do not tap Skip (that browses as a guest)". List destructive or
   outward actions the flow must avoid (post, send, pay, delete, request, favourite).
4. **Say how to answer system prompts.** Tracking, notifications, save-password and permission sheets
   appear mid-flow. Without instructions Jev split 49/33 between "Ask App Not to Track" and "Allow";
   write e.g. "If the system asks about tracking, notifications or saving the password, decline".
5. **One journey per flow, with an explicit finish line.** "Finish when X is showing" gives the goal-met
   check something concrete.
6. **Captures are ordered by the journey.** A capture can only be taken on its screen; the runner looks
   again before leaving a screen that is probably a pending capture, but it cannot go back.
7. **Inputs are literal.** The model never writes text; it only picks which declared value goes into
   which field. Put every value a flow must type in `inputs` and list it in the flow.
8. **Secrets are `secret: true`.** They are typed but never shown to the model or written to paths.
9. **Unlabeled icons.** When a handoff shows `unlabeled button at the top-right of "…"`, look at the
   screenshot, then add a `labels` entry with the exact key from `state.unlabeled`. Report the icon as an
   accessibility defect too; a `Semantics`/`contentDescription`/`accessibilityLabel` fix in the app is
   the real cure.

## Languages

`app.locales` lists the languages to capture. Goals and criteria can stay in one language: Jev
matched an English goal to a Spanish UI ("Search" → "Buscar", "You" → "Cuenta") at 0.8–1.0. If the
app stores its own language (many do, e.g. in shared preferences), the device language is ignored after
the first launch; add `language-<tag>` flows that switch it in the app's settings, with a finish line
naming text of the target language ("the language screen is titled Idioma"), and set
`app.languageFlow: language-{locale}` so `run-all` switches the language before each language batch.

## Production data

If flows run against production accounts, list every item they create and delete it afterwards.
Prefer read-only flows for screenshots; seed realistic content in a test account when possible.
