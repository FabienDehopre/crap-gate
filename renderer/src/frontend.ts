import type { LaneReport } from './report.ts';

// crap-typescript `--format json`. Unscored methods are `status: "skipped"` with `crap: null`.
interface CrapTypescriptMethod {
  status: 'passed' | 'failed' | 'skipped';
  crap: number | null;
  cc: number;
  cov: number | null;
  method: string;
  src: string;
  lineStart: number;
}

interface CrapTypescriptReport {
  methods: CrapTypescriptMethod[];
}

export function parseFrontend(json: string): LaneReport {
  const report = JSON.parse(json) as CrapTypescriptReport;
  if (!Array.isArray(report.methods)) {
    throw new Error('Not a crap-typescript JSON report: no "methods" array.');
  }

  const scored = [];
  let unscored = 0;
  for (const m of report.methods) {
    if (m.crap === null || m.cov === null) {
      unscored++;
      continue;
    }
    scored.push({
      method: m.method,
      location: `${m.src}:${m.lineStart}`,
      cc: m.cc,
      coverage: m.cov,
      crap: m.crap,
    });
  }
  return { lane: 'frontend', scored, unscored };
}
