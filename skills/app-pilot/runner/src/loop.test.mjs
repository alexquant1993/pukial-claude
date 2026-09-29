import { test } from 'node:test';
import assert from 'node:assert/strict';
import { POLICY, verdictOutcome } from './loop.mjs';

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
