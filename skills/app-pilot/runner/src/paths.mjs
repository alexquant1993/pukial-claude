// Recorded paths: where they live, what they are keyed by, and how a resumed run's recording marks the handoff.

/**
 * A flow that changes the app's language: named by `app.languageFlow` (e.g. language-{locale}) for one of
 * `app.locales`, or marked `languageFlow: true` on the flow itself.
 */
export function isLanguageFlow(map, flowId) {
  const flow = map.flows?.find(f => f.id === flowId);
  if (flow?.languageFlow !== undefined) return Boolean(flow.languageFlow);
  const pattern = map.app?.languageFlow;
  return Boolean(pattern && (map.app.locales ?? []).some(locale => pattern.replace('{locale}', locale) === flowId));
}

/**
 * The recording's file name. Paths are per language because they match controls by their visible labels ("Search"
 * vs "Buscar"); a language flow's labels depend on the language the app starts in, not the one requested.
 * Returns null when a language flow's start language is unknown: nothing is replayed or recorded then.
 */
export function pathName({ flow, platform, locale, languageFlow = false, startLocale = null }) {
  if (!languageFlow) return `${flow}-${platform}-${locale}.json`;
  return startLocale ? `${flow}-${platform}-from-${startLocale}.json` : null;
}

/** Steps around a handoff: the host agent's action is not a runner step, so the gap is kept as a marker. */
export function withHandoff(original, resumed, note) {
  return [...original, { kind: 'handoff', note: note ?? null }, ...resumed];
}

/** The JSON written to paths/. `partial` flags a recording with handoff gaps; `gaps` are their step indexes. */
export function recording({ flow, platform, locale, startLocale = null, steps, recordedAt = new Date().toISOString() }) {
  const gaps = steps.flatMap((s, i) => (s.kind === 'handoff' ? [i] : []));
  return { flow, platform, locale, ...(startLocale ? { startLocale } : {}), recordedAt, ...(gaps.length ? { partial: true, gaps } : {}), steps };
}

/** A partial recording (one with handoff gaps) never replaces a complete one: a flaky handoff would degrade it. */
export const replaces = (existing, next) => !existing || !(next.partial && !existing.partial);
