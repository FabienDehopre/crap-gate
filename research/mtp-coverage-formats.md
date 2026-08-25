# Which coverage formats can TUnit on Microsoft Testing Platform emit?

Research for [issue #2](https://github.com/FabienDehopre/crap-gate/issues/2). Documentation research only — no projects were created and no test runs were performed. Dates: researched 2026-08-25 against the then-current `main` of each repo.

Each claim is tagged **[documented]** (stated in first-party docs), **[source]** (read off the tool's own source or a committed artefact in its repo), or **[unverified]** (reasoned, not confirmed by running anything).

---

## Short answer

**No — `Microsoft.Testing.Extensions.CodeCoverage` cannot emit OpenCover XML.** Its only formats are `coverage` (binary), `xml` (Visual Studio coverage XML), and `cobertura`. The user's recollection is **wrong for the Microsoft collector**, and there is an open, explicitly-deprioritised feature request asking for exactly this.

**But the decision it was supposed to drive does not turn out to hinge on it,** for two separate reasons found while checking:

1. **OpenCover is reachable under MTP after all — via `coverlet.MTP`,** a real, shipping MTP-native coverlet extension (`--coverlet-output-format opencover`). It is not `coverlet.collector` and not `coverlet.msbuild`; both of those really are VSTest-only.
2. **ReportGenerator does not actually require OpenCover for CrapScore.** Its Cobertura parser reads the `complexity` attribute on `<method>` and computes CRAP from it — and both the Microsoft collector and coverlet write that attribute.

So **both backend candidates stay live**, and the plainest route (`dotnet test --coverage --coverage-output-format cobertura` → ReportGenerator Risk Hotspots) already yields a CrapScore.

The real caveat is not the format. It is that **the "complexity" in both Cobertura producers is a branch count, not a Roslyn cyclomatic complexity** — see [The complexity caveat](#the-complexity-caveat), which is the thing that should actually decide between the two candidates.

---

## 1. `Microsoft.Testing.Extensions.CodeCoverage` formats

**[documented]** The extension exposes exactly four options:

| Option | Description |
| --- | --- |
| `--coverage` | Collect code coverage using the dotnet-coverage engine |
| `--coverage-output` | Name/path of the produced file. Default `TestResults/<guid>.coverage` |
| `--coverage-output-format` | **Supported values: `coverage`, `xml`, `cobertura`.** Default `coverage` |
| `--coverage-settings` | XML/JSON code coverage settings file |

Source: [MTP code coverage — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage#microsoft-code-coverage)

**[documented]** The same three-value enumeration appears in the collector's own configuration reference, as the `Format` setting valid in `.runsettings`, a coverage-settings file, or `testconfig.json`: `Format | coverage, cobertura, xml | default coverage`.

Source: [microsoft/codecoverage `docs/configuration.md`](https://github.com/microsoft/codecoverage/blob/main/docs/configuration.md)

**[documented]** `dotnet-coverage` — the same engine, used standalone — offers the identical set for both `collect -f` and `merge -f`: "Supported values: `coverage`, `xml`, and `cobertura`."

Source: [dotnet-coverage — Microsoft Learn](https://learn.microsoft.com/dotnet/core/additional-tools/dotnet-coverage#dotnet-coverage-collect)

### OpenCover is an open, deprioritised feature request

**[documented]** [microsoft/codecoverage#98 "Support OpenCover output format"](https://github.com/microsoft/codecoverage/issues/98) is **open**, filed 2023, labelled `enhancement`. The reporter returned to it in a later comment after migrating to MTP for .NET 10 and finding OpenCover still absent.

A Microsoft maintainer (`fhnaseer`) replied:

> Unfortunately, it is still not prioritized from our side. Scope of this is very big as it doesn't involve only adding support of creating OpenCover report. But it also adding support in Visual Studio, Visual Studio Code. And merging with different report formats.

and proposed the workaround: emit `cobertura`, then convert to OpenCover with ReportGenerator.

**This is as close to a definitive "no" as a primary source gets.** The user's recollection that "MTP can generate OpenCover XML" does not hold for the Microsoft collector. It is plausible the recollection came from the coverlet MTP extension below, which genuinely can.

### Exact invocations

```bash
# Cobertura, explicit output path (executable form — MTP apps are exes)
dotnet run --project ./tests/MyProject.Tests -c Release -- \
  --coverage --coverage-output-format cobertura --coverage-output ./coverage/report.cobertura.xml

# Same via dotnet test (MTP mode, .NET 10 SDK)
dotnet test --coverage --coverage-output-format cobertura

# Multiple formats in one run: repeat the flag
dotnet run -c Release --coverage \
  --coverage-output-format cobertura \
  --coverage-output-format xml
```

Sources: [TUnit code coverage docs](https://github.com/thomhurst/TUnit/blob/main/docs/docs/extending/code-coverage.md); [microsoft/codecoverage sample scenario01](https://github.com/microsoft/codecoverage/blob/main/samples/Algorithms/scenarios/scenario01/README.md)

**[documented]** One MTP-specific gotcha worth carrying into the workflow: `IncludeTestAssembly` defaults to **`false`** in `Microsoft.Testing.Extensions.CodeCoverage`, where it was `true` under VSTest. Test projects are excluded by default. Source: [MTP code coverage — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage#microsoft-code-coverage) (for the CRAP gate this is what we want anyway).

---

## 2. Coverlet under MTP

Three distinct packages, and only the third one matters here.

### `coverlet.collector` — VSTest-only

**[documented]** It is a VSTest *data collector*, invoked as `dotnet test --collect:"XPlat Code Coverage"`. MTP does not host VSTest data collectors.

Source: [Use code coverage for unit testing — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/unit-testing-code-coverage#integrate-with-net-test)

**[documented]** TUnit's own docs are blunt about it:

> If you are migrating from another test framework and currently use **Coverlet** (`coverlet.collector` or `coverlet.msbuild`), you must remove it. TUnit uses Microsoft.Testing.Platform, not VSTest, and Coverlet only works with the legacy VSTest platform.

Source: [TUnit `docs/extending/code-coverage.md`](https://github.com/thomhurst/TUnit/blob/main/docs/docs/extending/code-coverage.md). Note this page has **not been updated** for `coverlet.MTP`; its blanket "Coverlet only works with VSTest" claim is now out of date (see below), though the specific claim about `coverlet.collector`/`coverlet.msbuild` remains correct.

Same from TUnit's maintainer on [TUnit#1905 "TUnit Coverlet Support?"](https://github.com/thomhurst/TUnit/issues/1905): *"Coverlet isn't supported and not something I can add as I don't own it. You can use the Microsoft package for code coverage."*

### `coverlet.msbuild` — VSTest-only, and deliberately so

**[documented]** [coverlet#1715 "coverlet.msbuild Support for Microsoft.Testing.Platform"](https://github.com/coverlet-coverage/coverlet/issues/1715) is where this was settled. The decisive comment, from `Youssef1313` (an MTP maintainer), after discussion with `MarcoRossignoli`:

> Coverlet should only support MTP via a platform extension, and not via MSBuild integration.

**So `/p:CollectCoverage=true /p:CoverletOutputFormat=opencover` does not survive under MTP, and by design never will.** The MSBuild route hooks the `VSTest` MSBuild target chain; under MTP that chain is either replaced (`TestingPlatformDotnetTestSupport` redirects `VSTest` to `InvokeTestingPlatform`) or absent entirely (MTP mode of `dotnet test`, .NET 10 SDK). **[documented]** for the target redirection: [Testing with `dotnet test` — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/unit-testing-with-dotnet-test).

Practical consequence for the ~3 repos on `coverlet.msbuild` and the ~35 on `coverlet.collector`: **those are the xunit-v2/VSTest tail, and they stay on the VSTest path.** They cannot be folded into the TUnit/MTP lane by keeping their existing coverage packages. This is directly relevant to the map's open "xunit-v2 / VSTest tail" question.

### `coverlet.MTP` — the MTP-native extension. This one does OpenCover.

**[documented]** It exists, it ships, and Microsoft Learn documents it on the MTP code coverage page:

> The Coverlet Microsoft Testing Platform Integration (`coverlet.MTP`) is a native extension for MTP that implements `coverlet.collector` functionality.

Its `--coverlet-output-format` option: **"Supported formats: `json`, `lcov`, `opencover`, `cobertura`, and `teamcity`."**

Sources: [MTP code coverage § Coverlet — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage#coverlet); [coverlet `Documentation/Coverlet.MTP.Integration.md`](https://github.com/coverlet-coverage/coverlet/blob/master/Documentation/Coverlet.MTP.Integration.md)

**[source]** Published on NuGet as versions `8.0.0`, `8.0.1`, `10.0.0`, `10.0.1` (checked via `https://api.nuget.org/v3-flatcontainer/coverlet.mtp/index.json`, 2026-08-25). Requires .NET ≥ 8.0.

**[documented]** Usage:

```bash
dotnet add package coverlet.MTP
dotnet test --coverlet --coverlet-output-format opencover
# or, executable form:
dotnet exec <test-assembly.dll> --coverlet --coverlet-output-format opencover
```

Default formats are `json` + `cobertura`; `--coverlet-output-format` may be repeated. Output lands in the `--results-directory` folder, filenames stamped `coverage.<ddMMyyHHmmssfff>.<ext>` (e.g. `coverage.cobertura.280326122803612.xml`). Source: [Coverlet.MTP.Integration.md](https://github.com/coverlet-coverage/coverlet/blob/master/Documentation/Coverlet.MTP.Integration.md).

It also reads MTP-standard `testconfig.json` under `platformOptions.Coverlet`, with a `format` key — and note the **breaking change**: when a config file is present it is *authoritative*, no default excludes are merged in. Same source.

### Does `coverlet.MTP` work with **TUnit** specifically?

**[unverified] — but the mechanism is framework-agnostic, and the inference is strong.**

**[source]** `coverlet.MTP` registers itself through the generic MTP extension-registration mechanism: an MSBuild `TestingPlatformBuilderHook` item pointing at `Coverlet.MTP.TestingPlatformBuilderHook`, which calls `testApplicationBuilder.AddCoverletExtensionProvider()`.

- [`src/coverlet.MTP/buildMultiTargeting/coverlet.MTP.props`](https://github.com/coverlet-coverage/coverlet/blob/master/src/coverlet.MTP/buildMultiTargeting/coverlet.MTP.props)
- [`src/coverlet.MTP/TestingPlatformBuilderHook.cs`](https://github.com/coverlet-coverage/coverlet/blob/master/src/coverlet.MTP/TestingPlatformBuilderHook.cs)

**[source]** TUnit registers itself through *the identical mechanism* — [`src/TUnit/TUnit.props`](https://github.com/thomhurst/TUnit/blob/main/src/TUnit/TUnit.props) declares a `TestingPlatformBuilderHook` item for `TUnit.Engine.Framework.TestingPlatformBuilderHook` — and [`src/TUnit.Engine/TUnit.Engine.csproj`](https://github.com/thomhurst/TUnit/blob/main/src/TUnit.Engine/TUnit.Engine.csproj) references `Microsoft.Testing.Platform.MSBuild`, the package whose `TestingPlatformEntryPoint` task generates the entry point that invokes every registered hook.

That is: coverlet.MTP plugs into the same generated entry point TUnit itself relies on. There is nothing framework-specific in coverlet.MTP's registration. Neither repo has an issue about the pairing (searched both, 2026-08-25) — no confirmation, but no reported breakage either.

**Two things to check in a prototype before betting on it:**
- Whether having both `Microsoft.Testing.Extensions.CodeCoverage` (which the `TUnit` meta-package pulls in — [`src/TUnit/TUnit.csproj`](https://github.com/thomhurst/TUnit/blob/main/src/TUnit/TUnit.csproj)) and `coverlet.MTP` in one project causes a clash. Both are opt-in behind different flags (`--coverage` vs `--coverlet`), so probably not, but two instrumentation engines in one process is exactly the sort of thing that surprises you.
- MTP version compatibility: coverlet.MTP 8.x targets MTP 2.x per its sample csproj; TUnit's pinned MTP version must line up.

---

## 3. What lands on disk

**[documented]** MTP test projects are executables (`<OutputType>Exe</OutputType>`, set by `TUnit.props`), so both invocations work and they write to *different* places:

| Invocation | Coverage file location |
| --- | --- |
| `dotnet test --coverage` | `TestResults/` at the repo/solution level, filename an auto-generated GUID, e.g. `TestResults/d7aaf428-827a-47b2-933b-00008b507595.cobertura.xml` |
| `dotnet run --project X -- --coverage` | `X/bin/<Config>/<tfm>/TestResults/` — i.e. next to the built executable |

Sources: [xUnit.net "Code Coverage with MTP"](https://xunit.net/docs/getting-started/v3/code-coverage-with-mtp) (documents both layouts explicitly); [MTP code coverage — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage#microsoft-code-coverage) for the `TestResults/<guid>.coverage` default.

**[documented]** TUnit's docs show the same shape:

```
TestResults/
  ├── coverage.cobertura.xml
  └── <guid>/
      └── coverage.xml
```

Source: [TUnit code coverage docs](https://github.com/thomhurst/TUnit/blob/main/docs/docs/extending/code-coverage.md)

**Practical CI note:** always pass `--coverage-output` explicitly. The GUID-named default is a nuisance to glob reliably across several test projects, which is precisely the map's "monorepo: per lane" problem. `--coverlet-file-prefix` exists for the same reason on the coverlet side.

### `dotnet test` mode matters

**[documented]** With .NET 10 SDK, `dotnet test` has two modes:

- **MTP mode** — opt in via `global.json`: `{"test": {"runner": "Microsoft.Testing.Platform"}}`. No `--` separator needed; `dotnet test --coverage` works directly.
- **VSTest mode** (default pre-.NET-10, legacy for MTP) — requires `TestingPlatformDotnetTestSupport=true` and MTP args after an extra `--`: `dotnet test -- --coverage`.

`TUnit.props` sets `TestingPlatformDotnetTestSupport=true` itself, so TUnit projects work in either mode — but **the `--` is required in VSTest mode and not in MTP mode**, and getting it wrong means the flag is silently ignored (MTP ≥1.9 emits warning MTP0001). Support for running MTP under VSTest mode **is removed in MTP v2 on the .NET 10 SDK**.

Source: [Testing with `dotnet test` — Microsoft Learn](https://learn.microsoft.com/dotnet/core/testing/unit-testing-with-dotnet-test)

---

## 4. Is there a conversion bridge?

### `dotnet-coverage`: no

**[documented]** `dotnet-coverage merge -f <format>` doubles as a converter, but only between `coverage`, `xml`, and `cobertura`. OpenCover is not an option, in or out.

Source: [dotnet-coverage — Microsoft Learn](https://learn.microsoft.com/dotnet/core/additional-tools/dotnet-coverage#merge-code-coverage-reports)

### ReportGenerator: yes, and it preserves complexity

**[source]** ReportGenerator has an `OpenCover` report *builder* — `src/ReportGenerator.Core/Reporting/Builders/OpenCoverReportBuilder.cs`, `ReportType => "OpenCover"` — so `-reporttypes:OpenCover` converts anything it can parse into OpenCover XML.

**[source]** That builder writes `cyclomaticComplexity` and `nPathComplexity` per method (line 178–179), plus `maxCyclomaticComplexity`/`minCyclomaticComplexity` at class/module/summary level, sourced from the parsed metrics. **So Cobertura-with-complexity → OpenCover round-trips the complexity.** Source: [OpenCoverReportBuilder.cs](https://github.com/danielpalme/ReportGenerator/blob/main/src/ReportGenerator.Core/Reporting/Builders/OpenCoverReportBuilder.cs)

**On the PRO-licence question:** a commenter on codecoverage#98 claims OpenCover output requires a ReportGenerator PRO licence. **[source] I could not confirm that against current `main`.** Grepping every `LicenseType.Pro` check in the tree, the only gates are on HTML/Markdown/LaTeX/SVG-chart *decorations*, `rawMode` (`CoverageReportParser.cs:203`), and the Testwell CTC *parser* (`CoverageReportParser.cs:472`). `OpenCoverReportBuilder.cs` contains no licence check, and `ReportBuilderFactory` does not filter builders by licence. **Treat as ambiguous** — the comment may predate a change, or may refer to something adjacent. Verify before relying on it; it is a one-command check.

---

## 5. Does ReportGenerator's CrapScore actually require OpenCover?

**No.** This is the finding that reframes the ticket.

**[source]** Grepping `src/ReportGenerator.Core/Parser/` for `CrapScore`/`CyclomaticComplexity`, exactly three parsers carry complexity metrics:

| Parser | Complexity? | CrapScore? |
| --- | --- | --- |
| `OpenCoverParser` | yes — `cyclomaticComplexity`, `nPathComplexity` attributes | **yes** (line 451) |
| `CoberturaParser` | yes — `complexity` attribute on `<method>` | **yes** (line 331) |
| `CloverParser` | yes — `complexity` attribute | complexity only, **no CrapScore** |
| `VisualStudioParser` (`.coveragexml`) | no — only `BlocksCovered`/`BlocksNotCovered` | no |
| `DynamicCodeCoverageParser` (MS `xml` format) | no — only `blocks_covered`/`blocks_not_covered` | no |
| `DotCoverParser` | **no metrics at all** | no |
| `JaCoCoParser`, `LCovParser`, `NCoverParser`, `GCovParser`, `SCoverageParser`, `MProfParser`, `CtcParser` | no | no |

Source: [ReportGenerator `src/ReportGenerator.Core/Parser/`](https://github.com/danielpalme/ReportGenerator/tree/main/src/ReportGenerator.Core/Parser)

**[source]** The Cobertura path is not incidental — `CoberturaParser.cs` computes CRAP inline, citing the original blog post:

```csharp
// https://testing.googleblog.com/2011/02/this-code-is-crap.html
// CRAP(m) = CC(m)^2 * U(m)^3 + CC(m)
var uncoveredPercent = (100f - (double)coveragePercent.Value) / 100.0;
var complexity = (double)cyclomaticComplexity.Value;
var crapScore = (Math.Pow(complexity, 2.0) * Math.Pow(uncoveredPercent, 3)) + complexity;
```

Source: [CoberturaParser.cs](https://github.com/danielpalme/ReportGenerator/blob/main/src/ReportGenerator.Core/Parser/CoberturaParser.cs) — the `complexity` attribute read at line 309, CrapScore emitted at line 331. It is conditional: `if (cyclomaticComplexity.HasValue && coveragePercent.HasValue)`. No `complexity` attribute, no CrapScore.

### Corrections to the ticket's premises

Two premises in the ticket are false, and both were load-bearing:

- **"Cobertura does not carry complexity"** — the Cobertura DTD has a `complexity` attribute on `<method>`, and both producers we care about populate it.
- **"dotCover / Visual Studio `.coverage` are complexity-carrying alternatives"** — for ReportGenerator's purposes they are not. `DotCoverParser` emits no metrics whatsoever; `VisualStudioParser` and `DynamicCodeCoverageParser` emit block counts only. **Neither can produce a CrapScore.** So `--coverage-output-format xml` is a dead end for this gate, and `--coverage-output-format cobertura` is the only Microsoft-collector format that works.

### Both producers do write the attribute

**[source] Microsoft collector.** A committed sample output in microsoft/codecoverage, generated by `dotnet run --coverage --coverage-output-format cobertura`:

```xml
<coverage line-rate="1" branch-rate="1" complexity="10" version="1.9" ... branches-valid="10">
  <package line-rate="1" branch-rate="1" complexity="10" name="Algorithms.Core">
    <class line-rate="1" branch-rate="1" complexity="10" name="Algorithms.Core.Merger" ...>
      <method line-rate="1" branch-rate="1" complexity="10" name="Merge" signature="(int[], int[])">
```

Source: [`samples/Algorithms/scenarios/scenario01/example.report.cobertura.xml`](https://github.com/microsoft/codecoverage/blob/main/samples/Algorithms/scenarios/scenario01/example.report.cobertura.xml)

**[source] Coverlet.** `CoberturaReporter.cs` writes `complexity` at package (line 54), class (75), and method (91) level:

```csharp
method.Add(new XAttribute("complexity", CoverageSummary.CalculateCyclomaticComplexity(meth.Value.Branches)));
```

Source: [coverlet `src/coverlet.core/Reporters/CoberturaReporter.cs`](https://github.com/coverlet-coverage/coverlet/blob/master/src/coverlet.core/Reporters/CoberturaReporter.cs)

### The complexity caveat

**This is the finding that should actually drive the tool choice, not the format question.**

**[source]** Coverlet's "cyclomatic complexity" is:

```csharp
public static int CalculateCyclomaticComplexity(IList<BranchInfo> branches)
{
  return Math.Max(1, branches.Count);
}
```

Source: [coverlet `src/coverlet.core/CoverageSummary.cs`](https://github.com/coverlet-coverage/coverlet/blob/master/src/coverlet.core/CoverageSummary.cs)

That is a count of IL branch *outcomes*, not McCabe complexity. Each two-way decision contributes 2, where McCabe would add 1. A method with no branches gets 1 (correct); a method with five `if`s gets ~10 where McCabe says 6.

**[source, inferred]** The Microsoft collector appears to do the same thing. In the sample above, `complexity="10"` on the single `Merge` method, and `branches-valid="10"` on the document. Reading `Merger.cs`, McCabe complexity is roughly 6. **Complexity equals the branch count exactly.** One sample is not proof of the formula, but it is a strong signal, and both tools landing on the same approximation is unsurprising — neither parses source, both only see IL.

**Why this matters for a CRAP gate.** CRAP squares complexity: `CC² × (1−cov)³ + CC`. A ~2× overstatement of CC becomes a ~4× overstatement of the CRAP score at low coverage. **A threshold of 30 calibrated against Roslyn-derived complexity means something quite different against branch-count complexity.**

Two consequences:

1. It reinforces the map's standing decision to go **warn-only first and measure the real distribution**. The distribution from Cobertura-via-ReportGenerator will be shifted high relative to any published CRAP threshold.
2. It is the genuine differentiator between the two backend candidates. `crap4dotnet` computing McCabe complexity from Roslyn is not redundant work — it produces a **different and more faithful number**. ReportGenerator's convenience comes at the cost of a branch-count proxy.

Neither is disqualified. But "which of these two produces a CRAP score we would be willing to gate on?" is now a sharper question than "which formats can we emit?", and it is not answered here.

### ReportGenerator can gate

**[source]** Worth flagging for the map's warn-only → enforcing path: ReportGenerator already has the gate built in. `RiskHotspotsAnalysisThresholds` carries `MaximumThresholdForCrapScore`, documented in source as *"If any risk hotspot is greater than this threshold, ReportGenerator will exit unsuccessfully."*

Defaults, from `src/ReportGenerator.Core/appsettings.json`:

```json
"riskHotspotsAnalysisThresholds": {
  "metricThresholdForCyclomaticComplexity": 15,
  "metricThresholdForCrapScore": 30,
  "metricThresholdForNPathComplexity": 200,
  "maximumThresholdForCyclomaticComplexity": null,
  "maximumThresholdForCrapScore": null,
  "maximumThresholdForNPathComplexity": null
}
```

`metricThresholdFor*` controls what is *listed* as a hotspot (the warn-only report); `maximumThresholdFor*` is null by default and controls the *exit code* (the gate). That is exactly the warn-only-then-enforce split the map wants, available without writing anything.

Sources: [RiskHotspotsAnalysisThresholds.cs](https://github.com/danielpalme/ReportGenerator/blob/main/src/ReportGenerator.Core/CodeAnalysis/RiskHotspotsAnalysisThresholds.cs), [MaxiumRiskhotspotsThresholdsValidator.cs](https://github.com/danielpalme/ReportGenerator/blob/main/src/ReportGenerator.Core/MaxiumRiskhotspotsThresholdsValidator.cs), [appsettings.json](https://github.com/danielpalme/ReportGenerator/blob/main/src/ReportGenerator.Core/appsettings.json)

---

## Routes to a CrapScore, ranked

| # | Route | Complexity source | Confidence |
| --- | --- | --- | --- |
| 1 | `--coverage --coverage-output-format cobertura` → `reportgenerator -reporttypes:HtmlSummary` (Risk Hotspots) | MS collector branch count | **[documented]** end to end; nothing extra to install |
| 2 | `coverlet.MTP --coverlet-output-format opencover` → ReportGenerator | coverlet branch count | **[documented]** for coverlet.MTP; **[unverified]** for the TUnit pairing |
| 3 | `--coverage-output-format cobertura` → `crap4dotnet` | Roslyn McCabe | not researched here — see issue #5 |
| 4 | cobertura → `reportgenerator -reporttypes:OpenCover` → downstream | passed through | works, but pointless as an intermediate for RG itself |

**Route 1 is the default recommendation.** It is the shortest path, uses only what the `TUnit` meta-package already pulls in, and does produce a CrapScore. Route 2 exists as a fallback and is the answer to "can MTP do OpenCover" in the only sense in which the answer is yes.

---

## What I could not determine

- **Whether `coverlet.MTP` actually runs under TUnit.** Registration mechanism is identical and framework-agnostic **[source]**, but no doc, sample, test, or issue in either repo confirms the pairing. Needs a five-minute prototype.
- **Whether the Microsoft collector's `complexity` is *exactly* the branch count.** One committed sample says complexity == `branches-valid`. The engine is closed-source; the algorithm is undocumented. **[inferred]**, worth confirming empirically on a method with known McCabe complexity — and worth confirming *before* picking any threshold.
- **Whether ReportGenerator's OpenCover output is PRO-gated.** A codecoverage#98 commenter says yes; current `main` shows no such gate. **Ambiguous.** Only matters if route 4 is ever needed.
- **Interaction of both coverage extensions in one project.** `Microsoft.Testing.Extensions.CodeCoverage` arrives transitively with the `TUnit` meta-package; adding `coverlet.MTP` puts two instrumentation engines in one process. Different opt-in flags, so probably fine. Unverified.
- **MTP/extension version compatibility matrix for TUnit.** Learn documents CodeCoverage 18.1.x ↔ MTP 2.0.x, 18.0.x ↔ 1.8.x, 17.14.x ↔ 1.6.2 ([source](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage#version-compatibility)). Which MTP version TUnit currently pins, and whether coverlet.MTP 10.x lines up with it, was not chased down.
