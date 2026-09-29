import { test } from 'node:test';
import assert from 'node:assert/strict';
import { matchReplay, POLICY, verdictOutcome } from './loop.mjs';

const fail = { kind: 'verdict', status: 'failed' };
const pass = { kind: 'verdict', status: 'passed' };

test('a low-confidence fail hands off instead of ending the run', () => {
  assert.equal(verdictOutcome(fail, { confidence: 0.3, margin: 0.05 }, POLICY), 'uncertain_fail');
});

test('a clear fail ends the run', () => {
  assert.equal(verdictOutcome(fail, { confidence: 0.9, margin: 0.8 }, POLICY), 'failed');
});

test('a fail at 0.50 with margin 0.30 is clear by the margin rule', () => {
  assert.equal(verdictOutcome(fail, { confidence: 0.5, margin: 0.3 }, POLICY), 'failed');
});

test('a pass verdict below the goal-met bar always goes to the host', () => {
  for (const confidence of [0.1, 0.5, 0.99]) assert.equal(verdictOutcome(pass, { confidence, margin: confidence }, POLICY), 'uncertain_pass');
});

const press = label => ({ kind: 'press', description: `Tap button "${label}".`, label });
const screen = (...labels) => labels.map((label, i) => ({ id: `a${i}`, ...press(label) }));

test('a path with a handoff gap replays up to the gap, then hands back to Jev', () => {
  const path = [press('Account'), { kind: 'handoff', note: 'Tap "Settings" -> changed' }, press('Language'), { kind: 'end', captures: [] }];
  const first = matchReplay(screen('Account', 'Language'), path, 0);
  assert.equal(first.match.label, 'Account');
  assert.equal(first.cursor, 1);
  // "Language" is on screen too, but re-syncing must not skip what the host did at the gap.
  const second = matchReplay(screen('Account', 'Language'), path, first.cursor);
  assert.equal(second.stop, 'handoff');
  assert.equal(second.planned.note, 'Tap "Settings" -> changed');
});

test('re-sync never crosses a gap from the step before it', () => {
  const path = [press('Intro'), { kind: 'handoff', note: null }, press('Language'), { kind: 'end' }];
  assert.equal(matchReplay(screen('Language'), path, 0).stop, 'diverged');
});

test('re-sync still skips an already-satisfied step without a gap', () => {
  const path = [press('Intro'), press('Language'), { kind: 'end' }];
  const step = matchReplay(screen('Language'), path, 0);
  assert.equal(step.skipped, 1);
  assert.equal(step.cursor, 2);
});

test('the end of the path stops the replay', () => {
  assert.equal(matchReplay(screen('Any'), [{ kind: 'end', captures: ['x'] }], 0).stop, 'end');
});
