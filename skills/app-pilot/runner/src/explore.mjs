import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { choice, noul } from '@typesafe-ai/sdk';
import { TAB_LABEL, buildActions, describeScreen, fingerprint, foregroundApp } from './actions.mjs';
import { Device } from './device.mjs';
import { Jev } from './jev.mjs';
import { labeledCount, mayHaveHiddenLayers, waitForContent } from './observe.mjs';
import { DISMISS, cornerControl, dismissControl, navBack, sheetSwipe, systemBackOf, windowOf } from './navigation.mjs';
import { newRunDir } from './output.mjs';
import { fastScreenshot, markHidden, ocr } from './vision.mjs';

const OUTWARD = /\b(post|publish|send|pay|buy|purchase|checkout|delete|remove|report|block|request|subscribe|donate|join|follow|unfollow|leave|accept|archive|clear|invite|share|log ?out|sign ?out|unirse|unirme|seguir|dejar de seguir|salir|aceptar|archivar|invitar|compartir|enviar|publicar|pagar|comprar|eliminar|borrar|reportar|bloquear|solicitar|suscribir|donar|cerrar sesi[oó]n)\b/i;
// Explore is read-only: on top of the outward actions, it never confirms, links or resets anything.
const CONFIRM = /\b(confirm|link|connect|reset|yes|ok|okay|continue|allow|consent|agree|s[ií]|confirmar|vincular|conectar|restablecer|continuar|permitir|consentir|acepto|de acuerdo)\b/i;
// A row whose status reads "Not Linked" / "Connected" manages an account connection: tapping it can start linking.
const ACCOUNT_LINK = /\b(not )?(linked|connected|unlinked|disconnected)\b|\b(no )?(vinculad[oa]|conectad[oa])\b/i;
// Words decide on the control's name; a short control's status line counts too (a card's lines are content).
const unsafe = action => {
  const name = firstLine(action.label);
  const lines = String(action.label ?? '').split('\n');
  return OUTWARD.test(name) || CONFIRM.test(name) || (lines.length < 3 && ACCOUNT_LINK.test(lines.slice(1).join(' ')));
};
// A dialog asks the user to decide something; explore records it and closes it, it never answers.
const isDialog = snapshot => snapshot.nodes.some(n => n.visibleToUser !== false && (/alert|dialog|sheet/i.test(n.type ?? '') || /alert|dialog/i.test(n.role ?? '') || n.label === 'Alert'));
// A native navigation bar's title plus its back button's label, when exactly one bar shows.
function barOf(snapshot) {
  const bars = snapshot.nodes.filter(n => /NavigationBar/i.test(n.type ?? '') && n.visibleToUser !== false && n.rect && n.identifier && !/^\W*$/.test(n.identifier));
  if (bars.length !== 1) return null;
  const [bar] = bars;
  const byIndex = new Map(snapshot.nodes.map(n => [n.index, n]));
  const inBar = n => { for (let p = byIndex.get(n.parentIndex); p; p = byIndex.get(p.parentIndex)) if (p === bar) return true; return false; };
  const back = snapshot.nodes.find(n => /button/i.test(n.type ?? '') && n.rect && n.rect.x <= bar.rect.x + 0.3 * bar.rect.width && inBar(n));
  return `${bar.identifier}|${back?.label ?? ''}`;
}
// A modal layer: a dialog, or anything behind a full-window barrier (Flutter's "Dismiss" on Android).
const isModal = snapshot => {
  if (isDialog(snapshot)) return true;
  const window = windowOf(snapshot);
  return Boolean(window) && snapshot.nodes.some(n => n.visibleToUser !== false && /^(scrim|dismiss|dismiss menu)$/i.test(String(n.label ?? '').trim())
    && n.rect?.width >= 0.9 * window.width && n.rect.height >= 0.5 * window.height);
};
const BACKWARD = /^(back|atr[aá]s|cancel|cancelar|close|cerrar|dismiss)$/i;
// The option of a "leave this page?" dialog that leaves without saving.
const LEAVE = /^(exit|leave|discard|discard changes|don'?t save|leave page|salir|descartar|abandonar|no guardar)$/i;
const NAV_PER_SCREEN = 6;
// Bump when the saved map's meaning changes, so an old map is ignored instead of misread.
const MAP_VERSION = 1;
const SAME_SCREEN = 0.8;
const ITEM = 0.5;
// A tap that changed nothing within this long is taken as a no-op (a screen push starts well within it).
const NO_CHANGE_MS = 1_000;
// Android's captures wait for the UI to go idle, so a change shows on the first look after it starts: every change
// after a tap showed on a look started within 0.6s of it (Waki, 113 taps under load). Another app a tap starts (a
// link) can draw later than that, but the activity manager names it at once and is asked before calling it a no-op.
// A back keeps the longer wait: taking a late back for a failed one would press a second back.
const TAP_NO_CHANGE_MS = { ios: NO_CHANGE_MS, android: 600 };
// How long another app that is starting may take to draw (Chrome's first-run page under load).
const OTHER_APP_MS = 6_000;
// Another app opened by a link takes over 1.3-1.6s after the tap (iOS simulator, measured); never sooner than this.
const EXIT_MS = 900;
const LINK_MS = 1_800;
// A row may highlight before its page opens; a look this long after the tap tells the two apart.
const CONFIRM_MS = 600;
// Cold starts of debug builds on a busy emulator can show a loading skeleton for well over 10s.
const LAUNCH_WAIT_MS = 30_000;

const firstLine = label => String(label ?? '').split('\n')[0].trim();
// Tab bars are reachable from everywhere, so their destinations are top-level sections, not children.
const TAB = TAB_LABEL;
const isTab = action => TAB.test(String(action.label ?? '')) || /tab/.test(String(action.description).split('"')[0].toLowerCase());
const NOT_A_TITLE = /^(scrim|dismiss|back|navigate up|atr[aá]s|close|cerrar|done|listo|ok|cancel|cancelar|\d+)$/i;

// A screen's identity is its set of controls (with the selected tab), not its content: two item pages are one screen type.
function screenKey(snapshot) {
  const { actions } = buildActions(snapshot, {});
  // List cards (multi-line labels) are content, not structure: a filtered feed is still the same screen.
  const controls = actions.filter(a => a.ref && a.label && String(a.label).split('\n').length < 3).map(a => firstLine(a.label).toLowerCase().replace(/\d+/g, '#'));
  const selected = snapshot.nodes.filter(n => n.selected && n.label && n.visibleToUser !== false).map(n => `*${firstLine(n.label).toLowerCase()}`);
  return new Set([...controls, ...selected]);
}

const refKey = ref => String(ref ?? '').replace(/^@/, '').replace(/~s\d+$/, '');
const kindOf = action => action.description.split('"')[0].trim().split(' ').slice(0, 3).join(' ');
// Controls of the same kind under one parent are a group; two or more make a list.
function groupsOf(snapshot, actions) {
  const parents = new Map(snapshot.nodes.filter(n => n.ref).map(n => [refKey(n.ref), n.parentIndex]));
  const groups = new Map();
  for (const a of actions) {
    const key = `${parents.get(refKey(a.ref))}|${kindOf(a)}`;
    groups.set(key, [...(groups.get(key) ?? []), a]);
  }
  return groups;
}
// A screen's shape with list contents dropped: two category pages with different tiles have the same shape.
function structure(snapshot) {
  // List cards (multi-line labels) are content; even a single one left after filtering says nothing about the page.
  const actions = buildActions(snapshot, {}).actions.filter(a => a.ref && String(a.label ?? '').split('\n').length < 3);
  const tokens = [];
  for (const members of groupsOf(snapshot, actions).values()) {
    if (members.length >= 2) tokens.push(`${kindOf(members[0])} ×list`);
    else for (const a of members) tokens.push(`${kindOf(a)} ${firstLine(a.label).toLowerCase()}`);
  }
  return new Set(tokens);
}

const similarity = (a, b) => {
  const inter = [...a].filter(x => b.has(x)).length;
  return inter / Math.max(1, new Set([...a, ...b]).size);
};

/**
 * Browses the app like a person and records its distinct screens, without typing or any outward action.
 * It keeps a map of every screen and every way found between them, always carries on from where it is, and
 * walks the shortest known route (a tap, a back, a tab) to the nearest screen with work left.
 * Jev decides which controls are worth following; code handles navigation and identity.
 */
export async function explore({ map, mapPath, platform, locale, ids, devices: deviceIds = [ids], maxScreens = 20, maxDepth = 2, minutes = 10, fresh = false, log = () => {} }) {
  const appId = map.app.ids[platform];
  const shout = log;
  const jev = new Jev({ timeoutMs: 8_000 });
  const debug = line => { if (process.env.APP_PILOT_DEBUG) log(line); };
  const runDir = newRunDir({ appName: map.app.name ?? appId, flow: 'explore', platform, locale });
  await mkdir(runDir, { recursive: true });
  const deadline = Date.now() + minutes * 60_000;
  const screens = [], edges = [], external = [], leadsTo = new Map();
  const file = join(dirname(mapPath), `discovery-${platform}-${locale}.json`);
  // A previous run's map: its screens are taken as they were, except each section's top screen, which is looked at
  // again; only controls not judged before are asked about and followed. `fresh` ignores it.
  const saved = fresh ? null : await readFile(file, 'utf8').then(JSON.parse).then(r => (r.map?.version === MAP_VERSION ? r : null)).catch(() => null);
  let jevRequests = 0, frames = 0, stoppedBecause = 'explored everything within depth';
  const gaveUp = [];

  // Hidden layers (e.g. a consent web view that stays in the tree without being drawn) are judged by OCR. The verdict
  // belongs to the layer, not the screen: the same layer on another screen reuses it. OCR runs again when hiding the
  // layer would leave almost nothing visible, which is what a layer that has actually come to the front looks like.
  const layerVerdicts = new Map();
  const vision = { checks: 0, ms: 0 };
  const signature = n => `${n.label}|${Math.round((n.rect?.x ?? 0) / 12)}|${Math.round((n.rect?.y ?? 0) / 12)}`;
  const layerNodes = snapshot => {
    const byIndex = new Map(snapshot.nodes.map(n => [n.index, n]));
    const windows = snapshot.nodes.filter(n => n.type === 'Window');
    const inLayer = n => { for (let p = n; p; p = byIndex.get(p.parentIndex)) if (p.type === 'WebView' || (windows.length > 1 && p.type === 'Window' && p !== windows[0])) return true; return false; };
    return snapshot.nodes.filter(n => n.label && inLayer(n));
  };
  const unhideOn = device => async snapshot => {
    // The view as the device reported it, before hiding layers: what a later capture of the same page will read.
    snapshot.rawPrint ??= fingerprint(snapshot);
    if (!mayHaveHiddenLayers(snapshot)) return snapshot;
    const layer = layerNodes(snapshot);
    const key = layer.map(signature).sort().join('\n');
    const known = layerVerdicts.get(key);
    if (known) {
      for (const n of layer) if (known.has(signature(n))) n.visibleToUser = false;
      if (labeledCount(snapshot) >= 3) return snapshot;
      for (const n of layer) delete n.visibleToUser;
    }
    const started = performance.now();
    const shot = await fastScreenshot(device.target, join(runDir, `frame-${frames++}.png`)).catch(() => null);
    const text = shot ? await ocr(shot).catch(() => null) : null;
    vision.checks++; vision.ms += performance.now() - started;
    markHidden(snapshot, text);
    if (text) layerVerdicts.set(key, new Set(layer.filter(n => n.visibleToUser === false).map(signature)));
    return snapshot;
  };
  const tabsOn = snapshot => buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref && a.label && isTab(a));
  // A control chosen on an earlier look is found again by its full label, nearest to where it was: list cards often
  // share a first line ("0.5km"), and refs are pinned to the snapshot that minted them.
  const locate = (snapshot, want) => {
    const presses = buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref);
    if (typeof want === 'string') return presses.find(a => firstLine(a.label) === want);
    const at = r => (r ? { x: r.x + r.width / 2, y: r.y + r.height / 2 } : { x: 0, y: 0 });
    const d = a => Math.hypot(at(a.rect).x - at(want.rect).x, at(a.rect).y - at(want.rect).y);
    return presses.filter(a => a.label === want.label).sort((a, b) => d(a) - d(b))[0];
  };
  // Same section with mostly the same controls is the same screen (a filtered feed is still the feed).
  // Apps can nest tab bars (bottom tabs, and top tabs inside one of them): every selected tab names a section shown.
  const selectedTabs = snapshot => new Set(snapshot.nodes.filter(n => n.selected && TAB.test(n.label ?? '') && n.visibleToUser !== false).map(n => firstLine(n.label)));
  const sectionOf = snapshot => firstLine(snapshot.nodes.find(n => n.selected && TAB.test(n.label ?? '') && n.visibleToUser !== false)?.label) || null;
  // A screen can be seen in several states (a filter chip picked, a list refilled); each state's key is kept.
  const find = key => screens.find(s => [s.key, ...s.states].some(k => similarity(k, key) >= SAME_SCREEN));
  // Native navigation bars name their page: the same title and back label is the same screen at any scroll position,
  // a different one is another screen. Without a bar (e.g. Flutter), the set of controls decides.
  const match = snapshot => {
    const bar = barOf(snapshot);
    const byBar = bar && screens.find(s => s.bar === bar);
    if (byBar) return byBar;
    const key = screenKey(snapshot);
    return screens.find(s => !(bar && s.bar) && [s.key, ...s.states].some(k => similarity(k, key) >= SAME_SCREEN));
  };
  const foreign = snapshot => { const owner = foregroundApp(snapshot); return Boolean(owner) && owner !== appId; };

  const record = (snapshot, reachedBy, depth, parent = null, tapped = null, home = null) => {
    const view = describeScreen(snapshot).elements;
    const { actions, unlabeled } = buildActions(snapshot, {});
    // Native iOS names the back button after the previous screen, so the names of the screens behind this one are never its title.
    const behind = new Set([parent?.title, parent?.reachedBy.at(-1), parent && !parent.reachedBy.length ? parent.title : null].filter(Boolean));
    const eligible = e => e.text && e.text.length >= 3 && !TAB.test(e.detail ?? '') && !NOT_A_TITLE.test(e.text) && !behind.has(e.text) && !/^(button|tab|link)/.test(e.role);
    // Tapping a one-line row ("Fonts") usually opens a screen headed by the same words; list cards are multi-line and name content.
    const echoed = tapped && String(tapped.label).split('\n').length === 1 ? view.find(e => eligible(e) && e.text === firstLine(tapped.label)) : null;
    // Native iOS names each page in its navigation bar's identifier.
    const barTitle = snapshot.nodes.find(n => /NavigationBar/i.test(n.type ?? '') && n.visibleToUser !== false && n.identifier && !/^\W*$/.test(n.identifier))?.identifier;
    const screen = {
      id: `s${screens.length + 1}`, depth, reachedBy,
      section: sectionOf(snapshot),
      tabs: tabsOn(snapshot).map(t => firstLine(t.label)),
      title: barTitle ?? (echoed ?? view.find(eligible))?.text ?? view.find(e => e.text && !TAB.test(e.detail ?? ''))?.text ?? '(untitled)',
      texts: view.map(e => e.text).filter(Boolean).slice(0, 15),
      controls: actions.filter(a => a.ref).map(a => a.description.replace(/^Tap |\.$/g, '')).slice(0, 25),
      inputs: view.filter(e => e.role === 'text field').length,
      unlabeledControls: unlabeled.length,
      home: home ?? (parent ? homeOf(parent) : sectionOf(snapshot) ?? START),
      // Reached through a list card (a post, a product): the way there changes with the content.
      viaCard: Boolean(parent?.viaCard || tapped?.isItem || (tapped && String(tapped.label).split('\n').length >= 3)),
      key: screenKey(snapshot), bar: barOf(snapshot), states: [], snapshot, pending: null, judged: null, seenAt: runStarted, isNew: true,
    };
    screens.push(screen);
    log(`${'  '.repeat(depth)}${screen.id} [${screen.section ?? '-'}] "${screen.title}" (${screen.controls.length} controls) via ${reachedBy.join(' > ') || 'launch'}`);
    return screen;
  };

  // Where the time goes, so a slow run can be explained: taps that found a screen versus taps spent moving around.
  const taps = { explore: 0, newScreen: 0, navigate: 0, back: 0, relaunch: 0, reopen: 0 };

  let root = null;
  const isAt = (snapshot, screen) => Boolean(snapshot) && !foreign(snapshot) && match(snapshot) === screen;
  // The screen the device shows, if it is one already on the map.
  const identify = snapshot => (snapshot && !foreign(snapshot) ? match(snapshot) ?? null : null);

  // The back affordance sits in the top-leading corner: labeled "Back", labeled with the previous screen's name
  // (native iOS), "Navigate up" (Android), or not labeled at all (custom icons). Tapped by its centre, never blind.
  // Only something that reads as "back" is tapped there: an avatar, a filter or a theme toggle can sit in that corner too.
  let onScreen = null;
  const backLike = node => {
    const name = firstLine(node.label);
    // A control named after another screen reads as back only on a known screen: on an unknown one (a view caught
    // mid-transition) a chip or filter named like a screen ("All") can sit in the corner.
    return !name || DISMISS.test(name) || /back/i.test(node.identifier ?? '') || (Boolean(onScreen) && screens.some(s => s.title !== onScreen.title && (s.title === name || s.reachedBy?.includes(name))));
  };
  const leadingCorner = snapshot => { onScreen = identify(snapshot); return cornerControl(snapshot, backLike); };
  const systemBack = systemBackOf(platform);
  const rungs = {
    dismiss: dismissControl,
    navBack,
    corner: leadingCorner,
    // iOS page sheets (e.g. a welcome or sign-in sheet) often have no close control: a person swipes them down. On a
    // plain page the same swipe at most refreshes it, which the ladder does not count as closed.
    sheet: snapshot => sheetSwipe(snapshot, platform),
    // On Android, back on a section's top screen closes the app (then a reopen or relaunch costs seconds); a person
    // uses the tab bar there instead. Pushed pages that also show the tab bar may still go back.
    system: snapshot => {
      if (platform !== 'android' || !tabsOn(snapshot).length) return systemBack;
      // A top-level screen has no way back: there the system back closes the app.
      if (atTop(snapshot)) return null;
      // A sheet or menu over a top screen still reads as that screen, but back only closes the sheet; so back is
      // withheld only on an exact top screen or on an unknown state of one (e.g. a filtered list).
      const known = identify(snapshot);
      return !known || (known.depth === 0 && similarity(screenKey(snapshot), known.key) >= 0.95) ? null : systemBack;
    },
  };

  // A top-level screen: nothing to close and no way back (an unlabeled corner icon counts only without a tab bar).
  const wayBackOn = view => Boolean(rungs.dismiss(view) || navBack(view) || cornerControl(view, n => DISMISS.test(firstLine(n.label)) || /back/i.test(n.identifier ?? '')));
  const atTop = view => !isModal(view) && !wayBackOn(view) && (tabsOn(view).length > 0 || !leadingCorner(view));
  // The main tab bar is the row with the most tabs (the lower one on a tie); its first tab is where most apps start.
  const firstTab = view => {
    const rows = new Map();
    for (const t of tabsOn(view).filter(t => t.rect)) { const y = Math.round((t.rect.y + t.rect.height / 2) / 40); rows.set(y, [...(rows.get(y) ?? []), t]); }
    const [, row] = [...rows].sort((a, b) => b[1].length - a[1].length || b[0] - a[0])[0] ?? [];
    return row?.sort((a, b) => a.rect.x - b.rect.x)[0] ?? null;
  };

  // --- The map: every way found from one screen to another. Tabs are ways from any screen that shows them. ---
  const links = new Map();
  const sectionScreens = new Map();
  const runStarted = new Date().toISOString();
  if (saved) {
    for (const { id, ...rest } of saved.screens) {
      const m = saved.map.screens[id] ?? {};
      // Section tops are looked at again; screens a shallower run never judged are explored now.
      const recheck = rest.depth === 0 || (!m.judged && rest.depth < maxDepth);
      screens.push({ id, ...rest, key: new Set(m.key ?? []), states: (m.states ?? []).map(k => new Set(k)), judged: m.judged ?? null,
        snapshot: null, pending: recheck ? null : [], known: true });
    }
    for (const { from, ...l } of saved.map.links ?? []) links.set(from, [...(links.get(from) ?? []), l]);
    for (const [name, id] of Object.entries(saved.map.sections ?? {})) { const screen = screens.find(x => x.id === id); if (screen) sectionScreens.set(name, screen); }
    for (const [label, to] of Object.entries(saved.map.leadsTo ?? {})) leadsTo.set(label, to);
    external.push(...(saved.external ?? []));
    edges.push(...(saved.edges ?? []));
    log(`  (map from ${saved.exploredAt}: ${screens.length} screens; checking section tops and anything new)`);
  }
  const byId = id => screens.find(s => s.id === id);
  const link = (from, to, via, kind = 'tap') => {
    if (!from || !to || from === to) return;
    const list = links.get(from.id) ?? [];
    if (!list.some(l => l.to === to.id && l.via === via)) list.push({ via, to: to.id, kind });
    links.set(from.id, list);
  };
  const unlink = (from, step) => {
    if (step.kind === 'tab') return;
    links.set(from.id, (links.get(from.id) ?? []).filter(l => l !== step));
  };

  // Shortest known route from where the device is to a screen that satisfies `goal`.
  // `failed` holds steps ("<screen>|<control>") that did not work during this trip, so a route never repeats them.
  const route = (snapshot, from, goal, failed = new Set()) => {
    const queue = [], seen = new Set();
    const push = (id, path) => { if (!seen.has(id)) { seen.add(id); queue.push({ id, path }); } };
    const ok = (fromId, via) => !failed.has(`${fromId}|${via}`);
    if (from) push(from.id, []);
    // Tabs showing right now work even when the current screen is not on the map, and so does a control named like one
    // that led to a top screen before (e.g. "All Categories" on every category page). Behind a sheet or a dialog they
    // cannot be tapped.
    if (snapshot && isModal(snapshot)) snapshot = null;
    for (const t of tabsOn(snapshot ?? { nodes: [] })) { const s = sectionScreens.get(firstLine(t.label)); if (s && ok(from?.id ?? '?', firstLine(t.label))) push(s.id, [{ kind: 'tab', via: firstLine(t.label), to: s.id, from: from?.id ?? '?' }]); }
    for (const a of snapshot ? buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref && !isTab(a)) : []) {
      const s = byId(leadsTo.get(firstLine(a.label)));
      if (s && s !== from && ok(from?.id ?? '?', firstLine(a.label))) push(s.id, [{ kind: 'tap', via: firstLine(a.label), to: s.id, from: from?.id ?? '?' }]);
    }
    while (queue.length) {
      const { id, path } = queue.shift();
      const screen = byId(id);
      if (path.length && goal(screen)) return { screen, path };
      for (const l of links.get(id) ?? []) if (ok(id, l.via)) push(l.to, [...path, { ...l, from: id }]);
      for (const name of screen?.tabs ?? []) { const s = sectionScreens.get(name); if (s && ok(id, name)) push(s.id, [...path, { kind: 'tab', via: name, to: s.id, from: id }]); }
    }
    return null;
  };

  // When the map has no working route, read the screen as a person would: which visible control leads to the target?
  const askWay = async (snapshot, target, avoid = new Set()) => {
    if (!snapshot) return null;
    const options = buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref && a.label && !avoid.has(firstLine(a.label)) && !/^Tap (switch|checkbox|radio|radiobutton|segmentedcontrol|slider)\b/.test(a.description)
      && !unsafe(a)).slice(0, 60);
    if (!options.length) return null;
    const { answers } = await jev.ask({ screen: describeScreen(snapshot), target: { title: target.title, shows: target.texts.slice(0, 8) } }, {
      way: choice('Pick the control a person would tap on `screen` to get to the `target` screen (e.g. a tab, a back arrow, a "show all" or "all categories" control).',
        Object.fromEntries(options.map(o => [o.id, o.description]))),
    });
    jevRequests++;
    const pick = options.find(o => o.id === answers.way?.choice);
    if (process.env.APP_PILOT_DEBUG) log(`    ? way to ${target.id}: "${firstLine(pick?.label)}" (p=${answers.way?.confidence?.toFixed(2)})`);
    return pick && answers.way.confidence >= 0.4 ? pick : null;
  };

  // One request per screen: for every control, "opens another screen?" and "one of many similar items?".
  const judgeKey = control => (String(control.label).split('\n').length >= 3 ? '⟨card⟩' : firstLine(control.label));

  const budgetLeft = () => {
    if (screens.length >= maxScreens) { stoppedBecause = `reached ${maxScreens} screens`; return false; }
    if (Date.now() > deadline) { stoppedBecause = `reached the ${minutes}-minute budget`; return false; }
    return true;
  };

  // Siblings (same container, same kind of control) are either a menu of different screens or a list of one screen
  // type. Two siblings opening screens of the same shape settle it: the rest of that group is skipped.
  const outcomes = new Map();
  // Groups whose member changed this page without leaving it (filter chips, segments): the rest are filters too.
  const inPlace = new Set(), stayed = new Set();
  // Screens reached by each set of cousins. After two cousins in a row lead to screens their cousins already reached,
  // the rest are taken to lead there too: a person who opened a few categories knows what the next one shows.
  const families = new Map();
  // The device that owns a screen takes its controls from the front; another device helping out takes them from the end.
  const nextControl = (screen, fromEnd = false) => {
    while (screen.pending?.length) {
      const control = fromEnd ? screen.pending.pop() : screen.pending.shift();
      if (inPlace.has(control.group)) { debug(`    - skip "${firstLine(control.label)}": its siblings only change this page`); continue; }
      if (families.get(control.cousins)?.repeats >= 2) { debug(`    - skip "${firstLine(control.label)}": its cousins lead to screens already seen`); continue; }
      const seen = outcomes.get(control.group) ?? [];
      // Native navigation bars name each page: two differently named pages are two screens, however alike.
      const [a, b] = seen.slice(-2);
      if (b && similarity(a.shape, b.shape) >= SAME_SCREEN && (!a.bar || !b.bar || a.bar.split('|')[0] === b.bar.split('|')[0])) { debug(`    - skip "${firstLine(control.label)}": its siblings open one screen type`); continue; }
      if (leadsTo.has(firstLine(control.label))) { debug(`    - skip "${firstLine(control.label)}": leads to ${leadsTo.get(firstLine(control.label))}`); continue; }
      return control;
    }
    return null;
  };
  const hasWork = screen => !screen.unreachable && (screen.pending === null ? screen.depth < maxDepth : screen.pending.length > 0);

  // Whether the tapped control itself changed between two views: selected, another value, or moved on its own (when
  // most of the page moved with it, the page scrolled or was still settling).
  const tookTap = (before, after, control) => {
    if (!before || !after || !control.rect) return false;
    const labeled = view => view.nodes.filter(n => n.visibleToUser !== false && n.label && n.rect);
    const nearest = (nodes, rect) => nodes.sort((a, b) => Math.hypot(a.rect.x - rect.x, a.rect.y - rect.y) - Math.hypot(b.rect.x - rect.x, b.rect.y - rect.y))[0];
    const was = nearest(labeled(before).filter(n => n.label === control.label), control.rect);
    const now = was && nearest(labeled(after).filter(n => n.label === was.label && n.type === was.type), was.rect);
    if (!was || !now) return false;
    if (Boolean(was.selected) !== Boolean(now.selected) || (was.value ?? '') !== (now.value ?? '')) return true;
    const moved = (a, b) => Math.hypot(a.rect.x - b.rect.x, a.rect.y - b.rect.y) > 4;
    if (!moved(was, now)) return false;
    const others = new Map(labeled(after).map(n => [`${n.type}|${n.label}`, n]));
    const shared = labeled(before).filter(n => n !== was && others.has(`${n.type}|${n.label}`));
    return shared.filter(n => moved(n, others.get(`${n.type}|${n.label}`))).length <= 0.3 * shared.length;
  };

  // Several devices of one platform share one map. Each takes whole sections (a tab and everything under it) from a
  // common queue, so two devices never work on the same screens; the first device records the start screen.
  const START = '⟨start⟩';
  const claims = new Map();
  // The section a screen belongs to: the tab it was found under (older maps: its first step, or the start's section).
  const homeOf = s => s.home ?? (s.depth === 0 ? s.section ?? s.reachedBy?.[0] ?? START : sectionScreens.has(s.reachedBy?.[0]) ? s.reachedBy[0] : root?.home ?? START);
  let rootReady;
  const rooted = new Promise(resolve => { rootReady = resolve; });
  // Devices still working, and the screen each one is on: a device out of sections helps another with its screens.
  const busy = new Set(), waiting = new Set(), where = new Map();
  let steals = 0;
  // The screen with untried controls highest up in another device's sections (a higher one opens a larger share of the
  // app); its last control becomes a section of its own for the helper. The owner keeps a control it is about to take.
  const steal = me => {
    const open = screens.filter(s => claims.get(homeOf(s)) !== me && !s.unreachable && !s.viaCard && s.depth < maxDepth && s.pending?.length >= (where.get(claims.get(homeOf(s))) === s ? 2 : 1))
      .sort((a, b) => a.depth - b.depth || b.pending.length - a.pending.length);
    for (const screen of open) {
      // A control a helper could not get to stays with its owner.
      if (screen.pending.at(-1)?.stay) continue;
      const control = nextControl(screen, true);
      if (!control) continue;
      const home = `${homeOf(screen)} › ${firstLine(control.label)}`;
      claims.set(home, me);
      steals++;
      return { screen, control, home };
    }
    return null;
  };
  const devices = [];

  const worker = async (ids, me) => {
    const tag = deviceIds.length > 1 ? `{${me + 1}} ` : '';
    const log = tag ? line => shout(tag + line) : shout;
    const debug = line => { if (process.env.APP_PILOT_DEBUG) log(line); };
    const device = new Device({ app: appId, platform, ...ids, session: `app-pilot-${platform}${me ? `-${me + 1}` : ''}`, locale: locale === 'default' ? null : locale });
    devices.push(device);
    const unhide = unhideOn(device);

    // The newest observation of the device; every tap, back and launch below replaces it.
    let last = null;
    const look = async () => (last = await unhide(await device.snapshot()));

    // After a launch, feeds and lists fill in after the frame appears; wait until two looks agree.
    // The newest capture is always kept: refs are pinned to the snapshot that minted them, older ones are rejected.
    const observe = async ({ timeoutMs } = {}) => {
      let { snapshot } = await waitForContent(device, undefined, { timeoutMs });
      for (let i = 0; i < 4; i++) {
        await new Promise(r => setTimeout(r, 400));
        const again = await device.snapshot().catch(() => null);
        if (!again) break;
        const settled = fingerprint(again) === fingerprint(snapshot);
        snapshot = again;
        if (settled) { device.markSettled(snapshot); break; }
      }
      return (last = await unhide(snapshot));
    };
    // After a tap, observeAfter has already seen the screen hold still; only a near-empty screen is still loading.
    const settled = async moved => (moved.changed && labeledCount(moved.snapshot) >= 3 ? (last = await unhide(moved.snapshot)) : observe());

    // A link can bring up another app 1-2s after its tap, when the next tap is already under way; the device then
    // brings ours back. A return seen sooner than EXIT_MS after a tap belongs to the tap before it.
    let lastTap = null;
    const flagExternal = (was, activation = device.lastActivation) => {
      if (!was?.screen || leadsTo.get(was.label) === 'external') return;
      external.push({ from: was.screen.id, via: was.label, app: `another app (pid ${activation?.otherActiveApplicationPid ?? '?'})` });
      leadsTo.set(was.label, 'external');
      log(`${'  '.repeat(was.screen.depth + 1)}↗ "${was.label}" opened another app; back in the app`);
    };
    const tap = async (snapshot, label, action = null) => {
      const prev = lastTap;
      lastTap = null;
      const target = action ?? locate(snapshot, label);
      if (!target) return null;
      const before = fingerprint(snapshot);
      // Lets the device skip its safety look when this is the view it saw settle.
      const pressed = { ...target, from: snapshot };
      last = null;
      const counted = device.leftApp ?? 0;
      // A failed tap still leaves a known view of the screen for whatever comes next.
      try { await device.act(pressed); } catch (error) { if ((device.leftApp ?? 0) > counted) flagExternal(prev); await look().catch(() => {}); throw error; }
      const away = device.inputMark ?? counted;
      if (away > counted || (prev && away > prev.away)) flagExternal(prev);
      let moved = await device.observeAfter(before, { changeMs: TAP_NO_CHANGE_MS[platform], until: foreign });
      if (!moved.changed && platform === 'android' && await device.topPackage().then(pkg => Boolean(pkg) && pkg !== appId)) {
        debug(`    … another app is starting`);
        moved = await device.observeAfter(before, { changeMs: OTHER_APP_MS, maxMs: OTHER_APP_MS, until: foreign });
      }
      if ((device.leftApp ?? 0) > away) {
        if (prev && device.lastActivation.at - device.inputAt < EXIT_MS) flagExternal(prev);
        // The device brought the app back after this tap opened another one (iOS): the tap leads out of the app.
        else moved.leftApp = device.lastActivation;
      }
      last = await unhide(moved.snapshot);
      return moved;
    };

    // A relaunch costs 3-9s (more for debug builds): it is the last resort, and each one is logged with its reason.
    // A restart in a fresh task can leave another app in front (the launcher, when the app had been killed): then a
    // cold launch.
    const launch = async () => {
      await device.open({ relaunch: true, freshTask: true });
      const view = await observe({ timeoutMs: LAUNCH_WAIT_MS });
      if (!foreign(view)) return view;
      await device.open({ relaunch: true });
      return observe({ timeoutMs: LAUNCH_WAIT_MS });
    };
    const relaunch = async reason => {
      taps.relaunch++;
      log(`  ↻ relaunch: ${reason}`);
      const snapshot = await launch();
      if (foreign(snapshot)) throw new Error(`${appId} did not come to the front (${foregroundApp(snapshot)} is showing)`);
      // Some apps reopen on the last screen they showed (e.g. iOS Settings): back out to the start screen first. A
      // top-level screen that does not read as the start (a feed that changed) is already there.
      if (root && !isAt(snapshot, root)) for (let i = 0; i < 5 && !isAt(last, root) && !atTop(last); i++) if (!await closeLayer(last)) break;
      return last;
    };
    // Back on a top-level screen can close the app (Android); bringing it back to the front is a warm start, not a cold one.
    const reopen = async () => {
      taps.reopen++;
      await device.open({ relaunch: false }).catch(() => {});
      const snapshot = await observe({ timeoutMs: LAUNCH_WAIT_MS }).catch(() => null);
      return snapshot && !foreign(snapshot) ? snapshot : null;
    };
    // Another app (e.g. a browser tab) usually closes with one back; bringing ours to the front keeps its navigation.
    // The app is waited on to hold still even when it comes back exactly as it was: an Android app that has just
    // resumed drops a tap sent at once (tried: the next tap did nothing in 3 of 5 runs).
    const leave = async (snapshot, reason) => {
      for (const step of [() => device.act({ kind: 'back' }), () => device.open({ relaunch: false })]) {
        if (await step().then(() => false, () => true)) continue;
        const moved = await device.observeAfter(fingerprint(snapshot));
        if (!foreign(moved.snapshot) && describeScreen(moved.snapshot).elements.length) { last = await unhide(moved.snapshot); return; }
      }
      await relaunch(reason);
    };

    // Closes the top layer, as a person would: the app's own back or close control first (the system back can close the
    // whole app from a page inside a modal flow), the system back only when the screen offers none.
    // `to`: the screen this is expected to go back to. On Android, whose captures wait for the UI to go idle, looking
    // exactly as it last did means it has settled; iOS reports a page's final layout while it is still animating in.
    const closeLayer = async (snapshot, to = null) => {
      for (const rung of ['dismiss', 'navBack', 'corner', 'sheet', 'system']) {
        const step = rungs[rung](snapshot);
        if (!step) continue;
        const before = fingerprint(snapshot);
        taps.back++;
        const error = await device.act(step).then(() => null, e => e);
        if (process.env.APP_PILOT_DEBUG) log(`    ⤺ ${rung} ${JSON.stringify(firstLine(step.label ?? step.kind))}${error ? ` failed: ${error.message}` : ''}`);
        if (error) continue;
        // A swipe down on a plain page refreshes it, and a refreshing list never holds still: that wait is kept short.
        const moved = await device.observeAfter(before, { changeMs: NO_CHANGE_MS, maxMs: rung === 'sheet' ? 1_500 : undefined, expect: platform === 'android' ? to?.snapshot?.rawPrint ?? null : null });
        if (foreign(moved.snapshot)) {
          log(`  ↺ ${rung} on ${identify(snapshot)?.id ?? 'an unknown screen'} ("${firstLine(describeScreen(snapshot).elements.find(e => e.text)?.text)}") left the app (${foregroundApp(moved.snapshot)}); reopening`);
          return reopen();
        }
        // Only a different screen counts as closed: a swipe can nudge the page (new fingerprint) without leaving it.
        let after = moved.changed ? await settled(moved) : (last = await unhide(moved.snapshot));
        // Back on a form can ask "leave this page?". Explore never types, so leaving discards nothing: that one dialog,
        // raised by our own back, is answered with its leave option. Every other dialog stays unanswered.
        const leaveOption = view => buildActions(view, {}).actions.find(a => a.kind === 'press' && a.ref && LEAVE.test(firstLine(a.label)));
        const leave = isModal(after) && !leaveOption(snapshot) && leaveOption(after);
        if (leave) {
          debug(`    ⤺ leave ${JSON.stringify(firstLine(leave.label))}`);
          const left = await tap(after, null, leave).catch(() => null);
          if (left?.changed) after = await settled(left);
        }
        const was = identify(snapshot), now = identify(after);
        if (similarity(screenKey(after), screenKey(snapshot)) < SAME_SCREEN || (isDialog(snapshot) && !isDialog(after)) || (now && now !== was)) return after;
        snapshot = after;
      }
      return null;
    };

    const toStart = async view => {
      let went = 0;
      for (; went < 8 && view && !atTop(view); went++) view = await closeLayer(view);
      if (!view || !atTop(view)) return null;
      if (went) log(`  ⤺ started on an inner screen; went back ${went} layer${went > 1 ? 's' : ''}`);
      const tab = firstTab(view);
      if (tab && !selectedTabs(view).has(firstLine(tab.label))) {
        const moved = await tap(view, null, tab).catch(() => null);
        if (moved?.changed) view = await settled(moved);
      }
      return view;
    };

    // Takes each step of a route; a step that does not land where the map says is dropped from the map.
    const walk = async (path, from, goal = () => false, failed = new Set()) => {
      let at = from;
      for (const step of path) {
        const snapshot = last ?? await look();
        taps.navigate++;
        let landed = null;
        if (step.kind === 'back') landed = identify(await closeLayer(snapshot, byId(step.to)));
        else {
          const moved = await tap(snapshot, step.via).catch(() => null);
          if (moved?.changed) landed = identify(await settled(moved));
        }
        if (landed && goal(landed)) return true;
        if (landed?.id !== step.to) { failed.add(`${step.from ?? at?.id ?? '?'}|${step.via}`); if (at) unlink(at, step); return false; }
        at = landed;
      }
      return true;
    };

    // Gets to a screen that satisfies `goal`: known routes first, then (for one target) asking Jev which control leads
    // there, then "back" and look again, as a person would; a relaunch only when nothing else works.
    const travel = async (goal, what, target = null, { mayRelaunch = true } = {}) => {
      for (let round = 0; round < 2; round++) {
        let asked = 0;
        const tried = new Set(), failed = new Set();
        for (let attempt = 0; attempt < maxDepth + 5; attempt++) {
          let snapshot = last ?? await look();
          // A capture taken while something was still closing may not match its screen yet: look once more first.
          if (!identify(snapshot) && !foreign(snapshot)) { await new Promise(r => setTimeout(r, 250)); snapshot = await look(); }
          // An unknown screen with no way back in an app without tabs is its start screen in another state (scrolled, say).
          const noWayBack = !rungs.dismiss(snapshot) && !navBack(snapshot) && !leadingCorner(snapshot);
          const here = identify(snapshot) ?? (noWayBack && !root.tabs.length && !foreign(snapshot) ? root : null);
          if (here && goal(here)) return here;
          // A section's top screen is wherever its tab is: with that tab selected and nothing pushed on top, a different
          // state of it (a filter, a scroll position, a list still loading) counts as arrived.
          if (target?.depth === 0 && target.section && selectedTabs(snapshot).has(target.section) && !(here?.depth > 0) && !isDialog(snapshot)) return target;
          const plan = route(snapshot, here, goal, failed);
          // A sheet or a dialog is closed before heading to another section, as a person would.
          if (isModal(snapshot) && (!plan || !here || homeOf(plan.screen) !== homeOf(here)) && await closeLayer(snapshot)) continue;
          if (plan && await walk(plan.path, here, goal, failed)) continue;
          // Heading up (the target is shallower): back first, as a person would. Sideways: ask which control leads there.
          const headingUp = here && target && target.depth < here.depth && !plan;
          if (target && asked < 3 && !headingUp) {
            asked++;
            const pick = await askWay(last, target, tried);
            if (pick) tried.add(firstLine(pick.label));
            if (pick) {
              taps.navigate++;
              const moved = await tap(last, null, pick).catch(() => null);
              if (moved?.changed) {
                const landed = identify(await settled(moved));
                if (here && landed) link(here, landed, firstLine(pick.label));
                continue;
              }
            }
          }
          // The known route and the suggested control did not get there: close whatever is on top and look again.
          const after = await closeLayer(last ?? snapshot, target);
          if (!after) break;
          const landed = identify(after);
          if (here && landed) link(here, landed, '⟨back⟩', 'back');
        }
        // A relaunch starts over from the first screen: worth it only if the map still knows a way from there.
        if (round === 0 && mayRelaunch && budgetLeft() && (goal(root) || route({ nodes: [] }, root, goal))) await relaunch(`no way found to ${what}`);
        else if (round === 0) break;
      }
      return null;
    };

    const choose = async screen => {
      screen.judged ??= {};
      if (isDialog(screen.snapshot)) { log(`${'  '.repeat(screen.depth + 1)}→ (a dialog: recorded, not answered)`); return []; }
      // A screen that shows almost nothing to follow may still be loading (a grid fetched after the page appeared):
      // look once more while still on it, and keep the richer view.
      const followable = snapshot => buildActions(snapshot, {}).actions.filter(a => a.kind === 'press' && a.ref && a.label && !isTab(a)).length;
      // A section's top screen is never a dead end: one with little to follow is looked at again too.
      if ((followable(screen.snapshot) <= 2 || (screen.depth === 0 && followable(screen.snapshot) <= 4)) && last && identify(last) === screen) {
        debug(`    … "${screen.title}" shows little to follow; looking again`);
        await new Promise(r => setTimeout(r, 600));
        const again = await look().catch(() => null);
        // A section top that filled in may not read as its half-loaded self any more; its selected tab still names it.
        const same = again && (identify(again) === screen || (screen.depth === 0 && !identify(again) && !isModal(again) && sectionOf(again) === screen.section));
        if (same && followable(again) > followable(screen.snapshot)) {
          debug(`    + "${screen.title}" finished loading (${followable(again)} controls)`);
          if (identify(again) !== screen) { screen.states.push(screen.key); screen.key = screenKey(again); }
          screen.snapshot = again;
        }
      }
      const { actions } = buildActions(screen.snapshot, {});
      // Flutter on iOS reports some nodes with the whole window as their frame: still pressable by ref, but a card like
      // that can be a page kept alive off screen, so it is the last choice to stand for its list.
      const window = windowOf(screen.snapshot);
      const fillsScreen = a => window && a.rect && a.rect.width * a.rect.height >= 0.9 * window.width * window.height;
      // Only what is on screen: a person scrolls before tapping a row below the fold (a tap there makes the list scroll
      // first, and a scrolled list reads as another screen).
      const onScreen = a => !window || !a.rect || (a.rect.y + a.rect.height / 2 > window.y && a.rect.y + a.rect.height / 2 < window.y + window.height
        && a.rect.x + a.rect.width / 2 > window.x && a.rect.x + a.rect.width / 2 < window.x + window.width);
      // A control named like the one that opened this page is the page's own title or its main switch (which can hand
      // the screen to the system, e.g. "Control Nearby Devices"), not a way further in.
      const echoesOpener = a => screen.depth > 0 && firstLine(a.label) === screen.reachedBy?.at(-1);
      // The way back is navigation, not something to explore (native iOS names it after the previous screen).
      const back = navBack(screen.snapshot) ?? leadingCorner(screen.snapshot);
      const isBack = a => Boolean(back?.rect && a.rect) && Math.abs(a.rect.x - back.rect.x) < 2 && Math.abs(a.rect.y - back.rect.y) < 2;
      // Explore must never change settings: switches, checkboxes and radios are never tapped.
      const candidates = actions.filter(a => a.kind === 'press' && a.ref && a.label && onScreen(a) && !/^Tap (switch|checkbox|radio|radiobutton|segmentedcontrol|slider)\b/.test(a.description)
        && !isTab(a) && !a.selected && !unsafe(a) && !BACKWARD.test(firstLine(a.label)) && !isBack(a) && !leadsTo.has(firstLine(a.label)) && !echoesOpener(a)
        && !(judgeKey(a) in screen.judged)).slice(0, 40);
      if (!candidates.length) { if (screen.known) log(`${'  '.repeat(screen.depth + 1)}→ (nothing new)`); return []; }
      const questions = {};
      candidates.forEach((c, i) => {
        questions[`nav${i}`] = noul(`Would "${c.description}" open a different screen or section of the app (not a toggle, a filter, a like, or a web link)?`);
        questions[`item${i}`] = noul(`Is "${c.description}" one entry in a list of similar items (a post, product, message, person or result)?`);
        // Words cannot catch every state change (a theme swatch, a consent button), so Jev is asked in the same request.
        questions[`change${i}`] = noul(`Would tapping "${c.description}" change a setting, a preference, a consent choice or saved data?`);
      });
      const { answers } = await jev.ask({ screen: describeScreen(screen.snapshot) }, questions);
      jevRequests++;
      // Cards in a list usually merge several texts into one multi-line label; three or more alike is a list.
      const cards = candidates.filter(c => String(c.label).split('\n').length >= 3);
      const listed = new Set(cards.length >= 3 ? cards : []);
      const scored = candidates.map((c, i) => ({ c, nav: answers[`nav${i}`]?.noul ?? 0, item: listed.has(c) ? 1 : answers[`item${i}`]?.noul ?? 0 }))
        .filter((s, i) => (answers[`change${i}`]?.noul ?? 0) < 0.5);
      // One threshold splits items from other controls, so a borderline control (e.g. a category tile) is never dropped by both.
      const nav = scored.filter(s => s.nav >= 0.6 && s.item < ITEM).sort((a, b) => b.nav - a.nav).slice(0, NAV_PER_SCREEN).map(s => s.c);
      // One representative per list is enough to learn the detail screen type (e.g. the first post).
      const items = scored.filter(s => s.item >= ITEM).map(s => s.c);
      const firstItem = items.find(c => !fillsScreen(c)) ?? items[0];
      if (firstItem) firstItem.isItem = true;
      const chosen = firstItem ? [firstItem, ...nav] : nav;
      // Cousins: controls of the same kind on screens opened from one screen (e.g. the subcategories on every category page).
      for (const [key, members] of groupsOf(screen.snapshot, chosen)) for (const c of members) { c.group = `${screen.id}|${key}`; c.cousins = `${screen.from ?? screen.id}|${kindOf(c)}`; }
      // Remembered for the next run: a control judged once is not asked about again (all cards count as one).
      for (const c of candidates) if (screen.judged[judgeKey(c)] !== 'follow') screen.judged[judgeKey(c)] = chosen.includes(c) ? 'follow' : 'skip';
      log(`${'  '.repeat(screen.depth + 1)}→ ${chosen.map(c => `"${firstLine(c.label)}"`).join(', ') || '(nothing to follow)'}`);
      return chosen;
    };

    // Taps one control on the current screen and returns the screen the app is on afterwards (null when unknown).
    const step = async (screen, control, asSection = false, home = null) => {
      const label = firstLine(control.label);
      const began = performance.now();
      try { return await stepOnce(screen, control, asSection, label, home); }
      finally { debug(`    · "${label}" took ${Math.round(performance.now() - began)}ms`); }
    };
    const stepOnce = async (screen, control, asSection, label, home) => {
      taps.explore++;
      const beforeView = last;
      const moved = await tap(last, control).then(m => { if (m && !m.leftApp) lastTap = { screen, label, away: device.leftApp ?? 0 }; return m; }).catch(error => { log(`${'  '.repeat(screen.depth + 1)}! could not tap "${label}": ${error.message}`); return null; });
      if (!moved) return identify(last);
      let after = moved.snapshot;
      if (moved.leftApp) {
        flagExternal({ screen, label }, moved.leftApp);
        if (!moved.changed || identify(last)) return identify(last) ?? screen;
        await settled(moved);
        return identify(last);
      }
      const outside = async view => {
        external.push({ from: screen.id, via: label, app: foregroundApp(view) });
        leadsTo.set(label, 'external');
        await leave(view, `"${label}" opened ${foregroundApp(view)}`);
        return identify(last);
      };
      if (foreign(after)) return outside(after);
      // The tapped control still there, same kind, same row, and the same way back: a filter or a toggle changed this
      // page's state. A control that navigates goes away with its page (at most its words come back as the next page's
      // title), and a push changes the way back (a new back button, or one named after this page).
      const wayBack = view => { const b = navBack(view) ?? leadingCorner(view); return b ? `${firstLine(b.label)}|${Math.round((b.rect?.x ?? b.point?.x ?? 0) / 20)}` : ''; };
      const row = r => (r ? r.y + r.height / 2 : -1e9);
      const stays = view => {
        const win = windowOf(view);
        return !asSection && !isTab(control) && !isDialog(view) && Boolean(control.rect && win) && !match(view) && wayBack(view) === wayBack(screen.snapshot)
          && buildActions(view, {}).actions.some(a => a.kind === 'press' && a.ref && a.label === control.label && kindOf(a) === kindOf(control) && Math.abs(row(a.rect) - row(control.rect)) <= 0.08 * win.height);
      };
      let changed = moved.changed;
      after = changed ? await settled(moved) : (last = await unhide(after));
      // Another app can take over while the view settles (a first capture mid-transition still shows ours).
      if (foreign(after)) return outside(after);
      // A tab can open its page a moment after its own highlight (e.g. a sheet over the page that was showing): while
      // another section's screen still shows and the tab is not selected, look again.
      for (let i = 0; asSection && i < 3 && !selectedTabs(after).has(label) && identify(after) && identify(after).section !== label; i++) {
        await new Promise(r => setTimeout(r, 400));
        const again = await look().catch(() => null);
        if (!again || fingerprint(again) === fingerprint(after)) continue;
        after = await settled({ ...await device.observeAfter(fingerprint(after), { changeMs: 0 }), changed: true });
        changed = true;
        debug(`    … the "${label}" tab opened late`);
      }
      // A tap that seems to have stayed on this screen gets one more look a little later. A row can highlight first and
      // open its page a moment after; on iOS a link hands over to Safari 1.3-1.6s after the tap without changing this
      // screen (the device then brings the app back, so no later tap can land in the other app).
      // It is skipped only when the tapped control itself changed (got selected, shows another value, or moved while the
      // page around it did not): this page took the tap, as a filter chip does. A page that is still settling can change
      // anywhere, and a link changes nothing before it hands over.
      if (!asSection && (!changed || ((identify(after) === screen || stays(after)) && !tookTap(beforeView, after, control)))) {
        device.markSettled(null);
        const counted = device.leftApp ?? 0;
        await new Promise(r => setTimeout(r, Math.max(0, (platform === 'ios' ? LINK_MS : CONFIRM_MS) - (performance.now() - device.inputAt))));
        const again = await look().catch(() => null);
        if ((device.leftApp ?? 0) > counted) { flagExternal({ screen, label }); lastTap = null; return identify(last) ?? screen; }
        if (again && fingerprint(again) !== fingerprint(after)) {
          const late = await device.observeAfter(fingerprint(after), { changeMs: 0 });
          after = await settled({ ...late, changed: true });
          changed = true;
          debug(`    … "${label}" changed the screen late`);
        }
      }
      if (!changed) { debug(`    = "${label}" changed nothing`); edges.push({ from: screen.id, to: screen.id, via: label }); return screen; }
      if (foreign(after)) return outside(after);
      // Nothing readable (e.g. a hand-off to another app or a blank web page): note it and leave.
      if (!describeScreen(after).elements.length) {
        external.push({ from: screen.id, via: label, app: foregroundApp(after) ?? 'unreadable' });
        leadsTo.set(label, 'external');
        await leave(after, `"${label}" showed nothing readable`);
        return identify(last);
      }
      if (control.group) outcomes.set(control.group, [...(outcomes.get(control.group) ?? []), { shape: structure(after), bar: barOf(after) }]);
      let reached = match(after);
      if (!reached && stays(after)) {
        debug(`    = "${label}" changed the state of ${screen.id}`);
        if (control.group) inPlace.add(control.group);
        screen.states.push(screenKey(after));
        edges.push({ from: screen.id, to: screen.id, via: label });
        return screen;
      }
      if (control.cousins && reached !== screen) {
        const family = families.get(control.cousins) ?? { reached: new Set(), repeats: 0 };
        family.repeats = reached && family.reached.has(reached.id) ? family.repeats + 1 : 0;
        families.set(control.cousins, family);
      }
      if (reached) {
        debug(`    = "${label}" -> ${reached.id} (known)`);
        // Back on this very screen: a filter if the tapped control itself changed, or when a sibling did the same.
      if (reached === screen && control.group) {
        if (tookTap(beforeView, after, control) || stayed.has(control.group)) inPlace.add(control.group);
        stayed.add(control.group);
      }
        if (reached.id !== screen.id && reached.depth <= 1) leadsTo.set(label, reached.id);
      } else {
        taps.newScreen++;
        reached = asSection ? record(after, [label], 0, null, control, label) : record(after, [...(screen.reachedBy ?? []), label], screen.depth + 1, screen, control, home);
        reached.from = screen.id;
      }
      if (control.cousins && reached !== screen) families.get(control.cousins).reached.add(reached.id);
      edges.push({ from: screen.id, to: reached.id, via: label });
      link(screen, reached, label, asSection ? 'tab' : 'tap');
      if (asSection) sectionScreens.set(label, reached);
      return reached;
    };

    const mine = screen => claims.get(homeOf(screen)) === me;
    const hasMyWork = screen => hasWork(screen) && mine(screen);
    try {
      // A fresh start every time: a running app keeps each tab's inner pages and chosen sub-tabs in memory.
      let first = await launch();
      // A stalled accessibility service or a slow cold start can yield an empty first look; one fresh launch recovers it.
      if (!buildActions(first, {}).actions.some(a => a.ref)) first = await relaunch('nothing readable at launch');
      // Explore only ever taps inside the app under test.
      if (foreign(first)) throw new Error(`${appId} did not come to the front (${foregroundApp(first)} is showing)`);
      // Apps that restore their last screen start deeper than their top: close layers as a person would until a
      // top-level screen shows, then pick the main tab bar's first tab.
      first = await toStart(first) ?? last;
      if (me === 0) {
        root = identify(first) ?? record(first, [], 0);
        if (root.section) sectionScreens.set(root.section, root);
        claims.set(homeOf(root), me);
      }
    } finally { if (me === 0) rootReady(); }
    await rooted;
    if (!root) return;

    let current = me === 0 ? root : identify(last) ?? root;
    busy.add(me);
    try { while (budgetLeft()) {
      where.set(me, current);
      // Work where the device is: choose this screen's controls once, then follow them one by one.
      if (current?.known && identify(last) === current) { current.seenAt = runStarted; if (current.pending === null) current.snapshot = last; }
      if (current && mine(current) && current.pending === null) current.pending = current.depth < maxDepth && current.snapshot ? await choose(current) : [];
      const control = current && mine(current) && nextControl(current);
      if (control) { current = await step(current, control); continue; }
      // This screen is done: walk to the nearest screen with work left.
      const plan = route(last, current, hasMyWork);
      if (plan) {
        const reached = await travel(s => s === plan.screen, plan.screen.id, plan.screen);
        if (!reached) { plan.screen.unreachable = true; gaveUp.push({ screen: plan.screen.id, reason: 'no way back to it' }); }
        current = reached ?? identify(last);
        continue;
      }
      // No known route: back out and look again (travel does that); it relaunches only as a last resort.
      if (screens.some(hasMyWork)) {
        current = await travel(hasMyWork, 'unfinished screens');
        if (!current) { for (const s of screens.filter(hasMyWork)) { s.unreachable = true; gaveUp.push({ screen: s.id, reason: 'no way back to it' }); } current = identify(last); }
        continue;
      }
      // Every screen of this device's sections is done: take the next section no device has taken yet.
      // A section whose top screen was already seen in this run (a refresh walks to them first) is not entered again.
      // Tab bars can nest (a top tab bar inside one section), so every section top's tabs count, not only the first's.
      const name = [...new Set(screens.filter(s => s.depth === 0).flatMap(s => s.tabs))].find(t => !claims.has(t) && sectionScreens.get(t)?.seenAt !== runStarted);
      if (name) {
        claims.set(name, me);
        // A sub-tab that is already selected is the section on screen: nothing to tap.
        const here = identify(last);
        if (here && selectedTabs(last).has(name) && tabsOn(last).some(t => firstLine(t.label) === name)) { sectionScreens.set(name, here); current = here; continue; }
        // The tab bar shows on most screens: tap the tab right here when it is visible, travel only when it is not.
        const at = tabsOn(last).some(t => firstLine(t.label) === name) ? (identify(last) ?? root) : await travel(s => s.tabs.includes(name), `the "${name}" tab`);
        const tab = at && tabsOn(last).find(t => firstLine(t.label) === name);
        current = tab ? await step(at, tab, true) : identify(last);
        continue;
      }
      // No section left: take over part of another device's work, or wait while another device may still find some.
      const help = steal(me);
      if (help) {
        log(`  ⇄ helping with "${firstLine(help.control.label)}" on ${help.screen.id}`);
        const at = await travel(s => s === help.screen, help.screen.id, help.screen, { mayRelaunch: false });
        if (!at) { help.control.stay = true; claims.delete(help.home); help.screen.pending.push(help.control); current = identify(last); continue; }
        current = await step(at, help.control, false, help.home);
        continue;
      }
      if (![...busy].some(d => d !== me && !waiting.has(d))) break;
      where.set(me, null);
      waiting.add(me);
      await new Promise(r => setTimeout(r, 500));
      waiting.delete(me);
    } } finally { busy.delete(me); where.delete(me); }
  };

  const started = Date.now();
  try {
    const results = await Promise.allSettled(deviceIds.map((ids, i) => worker(ids, i)));
    // One device failing (a stalled simulator) leaves the others' screens; with every device failing, the run fails.
    const failed = results.filter(r => r.status === 'rejected');
    if (failed.length === results.length) throw failed[0].reason;
    for (const f of failed) log(`  ! a device stopped: ${f.reason?.message ?? f.reason}`);
  } finally {
    await Promise.allSettled(devices.map(d => d.close()));
    await rm(runDir, { recursive: true, force: true });
  }


  const newScreens = screens.filter(s => s.isNew).map(s => s.id);
  const report = {
    app: map.app.name, platform, locale, exploredAt: new Date().toISOString(), stoppedBecause,
    mode: saved ? 'refresh' : 'fresh', newScreens,
    // Section tops the previous map had but this run did not find again: removed or changed beyond recognition.
    missing: saved ? screens.filter(s => s.known && s.depth === 0 && s.seenAt !== runStarted).map(s => s.id) : [],
    minutes: Number(((Date.now() - started) / 60_000).toFixed(1)), seconds: Math.round((Date.now() - started) / 1000), devices: deviceIds.length, handovers: steals, jevRequests, relaunches: taps.relaunch, taps, gaveUp,
    hiddenLayerChecks: { count: vision.checks, seconds: Number((vision.ms / 1000).toFixed(1)) },
    screens: screens.map(({ key, states, snapshot, pending, unreachable, judged, known, isNew, from, ...s }) => s),
    edges: [...new Map(edges.map(e => [`${e.from}|${e.via}|${e.to}`, e])).values()], external: [...new Map(external.map(e => [`${e.from}|${e.via}`, e])).values()],
    // What the next run needs to carry on from here (see `saved` above).
    map: {
      version: MAP_VERSION, maxDepth,
      screens: Object.fromEntries(screens.map(s => [s.id, { key: [...s.key], states: s.states.map(k => [...k]), judged: s.judged ?? null }])),
      links: [...links].flatMap(([from, list]) => list.map(l => ({ from, ...l }))),
      sections: Object.fromEntries([...sectionScreens].map(([name, screen]) => [name, screen.id])),
      leadsTo: Object.fromEntries(leadsTo),
    },
  };
  await writeFile(file, JSON.stringify(report, null, 2) + '\n');
  return { ...report, file };
}
