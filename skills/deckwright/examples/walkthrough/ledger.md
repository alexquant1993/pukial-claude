# Ledger - walkthrough

- Ruling: the cover carries no page number and no copyright line, and is
  exempt in `lint.toml`'s `required` and `kickers` checks - spec section 5,
  S01 - cost if wrong: a reader of the printed deck sees "1" on a slide with
  nothing to number; fix by removing the exemption and rebuilding.

- Ruling: the aside "If asked: the HTML draft is disposable" lives in the
  notes only and `lint.toml`'s `notes_only` check enforces it - spec section
  1, last rule - cost if wrong: the audience reads on the slide what the
  presenter meant to hold back; caught by the `walkthrough lint` gate step.
