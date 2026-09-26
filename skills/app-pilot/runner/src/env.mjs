import { readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

export const CONFIG_DIR = process.env.APP_PILOT_CONFIG_DIR || join(homedir(), '.config', 'app-pilot');

// Loads KEY=VALUE pairs without overriding variables already set in the shell.
export function loadEnv(file = join(CONFIG_DIR, '.env')) {
  if (!existsSync(file)) return;
  for (const line of readFileSync(file, 'utf8').split('\n')) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    const [, key, raw] = match;
    const value = raw.replace(/^(['"])(.*)\1$/, '$2');
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

// Replaces ${NAME} with the environment value and fails loudly on a missing one.
export function interpolate(text) {
  return text.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, name) => {
    const value = process.env[name];
    if (value === undefined || value === '') throw new Error(`Missing environment variable ${name}.`);
    return value;
  });
}

export function redact(message) {
  let text = message instanceof Error ? message.message : String(message);
  for (const [key, value] of Object.entries(process.env)) {
    if (value && value.length >= 6 && /KEY|TOKEN|SECRET|PASSWORD/.test(key)) text = text.replaceAll(value, `[${key}]`);
  }
  return text;
}
