import { existsSync } from 'node:fs';
import { join } from 'node:path';

// Load .env from the project root before anything reads process.env. Existing environment variables win.
const file = join(process.cwd(), '.env');
if (existsSync(file)) {
  try { process.loadEnvFile(file); } catch { /* malformed .env: carry on in offline mode */ }
}

// The product used to be called "Pitch Agent": keep honouring its PITCH_* settings if a NITRO_* one is not set.
for (const k of ['MODEL', 'LEAD', 'LIGHTHOUSE']) {
  if (process.env[`NITRO_${k}`] === undefined && process.env[`PITCH_${k}`] !== undefined) process.env[`NITRO_${k}`] = process.env[`PITCH_${k}`];
}
