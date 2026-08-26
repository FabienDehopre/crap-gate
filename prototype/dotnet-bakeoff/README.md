# THROWAWAY prototype — .NET CRAP bake-off

Answers issue #5: *ReportGenerator Risk Hotspots vs crap4dotnet*.
**Verdict: ReportGenerator.** See the resolution comment on the issue.

Nothing here is production code. It exists to make the two tools' numbers comparable
on the same coverage run so the divergence could be measured rather than assumed.

## Reproduce

```sh
# subject 1 — FordConnectToAbrpSync (2 projects, TUnit/MTP)
cd ~/Projects/GitHub/FordConnectToAbrpSync
dotnet test --configuration Release --results-directory /tmp/crapbake/ford -- \
  --coverage --coverage-output coverage.xml --coverage-output-format cobertura \
  --coverage-settings "$PWD/coverage.config"

reportgenerator -reports:/tmp/crapbake/ford/coverage.xml -targetdir:/tmp/crapbake/ford/rg -reporttypes:Html

dotnet tool install Crap4DotNet          # 0.1.1 at time of writing
dotnet dotnet-crap analyze ~/Projects/GitHub/FordConnectToAbrpSync/FordConnectToAbrpSync \
  --coverage /tmp/crapbake/ford/coverage.xml --output /tmp/crapbake/ford/crap4dotnet.json

python3 compare.py /tmp/crapbake/ford/coverage.xml /tmp/crapbake/ford/crap4dotnet.json
```

## Captured artifacts

| File | What it is |
|---|---|
| `compare.py` | Matches methods across both tools (incl. async state-machine demangling) and tabulates the complexity divergence |
| `ford-coverage.xml` | Raw MTP Cobertura output, FordConnectToAbrpSync |
| `ford-crap4dotnet.json` | crap4dotnet output for the same run |
| `netatmo-coverage.xml` | Raw MTP Cobertura, my-netatmo-24 — note it already merges 4 packages |
| `netatmo-crap4dotnet.json` | crap4dotnet output, my-netatmo-24 |

## The one number worth remembering

The `complexity` attribute the MTP collector writes into Cobertura is
**2 x the number of conditional branch points**, verified by counting `<condition>`
elements: `complexity == 2 * branch_points` exactly, on every method checked.

So **true McCabe = complexity / 2 + 1**, and ReportGenerator's CrapScore is computed
from a complexity roughly twice the real one — which CRAP then squares.
