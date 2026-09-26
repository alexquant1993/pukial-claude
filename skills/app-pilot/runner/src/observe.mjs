// Shared by the flow loop and explore mode: when is a screen "there", and when is a pixel check worth it.

// One labeled element is enough to know the app is past its splash screen (onboarding pages can have just two).
export const MIN_LABELED = 1;
const CONTENT_WAIT_MS = 10_000;

// Content means labeled, visible, native elements: web views (e.g. a consent SDK) and scroll bars do not count.
export function labeledCount(snapshot) {
  const nodes = snapshot?.nodes ?? [];
  const byIndex = new Map(nodes.map(n => [n.index, n]));
  const inWebView = n => { for (let p = n; p; p = byIndex.get(p.parentIndex)) if (p.type === 'WebView') return true; return false; };
  return nodes.filter(n => n.label && n.visibleToUser !== false && !/^(Application|Window)$/.test(n.type) && !/scroll bar/i.test(n.label) && !inWebView(n)).length;
}

// Web views and extra windows can sit in the tree without being drawn; only then is a pixel check worth its cost.
export const mayHaveHiddenLayers = snapshot => snapshot.nodes.some(n => n.type === 'WebView') || snapshot.nodes.filter(n => n.type === 'Window').length > 1;

// Snapshot errors while an app is starting (e.g. no foreground content yet) are retried within the same window.
export async function waitForContent(device, scope, { timeoutMs = CONTENT_WAIT_MS } = {}) {
  const started = performance.now();
  let snapshot = null, lastError = null;
  while (performance.now() - started < timeoutMs) {
    try { snapshot = await device.snapshot(scope); lastError = null; }
    catch (error) { lastError = error; }
    if (snapshot && labeledCount(snapshot) >= MIN_LABELED) break;
    await new Promise(r => setTimeout(r, 250));
  }
  if (!snapshot) throw lastError ?? new Error('No readable screen.');
  return { snapshot, ms: Math.round(performance.now() - started) };
}
