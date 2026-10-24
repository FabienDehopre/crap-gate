// Usage: node render.js <frontend|backend> <input> --threshold <n> [--mode warn|enforce]
//          [--unscored-warn-ratio <n>] [--artifact-url <url>] [--command <cmd>]
// <input> is crap-typescript's JSON report (frontend) or ReportGenerator's Xml directory (backend).
// Prints the Markdown report; under GitHub Actions also writes scored/unscored/over/unscored-warning outputs.

import { appendFileSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { parseBackend } from './backend.ts';
import { parseFrontend } from './frontend.ts';
import { render, unscoredWarning } from './markdown.ts';
import { overThreshold, type Gate, type LaneReport } from './report.ts';

const { positionals, values } = parseArgs({
  allowPositionals: true,
  options: {
    threshold: { type: 'string' },
    mode: { type: 'string', default: 'warn' },
    'unscored-warn-ratio': { type: 'string' },
    'artifact-url': { type: 'string' },
    command: { type: 'string' },
  },
});

const [lane, input] = positionals;
if ((lane !== 'frontend' && lane !== 'backend') || !input) fail('Usage: render.js <frontend|backend> <input> --threshold <n>');

const threshold = Number(values.threshold);
if (!values.threshold || !Number.isFinite(threshold)) fail(`--threshold must be a number, got "${values.threshold ?? ''}".`);
if (values.mode !== 'warn' && values.mode !== 'enforce') fail(`--mode must be "warn" or "enforce", got "${values.mode}".`);

const gate: Gate = { threshold, mode: values.mode };
if (lane === 'frontend' && values['unscored-warn-ratio'] !== undefined) {
  gate.unscoredWarnRatio = Number(values['unscored-warn-ratio']);
  if (!Number.isFinite(gate.unscoredWarnRatio)) fail(`--unscored-warn-ratio must be a number.`);
}

const report: LaneReport =
  lane === 'frontend'
    ? parseFrontend(readFileSync(input, 'utf8'))
    : parseBackend(
        readdirSync(input)
          .filter((f) => f.endsWith('.xml'))
          .map((f) => readFileSync(join(input, f), 'utf8')),
      );

process.stdout.write(render(report, gate, { artifactUrl: values['artifact-url'], command: values.command }));

if (process.env.GITHUB_OUTPUT) {
  const outputs = {
    scored: report.scored.length,
    unscored: report.unscored ?? '',
    over: overThreshold(report, threshold).length,
    'unscored-warning': unscoredWarning(report, gate) ?? '',
  };
  appendFileSync(process.env.GITHUB_OUTPUT, Object.entries(outputs).map(([k, v]) => `${k}=${v}\n`).join(''));
}

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}
