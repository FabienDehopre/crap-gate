import { XMLParser } from 'fast-xml-parser';
import type { LaneReport, ScoredMethod } from './report.ts';

// ReportGenerator `-reporttypes:Xml`: one file per class, root `<CoverageReport scope="Namespace.Class">`,
// with `<Metrics><Element name="…"><CrapScore>…` for every method. `Summary.xml` has scope="Summary" and no metrics.
// Element names carry no signature or line, so the location is the class.

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '',
  // LineAnalysis carries every source line; skip it.
  stopNodes: ['CoverageReport.Files'],
  isArray: (name) => name === 'Element',
  parseTagValue: false,
});

interface RgElement {
  name: string;
  CrapScore?: string;
  Cyclomaticcomplexity?: string;
  Linecoverage?: string;
}

export function parseBackendClass(xml: string): ScoredMethod[] {
  const doc = parser.parse(xml);
  const root = doc.CoverageReport;
  if (!root) throw new Error('Not a ReportGenerator Xml report: no <CoverageReport> root.');
  if (root.scope === 'Summary' || !root.Metrics) return [];

  const elements: RgElement[] = root.Metrics.Element ?? [];
  const methods: ScoredMethod[] = [];
  for (const e of elements) {
    if (!e.CrapScore || !e.Cyclomaticcomplexity) continue;
    methods.push({
      method: e.name,
      location: root.scope,
      cc: Number(e.Cyclomaticcomplexity),
      coverage: Number(e.Linecoverage ?? 0),
      crap: Number(e.CrapScore),
    });
  }
  return methods;
}

export function parseBackend(classFiles: string[]): LaneReport {
  return { lane: 'backend', scored: classFiles.flatMap(parseBackendClass), unscored: null };
}
