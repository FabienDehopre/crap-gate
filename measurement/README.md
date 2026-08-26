# CRAP distribution across the measurement subjects

Answers issue #6: *Measure the real CRAP distribution across candidate repos*.
Nothing to decide here — this is the data the threshold decision (#9) argues with.

`DISTRIBUTION.txt` is the generated report; regenerate with `python3 measurement/analyze.py`.
`raw/` holds the captured tool output so the numbers can be re-derived without re-running
any suite.

## Subjects

| Repo | Lane | Source of the numbers |
|---|---|---|
| `triple-yahtzee-score-board` @ `6576431` | frontend | reused from the [#3 bake-off](https://github.com/FabienDehopre/crap-gate/issues/3) run, as the ticket asked |
| `my-netatmo-24` (`MyNetatmo24.Frontend`) @ `3b88d7b` | frontend | fresh run, this ticket |
| `eslint-config` @ `c51801e` (plain-TS control) | frontend | fresh run, this ticket |
| `FordConnectToAbrpSync` | backend | reused Cobertura from the [#5 bake-off](https://github.com/FabienDehopre/crap-gate/issues/5) |
| `my-netatmo-24` (4 test projects merged) | backend | reused Cobertura from the #5 bake-off |

Frontend scores come straight out of crap-typescript 0.5.0. Backend scores are recomputed
from the MTP Cobertura in `analyze.py`, because ReportGenerator only renders CrapScore into
HTML. Both backend scales are reported: the one ReportGenerator shows (`cc` = the raw
`complexity` attribute) and the true-McCabe one (`cc = complexity / 2 + 1`), per the
finding in #5 that the attribute is exactly twice the branch count.

## Reproduce

```sh
# frontend, per repo — in a detached worktree, never the real checkout
pnpm install --ignore-scripts
pnpm exec ng test --coverage --watch=false      # or `vitest run --coverage`
crap-typescript --format json --output crap.json --threshold 30

# backend — the Cobertura files in raw/ came from
dotnet test --configuration Release -- --coverage --coverage-output coverage.xml \
  --coverage-output-format cobertura --coverage-settings "$PWD/coverage.config"
```

Both frontend suites needed a patch to run at all, applied only inside the worktree:

- **`my-netatmo-24`** — `tsconfig.spec.json` sets `"types": []` while the specs use bare
  `describe`/`test`/`expect`, so `ng test` fails typecheck at HEAD. Patched to
  `"types": ["vitest/globals"]`. Separately, `registration.spec.ts` hangs its `beforeEach`
  (120s timeout, not slowness — it is the WIP registration refactor at HEAD) and was
  removed for the run. 8 files / 20 tests then pass.
- **`eslint-config`** — has no coverage provider configured; `@vitest/coverage-v8` was added
  and a `coverage` block written. `pnpm build` must run first or the fixtures test fails.

## Findings

### 1. The frontend blind spot is structural, and it is the biggest result here

`my-netatmo-24` scores **22 methods out of 506**. The other **484 are N/A** — crap-typescript
reports `crap: null` because coverage never resolved for them. That is not the tool's fault:
v8 coverage under `@angular/build:unit-test` in browser mode only sees what the test bundle
actually loaded, and 10 spec files pull in just **11 files**, all under `src/` — not one of the 416 files in `libs/`.

**An N/A method passes the gate silently.** So on this repo a threshold of any value gates
4% of the code and waves the rest through.

The obvious fix — setting `coverage.include` to force whole-project instrumentation — **makes
it worse**: the report comes back with `covered: 0` on every one of 1132 statements, i.e. 0%
project-wide, turning every method into `cc² + cc`. That run is kept as
`raw/frontend-netatmo-crap-forced-include-BROKEN.json` so the failure is on record rather
than rediscovered. Whole-project frontend CRAP is **not currently obtainable** on the
Angular browser-mode pipeline.

`triple-yahtzee-score-board` does not have this problem: 77 methods, 11 N/A, and the 11 are
the `worker/**` tree the app suite legitimately does not run. Analog's per-module + jsdom
setup instruments everything the tool can see. This is the "instrument so differently"
warning from #11 turning into a concrete hole, and it belongs to the exclusion-policy
ticket (#7) and the workflow shape (#10), not to the threshold.

### 2. At 100% coverage, CRAP *is* cyclomatic complexity — which sets a floor under any threshold

`CRAP = cc² × (1 − cov)³ + cc`, so `cov = 1` collapses it to `cc`. Any threshold `T` therefore
fails every **fully tested** method whose CC exceeds `T`. The floor per subject:

| Lane / repo | Floor | Method setting it |
|---|---:|---|
| frontend / `triple-yahtzee-score-board` | **41** | `ScoringEngineService.computeScore` |
| frontend / `eslint-config` | 7 | `isInGitHooksOrLintStaged` |
| backend / `FordConnectToAbrpSync` (RG scale) | **40** | `AbrpTelemetryMapper.Map` |
| backend / `FordConnectToAbrpSync` (McCabe scale) | 21 | same method |
| backend / `my-netatmo-24` (RG scale) | 12 | `Extensions.GetApiHeaderPolicyCollection` |
| backend / `my-netatmo-24` (McCabe scale) | 7 | same method |

The single method failing yahtzee at 30 is `computeScore` — **100% covered, CC 41**, a 13-arm
scoring switch. `AbrpTelemetryMapper.Map` is the same shape: 100% covered, CC 40. These are
the best-tested methods in their repos and a threshold of 30 fails both. That is a direct
argument against crap-typescript's own advice of 6–8, which on this data is not a strict
gate but a complexity gate wearing a coverage costume.

### 3. The two lanes need different numbers, and not for the reason assumed

Fail counts at 30: yahtzee 1/77, netatmo-frontend 0/22, eslint-config 7/44, Ford 3/58 (RG
scale) or 0/58 (McCabe), netatmo-backend 3/155 (RG) or 0/155 (McCabe).

The backend RG scale is roughly the McCabe scale squared-ish in effect — the same code
scores 72 vs 30. **30 is not a shared number across lanes**; on the McCabe scale it fails
nothing at all in either backend repo, so as a backend threshold it is inert. The map's
standing note that the scales are incomparable is confirmed with numbers.

### 4. Nearly every failure is an untested method, not a badly tested one

Broken out by coverage band at threshold 30, failures are: yahtzee 1 (fully covered),
netatmo-frontend 0, eslint-config 7 (3 untested, 4 partly covered), Ford 3 (2 untested,
1 fully covered), netatmo-backend 3 (all untested).

So a warn-only gate would mostly be pointing at code with **zero** tests — `Theme.*`,
`hlm-*` UI primitives, OpenAPI transformers, `SyncWorker.NextWait`. Those are a coverage
problem CRAP happens to rank, not a "complex and half-tested" problem. The genuinely
CRAP-shaped findings — high CC *and* partial coverage — are almost all in `eslint-config`
(`namingConvention` CC 12 at 40.9%, `ensurePackages` CC 7 at 18.2%, `ngrx` CC 19 at 67.6%).

### 5. `eslint-config` is the stress test we thought we had lost

#4 recorded that the natural stress-test repo (`personal-url-shortener`) was excluded by the
eligibility rule, biasing the measurement optimistic. `eslint-config` partly repairs that:
**15.9% of its methods fail at 30**, max CRAP **506**, and its three worst are untested
config factories (`defineWorkspaceConfig` CC 22, `defineProjectConfig` CC 17). It is a
measurement subject only, never gated, so it costs nothing to keep it in the distribution —
and it is the one repo where a threshold would produce real work.

### 6. Nothing here is hopeless

The worst gated repo fails 5.2% of methods at 30 on the harsher of the two backend scales,
and the offenders are named and few. No repo needs a baseline mechanism to be gateable;
the ruled-out baseline decision holds.

## What this does not answer

Choosing the numbers. That is #9, and it now has: per-lane distributions, fail counts at
6/8/15/30/45/60, the floor that fully-covered code imposes, and the fact that the frontend
lane cannot currently see most of its own code.
