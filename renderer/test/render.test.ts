import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseBackend, parseBackendClass } from '../src/backend.ts';
import { parseFrontend } from '../src/frontend.ts';
import { render } from '../src/markdown.ts';
import { overThreshold } from '../src/report.ts';

const backendDir = join(import.meta.dirname, 'fixtures/backend');
const backendFiles = () => readdirSync(backendDir).map((f) => readFileSync(join(backendDir, f), 'utf8'));

const method = (overrides: object) => ({
  status: 'passed',
  crap: 2,
  cc: 1,
  cov: 0,
  covKind: 'stmt',
  method: 'f',
  src: 'src/a.ts',
  lineStart: 1,
  lineEnd: 3,
  ...overrides,
});

const frontendJson = (methods: object[]) => JSON.stringify({ status: 'passed', threshold: 30, methods });

describe('frontend', () => {
  it('counts skipped methods as unscored, never as scored', () => {
    const report = parseFrontend(
      frontendJson([method({}), method({ status: 'skipped', crap: null, cov: null, covKind: 'N/A', method: 'g' })]),
    );
    expect(report.scored).toHaveLength(1);
    expect(report.unscored).toBe(1);
    expect(report.scored[0]!.location).toBe('src/a.ts:1');
  });

  it('rejects a file that is not a crap-typescript report', () => {
    expect(() => parseFrontend('{}')).toThrow(/methods/);
  });

  it('warns when the unscored share is above the ratio, not at it', () => {
    const skipped = method({ status: 'skipped', crap: null, cov: null });
    const atTen = parseFrontend(frontendJson([...Array(9).fill(method({})), skipped]));
    const aboveTen = parseFrontend(frontendJson([...Array(8).fill(method({})), skipped, skipped]));
    const gate = { threshold: 30, mode: 'warn' as const, unscoredWarnRatio: 10 };
    expect(render(atTen, gate)).not.toContain('[!WARNING]');
    expect(render(aboveTen, gate)).toContain('20% of methods are unscored (above 10%)');
  });
});

describe('backend', () => {
  it('reads every method from per-class files and ignores Summary.xml', () => {
    const report = parseBackend(backendFiles());
    expect(report.scored).toHaveLength(8);
    expect(report.unscored).toBeNull();
    expect(report.scored.find((m) => m.method === 'Map')).toEqual({
      method: 'Map',
      location: 'FordConnectToAbrpSync.Sync.AbrpTelemetryMapper',
      cc: 40,
      coverage: 100,
      crap: 40,
    });
  });

  it('skips elements without a CRAP score', () => {
    const xml = `<CoverageReport scope="A.B"><Metrics><Element name="x"><Cyclomaticcomplexity>1</Cyclomaticcomplexity></Element></Metrics></CoverageReport>`;
    expect(parseBackendClass(xml)).toEqual([]);
  });

  it('says unscored is not detectable rather than zero', () => {
    expect(render(parseBackend(backendFiles()), { threshold: 30, mode: 'warn' })).toContain(
      'n/a (not detectable from Cobertura) unscored',
    );
  });
});

describe('threshold', () => {
  it('passes a method scoring exactly the threshold', () => {
    const report = parseBackend(backendFiles());
    expect(overThreshold(report, 40)).toEqual([]);
    expect(overThreshold(report, 39).map((m) => m.method)).toEqual(['Map']);
  });
});

describe('layout', () => {
  const report = parseBackend(backendFiles());

  it('starts with the lane marker so the sticky comment can be found', () => {
    expect(render(report, { threshold: 30, mode: 'warn' }).split('\n')[0]).toBe('<!-- crap-gate:backend -->');
  });

  it('matches the shared layout', () => {
    expect(
      render(report, { threshold: 11, mode: 'enforce' }, { artifactUrl: 'https://example.test/a', command: 'reportgenerator …' }),
    ).toMatchSnapshot();
  });

  it('caps the table at ten rows, highest CRAP first', () => {
    const many = parseFrontend(frontendJson(Array.from({ length: 12 }, (_, i) => method({ method: `m${i}`, crap: i }))));
    const md = render(many, { threshold: 30, mode: 'warn' });
    const rows = md.split('\n').filter((l) => l.startsWith('| `m'));
    expect(rows).toHaveLength(10);
    expect(rows[0]).toContain('`m11`');
    expect(md).not.toContain('<summary>');
  });
});
