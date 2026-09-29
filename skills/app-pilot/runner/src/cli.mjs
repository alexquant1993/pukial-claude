import { parseArgs } from 'node:util';
import { join, dirname } from 'node:path';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { loadEnv } from './env.mjs';
import { loadAppMap, resolveFlow } from './app-map.mjs';
import { Device } from './device.mjs';
import { Jev } from './jev.mjs';
import { runFlow, POLICY } from './loop.mjs';
import { finishRun, newRunDir, promoteCaptures } from './output.mjs';
import { bootedDevices, doctor, installed, setup } from './doctor.mjs';
import { explore } from './explore.mjs';
import { pathName, recording, replaces } from './paths.mjs';

const EXIT = { passed: 0, failed: 1, incomplete: 2, error: 3, needs_help: 4 };
const USAGE = `Usage (via the runner/app-pilot wrapper):
  app-pilot setup                                   create ~/.config/app-pilot/.env (private) for the TypeSafe key
  app-pilot doctor [app-map.yaml] [--json]          check key, OCR, devices, app installed, app-map inputs
  app-pilot explore <app-map.yaml> --platform P     walk the app and list its screens (read-only; no text input);
                                                    --platforms ios,android explores both at the same time. A later run
                                                    refreshes the saved map (section tops + anything new); --fresh starts over;
                                                    --devices N splits the sections across N booted devices per platform
  app-pilot run <app-map.yaml> <flow> --platform P  run one flow
  app-pilot run-all <app-map.yaml>                  flows x platforms x locales, one after another, with a summary
  app-pilot goal --app <id> --platform P "<goal>"   one-off goal without an app map

Options:
  --platform ios|android        run / explore / goal
  --flows a,b  --platforms ios,android  --locales es,en    run-all selection (defaults: all non-language flows,
                                every platform in app.platforms with a booted device, every app.locales entry)
  --udid <id> | --serial <id>   Target device (default: the booted one for the platform); explore takes a comma list
  --locale <tag>                App language for the run (default: first of app.locales)
  --explore                     Ignore the recorded path and let Jev choose every step
  --resume <run-dir> --note "<what the host agent did> -> <effect>"   continue after a handoff
  --keep                        Keep a passing run's working files for debugging
  --fresh                       explore: ignore the saved map and explore the whole app again
  --max-steps <n>  --max-screens <n>  --depth <n>  --min-confidence <0-1>  --record  --json

Output: passing runs update .app-pilot/screenshots/<platform>-<locale>/<flow>-<capture>.png (+ manifest.json);
explore writes .app-pilot/discovery-<platform>-<locale>.json. Working files live in the OS temp dir.
Exit codes: 0 passed, 1 failed, 2 incomplete, 3 error, 4 needs_help.`;

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    platform: { type: 'string' }, app: { type: 'string' }, udid: { type: 'string' }, serial: { type: 'string' },
    locale: { type: 'string' }, keep: { type: 'boolean' }, resume: { type: 'string' }, note: { type: 'string' },
    flows: { type: 'string' }, platforms: { type: 'string' }, locales: { type: 'string' },
    'min-confidence': { type: 'string' }, 'max-steps': { type: 'string' }, 'max-screens': { type: 'string' }, depth: { type: 'string' },
    devices: { type: 'string' }, record: { type: 'boolean' }, explore: { type: 'boolean' }, fresh: { type: 'boolean' }, json: { type: 'boolean' }, help: { type: 'boolean' },
  },
});

const [command, ...rest] = positionals;
if (values.help || !command) { console.log(USAGE); process.exit(values.help ? 0 : 3); }
loadEnv();

const out = value => console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2));

if (command === 'setup') {
  out(await setup());
  process.exit(0);
}

if (command === 'doctor') {
  const report = await doctor({ map: rest[0] ? loadAppMap(rest[0]) : null });
  if (values.json) out(report);
  else {
    for (const c of report.checks) console.log(`${c.warn ? '!' : c.ok ? '✓' : '✗'} ${c.name.padEnd(16)} ${c.detail}${c.fix ? `\n    fix: ${c.fix}` : ''}`);
    console.log(report.ok ? '\nReady.' : '\nNot ready: fix the ✗ items above.');
  }
  process.exit(report.ok ? 0 : 3);
}

// Picks the booted device for a platform unless one was named.
async function target(platform) {
  if (platform === 'ios' && values.udid) return { udid: values.udid };
  if (platform === 'android' && values.serial) return { serial: values.serial };
  const device = (await bootedDevices()).find(d => d.platform === platform);
  if (!device) throw new Error(`No booted ${platform} device. Boot one or pass --udid/--serial.`);
  return platform === 'ios' ? { udid: device.id } : { serial: device.id };
}

// Explore can split an app's sections across several devices of one platform: the ones named (comma-separated), else
// up to `count` booted simulators/emulators that have the app installed.
async function targets(platform, count, appId) {
  const named = (platform === 'ios' ? values.udid : values.serial)?.split(',').map(s => s.trim()).filter(Boolean);
  const ids = named?.length ? named : await bootedDevices().then(async devices => {
    const own = devices.filter(d => d.platform === platform);
    const ready = await Promise.all(own.map(d => installed(platform, d.id, appId)));
    return own.filter((d, i) => ready[i]).slice(0, count).map(d => d.id);
  });
  if (!ids.length) throw new Error(`No booted ${platform} device with ${appId} installed. Boot one or pass --udid/--serial.`);
  return ids.map(id => (platform === 'ios' ? { udid: id } : { serial: id }));
}

const defaultLocale = map => map?.app?.locales?.[0] ?? 'default';

/** Runs one flow end to end: replay/Jev loop, screenshot promotion, path recording, temp cleanup. */
async function runOne({ map, mapPath, flowId, platform, locale, ids, resume, note, explore: ignorePath, quiet = false }) {
  const flow = resolveFlow(map, flowId, platform);
  if (values['max-steps']) flow.maxSteps = Number(values['max-steps']);
  const appName = map.app.name ?? flow.app;
  const runDir = resume ?? newRunDir({ appName, flow: flow.id, platform, locale });
  const pathFile = startLocale => {
    const name = pathName({ flow: flow.id, platform, locale, languageFlow: flow.languageFlow, startLocale });
    return name && join(dirname(mapPath), 'paths', name);
  };
  const screenshotsDir = join(dirname(mapPath), 'screenshots');
  const load = file => (!ignorePath && !resume && file && existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')).steps : null);
  // A language flow's recording is picked once the runner has seen which language the app starts in.
  const replay = flow.languageFlow ? startLocale => load(pathFile(startLocale)) : load(pathFile());
  const device = new Device({ app: flow.app, platform, ...ids, session: `app-pilot-${platform}`, locale: locale === 'default' ? null : locale });

  if (!quiet) console.log(`${resume ? 'Resuming' : 'Running'} ${flow.id} on ${platform} (${locale})`);
  const state = await runFlow({
    flow, device, jev: new Jev(), runDir, resume: Boolean(resume), note, record: values.record, replay,
    policy: values['min-confidence'] ? { ...POLICY, act: Number(values['min-confidence']) } : POLICY,
    log: quiet ? () => {} : line => console.log(line),
  });

  const passed = state.result.status === 'passed';
  // A resumed run records too: its steps carry the handoff as a gap, where a replay hands back to Jev.
  const recordTo = pathFile(state.startLocale);
  if (passed && recordTo && (!load(recordTo) || state.replayed < state.path.length - 1)) {
    const next = recording({ flow: flow.id, platform, locale, startLocale: state.startLocale, steps: state.path });
    if (replaces(existsSync(recordTo) ? JSON.parse(readFileSync(recordTo, 'utf8')) : null, next)) {
      mkdirSync(dirname(recordTo), { recursive: true });
      writeFileSync(recordTo, JSON.stringify(next, null, 2));
      if (!quiet) console.log(`Recorded path -> ${recordTo}${next.partial ? ' (with a handoff gap)' : ''}`);
    } else if (!quiet) console.log(`Kept the complete recording at ${recordTo} (this run's path has a handoff gap)`);
  }
  const screenshots = passed && Object.keys(state.captured).length
    ? await promoteCaptures({ state, screenshotsDir, flow: flow.id, platform, locale, device: state.device }) : [];
  const keptRunDir = await finishRun({ runDir, appName, passed, keep: values.keep });

  const timings = state.timings ?? [];
  const stepMs = timings.map(t => (t.observeMs ?? 0) + (t.visionMs ?? 0) + (t.jevMs ?? 0) + (t.actMs ?? 0)).sort((a, b) => a - b);
  return {
    flow: flow.id, platform, locale, ...(state.startLocale ? { startLocale: state.startLocale } : {}), result: state.result, steps: state.step, replayedSteps: state.replayed,
    captured: Object.keys(state.captured), missingCaptures: state.missingCaptures,
    medianStepMs: stepMs[Math.floor(stepMs.length / 2)] ?? null,
    jevRequests: state.usage.requests, estimatedCostUsd: Number(state.estimatedCostUsd.toFixed(5)),
    unlabeledControls: Object.keys(state.unlabeled ?? {}).length, unlabeled: Object.values(state.unlabeled ?? {}),
    handoff: state.handoff, screenshots, runDir: keptRunDir, session: device.session,
  };
}

if (command === 'run') {
  if (!values.platform || rest.length < 2) { console.log(USAGE); process.exit(3); }
  const [mapPath, flowId] = rest;
  const map = loadAppMap(mapPath);
  const locale = values.locale ?? defaultLocale(map);
  const summary = await runOne({ map, mapPath, flowId, platform: values.platform, locale, ids: await target(values.platform),
    resume: values.resume, note: values.note, explore: values.explore });
  const { unlabeled, ...shown } = summary;
  out(shown);
  process.exit(EXIT[summary.result.status] ?? 3);
}

if (command === 'run-all') {
  const [mapPath] = rest;
  if (!mapPath) { console.log(USAGE); process.exit(3); }
  const map = loadAppMap(mapPath);
  const list = value => value?.split(',').map(s => s.trim()).filter(Boolean);
  const languageFlow = locale => map.app.languageFlow?.replace('{locale}', locale);
  const flows = list(values.flows) ?? map.flows.map(f => f.id).filter(id => !/^language-/.test(id));
  const devices = await bootedDevices();
  const platforms = list(values.platforms) ?? (map.app.platforms ?? Object.keys(map.app.ids)).filter(p => devices.some(d => d.platform === p));
  const locales = list(values.locales) ?? map.app.locales ?? ['default'];
  const rows = [];
  for (const platform of platforms) {
    const ids = await target(platform);
    for (const locale of locales) {
      // Apps that keep their own language setting are switched through the UI before the batch.
      const switcher = languageFlow(locale);
      const batch = switcher && map.flows.some(f => f.id === switcher) ? [switcher, ...flows] : flows;
      for (const flowId of batch) {
        const summary = await runOne({ map, mapPath, flowId, platform, locale, ids, explore: values.explore, quiet: values.json });
        rows.push(summary);
        await new Device({ app: map.app.ids[platform], platform, ...ids, session: summary.session }).close().catch(() => {});
        if (!values.json) console.log(`${summary.result.status === 'passed' ? '✓' : '✗'} ${platform}-${locale} ${flowId}: ${summary.result.status} (${summary.result.reason ?? ''})\n`);
        // A failed language switch would mislabel every screenshot in this batch.
        if (flowId === switcher && summary.result.status !== 'passed') break;
      }
    }
  }
  const table = rows.map(r => ({ run: `${r.platform}-${r.locale} ${r.flow}`, status: r.result.status, reason: r.result.reason,
    steps: r.steps, replayed: r.replayedSteps, jev: r.jevRequests, screenshots: r.screenshots.length, medianStepMs: r.medianStepMs, runDir: r.runDir }));
  const gaps = [...new Set(rows.flatMap(r => r.unlabeled.map(u => `${r.platform}: ${u}`)))];
  out({ passed: rows.filter(r => r.result.status === 'passed').length, total: rows.length,
    costUsd: Number(rows.reduce((s, r) => s + r.estimatedCostUsd, 0).toFixed(5)), runs: table, accessibilityGaps: gaps });
  process.exit(rows.every(r => r.result.status === 'passed') ? 0 : 1);
}

if (command === 'explore') {
  const [mapPath] = rest;
  const platforms = (values.platforms ?? values.platform ?? '').split(',').filter(Boolean);
  if (!platforms.length || !mapPath) { console.log(USAGE); process.exit(3); }
  const map = loadAppMap(mapPath);
  const locale = values.locale ?? defaultLocale(map);
  // Each platform has its own device and session, so they are explored at the same time.
  // One platform failing (a stalled device) must not throw away the other's run.
  const settledReports = await Promise.allSettled(platforms.map(async platform => {
    const prefix = platforms.length > 1 ? `[${platform}] ` : '';
    const report = await explore({ map, mapPath, platform, locale, devices: await targets(platform, Number(values.devices ?? 1), map.app.ids[platform]),
      maxScreens: Number(values['max-screens'] ?? 60), maxDepth: Number(values.depth ?? 3), fresh: values.fresh, log: values.json ? () => {} : line => console.log(prefix + line) });
    return values.json ? report : { platform, devices: report.devices, mode: report.mode, screens: report.screens.length, newScreens: report.newScreens.length, missing: report.missing,
      file: report.file, seconds: report.seconds, jevRequests: report.jevRequests,
      taps: report.taps, stoppedBecause: report.stoppedBecause, gaveUp: report.gaveUp.length, externalLinks: report.external.length };
  }));
  const reports = settledReports.map((r, i) => (r.status === 'fulfilled' ? r.value : { platform: platforms[i], error: String(r.reason?.message ?? r.reason) }));
  out(reports.length === 1 ? reports[0] : reports);
  process.exit(reports.some(r => r.error) ? 3 : 0);
}

if (command === 'goal') {
  if (!values.platform || !values.app || !rest[0]) { console.log(USAGE); process.exit(3); }
  const map = { app: { name: values.app, ids: { [values.platform]: values.app } }, flows: [{ id: 'adhoc', goal: rest.join(' ') }] };
  const summary = await runOne({ map, mapPath: join(process.cwd(), '.app-pilot', 'app-map.yaml'), flowId: 'adhoc', platform: values.platform,
    locale: values.locale ?? 'default', ids: await target(values.platform) });
  const { unlabeled, ...shown } = summary;
  out(shown);
  process.exit(EXIT[summary.result.status] ?? 3);
}

console.log(USAGE);
process.exit(3);
