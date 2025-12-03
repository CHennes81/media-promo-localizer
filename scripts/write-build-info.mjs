import { writeFileSync, mkdirSync } from 'node:fs';

const nowIso = new Date().toISOString();
const commit = (process.env.GITHUB_SHA || '').slice(0, 7) || 'local-dev';
const runNumber = process.env.GITHUB_RUN_NUMBER || '0';
const tag = (process.env.GITHUB_REF_NAME || '').startsWith('v') ? process.env.GITHUB_REF_NAME : '';
const buildVersion = process.env.BUILD_VERSION || (tag || `build-${runNumber}-${commit}`);

const payload = {
  version: buildVersion,
  commit,
  buildTime: nowIso,
  source: { tag: tag || null, runNumber, sha: process.env.GITHUB_SHA || null }
};

// Write relative to the current working dir (apps/web when run via prebuild)
mkdirSync('src', { recursive: true });
writeFileSync('src/buildInfo.ts', `export const buildInfo = ${JSON.stringify(payload, null, 2)} as const;\n`);

mkdirSync('public', { recursive: true });
writeFileSync('public/version.json', JSON.stringify(payload, null, 2));

console.log('[build-info] wrote src/buildInfo.ts and public/version.json');
