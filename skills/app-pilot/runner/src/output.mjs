import { copyFile, mkdir, readdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const KEEP_FAILED_RUNS = 5;

const slug = text => String(text).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

// Working files (snapshots, frames, traces) are scratch: they live in the OS temp dir, never in the app repo.
export function runsRoot(appName) {
  return join(process.env.APP_PILOT_RUNS_DIR || join(tmpdir(), 'app-pilot'), slug(appName));
}

export function newRunDir({ appName, flow, platform, locale }) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return join(runsRoot(appName), `${flow}-${platform}-${locale}-${stamp}`);
}

/**
 * Copies a passing run's captures into screenshots/<platform>-<locale>/<flow>-<capture>.png,
 * replacing the previous version, and records where each file came from in manifest.json.
 */
export async function promoteCaptures({ state, screenshotsDir, flow, platform, locale, device }) {
  const folder = join(screenshotsDir, `${platform}-${locale}`);
  await mkdir(folder, { recursive: true });
  const manifestPath = join(screenshotsDir, 'manifest.json');
  const manifest = await readFile(manifestPath, 'utf8').then(JSON.parse).catch(() => ({ screenshots: {} }));
  const written = [];
  for (const [id, capture] of Object.entries(state.captured ?? {})) {
    const name = `${flow}-${id}.png`;
    await copyFile(capture.path, join(folder, name));
    manifest.screenshots[`${platform}-${locale}/${name}`] = {
      flow, capture: id, platform, locale, device: device?.name ?? null,
      probability: capture.probability, capturedAt: state.finishedAt,
    };
    written.push(join(folder, name));
  }
  manifest.updatedAt = new Date().toISOString();
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  return written;
}

// A passed run has nothing left worth keeping; failed runs stay for debugging, newest few only.
export async function finishRun({ runDir, appName, passed, keep = false }) {
  if (passed && !keep) { await rm(runDir, { recursive: true, force: true }); return null; }
  const root = runsRoot(appName);
  const entries = await readdir(root).catch(() => []);
  const dated = await Promise.all(entries.map(async name => ({ name, time: (await stat(join(root, name))).mtimeMs })));
  const stale = dated.sort((a, b) => b.time - a.time).slice(KEEP_FAILED_RUNS);
  await Promise.all(stale.map(entry => rm(join(root, entry.name), { recursive: true, force: true })));
  return runDir;
}
