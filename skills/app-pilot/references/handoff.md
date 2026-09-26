# Handling a handoff (exit code 4)

The runner stopped on purpose and left the device session open (`app-pilot-<platform>`). It is asking
you, the reasoning agent, for one decision. Keep it to one step, then give control back.

## 1. Read the situation

```bash
jq '.handoff, .history[-3:]' <runDir>/state.json
agent-device screenshot /tmp/now.png --session app-pilot-ios      # then view it
```

- `handoff.reason`: why it stopped (table in SKILL.md).
- `handoff.topCandidates`: Jev's top options with probabilities. A near tie between two options that
  mean the same thing is a runner bug worth reporting (duplicate options); a tie between genuinely
  different options is the ambiguity you are here to resolve.
- `history`: each earlier action with its observed effect (`changed (gone: …; new: …)`).

## 2. Act once, in the same session

```bash
agent-device snapshot -i --session app-pilot-ios
agent-device press 'label="Continue with Email"' --settle --session app-pilot-ios
agent-device fill 'label="Email" editable=true' "$VALUE" --session app-pilot-ios
agent-device keyboard enter --session app-pilot-ios
```

Never type secrets literally in a command you print; read them from `~/.config/app-pilot/.env`.
Do not perform actions the flow's goal forbids.

## 3. Resume

```bash
node <runner>/src/cli.mjs run .app-pilot/app-map.yaml <flow> --platform ios --udid <udid> \
  --resume <runDir> --note 'Tap button "Continue with Email". -> screen changed'
```

The note goes into Jev's history, so describe the action and its visible effect in the same style.

## 4. Make it not happen again

If the handoff would recur on every run, fix the cause instead of repeating the manual step:

- Ambiguous goal → add a constraint to the flow's goal.
- Unlabeled icon → add a `labels` entry (key from `state.unlabeled`) and report the defect.
- Capture never recognised → reword `when` with on-screen text.
- System prompt (permissions, tracking, save password) → the runner handles these with Jev; if one
  keeps stalling, grant the permission on the device before the run (`xcrun simctl privacy`).
