import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isLanguageFlow, pathName, recording, replaces, withHandoff } from './paths.mjs';

const map = {
  app: { ids: { ios: 'x' }, locales: ['es', 'en'], languageFlow: 'language-{locale}' },
  flows: [{ id: 'language-es' }, { id: 'language-en' }, { id: 'search' }, { id: 'set-language', languageFlow: true }, { id: 'language-fr' }],
};

test('language flows come from app.languageFlow or a flow flag', () => {
  assert.equal(isLanguageFlow(map, 'language-es'), true);
  assert.equal(isLanguageFlow(map, 'set-language'), true);
  assert.equal(isLanguageFlow(map, 'search'), false);
  assert.equal(isLanguageFlow(map, 'language-fr'), false); // not one of app.locales
});

test('a language flow is keyed by its start language; other flows keep their key', () => {
  assert.equal(pathName({ flow: 'language-es', platform: 'android', locale: 'es', languageFlow: true, startLocale: 'en' }), 'language-es-android-from-en.json');
  assert.equal(pathName({ flow: 'language-es', platform: 'android', locale: 'es', languageFlow: true, startLocale: null }), null);
  assert.equal(pathName({ flow: 'search', platform: 'ios', locale: 'es' }), 'search-ios-es.json');
  assert.equal(pathName({ flow: 'search', platform: 'ios', locale: 'es', startLocale: 'en' }), 'search-ios-es.json');
});

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

test('a recording without a handoff is not partial and says its start language when it has one', () => {
  const json = recording({ flow: 'language-es', platform: 'android', locale: 'es', startLocale: 'en', steps: [{ kind: 'end' }], recordedAt: 'T' });
  assert.deepEqual(json, { flow: 'language-es', platform: 'android', locale: 'es', startLocale: 'en', recordedAt: 'T', steps: [{ kind: 'end' }] });
});

test('a partial recording never replaces a complete one; everything else does', () => {
  const complete = { steps: [] }, partial = { partial: true, steps: [] };
  assert.equal(replaces(complete, partial), false);
  assert.equal(replaces(null, partial), true);
  assert.equal(replaces(partial, partial), true);
  assert.equal(replaces(partial, complete), true);
  assert.equal(replaces(complete, complete), true);
});
