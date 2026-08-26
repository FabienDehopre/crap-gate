"""Build the per-repo, per-lane CRAP distribution from the captured raw reports.

Frontend numbers come straight from crap-typescript's JSON (`crap` per method).
Backend numbers are recomputed from the MTP Cobertura files, because ReportGenerator
renders CrapScore in HTML only. Two backend columns are produced:

  crap_rg     - what ReportGenerator shows: cc = the raw `complexity` attribute
  crap_mccabe - the same formula with cc = complexity / 2 + 1, the true McCabe value
                (issue #5 verified `complexity == 2 * branch_points` exactly)

Usage: python3 measurement/analyze.py
"""

import json
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

RAW = Path(__file__).parent / "raw"
THRESHOLDS = (6, 8, 15, 30, 45, 60)


def crap(cc, cov):
    return cc**2 * (1 - cov) ** 3 + cc


def load_frontend(path):
    """crap-typescript JSON -> (scored methods, n/a count).

    `crap: null` means coverage could not be resolved for the method. Those are
    counted apart, never folded in as zeros - a silent hole in the gate, not a pass.
    """
    methods = json.loads(Path(path).read_text())["methods"]
    scored = [
        {"name": m["method"], "src": m["src"], "cc": m["cc"], "cov": m["cov"] / 100, "crap": m["crap"]}
        for m in methods
        if m["crap"] is not None
    ]
    return scored, sum(1 for m in methods if m["crap"] is None)


def load_backend(path):
    """MTP Cobertura -> one entry per method, both cc conventions."""
    root = ET.parse(path).getroot()
    out = []
    for pkg in root.iter("package"):
        pkg_name = pkg.get("name", "")
        for cls in pkg.iter("class"):
            cls_name = cls.get("name", "")
            for meth in cls.iter("method"):
                lines = list(meth.iter("line"))
                if not lines:
                    continue
                cov = sum(1 for line in lines if int(line.get("hits", 0)) > 0) / len(lines)
                raw_cc = int(meth.get("complexity", 1))
                out.append(
                    {
                        "name": f"{cls_name}.{meth.get('name')}{meth.get('signature', '')}",
                        "src": pkg_name,
                        "cc": raw_cc,
                        "mccabe": raw_cc // 2 + 1,
                        "cov": cov,
                        "crap": crap(raw_cc, cov),
                        "crap_mccabe": crap(raw_cc // 2 + 1, cov),
                    }
                )
    return out


def percentiles(values):
    ordered = sorted(values)

    def at(p):
        if not ordered:
            return None
        idx = min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))
        return ordered[idx]

    return {
        "n": len(ordered),
        "median": statistics.median(ordered) if ordered else None,
        "p75": at(75),
        "p90": at(90),
        "p95": at(95),
        "max": ordered[-1] if ordered else None,
    }


def report(label, methods, key, na=0):
    scores = [m[key] for m in methods]
    stats = percentiles(scores)
    print(f"\n### {label}")
    print(f"scored methods: {stats['n']}" + (f"   N/A (coverage unresolved): {na}" if na else ""))
    if not scores:
        return
    print(
        "  median {median:.2f}   p75 {p75:.2f}   p90 {p90:.2f}   p95 {p95:.2f}   max {max:.2f}".format(**stats)
    )
    print("  fails: " + "   ".join(
        f"@{t}: {sum(1 for s in scores if s > t)} ({sum(1 for s in scores if s > t) / len(scores):.1%})"
        for t in THRESHOLDS
    ))
    print("  worst offenders:")
    for m in sorted(methods, key=lambda m: -m[key])[:8]:
        print(f"    {m[key]:9.2f}  cc={m['cc']:<4} cov={m['cov']:6.1%}  {m['name']}  [{m['src']}]")


def crosscut(rows):
    """The two questions a threshold argument actually turns on."""
    print("\n\n## Cross-cut: what a threshold would be failing")
    print("\nA method at 100% coverage scores exactly its CC, so any threshold T fails every")
    print("fully-tested method with CC > T. That sets a floor: below it, the gate punishes")
    print("code that is complex but *properly tested* - the opposite of what CRAP is for.\n")
    print(f"{'lane / repo':<52} {'floor':>6} {'method setting it':<48}")
    for label, methods, key in rows:
        covered = [m for m in methods if m["cov"] >= 0.999]
        if not covered:
            print(f"{label:<52} {'-':>6} (no fully-covered methods)")
            continue
        worst = max(covered, key=lambda m: m[key])
        print(f"{label:<52} {worst[key]:>6.0f} {worst['name'][:48]:<48}")

    print("\n\nFailures split by coverage band, so the count is readable as a work item:")
    for t in (8, 15, 30, 45, 60):
        print(f"\n  threshold {t}")
        for label, methods, key in rows:
            fails = [m for m in methods if m[key] > t]
            if not fails:
                print(f"    {label:<50} 0")
                continue
            untested = sum(1 for m in fails if m["cov"] == 0)
            partial = sum(1 for m in fails if 0 < m["cov"] < 0.999)
            full = sum(1 for m in fails if m["cov"] >= 0.999)
            print(
                f"    {label:<50} {len(fails):>3}   "
                f"({untested} untested, {partial} partly covered, {full} fully covered)"
            )


def main():
    print("# CRAP distribution across the measurement subjects")
    print("\n## Frontend lane - crap-typescript 0.5.0, v8 provider")
    for label, filename in (
        ("triple-yahtzee-score-board", "frontend-yahtzee-crap.json"),
        ("my-netatmo-24 (MyNetatmo24.Frontend)", "frontend-netatmo-crap.json"),
        ("eslint-config (plain-TS control)", "frontend-eslint-config-crap.json"),
    ):
        methods, na = load_frontend(RAW / filename)
        report(label, methods, "crap", na)

    rows = []
    for label, filename in (
        ("frontend / triple-yahtzee-score-board", "frontend-yahtzee-crap.json"),
        ("frontend / my-netatmo-24", "frontend-netatmo-crap.json"),
        ("frontend / eslint-config", "frontend-eslint-config-crap.json"),
    ):
        rows.append((label, load_frontend(RAW / filename)[0], "crap"))

    print("\n\n## Backend lane - recomputed from MTP Cobertura")
    for label, filename in (
        ("FordConnectToAbrpSync", "backend-ford-cobertura.xml"),
        ("my-netatmo-24 (4 test projects merged)", "backend-netatmo-cobertura.xml"),
    ):
        methods = load_backend(RAW / filename)
        report(f"{label} - as ReportGenerator scores it (cc = raw complexity)", methods, "crap")
        report(f"{label} - with true McCabe (cc = complexity/2 + 1)", methods, "crap_mccabe")
        rows.append((f"backend / {label} (RG scale)", methods, "crap"))
        rows.append((f"backend / {label} (McCabe scale)", methods, "crap_mccabe"))

    crosscut(rows)


if __name__ == "__main__":
    main()
