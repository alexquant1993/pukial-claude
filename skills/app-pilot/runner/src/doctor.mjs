import { execFile } from 'node:child_process';
import { chmod, mkdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { createAgentDeviceClient } from 'agent-device';
import { TypeSafeClient } from '@typesafe-ai/sdk';
import { CONFIG_DIR } from './env.mjs';
import { ensureOcr } from './vision.mjs';

const run = promisify(execFile);
const ENV_FILE = join(CONFIG_DIR, '.env');
const IDB = join(homedir(), '.cache', 'app-pilot', 'idb-venv', 'bin', 'idb');
const AGENT_DEVICE = join(dirname(fileURLToPath(import.meta.url)), '..', 'node_modules', '.bin', 'agent-device');

const TEMPLATE = `# app-pilot secrets. Private to this machine: never commit, never paste into a chat.
# Get a key at https://typesafe.ai (or via Vercel AI Gateway).
TYPESAFE_API_KEY=

# Test accounts referenced by app maps as \${NAME}, e.g.:
# MYAPP_EMAIL=qa@example.com
# MYAPP_PASSWORD=...
`;

// Creates the private secrets file once; a key already in the environment (CI, agents) needs no file.
export async function setup() {
  await mkdir(CONFIG_DIR, { recursive: true });
  if (!existsSync(ENV_FILE)) await writeFile(ENV_FILE, TEMPLATE, { mode: 0o600 });
  await chmod(ENV_FILE, 0o600);
  const hasKey = Boolean(process.env.TYPESAFE_API_KEY) || /^TYPESAFE_API_KEY=.+$/m.test(await readFile(ENV_FILE, 'utf8'));
  return {
    envFile: ENV_FILE, hasKey,
    next: hasKey ? 'Key found. Run doctor.'
      : `Add the key to ${ENV_FILE} (user, in Claude Code: ! open -e ${ENV_FILE}), or export TYPESAFE_API_KEY in the environment.`,
  };
}

const check = (name, ok, detail, fix) => ({ name, ok, detail, ...(ok ? {} : { fix }) });

/** Verifies everything a run needs and says how to fix what is missing. Read-only, unless closeStale is set. */
export async function doctor({ map = null, closeStale = false } = {}) {
  const checks = [];

  const key = process.env.TYPESAFE_API_KEY;
  if (!key) checks.push(check('typesafe key', false, 'TYPESAFE_API_KEY not set', `Run: app-pilot setup, then add the key to ${ENV_FILE}.`));
  else {
    const started = performance.now();
    try {
      await new TypeSafeClient({ apiKey: key, timeout: 8000, retry: { maxRetries: 0 }, logLevel: 'off' }).models.list();
      checks.push(check('typesafe key', true, `valid (${Math.round(performance.now() - started)} ms round trip)`));
    } catch (error) {
      checks.push(check('typesafe key', false, `rejected or unreachable: ${String(error.message).slice(0, 80)}`, 'Check the key value and network access to api.typesafe.ai.'));
    }
  }

  try {
    const binary = await ensureOcr();
    checks.push(binary ? check('ocr helper', true, 'Apple Vision helper ready')
      : { name: 'ocr helper', ok: true, detail: 'not macOS: hidden-layer filter and OCR fallback disabled (runs still work)' });
  } catch (error) {
    checks.push(check('ocr helper', false, 'could not compile native/ocr.swift', 'Install Xcode command line tools: xcode-select --install.'));
  }

  let devices = [];
  try {
    devices = await createAgentDeviceClient({}).devices.list({});
  } catch (error) {
    checks.push(check('agent-device', false, String(error.message).slice(0, 100), 'See https://oss.callstack.com/agent-device/docs/agent-setup (Xcode for iOS, adb for Android).'));
  }
  const booted = devices.filter(d => d.booted && ['ios', 'android'].includes(d.platform) && (d.target ?? 'mobile') === 'mobile');
  // Physical phones belong to people: they are only used when named explicitly (--udid/--serial).
  const all = booted.map(d => ({ platform: d.platform, name: d.name, id: d.identifiers?.udid ?? d.identifiers?.serial ?? d.id, kind: d.kind }));
  const found = all.filter(d => ['simulator', 'emulator'].includes(d.kind));
  const physical = all.filter(d => !found.includes(d));
  checks.push(check('devices', found.length > 0,
    (found.length ? found.map(d => `${d.platform}: ${d.name} (${d.id})`).join('; ') : 'no booted simulator or emulator')
      + (physical.length ? ` · ${physical.length} physical device(s) connected, used only if named` : ''),
    'Boot one: open -a Simulator (iOS), or emulator -avd <name> (Android).'));

  if (map) {
    for (const platform of map.app.platforms ?? Object.keys(map.app.ids)) {
      const id = map.app.ids[platform];
      const device = found.find(d => d.platform === platform);
      // A platform without a booted device is skipped, not a failure: the run can cover the others.
      if (!device) { checks.push({ name: `app on ${platform}`, ok: true, warn: true, detail: `skipped: no booted ${platform} simulator/emulator (boot one to include ${platform})` }); continue; }
      const isInstalled = await installed(platform, device.id, id);
      checks.push(isInstalled
        ? check(`app on ${platform}`, true, `${id} installed on ${device.name}`)
        : check(`app on ${platform}`, false, `${id} not installed on ${device.name}`, platform === 'ios'
          ? 'Build for the simulator and install: xcrun simctl install <udid> <App.app> (Flutter: flutter build ios --simulator --debug).'
          : 'Build and install: adb install -r <app.apk> (Flutter: flutter build apk --debug).'));
      if (isInstalled) checks.push(...await speedWarnings(platform, device, id));
    }
    checks.push(await sessionCheck(found.filter(d => (map.app.platforms ?? Object.keys(map.app.ids)).includes(d.platform)), closeStale));
    const missing = [...new Set(Object.values(map.inputs ?? {}).flatMap(spec => [...String(typeof spec === 'string' ? spec : spec.value).matchAll(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g)].map(m => m[1])))]
      .filter(name => !process.env[name]);
    checks.push(check('app-map inputs', missing.length === 0,
      missing.length ? `missing: ${missing.join(', ')}` : 'all referenced variables are set',
      `Add ${missing.join(', ')} to ${ENV_FILE} (ask the user for the values; do not invent them).`));
  }

  return { ok: checks.every(c => c.ok), checks, devices: found, physicalDevices: physical };
}

/**
 * agent-device sessions holding one of these devices. A session outlives the runner or agent that opened it, and
 * the next run on that device then fails with "Device is already in use by session".
 */
export function staleSessions(sessions, devices) {
  const ids = new Set(devices.map(d => d.id));
  return sessions
    .map(s => ({ name: s.name, platform: s.platform, device: typeof s.device === 'string' ? s.device : s.device?.name, deviceId: s.device_id ?? s.id ?? s.device?.id }))
    .filter(s => ids.has(s.deviceId))
    .map(s => ({ ...s, close: `agent-device close --session ${/^[\w.-]+$/.test(s.name) ? s.name : `'${s.name.replace(/'/g, `'\\''`)}'`}` }));
}

async function sessionCheck(devices, closeStale) {
  const agentDevice = (...args) => run(AGENT_DEVICE, [...args, '--json']).then(r => JSON.parse(r.stdout));
  let stale;
  try { stale = staleSessions((await agentDevice('session', 'list')).data?.sessions ?? [], devices); }
  catch (error) { return { name: 'device sessions', ok: true, warn: true, detail: `could not list agent-device sessions: ${String(error.message).slice(0, 80)}` }; }
  if (!stale.length) return check('device sessions', true, 'no session holds the app\'s devices');
  const held = s => `"${s.name}" holds ${s.platform} ${s.device ?? s.deviceId}`;
  if (closeStale) {
    const closed = await Promise.all(stale.map(s => agentDevice('close', '--session', s.name).then(() => null, error => `${s.name}: ${String(error.message).slice(0, 60)}`)));
    const failed = closed.filter(Boolean);
    return check('device sessions', !failed.length, failed.length ? `could not close ${failed.join('; ')}` : `closed ${stale.map(s => s.name).join(', ')}`,
      `Close by hand: ${stale.map(s => s.close).join(' ; ')}`);
  }
  // A run waiting on a handoff keeps its app-pilot-<platform> session on purpose: close only what nothing will resume.
  return check('device sessions', false, stale.map(held).join('; '),
    `If no run is using or waiting on them: ${stale.map(s => s.close).join(' ; ')} (agent-device is in runner/node_modules/.bin), or rerun doctor with --close-stale.`);
}

// Things that make runs slow without breaking them: said once here instead of showing up as slow runs.
async function speedWarnings(platform, device, appId) {
  const warn = (name, detail) => ({ name, ok: true, warn: true, detail });
  const found = [];
  try {
    if (platform === 'android') {
      // A Flutter debug build carries the Dart kernel instead of compiled code (libapp.so) and runs it in a JIT.
      const apk = (await run('adb', ['-s', device.id, 'shell', 'pm', 'path', appId])).stdout.split('\n')[0].replace(/^package:/, '').trim();
      const entries = apk ? (await run('adb', ['-s', device.id, 'shell', 'unzip', '-l', apk], { maxBuffer: 32 << 20 })).stdout : '';
      if (/flutter_assets\/kernel_blob\.bin/.test(entries)) found.push(warn('build', `${appId} is a Flutter debug build: cold starts take 7-25 s and every screen is slower; a profile build explores 2-3x faster (flutter build apk --profile, then adb install -r)`));
      if (device.kind === 'emulator') {
        const mem = await run('adb', ['-s', device.id, 'shell', 'cat', '/proc/meminfo']).then(r => Number(r.stdout.match(/MemTotal:\s+(\d+)/)?.[1] ?? 0) / 1024 ** 2);
        if (mem && mem < 3.5) found.push(warn('emulator memory', `${device.name} has ${mem.toFixed(1)} GB RAM: captures come back incomplete and apps restart under load; give the AVD 4+ GB (hw.ramSize in its config.ini)`));
      }
    } else {
      // iOS simulators only run Flutter debug builds, so there is nothing to suggest about the build there.
      if (device.kind === 'simulator' && !existsSync(IDB)) found.push(warn('idb', `optional speed-up missing: taps go through XCTest (~0.5 s each) instead of idb (a few ms). Install: brew install facebook/fb/idb-companion (needs brew trust --formula facebook/fb/idb-companion) and python3 -m venv ~/.cache/app-pilot/idb-venv && ~/.cache/app-pilot/idb-venv/bin/pip install fb-idb`));
    }
  } catch { /* warnings are best effort */ }
  return found;
}

// Booted simulators and emulators straight from simctl and adb, for picking run targets: agent-device's full listing
// (which doctor shows, physical devices included) takes about 1.5 s.
export async function bootedDevices() {
  const ios = run('xcrun', ['simctl', 'list', 'devices', 'booted', '-j']).then(({ stdout }) => Object.values(JSON.parse(stdout).devices).flat()
    .filter(d => d.state === 'Booted' && /iPhone|iPad/.test(d.deviceTypeIdentifier ?? d.name)).map(d => ({ platform: 'ios', id: d.udid, name: d.name, kind: 'simulator' }))).catch(() => []);
  const android = run('adb', ['devices']).then(({ stdout }) => stdout.split('\n').map(l => l.trim().split(/\s+/))
    .filter(([id, state]) => /^emulator-\d+$/.test(id ?? '') && state === 'device').map(([id]) => ({ platform: 'android', id, name: id, kind: 'emulator' }))).catch(() => []);
  return (await Promise.all([ios, android])).flat();
}

export async function installed(platform, deviceId, appId) {
  try {
    if (platform === 'ios') { await run('xcrun', ['simctl', 'get_app_container', deviceId, appId]); return true; }
    const { stdout } = await run('adb', ['-s', deviceId, 'shell', 'pm', 'list', 'packages', appId]);
    return stdout.split('\n').some(line => line.trim() === `package:${appId}`);
  } catch { return false; }
}
