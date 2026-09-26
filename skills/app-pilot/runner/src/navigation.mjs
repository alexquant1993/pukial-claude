// Going back as a person would, shared by explore and the flow loop: the app's own close or back control first, then
// the navigation bar's back button, a back-looking control in the top-leading corner, a swipe down on iOS sheets, and
// the system back last. Never a blind tap: agent-device's iOS in-app back taps a fixed point when it finds no labeled
// back button, which can open whatever is there (e.g. a photo).
import { buildActions, fingerprint } from './actions.mjs';

const firstLine = label => String(label ?? '').split('\n')[0].trim();

// Controls that close the top layer without side effects ("done"/"save" may submit, so they are not here).
export const DISMISS = /^(back|atr[aá]s|close|cerrar|cancel|cancelar|dismiss|dismiss menu|scrim|navigate up)$/i;
const EXPLICIT = [/^(cancel|cancelar|close|cerrar)$/i, /^(back|atr[aá]s|navigate up)$/i];
const BACKDROP = /^(scrim|dismiss|dismiss menu)$/i;

// The screen's frame. Android trees have no window node: the largest frame stands for the screen.
export const windowOf = snapshot => snapshot.nodes.find(n => n.rect && /^(Application|Window)$/.test(n.type ?? ''))?.rect
  ?? snapshot.nodes.filter(n => n.rect).sort((a, b) => b.rect.width * b.rect.height - a.rect.width * a.rect.height)[0]?.rect;

const centre = r => ({ x: r.x + r.width / 2, y: r.y + r.height / 2 });

// Explicit controls first: many dialogs ignore taps on the dimmed background ("Dismiss", "Scrim"). That background is
// tapped where nothing covers it; its centre usually lands on the sheet it sits behind.
export function dismissControl(snapshot) {
  const options = buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref && DISMISS.test(firstLine(a.label)));
  const [cancel, back] = EXPLICIT.map(re => options.find(a => re.test(firstLine(a.label))));
  if (cancel) return cancel;
  // The dimmed backdrop is often reported twice: as a whole-window layer and as the visible strip outside the sheet.
  const window = windowOf(snapshot);
  // A backdrop spans the screen's width; a small "Dismiss" is a sheet's drag handle, which does not close on a tap.
  const backdrop = window && snapshot.nodes.filter(n => n.visibleToUser !== false && BACKDROP.test(firstLine(n.label)) && n.rect?.height > 0 && n.rect.width >= 0.9 * window.width)
    .sort((a, b) => a.rect.height - b.rect.height)[0];
  // With a sheet or menu up, a "Back" belongs to the page under it: the layer on top closes first.
  if (!backdrop || !window) return back ?? options.find(a => BACKDROP.test(firstLine(a.label))) ?? null;
  // Tap a part of the backdrop that nothing else covers: the centre suits a pop-up menu, the top a bottom sheet.
  const r = backdrop.rect;
  const covered = p => snapshot.nodes.some(n => n !== backdrop && n.visibleToUser !== false && n.rect && (n.label || n.hittable) && !BACKDROP.test(firstLine(n.label))
    && n.rect.width * n.rect.height < 0.5 * window.width * window.height && p.x >= n.rect.x && p.x <= n.rect.x + n.rect.width && p.y >= n.rect.y && p.y <= n.rect.y + n.rect.height);
  const spots = [[0.5, 0.5], [0.5, 0.1], [0.5, 0.9], [0.1, 0.5], [0.9, 0.5]].map(([fx, fy]) => ({ x: r.x + fx * r.width, y: r.y + fy * r.height }));
  return { kind: 'press', point: spots.find(p => !covered(p)) ?? spots[0], label: backdrop.label };
}

// Native iOS: the first button at the leading edge of a navigation bar is its back button, whatever it is labeled.
export function navBack(snapshot) {
  const byIndex = new Map(snapshot.nodes.map(n => [n.index, n]));
  const bar = snapshot.nodes.find(n => /NavigationBar/i.test(n.type ?? '') && n.visibleToUser !== false && n.rect);
  if (!bar) return null;
  const inBar = n => { for (let p = byIndex.get(n.parentIndex); p; p = byIndex.get(p.parentIndex)) if (p === bar) return true; return false; };
  const button = snapshot.nodes.find(n => /button/i.test(n.type ?? '') && n.rect && n.rect.width > 0 && n.rect.x <= bar.rect.x + 0.3 * bar.rect.width && inBar(n));
  const action = button && buildActions(snapshot, {}).actions.find(a => a.ref && a.label === button.label && a.rect && Math.abs(a.rect.x - button.rect.x) < 2 && Math.abs(a.rect.y - button.rect.y) < 2);
  return action ?? (button ? { kind: 'press', point: centre(button.rect), rect: button.rect, label: button.label ?? '' } : null);
}

// The back affordance in the top-leading corner: labeled "Back", labeled with the previous screen's name (native iOS),
// or not labeled at all (custom icons). Only something that reads as back is tapped there (`backLike`): an avatar, a
// filter or a theme toggle can sit in that corner too.
export function cornerControl(snapshot, backLike = node => !firstLine(node.label) || DISMISS.test(firstLine(node.label)) || /back/i.test(node.identifier ?? '')) {
  const window = windowOf(snapshot);
  if (!window) return null;
  const rtl = snapshot.nodes.some(n => /^(ar|he|fa|ur)\b/i.test(n.language ?? ''));
  // A labeled one must be a button (a large page title can sit there too); an unlabeled one only has to be tappable.
  const corner = snapshot.nodes.filter(n => n.visibleToUser !== false && n.enabled !== false && (n.label ? /button/i.test(n.type ?? '') : n.hittable) && n.rect
    && n.rect.width > 0 && n.rect.width <= (n.label ? 0.5 : 0.3) * window.width && n.rect.height <= 0.12 * window.height && n.rect.y <= 0.15 * window.height
    && (rtl ? n.rect.x + n.rect.width >= 0.8 * window.width : n.rect.x <= 0.2 * window.width) && backLike(n));
  // A control labeled as back beats an unlabeled icon beside it (e.g. a filter button under a "Back" button).
  const named = n => (DISMISS.test(firstLine(n.label)) ? 0 : 1);
  const node = corner.sort((a, b) => named(a) - named(b) || a.rect.width * a.rect.height - b.rect.width * b.rect.height)[0];
  return node ? { kind: 'press', point: centre(node.rect), rect: node.rect, label: node.label ?? '' } : null;
}

// iOS page sheets (a welcome or sign-in sheet) often have no close control: a person swipes them down. On a plain page
// the same swipe at most refreshes it, which callers do not count as having gone back.
export function sheetSwipe(snapshot, platform) {
  const window = platform === 'ios' && windowOf(snapshot);
  return window ? { kind: 'swipe', label: 'swipe down', from: { x: window.width / 2, y: 0.12 * window.height }, to: { x: window.width / 2, y: 0.9 * window.height } } : null;
}

// iOS uses the edge-swipe gesture (agent-device's in-app back can tap blind); Android's back key is cheap and reliable.
export const systemBackOf = platform => ({ kind: 'back', mode: platform === 'ios' ? 'system' : undefined, label: 'system back' });

/** The back ladder for a screen, in the order a person would try it. `backLike` refines the corner rung. */
export function backLadder(snapshot, { platform, backLike } = {}) {
  return [
    ['dismiss', dismissControl(snapshot)],
    ['navBack', navBack(snapshot)],
    ['corner', cornerControl(snapshot, backLike)],
    ['sheet', sheetSwipe(snapshot, platform)],
    ['system', systemBackOf(platform)],
  ].filter(([, step]) => step).map(([rung, step]) => ({ rung, step }));
}

/**
 * Goes back one layer: tries each rung until the screen changes, and returns the settled view with the rung that
 * worked (or null when none changed anything). Used by the flow loop; explore adds screen identity on top.
 */
export async function goBack(device, snapshot, { platform, scope } = {}) {
  for (const { rung, step } of backLadder(snapshot, { platform })) {
    const before = fingerprint(snapshot);
    if (await device.act(step).then(() => false, () => true)) continue;
    const moved = await device.observeAfter(before, { scope, changeMs: 1_000 });
    if (moved.changed) return { ...moved, rung };
    snapshot = moved.snapshot;
  }
  return null;
}
