import { execFile } from 'node:child_process';
import { existsSync, mkdirSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const run = promisify(execFile);
const SOURCE = join(dirname(fileURLToPath(import.meta.url)), '..', 'native', 'ocr.swift');
const BINARY = join(homedir(), '.cache', 'app-pilot', 'ocr');

// Compiles the Apple Vision OCR helper once per source change. macOS only.
export async function ensureOcr() {
  if (process.platform !== 'darwin') return null;
  if (existsSync(BINARY) && statSync(BINARY).mtimeMs >= statSync(SOURCE).mtimeMs) return BINARY;
  mkdirSync(dirname(BINARY), { recursive: true });
  await run('xcrun', ['swiftc', '-O', SOURCE, '-o', BINARY]);
  return BINARY;
}

// Direct simulator/emulator capture skips the agent-device round trip (~250ms vs ~550ms).
export async function fastScreenshot({ platform, udid, serial }, path) {
  if (platform === 'ios') {
    await run('xcrun', ['simctl', 'io', udid ?? 'booted', 'screenshot', '--type=png', path]);
  } else {
    const { stdout } = await run('adb', [...(serial ? ['-s', serial] : []), 'exec-out', 'screencap', '-p'], { encoding: 'buffer', maxBuffer: 64 << 20 });
    await import('node:fs/promises').then(fs => fs.writeFile(path, stdout));
  }
  return path;
}

export async function ocr(path) {
  const binary = await ensureOcr();
  if (!binary) return null;
  const { stdout } = await run(binary, [path, 'fast'], { maxBuffer: 16 << 20 });
  return JSON.parse(stdout);
}

const norm = text => String(text ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');

// A label counts as drawn when a visible OCR line and the label share a meaningful prefix either way.
function drawn(label, screenText) {
  return String(label).split('\n').some(part => {
    const key = norm(part);
    if (key.length < 3) return false;
    // A short OCR line inside a long label is not evidence ("Sent" is inside "consent"); require real coverage.
    return screenText.some(line => line.includes(key.slice(0, 14)) || (line.length >= Math.max(6, key.length * 0.5) && key.includes(line)));
  });
}

/**
 * Hides accessibility subtrees that are not on screen (lingering SDK windows, occluded layers).
 * Each element is judged by its nearest container with enough evidence: if almost none of that
 * container's text is drawn, the element is hidden. Text OCR directly confirms is always kept.
 */
export function markHidden(snapshot, ocrResult) {
  if (!ocrResult?.lines?.length) return { hidden: 0 };
  const screenText = ocrResult.lines.filter(l => l.confidence >= 0.3).map(l => norm(l.text)).filter(Boolean);
  const nodes = snapshot.nodes;
  const byIndex = new Map(nodes.map(n => [n.index, n]));
  const inKeyboard = n => { for (let p = n; p; p = byIndex.get(p.parentIndex)) if (p.type === 'Keyboard') return true; return false; };
  const stats = new Map();
  for (const node of nodes) {
    // Keys and very short labels cannot be verified by OCR; they are neither evidence for nor against.
    if (!node.label || /scroll bar/i.test(node.label) || /^(Application|Window|Key|Keyboard)$/.test(node.type) || norm(node.label).length < 3 || inKeyboard(node)) continue;
    const seen = drawn(node.label, screenText);
    node.drawn = seen;
    for (let p = byIndex.get(node.parentIndex); p; p = byIndex.get(p.parentIndex)) {
      const s = stats.get(p.index) ?? { total: 0, seen: 0 };
      s.total++; if (seen) s.seen++;
      stats.set(p.index, s);
    }
  }
  let hidden = 0;
  for (const node of nodes) {
    if (node.drawn || inKeyboard(node)) continue;
    for (let p = byIndex.get(node.parentIndex) ?? null; p; p = byIndex.get(p.parentIndex)) {
      const s = stats.get(p.index);
      if (!s || s.total < 3) continue;
      if (s.seen / s.total < 0.15) { node.visibleToUser = false; hidden++; }
      break;
    }
  }
  return { hidden, lines: ocrResult.lines.length };
}
