// Recorded paths: how a resumed run's recording marks the handoff.

/** Steps around a handoff: the host agent's action is not a runner step, so the gap is kept as a marker. */
export function withHandoff(original, resumed, note) {
  return [...original, { kind: 'handoff', note: note ?? null }, ...resumed];
}

/** The JSON written to paths/. `partial` flags a recording with handoff gaps; `gaps` are their step indexes. */
export function recording({ flow, platform, locale, steps, recordedAt = new Date().toISOString() }) {
  const gaps = steps.flatMap((s, i) => (s.kind === 'handoff' ? [i] : []));
  return { flow, platform, locale, recordedAt, ...(gaps.length ? { partial: true, gaps } : {}), steps };
}

/** A partial recording (one with handoff gaps) never replaces a complete one: a flaky handoff would degrade it. */
export const replaces = (existing, next) => !existing || !(next.partial && !existing.partial);
