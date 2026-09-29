import { test } from 'node:test';
import assert from 'node:assert/strict';
import { recording, replaces, withHandoff } from './paths.mjs';

test('a resumed run records the original steps, the handoff gap and the steps after it', () => {
  const original = [{ kind: 'press', description: 'Tap tab "You".', label: 'You', captures: [] }];
  const resumed = [{ kind: 'press', description: 'Tap button "Save".', label: 'Save', captures: [] }, { kind: 'end', captures: ['saved'] }];
  const steps = withHandoff(original, resumed, 'Tap photo cell -> picker closed');
  const json = recording({ flow: 'create-post', platform: 'ios', locale: 'es', steps, recordedAt: 'T' });
  assert.deepEqual(json, {
    flow: 'create-post', platform: 'ios', locale: 'es', recordedAt: 'T', partial: true, gaps: [1],
    steps: [original[0], { kind: 'handoff', note: 'Tap photo cell -> picker closed' }, ...resumed],
  });
});

test('a recording without a handoff is not partial', () => {
  const json = recording({ flow: 'search', platform: 'android', locale: 'es', steps: [{ kind: 'end' }], recordedAt: 'T' });
  assert.deepEqual(json, { flow: 'search', platform: 'android', locale: 'es', recordedAt: 'T', steps: [{ kind: 'end' }] });
});

test('a partial recording never replaces a complete one; everything else does', () => {
  const complete = { steps: [] }, partial = { partial: true, steps: [] };
  assert.equal(replaces(complete, partial), false);
  assert.equal(replaces(null, partial), true);
  assert.equal(replaces(partial, partial), true);
  assert.equal(replaces(partial, complete), true);
  assert.equal(replaces(complete, complete), true);
});
