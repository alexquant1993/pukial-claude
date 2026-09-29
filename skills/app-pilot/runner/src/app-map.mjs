import { readFileSync } from 'node:fs';
import { parse } from 'yaml';
import { interpolate } from './env.mjs';
import { isLanguageFlow } from './paths.mjs';

export function loadAppMap(path) {
  const map = parse(readFileSync(path, 'utf8'));
  if (!map?.app?.ids || !Array.isArray(map.flows)) throw new Error(`${path} needs app.ids and flows.`);
  return map;
}

export function resolveFlow(map, flowId, platform) {
  const flow = map.flows.find(f => f.id === flowId);
  if (!flow) throw new Error(`Unknown flow "${flowId}". Known: ${map.flows.map(f => f.id).join(', ')}.`);
  const app = map.app.ids[platform];
  if (!app) throw new Error(`app.ids.${platform} is not set.`);
  const inputs = {};
  for (const name of flow.inputs ?? []) {
    const spec = map.inputs?.[name];
    if (!spec) throw new Error(`Flow "${flowId}" uses undefined input "${name}".`);
    const def = typeof spec === 'string' ? { value: spec } : spec;
    inputs[name] = { value: interpolate(String(def.value)), secret: Boolean(def.secret), hint: def.hint };
  }
  const capture = (flow.capture ?? []).map(c => ({ id: c.id, when: c.when, threshold: c.threshold ?? 0.85 }));
  return { id: flow.id, app, goal: flow.goal, inputs, capture, maxSteps: flow.maxSteps, scope: flow.scope, labels: map.labels ?? {}, allow: flow.allow ?? [],
    languageFlow: isLanguageFlow(map, flow.id), locales: map.app.locales ?? [] };
}
