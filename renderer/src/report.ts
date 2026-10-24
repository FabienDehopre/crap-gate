// One lane's scores, as its tool reported them. Nothing here computes a CRAP score.

export type Lane = 'frontend' | 'backend';

export interface ScoredMethod {
  method: string;
  location: string;
  cc: number;
  coverage: number;
  crap: number;
}

export interface LaneReport {
  lane: Lane;
  scored: ScoredMethod[];
  // null when the lane cannot detect unscored code (backend: a project no test loads is absent from Cobertura).
  unscored: number | null;
}

export interface Gate {
  threshold: number;
  mode: 'warn' | 'enforce';
  // Frontend only: warn when the unscored share is above this percentage.
  unscoredWarnRatio?: number;
}

// A method scoring exactly the threshold passes.
export function overThreshold(report: LaneReport, threshold: number): ScoredMethod[] {
  return report.scored.filter((m) => m.crap > threshold);
}

export function unscoredShare(report: LaneReport): number | null {
  if (report.unscored === null) return null;
  const total = report.scored.length + report.unscored;
  return total === 0 ? 0 : (report.unscored / total) * 100;
}

export function byCrapDescending(methods: ScoredMethod[]): ScoredMethod[] {
  return [...methods].sort((a, b) => b.crap - a.crap);
}
