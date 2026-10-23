# Whole-project coverage on the Angular browser-mode builder

PROTOTYPE, throwaway: never merged. It answers issue #12, *Whole-project coverage on the Angular
browser-mode builder*.

**Verdict: you can get whole-project coverage without leaving browser mode. This was
a configuration problem, not a pipeline limit.** On `my-netatmo-24` @ `3b88d7b` the run goes from
**22 / 506** methods scored to **503 / 506**. The 22 methods scored in the baseline keep
the same scores, and the extra run time is negligible (~8 s for the whole run).

## The recipe

```sh
pnpm exec ng test --coverage --watch=false \
  --coverage-include='src/**/*.ts' --coverage-include='libs/**/*.ts'
```

plus one line in `vitest.config.ts` (see `vitest.config.ts.patched`):

```ts
resolve: { tsconfigPaths: true },
```

Each part fixes a separate failure:

| Run | Change | Scored | N/A | Fail @30 |
|---|---|---:|---:|---:|
| `crap-0-baseline` | none | 22 | 484 | 0 |
| `crap-1-builder-include` | `--coverage-include` on the **builder** | 325 | 181 | 5 |
| `crap-2-…+tsconfigPaths` | + `resolve.tsconfigPaths` | 503 | 3 | 13 |
| `crap-3-final` | + `--include '../libs/**/*.spec.ts'` | 503 | 3 | 13 |

### 1. Use the builder's `coverageInclude`, never vitest's `coverage.include`

This explains the "forced include → 0% everywhere" result in #6. From `@angular/build`
`unit-test/runners/vitest/plugins.js`:

```js
// The pre-check uses the bundled files, so specific bundled entry points and chunks need to be included.
...(optionsCoverage.include ? { include: ['spec-*.js', 'chunk-*.js', ...optionsCoverage.include] } : {}),
```

When the include arrives through the builder option (`--coverage-include`, or `coverageInclude`
in `angular.json`), the builder adds the bundle globs in front of it. When it arrives through
`vitest.config.ts`, nothing adds those globs: the pre-check throws away the bundle that actually
ran, so only the 0% stubs for unloaded files are left. I re-ran this with the path fix
in place and got the same result: 443 files, 3039 statements, **0 covered**. That makes this an
**`@angular/build:unit-test` problem, not a `my-netatmo-24` one**. Every browser-mode Angular
repo hits it.

### 2. Unloaded files go through Vite, which needs the tsconfig path aliases

With the builder include in place, v8 has to load every file the tests never imported
and transform it through Vite. That transform cannot resolve `@app/*` or
`@spartan-ng/helm/*`, which are tsconfig `paths`. It logged 665 pre-transform errors, and 81 files
fell back to raw TypeScript, failed to parse (`import type`), and were **dropped from the
coverage map**. Dropped files show up as N/A, so this failure is silent as well.
`resolve.tsconfigPaths: true` fixes all 81. The bundled test files never needed it, because
the Angular build already resolves the aliases.

### 3. `include` is relative to `sourceRoot`, not the project root

The schema says "relative to the project root", but `--include 'libs/**/*.spec.ts'` finds
nothing. `sourceRoot` is `src`, so `libs/` must be written `../libs/**/*.spec.ts`. As a
result, the one spec in `libs/` (`prevent-default-event.spec.ts`) **never ran in
`my-netatmo-24`'s CI**. This is a repo bug and affects one test. Its 4 methods go from 0% to 100%.

## What the N/A that remain look like

Three methods: `loadComponent` / `loadChildren` arrow functions in the route tables. They are
lazy-import thunks with no statements v8 attributes to them. The tool is right to call them N/A.

## What the full picture shows

- **449 of 506 methods are `libs/ui`.** That is the spartan-ng *helm* layer, vendored
  into the repo by the spartan CLI. It is **12 of the 13 failures at 30**, 24 of 28 at 15,
  and 41 of 48 at 8. With it visible, the report is mostly about third-party code
  copied into the repo, which makes it an exclusion-policy question (#7), not a coverage one.
- Of the 46 scored `src/` methods, 40 are at 0% coverage. `src/` has one failure at 30
  (`Registration.cancel`, CC 6, untested).

## Reproduce

In a detached worktree of `my-netatmo-24` @ `3b88d7b`, with the #6 patches applied
(`tsconfig.spec.json` `"types": ["vitest/globals"]`, `registration.spec.ts` removed):

```sh
pnpm install --ignore-scripts
# add `resolve: { tsconfigPaths: true }` to vitest.config.ts
pnpm exec ng test --coverage --watch=false \
  --include='**/*.spec.ts' --include='../libs/**/*.spec.ts' \
  --coverage-include='src/**/*.ts' --coverage-include='libs/**/*.ts'
cp coverage/MyNetatmo24.Frontend/coverage-final.json coverage/coverage-final.json
crap-typescript --format json --output crapout/final.json --threshold 30   # 0.5.0
python3 summarize.py crapout/final.json
```
