#!/usr/bin/env python3
"""THROWAWAY prototype - .NET CRAP bake-off (issue #5).

Compares the cyclomatic complexity and CRAP score that ReportGenerator (via the
`complexity` attribute in Cobertura) and crap4dotnet (via its own Roslyn walk)
report for the SAME methods on the SAME coverage run.

    python3 compare.py <coverage.xml> <crap4dotnet.json>
"""
import json, re, sys, xml.etree.ElementTree as ET

def crap(cc, cov):
    return cc ** 2 * (1 - cov) ** 3 + cc

def demangle(cls_short, method):
    """`<RunCycleAsync>d__14.MoveNext` is the state machine for `RunCycleAsync`.

    RG demangles these for display; we must too, or async methods look like they
    exist in only one of the two tools.
    """
    g = re.match(r"<([^>]+)>[dg]__\d+", cls_short)
    if g and method in ("MoveNext", "<MoveNext>b__0"):
        return g.group(1)
    return method

def load_cobertura(path):
    """RG's view: complexity attribute as written by the MTP coverage collector."""
    out = {}
    for cls in ET.parse(path).getroot().iter("class"):
        cname = cls.get("name", "")
        short = cname.rsplit(".", 1)[-1]
        outer = short.split("/")[0] if "/" in short else short
        if re.match(r"<[^>]+>[dg]__\d+", short):
            outer = cname.rsplit(".", 2)[-2] if cname.count(".") >= 2 else outer
        for m in cls.iter("method"):
            name = demangle(short, m.get("name"))
            short_key = outer
            lines = list(m.iter("line"))
            hit = sum(1 for l in lines if int(l.get("hits", 0)) > 0)
            cov = hit / len(lines) if lines else 0.0
            out[(short_key, name)] = dict(cc=int(float(m.get("complexity", 0))), cov=cov)
    return out

def load_crap4dotnet(path):
    out = {}
    for m in json.load(open(path))["methods"]:
        out[(m["className"].rsplit(".", 1)[-1], m["methodName"])] = dict(
            cc=m["complexity"], cov=m["coverage"], crap=m["crap"])
    return out

cob, c4d = load_cobertura(sys.argv[1]), load_crap4dotnet(sys.argv[2])

print(f"{'Class.Method':<52}{'RG cc':>6}{'c4d cc':>7}{'ratio':>7}   "
      f"{'RG crap':>8}{'c4d crap':>9}")
print("-" * 92)
rows, only_rg, only_c4d = [], [], []
for k in sorted(set(cob) | set(c4d)):
    label = f"{k[0]}.{k[1]}"[:51]
    if k in cob and k in c4d:
        a, b = cob[k], c4d[k]
        ratio = f"{a['cc']/b['cc']:.1f}x" if b["cc"] else "-"
        rows.append((a["cc"] - b["cc"], label, a, b, ratio))
    elif k in cob:
        only_rg.append(label)
    else:
        only_c4d.append(label)

for _, label, a, b, ratio in sorted(rows, key=lambda r: -r[0]):
    print(f"{label:<52}{a['cc']:>6}{b['cc']:>7}{ratio:>7}   "
          f"{crap(a['cc'], a['cov']):>8.1f}{b['crap']:>9.1f}")

agree = sum(1 for _, _, a, b, _ in rows if a["cc"] == b["cc"])
print("-" * 92)
print(f"{len(rows)} methods in both | complexity agrees on {agree} "
      f"({agree/len(rows)*100:.0f}%)")
print(f"only in Cobertura/RG ({len(only_rg)}): {', '.join(only_rg[:6])}")
print(f"only in crap4dotnet ({len(only_c4d)}): {', '.join(only_c4d[:6])}")
