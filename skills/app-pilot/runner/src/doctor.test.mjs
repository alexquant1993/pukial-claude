import { test } from 'node:test';
import assert from 'node:assert/strict';
import { staleSessions } from './doctor.mjs';

// Entries as `agent-device session list --json` prints them (data.sessions).
const sessions = [
  { name: 'requester-android', platform: 'android', device: 'emulator-5554', id: 'emulator-5554', device_id: 'emulator-5554' },
  { name: 'owner-ios1', platform: 'ios', device: 'iPhone 17 Pro', id: '59C44B1A', device_id: '59C44B1A', device_udid: '59C44B1A' },
  { name: 'someone-else', platform: 'android', device: 'Pixel 9', id: '3A1B2C', device_id: '3A1B2C' },
];

test('only sessions on the map\'s devices are reported, each with its close command', () => {
  const found = staleSessions(sessions, [{ platform: 'android', id: 'emulator-5554' }, { platform: 'ios', id: '59C44B1A' }]);
  assert.deepEqual(found, [
    { name: 'requester-android', platform: 'android', device: 'emulator-5554', deviceId: 'emulator-5554', close: 'agent-device close --session requester-android' },
    { name: 'owner-ios1', platform: 'ios', device: 'iPhone 17 Pro', deviceId: '59C44B1A', close: 'agent-device close --session owner-ios1' },
  ]);
});

test('no devices, no sessions to report', () => {
  assert.deepEqual(staleSessions(sessions, []), []);
});

test('an unusual session name is quoted in the close command', () => {
  const [s] = staleSessions([{ name: "qa run's", platform: 'ios', device_id: 'U' }], [{ id: 'U' }]);
  assert.equal(s.close, `agent-device close --session 'qa run'\\''s'`);
});
