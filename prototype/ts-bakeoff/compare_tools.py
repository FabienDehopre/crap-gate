"""Part B: crap-typescript vs crap4ts on the same coverage run.

Usage: compare_tools.py <crap-typescript.json> <crap4ts.clean.json>
crap4ts's raw stdout mixes the test runner's output with the JSON; .clean.json is
the JSON tail extracted from it (see README).
"""
import json, re, sys, collections

ct = json.load(open(sys.argv[1]))["methods"]
c4 = json.load(open(sys.argv[2]))["entries"]

def ct_key(m):
    p = re.sub(r"\.tsx?$", "", re.sub(r"^src/", "", m["src"]))
    return (p.replace("/", "."), m["method"])

C = {ct_key(m): m for m in ct}
F = {(e["module"], e["name"]): e for e in c4}
both, onlyC, onlyF = sorted(set(C) & set(F)), sorted(set(C) - set(F)), sorted(set(F) - set(C))

print(f"crap-typescript methods : {len(ct)}  over {len({m['src'] for m in ct})} files")
print(f"crap4ts entries         : {len(c4)}  over {len({e['module'] for e in c4})} modules")
print(f"matched={len(both)}  only-crap-typescript={len(onlyC)}  only-crap4ts={len(onlyF)}")

print("\n--- complexity disagreements on matched methods ---")
dis = [k for k in both if C[k]["cc"] != F[k]["complexity"]]
for k in sorted(dis, key=lambda k: -abs(C[k]["cc"] - F[k]["complexity"])):
    print(f"   {k[1]:<42} ct={C[k]['cc']:>3}  c4={F[k]['complexity']:>3}")
print(f"   {len(dis)} of {len(both)} disagree")

print("\n--- test-file entries in each report ---")
istest = lambda s: ".spec" in s or "testing" in s
print(f"   crap-typescript: {sum(1 for m in ct if istest(m['src']))}")
print(f"   crap4ts        : {sum(1 for e in c4 if istest(e['module']))}")

print("\n--- N/A (coverage not resolvable) ---")
print(f"   crap-typescript: {sum(1 for m in ct if m['cov'] is None)} reported as N/A")
print(f"   crap4ts        : no N/A concept; unmatched ranges score as 0% coverage")

print("\n--- NgRx Signals stores (signalStore(...) call initializer) ---")
for f, mod in [("src/app/services/session.store.ts", "app.services.session.store"),
               ("src/app/services/undo.store.ts", "app.services.undo.store")]:
    a = [m["method"] for m in ct if m["src"] == f]
    b = [e["name"] for e in c4 if e["module"] == mod]
    print(f"   {f}\n      crap-typescript ({len(a)}): {sorted(a)}\n      crap4ts         ({len(b)}): {sorted(b)}")
