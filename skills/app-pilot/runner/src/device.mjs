import { createAgentDeviceClient } from 'agent-device';
import { setTimeout as delay } from 'node:timers/promises';
import { execFile, spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { fingerprint } from './actions.mjs';

const run = promisify(execFile);
const IDB = join(homedir(), '.cache', 'app-pilot', 'idb-venv', 'bin', 'idb');

// One long-lived `idb shell` per simulator: each command answers with a SUCCESS or error line, so commands are sent
// one at a time and each waits for its own answer.
async function openIdbShell(udid) {
  await run(IDB, ['connect', udid], { timeout: 20_000 });
  const child = spawn(IDB, ['shell', '--no-prompt', '--udid', udid], { stdio: ['pipe', 'pipe', 'ignore'] });
  let carry = '', waiting = null, queue = Promise.resolve();
  child.stdout.on('data', data => {
    carry += data;
    for (let i; (i = carry.indexOf('\n')) >= 0;) {
      const line = carry.slice(0, i); carry = carry.slice(i + 1);
      if (waiting && /SUCCESS|error/i.test(line)) { const done = waiting; waiting = null; done(line); }
    }
  });
  const send = command => (queue = queue.then(() => new Promise((resolve, reject) => {
    const timer = setTimeout(() => { waiting = null; reject(new Error(`idb: no answer to "${command}"`)); }, 5_000);
    waiting = line => { clearTimeout(timer); /SUCCESS/.test(line) ? resolve() : reject(new Error(`idb: ${line}`)); };
    child.stdin.write(command + '\n');
  })));
  return { send, close: () => child.stdin.end() };
}

const TRANSITION_MS = 600;
const ANIMATION_SETTINGS = ['window_animation_scale', 'transition_animation_scale', 'animator_duration_scale'];
// Captures taken mid-transition or under load can fail once and succeed on the next try; a stalled one times out.
const TRANSIENT_CAPTURE = /IncompleteCapture|insufficient foreground app content|content-poor|could not be parsed|timed out/i;

export class Device {
  constructor({ app, platform, udid, serial, session, locale }) {
    if (!['ios', 'android'].includes(platform)) throw new Error('platform must be ios or android.');
    this.target = { app, platform, udid, serial };
    this.locale = locale;
    this.session = session;
    this.client = createAgentDeviceClient({ session, lockPolicy: 'reject', lockPlatform: platform, responseLevel: 'full' });
  }

  // iOS opens in the foreground to give the fast accessibility bridge a chance; Android's immediate snapshot can
  // race the app's first frame, so it opens plainly and retries once if the app is not showing yet.
  // `freshTask` (Android): a running app starts over in a new task instead of a new process. Its screens and
  // navigation start over as in a cold start, in about a second instead of 5-10s; flows keep the full relaunch.
  async open({ relaunch = true, freshTask = false } = {}) {
    if (this.target.platform === 'android' && !this.savedAnimations) await this.stillAnimations();
    if (this.locale && this.target.platform === 'android') await this.setAndroidLocale();
    if (relaunch && freshTask && this.target.platform === 'android' && await this.restartTask()) relaunch = false;
    const options = { ...this.target, relaunch, foreground: this.target.platform === 'ios', timeoutMs: 120_000, waitMs: 5_000, ...this.localeOptions() };
    // Connecting idb takes seconds; it happens while the app starts instead of on the first tap.
    this.directTap().catch(() => {});
    let result;
    try { result = await this.client.apps.open(options); }
    catch (error) {
      await delay(1_500);
      result = await this.client.apps.open({ ...options, relaunch: false });
    }
    return result.device ?? result.selection ?? null;
  }

  // Clears the app's task and starts its launcher activity again, when the app is running (false otherwise).
  async restartTask() {
    const adb = args => run('adb', [...(this.target.serial ? ['-s', this.target.serial] : []), 'shell', ...args], { timeout: 30_000 }).then(r => r.stdout);
    try {
      if (!(await adb(['pidof', this.target.app])).trim()) return false;
      this.launcher ??= (await adb(['cmd', 'package', 'resolve-activity', '--brief', this.target.app])).trim().split('\n').at(-1).trim();
      if (!this.launcher.includes('/')) return false;
      // FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TASK
      return /Status: ok/.test(await adb(['am', 'start', '-W', '-f', '0x10008000', '-n', this.launcher]));
    } catch { return false; }
  }

  // iOS takes the language per launch; the app sees it as the device language without touching Settings.
  localeOptions() {
    if (!this.locale || this.target.platform !== 'ios') return {};
    const [lang, region] = this.locale.split(/[-_]/);
    return { launchArgs: ['-AppleLanguages', `(${lang})`, '-AppleLocale', region ? `${lang}_${region}` : lang] };
  }

  // Every capture waits for the UI to hold still, so animations cost time on every step; test tools (Espresso,
  // Maestro) switch them off on emulators. The previous values are restored on close. Physical phones are left alone.
  async stillAnimations() {
    const serial = this.target.serial ?? '';
    if (!/^emulator-/.test(serial)) { this.savedAnimations = {}; return; }
    const adb = args => run('adb', ['-s', serial, 'shell', 'settings', ...args]).then(r => r.stdout.trim());
    this.savedAnimations = {};
    for (const key of ANIMATION_SETTINGS) {
      this.savedAnimations[key] = await adb(['get', 'global', key]).catch(() => 'null');
      await adb(['put', 'global', key, '0']).catch(() => {});
    }
  }

  async restoreAnimations() {
    const serial = this.target.serial;
    for (const [key, value] of Object.entries(this.savedAnimations ?? {})) {
      const args = value === 'null' ? ['delete', 'global', key] : ['put', 'global', key, value];
      await run('adb', ['-s', serial, 'shell', 'settings', ...args]).catch(() => {});
    }
    this.savedAnimations = null;
  }

  // Android 13+ keeps a per-app language, so the rest of the emulator is left alone.
  async setAndroidLocale() {
    const serial = this.target.serial ? ['-s', this.target.serial] : [];
    await run('adb', [...serial, 'shell', 'cmd', 'locale', 'set-app-locales', this.target.app, '--locales', this.locale]);
  }

  // Android: the package whose activity is on top, or null. The activity manager switches as soon as a tap starts
  // another app (a link: Chrome within ~0.2s), while the accessibility tree shows the old app until the new one draws
  // (0.6-1.1s later, more under load).
  async topPackage() {
    if (this.target.platform !== 'android') return null;
    const serial = this.target.serial ? ['-s', this.target.serial] : [];
    const { stdout } = await run('adb', [...serial, 'shell', 'dumpsys activity activities | grep -m1 -E "topResumedActivity|mResumedActivity"'], { timeout: 5_000 }).catch(() => ({ stdout: '' }));
    return stdout.match(/ActivityRecord\{\S+ \S+ ([\w.]+)\//)?.[1] ?? null;
  }

  // Raw keeps unlabeled controls and platform classes (e.g. Flutter text inputs); on iOS it costs the same as the default view.
  // Captures taken mid-transition (or on a device short of memory) can come back incomplete; they succeed on a retry.
  async snapshot(scope) {
    for (let attempt = 0; ; attempt++) {
      try {
        const snapshot = await this.client.capture.snapshot({ forceFull: true, raw: true, scope, timeoutMs: 15_000 });
        // iOS: when another app (e.g. Safari from a link) took the foreground, the runner brings ours back before
        // answering and says so. `inputMark` is the count when an action's input was sent: returns counted after it
        // belong to that action, earlier ones (e.g. during a press's safety look) to the action before.
        if (snapshot.targetActivation?.reason) {
          this.leftApp = (this.leftApp ?? 0) + 1;
          this.lastActivation = { ...snapshot.targetActivation, at: performance.now() };
        }
        return snapshot;
      }
      catch (error) {
        if (attempt >= 3 || !(error?.details?.retriable || TRANSIENT_CAPTURE.test(`${error?.message} ${error?.details?.stdout ?? ''}`))) throw error;
        await delay(400 * (attempt + 1));
      }
    }
  }

  /**
   * Polls until the screen differs from `before` and then holds still for one more capture.
   * The last capture is returned so the next decision needs no extra observation.
   */
  async observeAfter(before, { scope, changeMs = 1_500, maxMs = 4_000, until = null, expect = null } = {}) {
    const started = performance.now();
    this.settled = null;
    let previous = null, snapshot = null, changed = false, polls = 0;
    while (performance.now() - started < maxMs) {
      snapshot = await this.snapshot(scope);
      polls++;
      const print = fingerprint(snapshot);
      if (print !== before && !changed) { changed = true; this.changedAt = this.inputAt; }
      // The caller needs no settled view of some screens (e.g. another app, which it leaves at once).
      if (changed && until?.(snapshot)) break;
      // Exactly the view the caller expects (a page it left, going back to it): that page is already still.
      if (changed && expect && print === expect) { this.settled = snapshot; break; }
      // Two identical looks after a change: the screen has settled, and this view can be tapped from without re-checking.
      if (changed && print === previous) { this.settled = snapshot; break; }
      if (!changed && performance.now() - started > changeMs) break;
      previous = print;
    }
    return { snapshot, changed, polls, ms: Math.round(performance.now() - started) };
  }

  markInput() { this.inputMark = this.leftApp ?? 0; this.inputAt = performance.now(); }

  // iOS reports a page at its final place while its transition still runs, and drops taps until it ends (more so on
  // a busy machine): the first tap after an input that changed the screen waits until the transition is surely over.
  async afterTransition() {
    const wait = this.target.platform === 'ios' && this.changedAt ? TRANSITION_MS - (performance.now() - this.changedAt) : 0;
    this.changedAt = null;
    if (wait > 0) await delay(wait);
  }

  // Callers may mark a view as settled after their own repeated looks agreed (e.g. after a launch).
  markSettled(snapshot) { this.settled = snapshot; }

  act(action) {
    if (action.kind !== 'press') { this.settled = null; this.markInput(); }
    const opts = { timeoutMs: 8_000 };
    switch (action.kind) {
      case 'press': return this.press(action, opts);
      case 'fill': return this.fill(action, opts);
      case 'scroll': return this.client.interactions.scroll({ direction: action.direction, ...opts });
      case 'swipe': return this.client.interactions.swipe({ from: action.from, to: action.to, ...opts });
      // An emulator takes the back key straight from adb (~0.1s against ~0.45s through agent-device).
      case 'back': return !action.mode && this.target.platform === 'android' && /^emulator-/.test(this.target.serial ?? '')
        ? run('adb', ['-s', this.target.serial, 'shell', 'input', 'keyevent', '4'])
        : this.client.command.back(action.mode ? { mode: action.mode } : {});
      case 'wait': return delay(400);
      case 'keyboard': return this.client.command.keyboard({ action: action.key });
      default: throw new Error(`Unsupported action kind: ${action.kind}.`);
    }
  }

  // A direct tap skips agent-device's resolve-and-check round trip: adb on an Android emulator (~60ms against ~370ms),
  // idb on an iOS simulator (a few ms against ~500ms of XCTest event synthesis). The check still matters: mid-transition
  // a closing page can report a control where something else is now drawn. So one fresh capture (which waits out
  // transitions) must show the same control in the same place; otherwise, and for whole-window or off-screen frames,
  // the tap goes through agent-device.
  async press(action, opts) {
    // `action` may be re-pointed at a fresher ref below, so the agent call reads it when it runs.
    const viaAgent = () => (this.markInput(), this.client.interactions.press(action.point && !action.ref ? { ...action.point, ...opts } : { ref: action.ref, ...opts }));
    await this.afterTransition();
    const direct = await this.directTap();
    const rect = action.rect;
    if (!direct || !rect || !(rect.width > 0)) return viaAgent();
    // Tapping from a view that settled after the last change needs no second look; any other view is checked first.
    const settled = Boolean(this.settled) && action.from === this.settled;
    this.settled = null;
    const fresh = settled ? null : await this.snapshot().catch(() => null);
    if (settled) {
      const point = action.point ?? { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
      this.markInput();
      return direct(Math.round(point.x), Math.round(point.y));
    }
    const screen = this.target.platform === 'android' ? await this.screenSize() : fresh?.nodes.find(n => n.rect && /^(Application|Window)$/.test(n.type ?? ''))?.rect;
    const point = action.point ?? { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
    const onScreen = screen && point.x > 0 && point.y > 0 && point.x < screen.width && point.y < screen.height && rect.width * rect.height < 0.5 * screen.width * screen.height;
    const near = (a, b) => Math.abs(a - b) <= (this.target.platform === 'android' ? 24 : 8);
    const stillThere = onScreen && fresh?.nodes.some(n => n.visibleToUser !== false && (n.label ?? '') === (action.label ?? '') && n.rect
      && near(n.rect.x, rect.x) && near(n.rect.y, rect.y) && near(n.rect.width, rect.width) && near(n.rect.height, rect.height));
    if (!stillThere) {
      // The fresh look superseded the action's ref: go through agent-device with that look's own ref for the control.
      const twin = fresh?.nodes.filter(n => n.ref && n.visibleToUser !== false && (n.label ?? '') === (action.label ?? '') && n.rect)
        .sort((a, b) => Math.hypot(a.rect.x - rect.x, a.rect.y - rect.y) - Math.hypot(b.rect.x - rect.x, b.rect.y - rect.y))[0];
      if (!action.ref || (fresh && !twin)) throw new Error(`"${action.label ?? 'target'}" is no longer where it was`);
      if (twin) action = { ...action, ref: `@${String(twin.ref).replace(/^@/, '')}${fresh.refsGeneration != null ? `~s${fresh.refsGeneration}` : ''}` };
      return viaAgent();
    }
    this.markInput();
    return direct(Math.round(point.x), Math.round(point.y));
  }

  // The direct tap for this device, or null: adb for Android emulators, idb (when installed) for iOS simulators.
  directTap() {
    this.tapper ??= (async () => {
      const { platform, serial, udid } = this.target;
      if (platform === 'android' && /^emulator-/.test(serial ?? '')) return (x, y) => run('adb', ['-s', serial, 'shell', 'input', 'tap', String(x), String(y)]);
      if (platform !== 'ios' || !udid || !existsSync(IDB)) return null;
      const shell = await openIdbShell(udid).catch(() => null);
      if (!shell) return null;
      this.idb = shell;
      return (x, y) => shell.send(`ui tap ${x} ${y}`);
    })();
    return this.tapper;
  }

  async screenSize() {
    if (!this.size) {
      const { stdout } = await run('adb', ['-s', this.target.serial, 'shell', 'wm', 'size']);
      const [, width, height] = stdout.match(/(\d+)x(\d+)\s*$/m) ?? [];
      this.size = width ? { width: Number(width), height: Number(height) } : { width: 0, height: 0 };
    }
    return this.size;
  }

  // Verified replacement costs ~4s; an empty field only needs focus and typing, and obscured fields
  // (which read back as dots) cannot be verified anyway. The next observation shows what landed.
  async fill(action, opts) {
    if (!action.secret && (action.hasText || action.verified || this.verifiedFills)) return this.client.interactions.fill({ ref: action.ref, text: action.text, ...opts });
    await this.client.interactions.press({ ref: action.ref, ...opts });
    await delay(150);
    return this.client.interactions.type({ text: action.text });
  }

  // Store-quality capture: normalized status bar and full pixel density on iOS.
  screenshot(path) {
    const extra = this.target.platform === 'ios' ? { normalizeStatusBar: true, pixelDensity: 3 } : {};
    return this.client.capture.screenshot({ path, ...extra });
  }

  startRecording(path) { return this.client.recording.record({ action: 'start', path, quality: 'medium' }); }
  stopRecording() { return this.client.recording.record({ action: 'stop' }); }
  async close() {
    await this.tapper?.catch(() => null);
    this.idb?.close();
    await this.restoreAnimations();
    return this.client.sessions.close();
  }
}
