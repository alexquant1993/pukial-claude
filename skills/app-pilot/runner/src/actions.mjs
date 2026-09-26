const TAPPABLE = new Set(['tile', 'button', 'link', 'switch', 'checkbox', 'radio', 'radiobutton', 'tab', 'tabbaritem', 'menuitem', 'cell', 'segmentedcontrol', 'imagebutton']);
// textinputsemanticsobject is how Flutter text fields surface in the iOS accessibility tree.
const EDITABLE = new Set(['textfield', 'securetextfield', 'searchfield', 'textbox', 'edittext', 'textview', 'textarea', 'textinputsemanticsobject']);
const TEXT = new Set(['statictext', 'text', 'other']);
const NEVER_TAP = new Set(['statictext', 'text', 'window', 'webview', 'scrollview', 'scrollarea', 'application', 'image', 'key', 'keyboard']);
const norm = value => String(value ?? '').toLowerCase().replace(/[^a-z0-9]/g, '');
const isScrollBar = label => /scroll bar/i.test(label ?? '');

export const MAX_CHOICES = 255;
const MAX_ELEMENTS = 80;

export const TERMINAL = [
  { id: 'done_pass', kind: 'verdict', status: 'passed', description: 'Finish: PASSED. The current screen itself shows the goal is achieved and no constraint was broken.' },
  { id: 'done_fail', kind: 'verdict', status: 'failed', description: 'Finish: FAILED. The app visibly contradicts the goal (an error message, a wrong result, a broken screen) or a constraint was broken. Missing evidence alone is not a failure.' },
  { id: 'need_help', kind: 'handoff', description: 'Hand off to a reasoning agent: none of the listed actions clearly moves toward the goal, or the goal needs judgment this screen cannot settle.' },
];

const CONTROLS = [
  { id: 'wait', kind: 'wait', description: 'Wait: content is still loading or animating, then look again.' },
  { id: 'back', kind: 'back', description: 'Go back one screen.' },
  ...['down', 'up'].map(direction => ({ id: `scroll_${direction}`, kind: 'scroll', direction, description: `Scroll ${direction} to reveal more content on this screen.` })),
];

export function isUsable(snapshot) {
  return Array.isArray(snapshot?.nodes) && snapshot.nodes.length > 0 && !snapshot.truncated && snapshot.snapshotQuality?.state !== 'sparse';
}

// Other processes' elements (Android status bar, system dialogs' chrome) are not part of the app under test.
const foreign = (snapshot, n) => n.bundleId && snapshot.appBundleId && n.bundleId !== snapshot.appBundleId && /systemui/.test(n.bundleId);
// A pushed page can leave the page under it in the tree, shifted left (iOS parallax): wide elements that start left of
// the screen belong to that page, which the new one covers. Small ones (a chip scrolled half out) are still visible.
const windowRect = snapshot => snapshot.nodes.find(n => n.rect && /^(Application|Window)$/.test(n.type ?? ''))?.rect;
function behind(window, n) {
  return Boolean(window && n.rect) && n.rect.x < window.x - 2 && n.rect.width >= 0.5 * window.width && n.rect.x + n.rect.width < window.x + window.width + 2;
}
const visible = snapshot => {
  const window = windowRect(snapshot);
  return snapshot.nodes.filter(n => n.visibleToUser !== false && !foreign(snapshot, n) && !behind(window, n));
};

/**
 * The app that owns what is on screen. Android reports the session's app even when a Chrome Custom Tab or another
 * app's activity runs inside its task, so the owner is read from the nodes (system UI aside) when they carry one.
 */
export function foregroundApp(snapshot) {
  const owners = new Map();
  for (const n of snapshot?.nodes ?? []) if (n.bundleId && !/systemui/.test(n.bundleId)) owners.set(n.bundleId, (owners.get(n.bundleId) ?? 0) + 1);
  const [top] = [...owners].sort((a, b) => b[1] - a[1]);
  return top?.[0] ?? snapshot?.appBundleId ?? snapshot?.appName;
}

function pin(snapshot, ref) {
  const base = ref.startsWith('@') ? ref : `@${ref}`;
  return snapshot.refsGeneration != null && !base.includes('~s') ? `${base}~s${snapshot.refsGeneration}` : base;
}

// Android reports class names (android.widget.Button); its TextView is static text, unlike iOS UITextView.
const shortType = type => {
  const last = String(type ?? '').split('.').pop();
  if (/^android\./.test(type ?? '')) return last === 'TextView' ? 'text' : last === 'View' ? 'other' : last === 'ImageView' ? 'image' : norm(last);
  return norm(last);
};
const roleOf = node => {
  const roles = [shortType(node.type), norm(node.role)];
  return roles.find(r => EDITABLE.has(r)) || roles.find(r => TAPPABLE.has(r)) || roles[0] || 'control';
};

// Tab bars announce each tab's position ("Search\nTab 2 of 5"); some frameworks (Flutter on iOS) report an unselected tab
// as static text, so the announcement, not the element type, makes it a tab.
export const TAB_LABEL = /\b(tab \d+ of \d+|pesta[nñ]a \d+ de \d+)\b/i;
// A hittable, labeled picture that no control wraps is a tile a person would tap (Flutter on iOS reports category
// tiles as images); an image inside a button or cell is only that control's icon.
function tileRole(node, index) {
  if (TAB_LABEL.test(node.label ?? '')) return 'tab';
  if (roleOf(node) !== 'image' || !node.label || node.hittable !== true || !node.rect || node.rect.width < 44 || node.rect.height < 44) return null;
  for (let p = index.byIndex.get(node.parentIndex); p; p = index.byIndex.get(p.parentIndex)) if (TAPPABLE.has(roleOf(p))) return null;
  return 'tile';
}

// "Search\nTab 2 of 5" reads better as name "Search" with detail "tab 2 of 5".
function splitLabel(label) {
  const [name, ...rest] = String(label).split('\n').map(s => s.trim()).filter(Boolean);
  return { name: name ?? '', detail: rest.join(', ') };
}

function buildIndex(snapshot) {
  const byIndex = new Map(snapshot.nodes.map(n => [n.index, n]));
  const textsUnder = new Map();
  for (const n of visible(snapshot)) {
    if (!n.label || isScrollBar(n.label) || !TEXT.has(shortType(n.type))) continue;
    for (let p = byIndex.get(n.parentIndex); p; p = byIndex.get(p.parentIndex)) {
      const list = textsUnder.get(p.index) ?? [];
      if (list.length < 3) list.push(n.label);
      textsUnder.set(p.index, list);
    }
  }
  return { byIndex, textsUnder };
}

// The nearest ancestor that carries other text names the control's surroundings (e.g. its item card).
function context(index, node) {
  for (let p = index.byIndex.get(node.parentIndex); p; p = index.byIndex.get(p.parentIndex)) {
    const texts = (index.textsUnder.get(p.index) ?? []).filter(t => t !== node.label);
    if (texts.length) return { container: p, text: splitLabel(texts[0]).name.slice(0, 48) };
  }
  return null;
}

function position(rect, container) {
  if (!rect || !container?.rect) return '';
  const cx = (rect.x + rect.width / 2 - container.rect.x) / container.rect.width;
  const cy = (rect.y + rect.height / 2 - container.rect.y) / container.rect.height;
  const v = cy < 0.33 ? 'top' : cy > 0.66 ? 'bottom' : 'middle';
  const h = cx < 0.33 ? 'left' : cx > 0.66 ? 'right' : 'center';
  return `${v}-${h}`;
}

// Many apps render a field's label as separate text just above it; borrow that text.
function inferLabel(snapshot, field) {
  if (!field.rect) return undefined;
  const { x, width } = field.rect;
  // Gap scaled to the screen so it holds for iOS points and Android pixels alike.
  const maxGap = 0.065 * (snapshot.nodes.find(n => n.rect)?.rect.width || 430);
  const above = snapshot.nodes.filter(n => TEXT.has(shortType(n.type)) && n.label && n.rect && n.visibleToUser !== false
    && field.rect.y - (n.rect.y + n.rect.height) >= -2 && field.rect.y - (n.rect.y + n.rect.height) <= maxGap
    && n.rect.x < x + width && n.rect.x + n.rect.width > x);
  above.sort((a, b) => (b.rect.y + b.rect.height) - (a.rect.y + a.rect.height));
  return above[0];
}

const area = n => (n.rect ? n.rect.width * n.rect.height : Infinity);

function overlaps(a, b) {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
}

/**
 * Turns a snapshot into executable options, one per on-screen control.
 * `learned` maps "<context>|<position>" to names Claude assigned to unlabeled icons.
 */
export function buildActions(snapshot, inputs = {}, learned = {}, screenText = []) {
  const index = buildIndex(snapshot);
  const elements = [];
  const unlabeled = [];
  const captions = new Set();

  // The on-screen keyboard is driven through the submit/dismiss controls, never key by key.
  const inKeyboard = node => { for (let p = node; p; p = index.byIndex.get(p.parentIndex)) if (p.type === 'Keyboard') return true; return false; };
  for (const node of visible(snapshot)) {
    if (!node.ref || node.enabled === false || node.interactionBlocked || inKeyboard(node)) continue;
    const role = tileRole(node, index) ?? roleOf(node);
    if (NEVER_TAP.has(role) || isScrollBar(node.label)) continue;
    const own = node.label || node.identifier;
    if (EDITABLE.has(role) || node.editable === true) {
      // Android labels a field with its current text; that names the content, not the field.
      const ownName = node.label && node.label !== node.value ? node.label : node.identifier;
      const caption = inferLabel(snapshot, node);
      // A caption that names a field is part of the field, not a separate control.
      if (caption) captions.add(caption.index);
      const label = ownName || caption?.label.replace(/\s*\*$/, '');
      elements.push({ node, role: 'text field', label: label ?? '', value: node.value });
      if (!ownName) unlabeled.push({ ref: node.ref, role: 'text field', inferred: label ?? null, rect: node.rect });
    } else if (TAPPABLE.has(role) || (node.hittable === true && own)) {
      // Large unlabeled containers are layout wrappers, not controls.
      if (!own && (!TAPPABLE.has(role) || (node.rect && (node.rect.width > 300 || node.rect.height > 200)))) continue;
      elements.push({ node, role: role === 'other' ? 'element' : role, label: own ?? '' });
      if (!own) unlabeled.push({ ref: node.ref, role, rect: node.rect });
    }
  }

  // Nested wrappers repeat a control's label in the same place; keep the innermost one.
  const kept = [];
  for (const el of elements.filter(e => !captions.has(e.node.index)).sort((a, b) => area(a.node) - area(b.node))) {
    const twin = kept.find(k => k.label && k.label === el.label && k.node.rect && el.node.rect && overlaps(k.node.rect, el.node.rect));
    if (!twin) kept.push(el);
  }
  kept.sort((a, b) => (a.node.rect?.y ?? 0) - (b.node.rect?.y ?? 0) || (a.node.rect?.x ?? 0) - (b.node.rect?.x ?? 0));

  // Some frameworks (Flutter on iOS) report labeled groups as hittable elements with a zero-size or whole-window frame,
  // or with a frame whose centre is another control (a section header over its rows). A tap there presses something
  // else, so such groups are not offered; real controls (buttons, links, cells) always are.
  const window = snapshot.nodes.find(n => n.rect && /^(Application|Window)$/.test(n.type ?? ''))?.rect;
  const centre = r => ({ x: r.x + r.width / 2, y: r.y + r.height / 2 });
  const inside = (p, r) => p.x >= r.x && p.x <= r.x + r.width && p.y >= r.y && p.y <= r.y + r.height;
  const zeroSize = el => el.node.rect && (el.node.rect.width <= 0 || el.node.rect.height <= 0);
  const group = el => el.role === 'element' && el.node.rect && ((window && area(el.node) >= 0.9 * window.width * window.height)
    || kept.some(k => k !== el && TAPPABLE.has(k.role) && k.node.rect && area(k.node) < area(el.node) && inside(centre(el.node.rect), k.node.rect)));
  for (let i = kept.length - 1; i >= 0; i--) if (zeroSize(kept[i]) || group(kept[i])) kept.splice(i, 1);

  const counts = new Map();
  for (const el of kept) counts.set(el.label, (counts.get(el.label) ?? 0) + 1);

  const actions = [...TERMINAL, ...CONTROLS];
  // Android's keyboard lives outside the app tree, so a focused input is the signal there.
  const typing = snapshot.keyboard?.visible || snapshot.keyboard?.kind === 'visible'
    || snapshot.nodes.some(n => /^(Keyboard|Key)$/.test(n.type ?? '') || (n.focused && (n.editable === true || EDITABLE.has(roleOf(n)))));
  if (typing) {
    actions.push({ id: 'submit', kind: 'keyboard', key: 'enter', description: 'Press the keyboard Enter/Search key to submit what was typed.' },
      { id: 'dismiss_keyboard', kind: 'keyboard', key: 'dismiss', description: 'Hide the on-screen keyboard.' });
  }
  for (const el of kept.slice(0, MAX_ELEMENTS)) {
    const { name, detail } = splitLabel(el.label);
    const ctx = !el.label || counts.get(el.label) > 1 ? context(index, el.node) : null;
    const pos = position(el.node.rect, ctx?.container);
    const where = ctx ? ` in "${ctx.text}"` : '';
    const learnedName = el.label ? undefined : learned[`${ctx?.text ?? ''}|${pos}`];
    const what = el.label ? `${el.role} "${name}"${detail ? ` (${detail})` : ''}${where}`
      : learnedName ? `${el.role} "${learnedName}"${where}`
      : `unlabeled ${el.role} at the ${pos || 'screen'} of ${ctx ? `"${ctx.text}"` : 'the screen'}`;
    const base = { ref: pin(snapshot, el.node.ref), rect: el.node.rect, label: el.label, contextKey: `${ctx?.text ?? ''}|${pos}` };
    if (el.role === 'text field') {
      const current = el.value && el.value !== el.label ? ` (currently ${JSON.stringify(String(el.value).slice(0, 40))})` : '';
      const entries = Object.entries(inputs);
      if (!entries.length) actions.push({ ...base, id: `a${actions.length}`, kind: 'press', description: `Focus ${what}${current}.` });
      for (const [inputName, input] of entries) {
        const shown = input.secret ? `the secret value "${inputName}"` : JSON.stringify(input.value);
        actions.push({ ...base, id: `a${actions.length}`, kind: 'fill', text: input.value, inputName, secret: input.secret, hasText: Boolean(current),
          description: `Type ${shown} into ${what}${current}.${input.hint ? ` (${input.hint})` : ''}` });
      }
    } else {
      actions.push({ ...base, id: `a${actions.length}`, kind: 'press', description: `Tap ${what}.` });
    }
  }
  for (const line of screenText) {
    actions.push({ id: `a${actions.length}`, kind: 'press', point: { x: line.x, y: line.y }, label: line.text,
      description: `Tap the text "${line.text}" seen on screen.` });
  }
  const distinct = mergeIdentical(actions, snapshot);
  if (distinct.length > MAX_CHOICES) distinct.length = MAX_CHOICES;
  return { actions: distinct, unlabeled, truncated: kept.length > MAX_ELEMENTS };
}

// Options that read the same are indistinguishable to the model and split its probability (e.g. a
// carousel caught mid-slide shows two "Get started" buttons). Keep the one with the most visible area.
function mergeIdentical(actions, snapshot) {
  const screen = snapshot.nodes.find(n => n.rect && /^(Application|Window)$/.test(n.type ?? ''))?.rect;
  const onScreen = a => {
    if (!a.rect || !screen) return 0;
    const w = Math.max(0, Math.min(a.rect.x + a.rect.width, screen.x + screen.width) - Math.max(a.rect.x, screen.x));
    const h = Math.max(0, Math.min(a.rect.y + a.rect.height, screen.y + screen.height) - Math.max(a.rect.y, screen.y));
    return w * h;
  };
  const best = new Map();
  for (const a of actions) {
    const kept = best.get(a.description);
    if (!kept || onScreen(a) > onScreen(kept)) best.set(a.description, a);
  }
  return actions.filter(a => best.get(a.description) === a);
}

// Compact screen description for the model: visible text and controls in reading order, no refs.
export function describeScreen(snapshot, screenText = []) {
  const seen = new Set();
  const isInput = n => EDITABLE.has(roleOf(n)) || n.editable === true;
  const elements = visible(snapshot)
    .filter(n => (n.label || n.value || isInput(n)) && !isScrollBar(n.label) && !/^(Application|Window|WebView)$/.test(n.type) && !foreign(snapshot, n))
    .filter(n => { const key = `${n.label}|${n.value}|${isInput(n) ? n.index : ''}`; return !seen.has(key) && seen.add(key); })
    .sort((a, b) => (a.rect?.y ?? 0) - (b.rect?.y ?? 0) || (a.rect?.x ?? 0) - (b.rect?.x ?? 0))
    .slice(0, 120)
    .map(n => {
      // Inputs are always listed, even unlabeled ones, so the model knows a field exists.
      if (isInput(n)) {
        const caption = n.label && n.label !== n.value ? n.label : inferLabel(snapshot, n)?.label.replace(/\s*\*$/, '');
        return { role: 'text field', text: caption || undefined, value: n.value ? String(n.value).slice(0, 60) : '(empty)' };
      }
      const { name, detail } = splitLabel(n.label ?? '');
      return {
        role: roleOf(n), text: name || undefined, detail: detail || undefined,
        value: n.value && n.value !== n.label ? String(n.value).slice(0, 60) : undefined,
        selected: n.selected || undefined,
      };
    });
  for (const line of screenText) elements.push({ role: 'text seen on screen', text: line.text });
  return { app: foregroundApp(snapshot), elements };
}

// What appeared and disappeared between two screens, as short text lists for the model's history.
export function screenChanges(before, after) {
  const texts = snap => new Set(describeScreen(snap).elements.map(e => e.text).filter(Boolean));
  const a = texts(before), b = texts(after);
  return { gone: [...a].filter(t => !b.has(t)), added: [...b].filter(t => !a.has(t)) };
}

export function screenDiff(before, after) {
  const { gone, added } = screenChanges(before, after);
  const cut = list => list.slice(0, 4).map(t => `"${t.slice(0, 30)}"`).join(', ');
  return [gone.length ? `gone: ${cut(gone)}` : '', added.length ? `new: ${cut(added)}` : ''].filter(Boolean).join('; ');
}

// A pressed control that vanished (e.g. replaced by a spinner) with nothing new on screen means the app is working.
export function looksBusy(before, after, action) {
  if (action.kind !== 'press' || !action.label) return false;
  const { gone, added } = screenChanges(before, after);
  return added.length === 0 && gone.includes(splitLabel(action.label).name);
}

// Includes coarse positions so a sliding or animating screen is not mistaken for a settled one.
export function fingerprint(snapshot) {
  const grid = v => Math.round((v ?? 0) / 12);
  return JSON.stringify(visible(snapshot)
    .filter(n => (n.label || n.value) && !isScrollBar(n.label) && !foreign(snapshot, n))
    .map(n => [n.label, n.value, grid(n.rect?.x), grid(n.rect?.y)]));
}
