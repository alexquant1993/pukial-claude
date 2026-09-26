import { mkdir, writeFile, readFile, appendFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { buildActions, describeScreen, fingerprint, foregroundApp, isUsable, looksBusy, screenDiff } from './actions.mjs';
import { dismissControl, goBack, navBack } from './navigation.mjs';
import { redact } from './env.mjs';
import { fastScreenshot, markHidden, ocr } from './vision.mjs';
import { labeledCount, mayHaveHiddenLayers, MIN_LABELED, waitForContent as waitForContentOn } from './observe.mjs';

const HISTORY = 10;
const BUSY_WAIT_MS = 8_000;

/**
 * Acting policy: act on a clear winner, hand off on a close call.
 * Overlapping or ambiguous options show up as a small margin even when the top option is right.
 */
export const POLICY = { act: 0.7, actWithMargin: 0.45, margin: 0.25, pass: 0.6, goalMet: 0.9 };

export async function runFlow({ flow, device, jev, runDir, resume = false, note, replay = null, policy = POLICY, timeoutMs = 240_000, record = false, log = () => {} }) {
  runDir = resolve(runDir);
  await mkdir(join(runDir, 'captures'), { recursive: true });
  const statePath = join(runDir, 'state.json');
  const state = resume
    ? JSON.parse(await readFile(statePath, 'utf8'))
    : { flow: flow.id, goal: flow.goal, session: device.session, step: 0, history: [], captured: {}, unlabeled: {}, path: [], replayed: 0, usage: { requests: 0, inputTokens: 0 }, timings: [], startedAt: new Date().toISOString() };
  if (resume) {
    // The host agent acted during the handoff; record what it did so Jev's history stays truthful.
    if (note) state.history.push(`${note} (done by the reasoning agent)`);
    delete state.handoff;
  }
  const maxSteps = flow.maxSteps ?? 40;
  const deadline = Date.now() + timeoutMs;
  const save = () => writeFile(statePath, JSON.stringify(state, null, 2));
  const trace = entry => appendFile(join(runDir, 'trace.jsonl'), JSON.stringify(entry) + '\n');
  let result = { status: 'incomplete', reason: 'step_limit' };
  let cursor = 0, lastSignature = '', repeats = 0, failures = 0, captureWaits = 0, settleWaits = 0, recording = false, next = null, diverged = !replay?.length;

  const waitForContent = () => waitForContentOn(device, flow.scope);

  try {
    const [opened] = await Promise.all([resume ? null : device.open(), jev.warm()]);
    if (opened) state.device = opened;
    if (record) { await device.startRecording(join(runDir, `run-${state.step}.mp4`)); recording = true; }

    while (state.step < maxSteps) {
      if (Date.now() > deadline) { result = { status: 'incomplete', reason: 'timeout' }; break; }
      state.step++;
      const t = { step: state.step };

      const observed = next ?? await waitForContent();
      next = null;
      let { snapshot } = observed;
      t.observeMs = observed.ms;
      if (labeledCount(snapshot) < MIN_LABELED) {
        const again = await waitForContent();
        snapshot = again.snapshot; t.observeMs += again.ms;
      }
      const snapshotFile = `snapshot-${state.step}.json`;
      if (!isUsable(snapshot)) { await writeFile(join(runDir, snapshotFile), JSON.stringify(snapshot)); result = handoff('unreadable_screen'); break; }

      let screenText = null, ocrFallback = [];
      // Pixel check: hide layers that are in the tree but not drawn, and re-look if nothing visible survives.
      const see = async () => {
        for (let attempt = 0; attempt < 3; attempt++) {
          if (!mayHaveHiddenLayers(snapshot) && labeledCount(snapshot) >= MIN_LABELED) break;
          const v0 = performance.now();
          const shot = await fastScreenshot(device.target, join(runDir, `frame-${state.step}.png`)).catch(() => null);
          screenText = shot ? await ocr(shot).catch(() => null) : null;
          t.hidden = markHidden(snapshot, screenText).hidden;
          t.visionMs = (t.visionMs ?? 0) + Math.round(performance.now() - v0);
          if (labeledCount(snapshot) >= MIN_LABELED || attempt === 2) break;
          // The accessibility tree lags the pixels (e.g. Flutter still building semantics). Look again.
          const again = await waitForContent();
          snapshot = again.snapshot; t.observeMs += again.ms;
        }
        // Last resort: text the tree does not expose becomes tappable by position.
        ocrFallback = labeledCount(snapshot) < MIN_LABELED ? toScreenText(screenText, snapshot) : [];
        if (ocrFallback.length) t.ocrFallback = ocrFallback.length;
      };

      // A recorded path replays with no model call and no pixel check; the first step it cannot match hands control to Jev.
      let planned = diverged ? null : replay[cursor];
      const replaying = planned && planned.kind !== 'end';
      if (!replaying) await see();
      let built = buildActions(snapshot, flow.inputs, flow.labels, ocrFallback);
      const pending = flow.capture.filter(c => !state.captured[c.id]);
      let decision = null, plannedCaptures = [];
      if (planned?.kind === 'end') {
        // The recorded path is exhausted; its last screen's captures are known, and Jev confirms the goal.
        plannedCaptures = planned.captures ?? [];
        diverged = true;
      } else if (planned) {
        let match = findPlanned(built.actions, planned);
        // Re-sync: a step already satisfied (e.g. an intro the app skipped this time) should not end the replay.
        for (let ahead = 1; !match && ahead <= 2 && replay[cursor + ahead]?.kind && replay[cursor + ahead].kind !== 'end'; ahead++) {
          const later = findPlanned(built.actions, replay[cursor + ahead]);
          if (later) { match = later; cursor += ahead; planned = replay[cursor]; log(`   replay re-synced: skipped ${ahead} recorded step(s)`); }
        }
        if (match) {
          if (planned.verified) match.verified = true;
          decision = { choice: match.id, confidence: 1, margin: 1, goalMet: 0, latencyMs: 0, source: 'replay',
            captureProbabilities: Object.fromEntries(pending.map(c => [c.id, planned.captures?.includes(c.id) ? 1 : 0])) };
          state.replayed++;
          cursor++;
        } else {
          diverged = true;
          log(`   replay diverged at step ${state.step} (expected: ${planned.description}); Jev takes over`);
          await see();
          built = buildActions(snapshot, flow.inputs, flow.labels, ocrFallback);
        }
      }
      let { actions } = built;
      // A screen with its own back or close control offers it as a press; the generic "go back" would only split the
      // model's confidence between two ways of saying the same thing. Replayed paths keep it, to match recorded steps.
      // Native iOS names its back button after the previous page ("General"): the option says what it does.
      if (!decision && (dismissControl(snapshot)?.ref || navBack(snapshot)?.ref)) {
        const barBack = navBack(snapshot)?.ref;
        actions = actions.filter(a => a.kind !== 'back')
          .map(a => (barBack && a.ref === barBack ? { ...a, description: a.description.replace(/\.$/, ' (the back button: goes back one screen).') } : a));
      }
      for (const a of actions) if (!a.label && a.contextKey) state.unlabeled[a.contextKey] = a.description;
      await writeFile(join(runDir, snapshotFile), JSON.stringify(snapshot));
      if (!decision) {
        // The model service can be slow or down; retry once with more time, then hand off instead of crashing.
        const ask = timeoutMs => jev.step({ timeoutMs, goal: flow.goal, screen: describeScreen(snapshot, ocrFallback), history: state.history.slice(-HISTORY), actions, captures: pending });
        try { decision = await ask(); }
        catch (error) {
          try { decision = await ask(10_000); }
          catch (again) { await writeFile(join(runDir, snapshotFile), JSON.stringify(snapshot)); result = handoff('model_unavailable'); state.handoff.error = redact(again); break; }
        }
        state.usage.requests++;
        state.usage.inputTokens += decision.usage?.input_tokens ?? 0;
      }
      t.jevMs = decision.latencyMs;
      const action = actions.find(a => a.id === decision.choice);
      const capturedNow = [];

      for (const c of pending) {
        if (decision.captureProbabilities[c.id] < c.threshold && !plannedCaptures.includes(c.id)) continue;
        const path = join(runDir, 'captures', `${c.id}.png`);
        await device.screenshot(path);
        state.captured[c.id] = { path, step: state.step, probability: Number((decision.captureProbabilities[c.id] ?? 1).toFixed(3)) };
        capturedNow.push(c.id);
        log(`   capture ${c.id} (p=${decision.captureProbabilities[c.id].toFixed(2)})`);
      }

      const entry = { ...t, source: decision.source ?? 'jev', goalMet: decision.goalMet, action: action.description, kind: action.kind, confidence: decision.confidence, margin: decision.margin,
        captures: decision.captureProbabilities, candidates: actions.length, snapshot: snapshotFile };
      const line = () => `${String(state.step).padStart(2)} ${(decision.source === 'replay' ? 'replay' : action.kind).padEnd(7)} c=${decision.confidence.toFixed(2)} m=${decision.margin.toFixed(2)} | obs ${t.observeMs}${t.visionMs ? `+${t.visionMs}v` : ''} jev ${t.jevMs} act ${t.actMs ?? '-'} settle ${t.settleMs ?? '-'} ms | ${action.description}`;

      const clear = decision.confidence >= policy.act || (decision.confidence >= policy.actWithMargin && decision.margin >= policy.margin);
      // The goal_met yes/no is calibrated on its own; a choice among many options spreads probability even when right.
      const passes = decision.goalMet >= policy.goalMet || (action.id === 'done_pass' && (decision.confidence >= policy.pass || decision.goalMet >= 0.6));
      if (passes && flow.capture.every(c => state.captured[c.id])) {
        log(line().replace(/\| [^|]*$/, `| goal met (p=${decision.goalMet.toFixed(2)})`)); await trace(entry);
        state.path.push({ kind: 'end', captures: capturedNow });
        result = { status: 'passed', reason: 'goal_met', confidence: decision.goalMet };
        break;
      }
      const nearMiss = pending.filter(c => !state.captured[c.id] && (decision.captureProbabilities[c.id] ?? 0) >= 0.5);
      if (passes && nearMiss.length && captureWaits < 3) {
        // Goal reached but a screenshot is still pending: content may be loading, so look again before giving up.
        captureWaits++;
        log(line().replace(/\| [^|]*$/, `| goal met, waiting for pending captures (${captureWaits}/3)`)); await trace(entry);
        await new Promise(r => setTimeout(r, 700));
        continue;
      }
      if (passes) {
        // The goal is reached but a required screenshot was never recognised: its criterion likely needs rewording.
        log(line()); await trace(entry);
        result = handoff('missing_captures', { snapshotFile, actions, decision });
        state.handoff.missing = flow.capture.filter(c => !state.captured[c.id]).map(c => ({ id: c.id, when: c.when, lastProbability: decision.captureProbabilities[c.id] }));
        break;
      }
      if (action.kind === 'verdict') {
        log(line()); await trace(entry);
        if (action.status === 'passed') { result = handoff('uncertain_pass', { snapshotFile, actions, decision }); break; }
        result = { status: action.status, reason: action.id, confidence: decision.confidence };
        break;
      }
      if (action.kind === 'handoff' || !clear) {
        log(line()); await trace(entry);
        result = handoff(action.kind === 'handoff' ? 'jev_requested_help' : 'uncertain', { snapshotFile, actions, decision });
        break;
      }

      // Outward or irreversible actions (posting, paying, deleting, requesting, signing out) need the flow's explicit
      // allow list; otherwise the reasoning agent decides. Real accounts and real people are on the other side.
      if (action.kind === 'press' && isOutward(action.label) && !flow.allow.some(word => action.label.toLowerCase().includes(String(word).toLowerCase()))) {
        log(line()); await trace(entry);
        result = handoff('guarded_action', { snapshotFile, actions, decision });
        state.handoff.action = action.description;
        break;
      }
      // Another app on screen (e.g. a browser tab opened by a link): tapping or typing there acts outside the app under test.
      const owner = foregroundApp(snapshot);
      if (['press', 'fill'].includes(action.kind) && owner && owner !== flow.app && !SYSTEM_PROMPT.test(owner)) {
        log(line()); await trace(entry);
        result = handoff('other_app', { snapshotFile, actions, decision });
        state.handoff.action = action.description;
        state.handoff.app = owner;
        break;
      }
      // Leaving a screen that is probably a capture target before it is recognised loses the screenshot: look again first.
      if (nearMiss.length && settleWaits < 2) {
        settleWaits++;
        log(line().replace(/\| [^|]*$/, `| ${nearMiss.map(c => c.id).join(', ')} not yet recognised, looking again`)); await trace(entry);
        await new Promise(r => setTimeout(r, 700));
        continue;
      }
      settleWaits = 0;
      const before = fingerprint(snapshot);
      const signature = before + action.description;
      repeats = signature === lastSignature ? repeats + 1 : 0;
      lastSignature = signature;
      if (repeats >= 2) { log(line()); await trace(entry); result = handoff('no_progress', { snapshotFile, actions, decision }); break; }

      const a0 = performance.now();
      // A failed action is an observation, not a crash: retry once, then let the next decision see the failure.
      let actError = null, wentBack = null;
      // "Back" goes through the same ladder as explore (the app's own back or close control first, never a blind tap).
      const perform = async extra => {
        if (action.kind !== 'back') return device.act({ ...action, ...extra });
        wentBack = await goBack(device, snapshot, { platform: device.target.platform, scope: flow.scope });
        if (wentBack) entry.backVia = wentBack.rung;
      };
      try { await perform(); }
      catch (error) {
        try { await new Promise(r => setTimeout(r, 300)); await perform({ verified: true }); }
        catch (again) { actError = redact(again); }
      }
      t.actMs = Math.round(performance.now() - a0);
      if (actError) {
        failures++;
        entry.actError = actError;
        log(`   action failed: ${actError}`);
        if (failures >= 2) { log(line()); await trace(entry); result = handoff('action_failed', { snapshotFile, actions, decision }); break; }
      } else failures = 0;
      // Code, not the model, owns whether the action changed anything; the settled capture is the next observation.
      next = wentBack ?? await device.observeAfter(before, { scope: flow.scope });
      // Fast typing can lose focus to another layer; code checks the text landed and falls back to a verified fill.
      if (action.kind === 'fill' && !action.secret && !textLanded(next.snapshot, action.text)) {
        const field = buildActions(next.snapshot, flow.inputs).actions
          .find(a => a.kind === 'fill' && a.inputName === action.inputName && a.rect && action.rect && Math.abs(a.rect.y - action.rect.y) < 12);
        if (field) {
          const r0 = performance.now();
          await device.act({ ...field, hasText: true });
          next = await device.observeAfter(fingerprint(next.snapshot), { scope: flow.scope });
          t.actMs += Math.round(performance.now() - r0);
          t.refilled = true;
          action.verified = true;
          // Once fast typing has failed in this app, it is not worth trying again this run.
          device.verifiedFills = true;
          log('   typed text did not land; refilled with verification');
        }
      }
      // Busy after a press is a fact code can see; poll for the result instead of spending model calls on it.
      if (!actError && looksBusy(snapshot, next.snapshot, action)) {
        const b0 = performance.now();
        const busyPrint = fingerprint(next.snapshot);
        while (performance.now() - b0 < BUSY_WAIT_MS) {
          await new Promise(r => setTimeout(r, 350));
          const probe = await device.snapshot(flow.scope).catch(() => null);
          if (probe && fingerprint(probe) !== busyPrint) { next = await device.observeAfter(busyPrint, { scope: flow.scope }); break; }
        }
        t.busyMs = Math.round(performance.now() - b0);
        log(`   app busy after "${action.label.split('\n')[0]}"; waited ${t.busyMs}ms for the result`);
      }
      t.settleMs = next.ms;
      Object.assign(entry, { actMs: t.actMs, settleMs: t.settleMs, changed: next.changed });
      log(line()); await trace(entry);
      state.timings.push(t);
      const diff = next.changed ? screenDiff(snapshot, next.snapshot) : '';
      state.history.push(`${action.description} -> ${actError ? `failed (${actError.slice(0, 80)})` : next.changed ? `changed (${diff || 'layout only'})` : 'no visible change'}`);
      if (actError) diverged = true;
      state.path.push({ kind: action.kind, description: action.description, label: action.label, inputName: action.inputName, direction: action.direction, key: action.key, verified: action.verified, captures: capturedNow });
      await save();
    }
  } catch (error) {
    result = { status: 'error', reason: redact(error) };
  } finally {
    if (recording) await device.stopRecording().catch(() => {});
    // A handoff keeps the session open so the host agent can act in it and resume.
    if (result.status !== 'needs_help') await device.close().catch(() => {});
  }

  const missing = flow.capture.filter(c => !state.captured[c.id]).map(c => c.id);
  Object.assign(state, { result, missingCaptures: missing, finishedAt: new Date().toISOString(),
    estimatedCostUsd: state.usage.inputTokens / 1e6 * Number(process.env.JEV_INPUT_USD_PER_MILLION ?? 0.042) });
  await save();
  return state;

  function handoff(reason, detail = {}) {
    const top = detail.decision
      ? Object.entries(detail.decision.probabilities ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 5)
        .map(([id, p]) => ({ p: Number(p.toFixed(3)), ...pick(detail.actions.find(a => a.id === id)) }))
      : [];
    state.handoff = { reason, session: device.session, snapshot: detail.snapshotFile, topCandidates: top };
    return { status: 'needs_help', reason };
  }
}

// Only an input counts: the same word elsewhere (e.g. a "recent searches" chip) is not proof the field received it.
const INPUT_TYPES = /^(TextField|SecureTextField|SearchField|TextView|EditText)$/;
const textLanded = (snapshot, text) => snapshot.nodes.some(n => (INPUT_TYPES.test(n.type ?? '') || /TextInput/.test(n.role ?? '') || n.editable === true)
  && (String(n.value ?? '').includes(text) || String(n.label ?? '').includes(text)));

const OUTWARD = /\b(post|publish|send|pay|buy|purchase|checkout|place order|delete|remove|report|block|request|subscribe|donate|join|follow|unfollow|leave|accept|archive|clear|invite|share|log ?out|sign ?out|unirse|unirme|seguir|dejar de seguir|salir|aceptar|archivar|invitar|compartir|enviar|publicar|pagar|comprar|eliminar|borrar|reportar|bloquear|solicitar|suscribir|donar|cerrar sesi[oó]n)\b/i;
// Permission dialogs belong to the system, not another app; flows answer them as their goals say.
const SYSTEM_PROMPT = /permissioncontroller|packageinstaller|springboard/i;
const isOutward = label => OUTWARD.test(String(label ?? '').split('\n')[0]);

// OCR lines in screenshot pixels, converted to the tree's point coordinates.
function toScreenText(read, snapshot) {
  if (!read?.lines?.length) return [];
  const root = snapshot.nodes.find(n => n.type === 'Application')?.rect;
  const scale = root?.width ? read.size[0] / root.width : 1;
  return read.lines
    .filter(l => l.confidence >= 0.5 && /[a-z0-9]{2,}/i.test(l.text) && !/^\d{1,2}:\d{2}$/.test(l.text.trim()))
    .map(l => ({ text: l.text.trim(), x: Math.round((l.rect[0] + l.rect[2] / 2) / scale), y: Math.round((l.rect[1] + l.rect[3] / 2) / scale) }));
}

// Same description first; the same control by label and kind survives small wording or position changes.
function findPlanned(actions, planned) {
  if (!planned.kind || planned.kind === 'end') return null;
  return actions.find(a => a.description === planned.description)
    ?? actions.find(a => a.kind === planned.kind && a.label && a.label === planned.label && a.inputName === planned.inputName)
    ?? (['back', 'scroll', 'wait', 'keyboard'].includes(planned.kind) ? actions.find(a => a.kind === planned.kind && a.direction === planned.direction && a.key === planned.key) : null);
}

function pick(action) {
  if (!action) return {};
  const { id, kind, ref, description } = action;
  return { id, kind, ref, description };
}
