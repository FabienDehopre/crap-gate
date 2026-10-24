# crap-gate

CRAP score gating for my TypeScript (Angular + Vitest) and C# (TUnit + Microsoft Testing Platform) projects.

`CRAP(m) = CC² × (1 − cov)³ + CC` — Change Risk Anti-Patterns, combining cyclomatic complexity
with test coverage to find the methods that are both hard to understand and poorly tested.

Two composite actions, one per **lane**. Each runs as a step after your existing test step, reads the
coverage that step already produced, scores it with the lane's tool, and reports:

- the **job summary** on every run;
- one **sticky PR comment** per lane on `pull_request` runs, updated in place, posted even when clean;
- the full report as a **run artifact**.

The two lanes are never merged or compared: each has its own tool, complexity scale and threshold.

## Frontend (Angular + Vitest)

Scores with [`@barney-media/crap-typescript`](https://www.npmjs.com/package/@barney-media/crap-typescript) 2.0.0, on McCabe complexity.

```yaml
jobs:
  test:
    permissions:
      contents: read
      pull-requests: write # sticky comment
    steps:
      # … checkout, setup-node (22.13+), install …
      - run: pnpm test --coverage
      - uses: FabienDehopre/crap-gate/frontend@v1
        with:
          exclude: |
            worker/**
```

| Input | Default | |
|---|---|---|
| `working-directory` | `.` | Where crap-typescript runs. It reads `coverage/coverage-final.json` from here. |
| `coverage-file` | | An existing `coverage-final.json` elsewhere (e.g. Angular's `coverage/<project>/`), copied into place first. |
| `exclude` | | Extra globs, one per line, on top of the lane's standard set. |
| `threshold` | `30` | A method scoring **above** this is over the threshold. Exactly the threshold passes. |
| `mode` | `warn` | `warn` reports only. `enforce` fails the job when any method is over the threshold. |
| `unscored-warn-ratio` | `10` | Warn when more than this % of methods is unscored. Never fails the job. |
| `github-token` | `github.token` | Used for the PR comment. |

**Always excluded** (the lane's standard set, on top of crap-typescript's own defaults for specs, `.d.ts`,
`dist/`, generated files): `**/test-setup.ts`, `**/test-providers.ts`, `**/testing/**`, `**/*.mock.ts`,
`**/main.ts`, `**/main.server.ts`.

### Prerequisites in the repo

- **Vitest coverage with the v8 provider and the `json` reporter**, so `coverage-final.json` exists before
  crap-gate runs (`@vitest/coverage-v8`, `coverage: { provider: 'v8', reporter: ['json', …] }`).
  If the file is missing the action fails: crap-typescript would otherwise run the suite itself.
- **Angular `@angular/build:unit-test`**: set `coverageInclude` on the `angular.json` test target
  (never `coverage.include` in `vitest.config.ts`, which reports 0% everywhere), and
  `resolve: { tsconfigPaths: true }` in `vitest.config.ts` if the repo uses tsconfig path aliases.
  Without them most methods come out **unscored**.
- Node 22.13 or later on `PATH`.

## Backend (.NET + Microsoft Testing Platform)

Scores with [ReportGenerator](https://github.com/danielpalme/ReportGenerator)'s CrapScore from Cobertura.

```yaml
jobs:
  test:
    permissions:
      contents: read
      pull-requests: write # sticky comment
    steps:
      # … checkout, setup-dotnet, build …
      - run: >
          dotnet test --no-build -- --coverage --coverage-output-format cobertura
          --coverage-output coverage.xml --coverage-settings "$GITHUB_WORKSPACE/coverage.config"
      - uses: FabienDehopre/crap-gate/backend@v1
```

| Input | Default | |
|---|---|---|
| `reports` | `**/coverage.xml` | Cobertura files, as a ReportGenerator glob. Several files are merged. |
| `threshold` | `30` | Whole number, on ReportGenerator's scale. Exactly the threshold passes. |
| `mode` | `warn` | As for the frontend. |
| `github-token` | `github.token` | Used for the PR comment. |

**The backend scale is not McCabe.** ReportGenerator's complexity is branch-based, about 2× McCabe, and CRAP
squares it. 30 on the backend is stricter than 30 on the frontend, deliberately; the numbers are not comparable.

### Prerequisites in the repo

- **Exclusions live in `coverage.config`**, passed by your own `dotnet test`. Start from
  [`templates/coverage.config`](templates/coverage.config): its path patterns use `[\\/]` so they work on Linux.
- **One Cobertura file per test project.** With several test projects writing the same
  `TestResults/coverage.xml`, the last one wins and the others vanish from the report. Code that no test
  project loads is absent from Cobertura altogether, so the backend cannot count it as unscored.
- A .NET SDK on the runner (ReportGenerator runs as a .NET tool).

## Exclusions and unscored code

Exclude only code that isn't yours (generated, or vendored by a CLI), isn't production, or is entry-point
wiring, plus deliberately untested files with a comment saying why. **Never exclude to make a score go
away.** Excluded code does not appear in the report. **Unscored** code (in scope, but no coverage data) is
always counted and never fails the job.

## From warn-only to enforcing

1. Start with the default `mode: warn` and the lane's default threshold.
2. Once the over-threshold count on the default branch reaches zero, set `mode: enforce`.
3. Or ratchet: enforce with `threshold:` set to today's highest score, then lower it toward 30 as methods get fixed.

Permanent warn-only is a legitimate end state. A fully covered method scores its own complexity, so a
method with complexity above 30 fails however well it is tested; that is by design.

## Running it locally

The job summary includes the exact command each run used, under **Run it locally**. The renderer can be
run on its own too: `node renderer/dist/render.js <frontend|backend> <report> --threshold 30`.

## Versioning

Callers use `@v1`, which moves only when a `v1.x.y` release is cut. Breaking input changes go to `v2`.

## Planning

This effort was planned as a wayfinder map:
[CRAP gate for TypeScript and C# (#1)](https://github.com/FabienDehopre/crap-gate/issues/1).
Prior-art survey that seeded the map: https://claude.ai/code/artifact/cf08f084-a618-4d45-9bf4-40a5207398c2
