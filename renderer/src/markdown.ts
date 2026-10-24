import {
  byCrapDescending,
  overThreshold,
  unscoredShare,
  type Gate,
  type Lane,
  type LaneReport,
  type ScoredMethod,
} from './report.ts';

export const marker = (lane: Lane) => `<!-- crap-gate:${lane} -->`;

const SCALE: Record<Lane, string> = {
  frontend: 'Frontend scale: crap-typescript, McCabe complexity.',
  backend:
    'Backend scale: ReportGenerator branch-based complexity (≈2× McCabe). Not comparable with the frontend.',
};

const TOP = 10;

export interface RenderOptions {
  artifactUrl?: string;
  // The exact command the action ran, so it can be reproduced locally.
  command?: string;
}

export function render(report: LaneReport, gate: Gate, options: RenderOptions = {}): string {
  const over = byCrapDescending(overThreshold(report, gate.threshold));
  const lines: string[] = [marker(report.lane), `## CRAP · ${report.lane}`, ''];

  const unscored = report.unscored === null ? 'n/a (not detectable from Cobertura)' : `**${report.unscored}**`;
  lines.push(
    `**${report.scored.length}** scored · ${unscored} unscored · **${over.length}** over threshold ${gate.threshold} (${modeLabel(gate.mode)})`,
    '',
    `_${SCALE[report.lane]}_`,
    '',
  );

  const warning = unscoredWarning(report, gate);
  if (warning) lines.push(`> [!WARNING]`, `> ${warning}`, '');

  if (report.scored.length === 0) {
    lines.push('No scored methods.', '');
  } else {
    lines.push(`### Top ${Math.min(TOP, report.scored.length)}`, '', ...table(byCrapDescending(report.scored).slice(0, TOP)), '');
  }

  if (over.length > 0) {
    lines.push(
      '<details>',
      `<summary>${over.length} method${over.length === 1 ? '' : 's'} over ${gate.threshold}</summary>`,
      '',
      ...table(over),
      '',
      '</details>',
      '',
    );
  }

  if (options.artifactUrl) lines.push(`[Full report](${options.artifactUrl})`, '');
  if (options.command) lines.push('<details>', '<summary>Run it locally</summary>', '', '```sh', options.command, '```', '', '</details>', '');

  return lines.join('\n');
}

export function unscoredWarning(report: LaneReport, gate: Gate): string | null {
  const share = unscoredShare(report);
  if (share === null || gate.unscoredWarnRatio === undefined || share <= gate.unscoredWarnRatio) return null;
  return `${format(share)}% of methods are unscored (above ${gate.unscoredWarnRatio}%). That points at the coverage pipeline, not at risky code.`;
}

function modeLabel(mode: Gate['mode']): string {
  return mode === 'enforce' ? 'enforcing' : 'warn-only';
}

function table(methods: ScoredMethod[]): string[] {
  return [
    '| Method | Location | CC | Coverage % | CRAP |',
    '|---|---|---:|---:|---:|',
    ...methods.map((m) => `| \`${cell(m.method)}\` | \`${cell(m.location)}\` | ${m.cc} | ${format(m.coverage)} | ${format(m.crap)} |`),
  ];
}

function cell(text: string): string {
  return text.replaceAll('|', '\\|').replaceAll('`', "'");
}

function format(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}
