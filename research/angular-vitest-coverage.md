# How do Angular's and Analog's Vitest builders configure coverage?

Research for [issue #11](https://github.com/FabienDehopre/crap-gate/issues/11). Documentation and source reading only — no packages installed, no test suites run, nothing modified in the two reference repos. Researched 2026-08-26.

Each claim is tagged **[documented]** (stated in first-party docs), **[source]** (read off the shipped source of the installed package, or off a committed artefact in the user's own repos), or **[unverified]** (reasoned from the above, not confirmed by executing anything).

---

## Short answer

**Yes for both. Istanbul-format `coverage-final.json` is reachable from both builders, and neither needs an escape hatch.**

- **`@angular/build:unit-test`** accepts a user `vitest.config.ts` via the `runnerConfig` option. `test.coverage.provider` and `test.coverage.reportsDirectory` from that file are read by the builder and win over its own defaults. The builder has no `coverageProvider` option of its own, so the config file is the *only* way to pin the provider — but it works.
- **`@analogjs/vitest-angular:test`** is a ~60-line wrapper around `startVitest`. It touches exactly one coverage field (`enabled`). Everything else — provider, reporter, reportsDirectory — comes straight from the Vite/Vitest config file, unmediated.

**But the ticket's framing, and the map's standing "Istanbul, not v8" decision, rest on a premise that does not hold on Vitest 4:**

> **[documented]** "Since v3.2.0 Vitest has used AST based coverage remapping for V8 coverage, **which produces identical coverage reports to Istanbul**."
> — [Vitest — Coverage](https://vitest.dev/guide/coverage.html)

**[source]** And structurally: `@vitest/coverage-v8@4.1.11` depends on `ast-v8-to-istanbul`, `istanbul-lib-coverage`, `istanbul-lib-report` and `istanbul-reports`, and its `dist/provider.js` calls `createCoverageMap` and renders through `istanbul-reports`. The `json` reporter is `istanbul-reports`' own, and writes `coverage-final.json` in Istanbul's `statementMap`/`fnMap`/`branchMap` shape *regardless of provider*.

**[source]** This is already true in practice today: `my-netatmo-24`'s CI consumes `MyNetatmo24.Frontend/coverage/MyNetatmo24.Frontend/coverage-final.json` (`.github/workflows/ci.yml`, lines 94-95) with `provider: 'v8'` configured. **The frontend lane is already being handed an Istanbul-format JSON file.**

So the real question is not "can we get the format" (yes, either way) but "do we want the extra fidelity of true instrumentation". See [Comparability](#5-comparability-between-the-two-repos).

---

## Versions actually installed

Both repos use a pnpm catalog; these are the resolved versions.

| | `my-netatmo-24/MyNetatmo24.Frontend` | `triple-yahtzee-score-board` |
| --- | --- | --- |
| Test builder | `@angular/build:unit-test` | `@analogjs/vitest-angular:test` |
| `@angular/build` | **22.1.4** | 22.1.4 (present, not used for `test`) |
| `@angular/core` | 22.1.2 | 22.1.2 |
| `@analogjs/vitest-angular` | — | **2.7.0** |
| `@analogjs/vite-plugin-angular` | — | 2.7.0 |
| `vitest` | **4.1.11** | **4.1.10** |
| `vite` | (via `@angular/build`) | 8.2.1 |
| Coverage provider pkg | `@vitest/coverage-v8` 4.1.11 | **none installed** |
| Test environment | **browser mode**, Playwright + chromium, headless | jsdom |

Sources: `pnpm-workspace.yaml` in each repo (catalog blocks), and the resolved directory names under `node_modules/.pnpm/`.

**Every claim below about `@angular/build:unit-test` is read off version 22.1.4 specifically.** This builder is new and moving fast; the private helpers quoted here (`generateCoverageOption`, `determineCoverageProvider`) are internal and can change between minors without notice.

---

## 1. `@angular/build:unit-test`

### Does it accept a user `vitest.config.ts`? — Yes, opt-in via `runnerConfig`

**[documented]** The `runnerConfig` option:

> "Specifies the configuration file for the selected test runner. If a string is provided, it will be used as the path to the configuration file. If `true`, the builder will search for a default configuration file (e.g., `vitest-base.config.ts` or `karma.conf.js`). If `false`, no external configuration file will be used. For Vitest, this enables advanced options and the use of custom plugins. Please note that while the file is loaded, the Angular team does not provide direct support for its specific contents or any third-party plugins used within it."
>
> Default: `false`.

Source: `@angular/build@22.1.4`, `src/builders/unit-test/schema.json`; mirrored at [angular.dev/guide/testing](https://angular.dev/guide/testing).

**[source]** Note the trap in `runnerConfig: true`: the auto-search list is `vitest-base.config.{ts,mts,cts,js,mjs,cjs}` — **not** `vitest.config.ts` (`src/builders/unit-test/runners/vitest/configuration.js`, `POTENTIAL_CONFIGS`). `my-netatmo-24` passes the explicit string `"runnerConfig": "vitest.config.ts"`, which is the reliable form. Paths resolve against the workspace root (`options.js`: `path.resolve(workspaceRoot, runnerConfig)`).

**[source]** A second, undocumented consequence of setting `runnerConfig`: the builder *skips all its dependency pre-checks except `vitest` itself* (`runners/vitest/index.js`, `validateDependencies` returns early). With a runner config present you get Vitest's own error messages instead of the builder's friendlier ones.

### What survives, what the builder overrides

**[documented]** The public statement is thin:

> "The CLI will also override certain properties (`test.projects`, `test.include`) to ensure proper integration." — [angular.dev/guide/testing](https://angular.dev/guide/testing)

**[source]** The full picture, from `src/builders/unit-test/runners/vitest/plugins.js` (`createVitestConfigPlugin`, a Vite `config()` hook). Deleted from the user's config, with a warning logged:

| User `test.*` key | Fate |
| --- | --- |
| `projects` | **deleted** — "the Angular CLI Test system will construct its own project configuration" |
| `include` | **deleted** — "the Angular CLI Test system will manage test file discovery" |
| `watch` | **deleted** if it disagrees with the builder's `--watch` |
| `reporters` | **deleted** *only if* `reporters` was set in `angular.json` |
| `coverage.reporter` | **deleted** *only if* `coverageReporters` was set in `angular.json` |
| `exclude` | kept, but warned: evaluated after compile, prefer the builder's `exclude` |
| `plugins` | user plugins are extracted and re-injected into the constructed project; the top-level `plugins` array is deleted |

Everything else (`setupFiles`, `globals`, `isolate`, `sequence`, `browser`, `environment`, `resolve`, `optimizeDeps`, …) is merged: `mergeConfig(projectDefaults, {test: userConfig})` then `mergeConfig(..., projectOverrides)`, and lands inside the single generated `test.projects[0]`.

**[source]** The builder also forces the test build: `sourceMap: { scripts: true, vendor: false, styles: false }`, `optimization: false`, `externalPackages: true`, and bundles every spec into `spec-*.js` + `chunk-*.js` entry points via esbuild before Vitest ever sees them (`runners/vitest/build-options.js`). Coverage is therefore always collected on a **bundle** and remapped back through source maps — for both providers.

### Coverage options the builder owns

**[documented]** From `schema.json` / [angular.dev/guide/testing/code-coverage](https://angular.dev/guide/testing/code-coverage): `coverage` (boolean), `coverageInclude`, `coverageExclude`, `coverageReporters`, `coverageThresholds`, `coverageWatermarks`.

`coverageReporters` is a closed enum: `html`, `lcov`, `lcovonly`, `text`, `text-summary`, `cobertura`, `json`, `json-summary`. **`json` is in it** — so the Istanbul JSON reporter is selectable from `angular.json` alone.

**[documented]** `coverage`: "Enables coverage reporting for tests. If not specified, the coverage configuration from a runner configuration file will be used if present. Otherwise, coverage is disabled by default."

**There is no `coverageProvider` option.** Confirmed absent from `schema.json`, and [angular.dev/guide/testing/code-coverage](https://angular.dev/guide/testing/code-coverage) never mentions Istanbul at all — it only tells you to `npm install --save-dev @vitest/coverage-v8`. **The docs are silent on provider selection.**

### Can the provider be set to `istanbul`? — Yes, from the runner config

**[source]** `plugins.js`, `determineCoverageProvider()`:

```js
let determinedProvider = testConfig?.coverage?.provider;
if (!determinedProvider && (optionsCoverageEnabled || testConfig?.coverage?.enabled)) {
    // ... auto-detection ...
}
return determinedProvider;
```

**The user's `test.coverage.provider` is read first and never overridden.** Setting `provider: 'istanbul'` in the `runnerConfig` file is honoured verbatim.

**[source]** The auto-detection fallback is worth knowing for `my-netatmo-24` specifically, because it runs browser mode:

1. any non-Chromium browser configured → `istanbul` (forced);
2. otherwise, if `@vitest/coverage-istanbul` resolves **and** (browsers are configured **or** `@vitest/coverage-v8` is absent) → `istanbul`;
3. otherwise → `v8`.

with the comment: *"Favor istanbul when browser testing is enabled (to avoid slow CDP V8 HTTP sourcemap remapping) or when only istanbul is installed."*

**[unverified, but a direct reading]** Because `my-netatmo-24` configures a browser, simply **installing `@vitest/coverage-istanbul` would flip it to Istanbul automatically** — except that its `vitest.config.ts` pins `provider: 'v8'` explicitly, and the explicit value wins. Removing that one line would also do it. Angular itself considers Istanbul the better fit for browser-mode coverage.

**[source]** Also: `validateBrowserCoverage()` returns immediately when the provider is `istanbul`; V8 in browser mode is hard-restricted to `chrome`/`chromium`/`edge`. Istanbul is the strictly safer choice under browser mode.

### What the builder does to the coverage block

**[source]** `generateCoverageOption()` builds the *root* `test.coverage` object:

```js
return {
    provider,
    excludeAfterRemap: true,
    reportsDirectory: configCoverage?.reportsDirectory ?? toPosixPath(path.join('coverage', projectName)),
    ...(optionsCoverage.enabled !== undefined ? { enabled: optionsCoverage.enabled } : {}),
    ...(optionsCoverage.include ? { include: ['spec-*.js', 'chunk-*.js', ...optionsCoverage.include] } : {}),
    thresholds: mergeCoverageObjects(configCoverage?.thresholds, optionsCoverage.thresholds),
    watermarks: mergeCoverageObjects(configCoverage?.watermarks, optionsCoverage.watermarks),
    ...(optionsCoverage.exclude ? { exclude: [...] } : {}),
    ...(optionsCoverage.reporters ? { reporter: optionsCoverage.reporters } : {}),
};
```

Reading:

- **`reportsDirectory`** — user config wins; otherwise `coverage/<projectName>`. **Not** Vitest's documented `./coverage` default. For `my-netatmo-24` that is `MyNetatmo24.Frontend/coverage/MyNetatmo24.Frontend/`, which is exactly what its CI reads back.
- **`reporter`** — the builder only sets it when `angular.json` did. Otherwise the user config's `coverage.reporter` reaches Vitest through the Vite config merge (which is why the code bothers to `delete testConfig.coverage.reporter` in the conflicting case — Vite's `mergeConfig` concatenates arrays, so leaving both would union them).
- **`excludeAfterRemap: true`** is forced, unconditionally. Not overridable.
- **`coverage.include` is a trap.** If you set it in the *vitest config* rather than as `coverageInclude` in `angular.json`, you lose the `'spec-*.js', 'chunk-*.js'` prefix that the builder's own comment says is needed for Vitest's pre-remap check against the bundled files. **[unverified]** — reasoned from the code comment, not measured. Use `coverageInclude`.
- `provider`, `thresholds`, `watermarks`, `reportsDirectory` are the only user-config coverage keys the builder reads deliberately. Others survive only incidentally, via Vite's merge of the plugin's returned partial config.

### 3a. Exact invocation for `coverage/coverage-final.json`

The `json` reporter is `istanbul-reports`' JSON reporter; **[source]** `istanbul-reports/lib/json/index.js` line 12: `this.file = opts.file || 'coverage-final.json';`.

`vitest.config.ts` (the `runnerConfig`):

```ts
export default defineConfig({
  test: {
    // ... existing browser/setup config ...
    coverage: {
      provider: 'istanbul',      // the only place this can be set
      reportsDirectory: 'coverage',  // else it lands in coverage/<projectName>/
    },
  },
});
```

`angular.json`:

```json
"test": {
  "builder": "@angular/build:unit-test",
  "options": {
    "providersFile": "src/test-providers.ts",
    "runnerConfig": "vitest.config.ts",
    "coverageReporters": ["json", "json-summary", "text-summary"]
  }
}
```

Run:

```bash
ng test --coverage --watch=false
```

Lands at **`<workspaceRoot>/coverage/coverage-final.json`** — i.e. `MyNetatmo24.Frontend/coverage/coverage-final.json`, because `reportsDirectory` resolves against Vitest's `root`, which the executor sets to `workspaceRoot` (`runners/vitest/executor.js`: `root: workspaceRoot`).

**Minimal-change alternative:** change nothing but `provider: 'v8'` → `'istanbul'` in the existing `vitest.config.ts`, and read the file from the existing path `MyNetatmo24.Frontend/coverage/MyNetatmo24.Frontend/coverage-final.json`. The repo's CI already publishes that path as an artifact; the CRAP step could reuse it rather than moving it. **[unverified]** — untested, but it is the path the repo's own CI already asserts.

---

## 2. `@analogjs/vitest-angular:test`

### Which config does the Angular app actually run against?

**The root `vite.config.ts`.** Not `worker/vitest.config.ts`.

**[source]** `@analogjs/vitest-angular@2.7.0`, `src/lib/builders/test/vitest.impl.js`, in full essence:

```js
const projectConfig = await context.getProjectMetadata(context.target);
const { coverageArgs, ...extraArgs } = await getExtraArgs(options);
const config = {
    root: `${projectConfig['root'] || '.'}`,
    watch, ui,
    config: options.configFile,
    coverage: { enabled: coverageEnabled, ...coverageArgs },
    update,
    ...extraArgs,
};
const viteOverrides = { test: { watch } };
const server = await startVitest('test', options.testFiles ?? [], config, viteOverrides);
```

`triple-yahtzee-score-board`'s `angular.json` sets `"root": ""` for the project and passes **no options at all** to the builder. So `root` falls through to `'.'` (the workspace root) and `config` is `undefined`, which hands file discovery to Vitest.

**[documented]** Vitest's resolution order: `vitest.config.ts` takes priority and overrides `vite.config.ts`; `vite.config.ts` is the fallback ([vitest.dev/config](https://vitest.dev/config/)). There is no `vitest.config.*` at the workspace root, so **`vite.config.ts` is what runs** — the one with `plugins: [angular()]`, `environment: 'jsdom'`, `include: ['src/**/*.spec.ts']`.

`worker/vitest.config.ts` belongs to the `worker` pnpm workspace package and is run separately: `.github/workflows/ci.yml` line 74, `pnpm --filter ./worker/ run test --watch=false`. It never sees Angular code.

### What the builder overrides — almost nothing

**[source]** The only coverage field the builder writes is `coverage.enabled` (from the `--coverage` flag), plus `root`, `watch`, `ui`, `update`, `config`, and `test.watch` as a Vite override. `provider`, `reporter`, `reportsDirectory`, `include`, `exclude`, `thresholds` are **entirely the config file's business.** No merging, no deletion, no warnings. It is a pass-through.

Corollary: **there is no `reporters` / `include` / `projects` restriction of the Angular-builder kind here.** The `test.include` in `vite.config.ts` is authoritative.

### Two dead options in the schema

**[source]** `src/lib/builders/test/schema.json` declares `reportsDirectory` ("Directory to write coverage report to.") and `mode` ("Mode for Vite."). `getExtraArgs()` collects *only* option keys **absent** from the schema; the impl then uses `configFile`, `testFiles`, `watch`, `ui`, `coverage`, `update` and spreads the rest. `reportsDirectory` and `mode` are in the schema, so they are excluded from `extraArgs` **and never read** — they are accepted and silently discarded. Do not use `"reportsDirectory"` in `angular.json` here; set `coverage.reportsDirectory` in `vite.config.ts` instead.

### An undocumented pass-through worth knowing

**[source]** Because `getExtraArgs()` forwards every *unknown* option key into the Vitest CLI-options object, and destructures `coverageArgs` into the coverage block, arbitrary Vitest coverage options can be set from `angular.json` without touching `vite.config.ts`:

```json
"test": {
  "builder": "@analogjs/vitest-angular:test",
  "options": {
    "coverage": true,
    "coverageArgs": {
      "provider": "istanbul",
      "reporter": ["json", "json-summary", "text-summary"],
      "reportsDirectory": "coverage"
    }
  }
}
```

**[unverified]** — read straight off the impl, but not executed. The risk is Angular's builder-schema validation rejecting or stripping unknown properties; the schema has no `additionalProperties: false`, and the mechanism exists precisely to "support passing extra args to Vitest CLI" (the code's own comment), so it should pass. If it does not, the `vite.config.ts` route below is the documented-shaped one.

### 3b. Exact invocation for `coverage/coverage-final.json`

`vite.config.ts`:

```ts
export default defineConfig(({ mode }) => ({
  plugins: [angular()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['dotenv/config', 'src/test-setup.ts'],
    include: ['src/**/*.spec.ts'],
    reporters: ['default'],
    coverage: {
      provider: 'istanbul',
      reporter: ['json', 'json-summary', 'text-summary'],
      // reportsDirectory defaults to './coverage' — already what we want
    },
  },
  // ...
}));
```

Run:

```bash
ng test --coverage --watch=false
```

**[documented]** `coverage.reportsDirectory` defaults to `./coverage` ([Vitest config reference](https://vitest.dev/config/#coverage-reportsdirectory)), resolved against `root` — here `'.'`, the repo root. Result: **`<repo root>/coverage/coverage-final.json`**.

**Caveat on `--watch=false`:** the repo's `test:ci` script is `ng test --configuration ci`, but `angular.json`'s `test` target declares **no `configurations` block at all** — that script cannot work as written. Its CI uses `pnpm run test --watch=false` instead. `--watch` *is* a schema option on this builder, so it is passed correctly. **[source]**, from `angular.json` + `.github/workflows/ci.yml`.

---

## 4. Does `@vitest/coverage-istanbul` need installing? — Yes, in both, and the version is pinned exactly

**[documented]** "To use Istanbul, install `@vitest/coverage-istanbul`" — [Vitest — Coverage](https://vitest.dev/guide/coverage.html). V8 is the default provider and needs `@vitest/coverage-v8`.

**[source]** `@angular/build@22.1.4` enforces this itself when no `runnerConfig` is set: `checkAny(['@vitest/coverage-v8', '@vitest/coverage-istanbul'], 'Code coverage requires either "@vitest/coverage-v8" or "@vitest/coverage-istanbul" to be installed.')` (`runners/vitest/index.js`). With a `runnerConfig` present that check is skipped and the failure comes from Vitest instead.

### Version constraints

**[source]** `@vitest/coverage-istanbul` declares `"peerDependencies": { "vitest": "4.1.11" }` — an **exact pin, not a range**. Verified with `npm view @vitest/coverage-istanbul@4.1.11 peerDependencies`. Every 4.x patch pins its exact matching `vitest`.

Therefore:

| Repo | Installed `vitest` | Required package |
| --- | --- | --- |
| `MyNetatmo24.Frontend` | 4.1.11 | `@vitest/coverage-istanbul@4.1.11` |
| `triple-yahtzee-score-board` | 4.1.10 | `@vitest/coverage-istanbul@4.1.10` |

Both repos run pnpm with `catalogMode: strict`, so the version must be added to the catalog (`vitest` catalog group in `my-netatmo-24`, the flat `catalog` in `triple-yahtzee-score-board`) and kept in lockstep with `vitest` on every Renovate bump. That lockstep is the real ongoing cost — a `vitest` bump that misses `@vitest/coverage-istanbul` becomes a peer-dependency failure, not a warning.

**No constraint from Angular or Analog beyond that.** `@angular/build@22.1.4` peer-depends on `vitest: "^4.0.8"` (optional). `@analogjs/vitest-angular@2.7.0` peer-depends on `vitest: "^1.3.1 || ^2.0.0 || ^3.0.0 || ^4.0.0"`. Neither mentions any coverage package as a peer. `@angular/build` does carry an optional peer on `istanbul-lib-instrument@^6.0.0`, but **[source]** that is for the *Karma* builder's `add-code-coverage` Babel plugin (`src/tools/babel/plugins/add-code-coverage.js`, used from `src/builders/karma/application_builder.js`) — it is unrelated to the Vitest path.

**`triple-yahtzee-score-board` has no coverage provider installed at all today**, so it needs an addition either way; there is no incumbent to migrate from.

---

## 5. Comparability between the two repos

**Not comparable out of the box, and the provider is the smaller of the two reasons.**

**[documented]** Provider-level, the difference has largely closed: *"Since v3.2.0 Vitest has used AST based coverage remapping for V8 coverage, which produces identical coverage reports to Istanbul"* ([Vitest — Coverage](https://vitest.dev/guide/coverage.html)). Both providers render through `istanbul-reports` into the same `coverage-final.json` schema. **[unverified]** how literally "identical" holds in practice for Angular's bundled output — the claim is Vitest's, unqualified, and I did not measure it.

The differences that actually bite are structural, and they sit **upstream of the coverage provider**:

| | `MyNetatmo24.Frontend` (`@angular/build:unit-test`) | `triple-yahtzee-score-board` (Analog) |
| --- | --- | --- |
| What gets instrumented | esbuild **bundle** (`spec-*.js`, `chunk-*.js`), remapped to `.ts` via source maps | per-module Vite transform of near-original TS |
| Optimisation | `optimization: false`, but esbuild still bundles and may tree-shake | none |
| Execution environment | **browser** (Playwright chromium) | **jsdom** |
| `excludeAfterRemap` | forced `true` | Vitest default (`false`) |
| Default `coverage.exclude` | Vitest defaults, unless `coverageExclude` is set (which then *appends* the defaults) | Vitest defaults |

**[unverified]** The consequences I would expect but did not measure: statement and branch counts drawn from a bundled-then-remapped artefact will not line up one-for-one with those from an untransformed module graph, especially around Angular decorators, class field initialisers and template-generated code; and `excludeAfterRemap` differing changes which files appear in the report at all. Since CRAP squares complexity, small differences in what counts as a covered branch move the score more than they move the coverage percentage.

**Practical recommendation for the frontend lane:** treat the two repos as two independent distributions when calibrating the warn-only threshold, exactly as the map already treats frontend and backend. If they must be compared, the cheapest way to level the footing is to pin **both** to `provider: 'istanbul'` and an identical `coverageExclude`, and accept that the bundling difference remains. **[unverified]** — this is judgement, not a measured result.

Note also that this is a *coverage*-side concern only. Whichever TS CRAP tool is chosen computes complexity from the TypeScript source itself, not from `coverage-final.json`; that half of the score will be comparable. It is the `(1 − cov)³` term that differs.

---

## 6. Escape hatches — not needed, but here is what exists

**Analog:** running Vitest directly is trivially available. `vite.config.ts` is an ordinary Vitest config; `pnpm vitest run --coverage --coverage.provider=istanbul --coverage.reporter=json` bypasses the builder completely. **[unverified]** the only builder side-effects are `process.env.TEST='true'` and `process.env.VITEST='true'` — Vitest sets `VITEST` itself; whether anything in `src/test-setup.ts` depends on `TEST` was not checked.

**Angular:** running Vitest directly is **not possible**, and this is worth stating plainly. The builder does not generate a config file on disk. It calls `startVitest()` in-process with an in-memory config, injecting virtual modules (`angular:test-bed-init`, `angular:vitest-mock-patch`) and plugins that serve the pre-built esbuild output from memory (`runners/vitest/plugins.js`, `createVitestPlugins`). A bare `vitest run` against `vitest.config.ts` would find no test files (the builder deletes `test.include` and supplies bundle entry points) and no TestBed initialisation. **[source]**

**Post-processing conversion:** unnecessary. No lcov→Istanbul or cobertura→Istanbul step is required from either builder.

---

## Secondary: multiple Vitest projects in one repo

Falling out for free, relevant to the open `OpenGenerativeUI` fog on the map:

- **[source]** `@angular/build:unit-test` **actively forbids** `test.projects` in the runner config: it deletes the key and warns *"The `test.projects` option in the Vitest configuration file is not supported. The Angular CLI Test system will construct its own project configuration."* It builds exactly one project, named after the Angular project. A monorepo under this builder therefore fans out as **one `ng test` invocation per Angular project**, each writing to its own `coverage/<projectName>/` — merging is on us.
- **[source]** `@analogjs/vitest-angular:test` imposes no such restriction; `test.projects` in the Vite config would pass straight through to Vitest.
- `triple-yahtzee-score-board` is already a two-config repo (`vite.config.ts` for the app, `worker/vitest.config.ts` for the Cloudflare worker) and handles it as **two separate runs**, not a Vitest workspace: `.github/workflows/ci.yml` lines 73-74.

Not pursued further.

---

## What I could not determine

- **Nothing was executed.** Every "exact invocation" above is derived from schema, source and docs. In particular I did not confirm that `@vitest/coverage-istanbul` instruments Angular's *bundled* test output cleanly under browser mode — Angular's own auto-detection prefers Istanbul there, which is encouraging, but it is not proof.
- **Whether the numbers actually differ, and by how much.** Section 5 predicts a difference from first principles. Measuring it means running both suites twice (v8 vs istanbul), which the ticket excluded. It is cheap to do during the TS bake-off and would settle the question properly.
- **Whether `"coverageArgs"` survives Angular's builder-schema validation** in the Analog case. The mechanism is in the source; the validation layer is not something I could exercise without running it.
- **How literally Vitest's "identical coverage reports" claim holds** for esbuild-bundled, source-map-remapped Angular output. The claim is documented and unqualified; the pipeline it is claimed against is not this one.
- **Whether the `coverage.include` trap** (builder needs the `spec-*.js`/`chunk-*.js` prefix) actually breaks reports in practice, or is merely inefficient. Inferred from a code comment.
