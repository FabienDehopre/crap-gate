# THROWAWAY prototype — TypeScript CRAP bake-off

Answers issue #3: *TypeScript bake-off: crap-typescript vs crap4ts*, plus the
Istanbul-vs-v8 provider question folded into the same ticket.

**Verdict: `@barney-media/crap-typescript`, on the v8 provider. The Istanbul
migration is dropped.** See the resolution comment on the issue.

Nothing here is production code. It exists to put both tools on the same coverage
run so the divergence could be measured rather than assumed.

## Subject

`triple-yahtzee-score-board` @ `6576431`, Angular 22.1.3 + `@analogjs/vitest-angular:test` 2.7.0,
vitest **4.1.11** (the ticket recorded 4.1.10; the catalog has since bumped), 21 spec files / 277 tests.

Nothing in the real repo was modified — all runs happened in a detached `git worktree`.

## Reproduce

```sh
git worktree add /tmp/yahtzee HEAD --detach   # from triple-yahtzee-score-board
cd /tmp/yahtzee

# add both providers to package.json + the pnpm catalog (catalogMode: strict), then:
pnpm install --ignore-scripts

# apply vite.config.ts.patched — adds an env-driven coverage block
CRAP_PROVIDER=v8       CRAP_OUT=cov-v8       pnpm exec ng test --coverage --watch=false
CRAP_PROVIDER=istanbul CRAP_OUT=cov-istanbul pnpm exec ng test --coverage --watch=false

npm install @barney-media/crap-typescript@0.5.0 @sebassdc/crap4ts@0.1.1

# crap-typescript reuses coverage/coverage-final.json when it is already there
cp cov-v8/coverage-final.json coverage/coverage-final.json
crap-typescript --format json --output crapout/ct-v8.json --threshold 30

# crap4ts always wipes coverage/ and re-runs the suite itself
CRAP_PROVIDER=v8 CRAP_OUT=coverage crap4ts --src src --output json \
  --coverage-command "pnpm exec ng test --coverage --watch=false" > crapout/c4-v8.json

python3 part_a.py crapout/ct-v8.json crapout/ct-istanbul.json
python3 compare_tools.py crapout/ct-v8.json crapout/c4-v8.clean.json
```

`crap4ts --output json` writes its JSON to **stdout after the test runner's own stdout**,
so the raw capture is not parseable. `*.clean.json` here is the JSON tail extracted from it.

## Captured artifacts

| File | What it is |
|---|---|
| `part_a.py` | Threshold sweep (5–60) and relative-divergence cap for the pre-registered Istanbul-vs-v8 rule |
| `compare_tools.py` | Matches methods across both tools and tabulates discovery and complexity divergence |
| `yahtzee-coverage-v8.json` | Raw Istanbul-format coverage, `provider: 'v8'` |
| `yahtzee-coverage-istanbul.json` | Raw Istanbul-format coverage, `provider: 'istanbul'` |
| `crap-typescript-{v8,istanbul}.json` | crap-typescript 0.5.0 reports — **byte-identical to each other** |
| `crap4ts-{v8,istanbul}.json` | crap4ts 0.1.1 reports — **byte-identical to each other** |
| `vite.config.ts.patched` | The env-driven coverage block added to the subject's `vite.config.ts` |

## The numbers worth remembering

**Part A — the providers do not differ at all.** Across 77 scored methods (25 of them
partially covered, where all real divergence would have to live):

- threshold sweep 5..60: **0 classification flips at every threshold**
- max per-method relative CRAP divergence: **0.0000%**

Both tools' reports are byte-identical across providers (`md5` matches). The two
`coverage-final.json` files *are* genuinely different (121KB vs 96KB, different
`statementMap` columns) — but every `s`/`b`/`f` **counter** matches. v8 emits 4 files
Istanbul omits; all four are pure type declarations with zero statements and zero
functions, so they are inert for CRAP.

Vitest's documented claim that AST-remapped v8 "produces identical coverage reports to
Istanbul" holds exactly on this pipeline. Both pre-registered tests pass ⇒ **drop Istanbul**.

**Part B — crap4ts cannot see the state layer.** It walks only *top-level statements*,
so a `signalStore(...)` call initializer is invisible: it finds **0 of 3** `UndoStore`
methods and **4 of 13** `SessionStore` methods, missing `placeScore` — the #3 highest-CRAP
method in the codebase (CRAP 7.48, CC 7, 78.6% covered). Meanwhile 15 of its 71 entries
are test helpers from `.spec.ts` files.

**crap4ts undercounts complexity on `?.`.** Its decision-point list (`src/complexity.ts`)
has `IfStatement`, `ConditionalExpression`, the loops, `CatchClause`, `CaseClause`,
`&&`, `||`, `??` — and **no optional-chaining token**. Hand-verified on
`ScoringEngineService.computeColumnStats`: `for` +1, `if` +1, three `??` +3, two `?.` +2,
base 1 = **8**. crap-typescript says 8; crap4ts says 6 — exactly the two `?.` it ignores.
This is the same failure class that sank crap4dotnet in the .NET bake-off.

**Where they agree, both are right.** Hand-verified `ScoringEngineService.computeScore`:
13 `case` +13, 6 ternaries +6, 21 `&&`/`||` +21, base 1 = **41**. Both tools report 41.
Only 1 of 57 matched methods disagrees on complexity. The problem is discovery, not arithmetic.

## CI fitness

| | crap-typescript 0.5.0 | crap4ts 0.1.1 |
|---|---|---|
| npm | `@barney-media/crap-typescript` (+ vitest/jest adapters) | `@sebassdc/crap4ts`. **Unscoped `crap4ts` on npm is a different project** (`breezy-bays-labs`) |
| Machine-readable output | `--format json\|toon\|text\|junit`, `--output <file>` (must be inside project root) | `--output json\|markdown\|csv`, **stdout only, polluted by the test runner's output** |
| Exit codes | **0 pass / 2 threshold exceeded / 1 usage or execution failure** — verified | **1 for all three** — threshold, runtime error and bad flag are indistinguishable. Its README claims usage = 2; that is wrong |
| Exclusions | `--exclude <glob>`, `--exclude-path-regex`, `--exclude-generated-marker`, `--use-default-exclusions`; baseline always skips `.spec`/`__tests__`/`dist`/`coverage`; report carries a `sourceExclusions` audit | `--exclude <substring>` only. No baseline test-file exclusion |
| Unresolvable coverage | reports `cov: null`, `crap: null` (**N/A**) — 11 `worker/src/**` methods, correctly not scored as 0% | no N/A concept; unmatched line ranges read as 0% coverage |
| Reuses existing coverage | yes, reads `coverage/coverage-final.json` if present | no, always deletes it and re-runs the suite |
| Non-standard `reportsDirectory` | not read; falls back to running the suite itself | **`coverageDir` is hard-coded to `coverage/`** (`src/options.ts:159` overwrites the parsed value) |
| Angular constructs | decorated methods, class-field arrows, accessors, `#private`, computed/string-keyed members, nested functions — all found, and backed by golden fixtures in `docs/compatibility-matrix.md` | misses object-literal methods returned from a call expression, i.e. all of NgRx Signals |
| Provenance | v0.5.0, Aug 2026, Apache-2.0, changelog + release workflow | v0.1.1, last commit Apr 2026, MIT |

Neither tool reads Angular's default `coverage/<projectName>/` layout, so the frontend
lane must set `coverage.reportsDirectory` explicitly — as the builder research already advised.

crap-typescript analyses **any nested `src/` tree**, so it picked up `worker/src/**` in this
repo (correctly as N/A, since the app test run does not cover it). The frontend lane wants
`--exclude 'worker/**'`, which drops it to 77 methods over one tree. That is an input to the
exclusion-policy ticket.

**Threshold note:** crap-typescript's default threshold is **6.0**, and it warns above 8.0
that the gate is "too lenient even for hard gates". That is a very different scale from the
conventional 30 the map assumes. On this repo, threshold 30 fails exactly one method
(`computeScore`, CRAP 41); threshold 6 would fail several. Input to the threshold ticket.
