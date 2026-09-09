# HANDOFF - <deck>: <what this session did> -> <what the next one does>

**Date:** <YYYY-MM-DD>
**Deck:** `<path to the author's current file>` (read-only; never overwritten)
**Work directory:** `<path>` - every generated file goes here and is named `stepN_*` or `vN_*`

---

## 0. How to work here

These are defaults the author can override, not law. They decide whether an
agent loading this file is useful or destructive.

- **Propose text changes in the conversation**, in a small number of
  alternatives, and let the author apply them. Act on files only when told
  to, with an explicit go.
- **Never overwrite the author's deck.** Read one path, write another. The
  author's file is usually open in PowerPoint and locked, with a `~$`
  sidecar present; write to the work directory and say so, and do not
  retry against the lock.
- **Reading order before touching anything:** this handoff, then the spec,
  then the ledger, then dump the current deck's text
  (`scripts/dump_text.py --deck DECK --out WORK/text.txt`) and diff it
  against the last known dump, then look at the current PNGs. The dump and
  diff are what discover the author's manual edits; regenerating from a
  stale assumption destroys them.
- **One question per message, in prose**, with enough context to decide
  and the reasoning behind any recommendation.
- **Replacement copy more than 35% longer than the original run text is
  shortened, not allowed to overflow**, and every shortening is reported.
- **The intake before any deck.** Run `scripts/discover.py`, then ask four
  questions, one per message: which design system (one the user points at,
  one the report found, or the default `brands/relay` - never a corporate
  `.pptx` master, which this pipeline does not adopt), whether the HTML
  draft is on (the default) or skipped with a reason, whether the deck
  carries speaker notes (`none`, the default; `pptx`, `teleprompter` or
  `both`), and what it ships as (`html`, `pptx` or `both`, the default).
  Record the answers on the spec's `Design system`, `HTML draft`, `Notes`
  and `Output` lines before starting anything; never assume them.

## 1. Where everything is

| Artifact | Path |
|---|---|
| Spec | `<path>` |
| Ledger | `<path>` |
| Author's current deck | `<path>` |
| Last text dump | `<path>` |
| Builders | `<path>` |
| Current PNGs | `<path>` |

Pipeline: `<the literal run command>`

## 2. Deck structure

<position -> printed number -> title, one line per slide, hidden slides marked; which positions are generated and which are the author's>

## 3. Decisions closed - do not relitigate

- <decision, with the ruling's date and its cost-if-wrong clause>

## 4. Changes agreed in conversation that the author said they would apply by hand

<verify each one in the current file, one by one, before building anything>

- <change>

## 5. What the next session does

1. <step>

## 6. Open flags

- <flag, and who decides it>
