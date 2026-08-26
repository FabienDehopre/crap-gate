"""Part A: Istanbul vs v8 provider divergence, per the ticket's pre-registered rule."""
import json, sys

CT_V8, CT_IST = sys.argv[1], sys.argv[2]

def load_ct(p):
    d = json.load(open(p))
    out = {}
    for m in d["methods"]:
        key = (m["src"], m["method"], m["lineStart"])
        out[key] = m
    return out

v8, ist = load_ct(CT_V8), load_ct(CT_IST)

only_v8 = sorted(set(v8) - set(ist))
only_ist = sorted(set(ist) - set(v8))
both = sorted(set(v8) & set(ist))

print(f"methods: v8={len(v8)} istanbul={len(ist)} common={len(both)}")
print(f"only in v8: {len(only_v8)}   only in istanbul: {len(only_ist)}")
for k in only_v8[:20]: print("   +v8 ", k[1], k[0], k[2], v8[k]["cc"], v8[k]["cov"], v8[k]["crap"])
for k in only_ist[:20]: print("   +ist", k[1], k[0], k[2], ist[k]["cc"], ist[k]["cov"], ist[k]["crap"])

# sanity: complexity must be provider-independent
cc_mismatch = [k for k in both if v8[k]["cc"] != ist[k]["cc"]]
print(f"\nCC mismatches (expect 0): {len(cc_mismatch)}")
for k in cc_mismatch[:10]:
    print("   ", k[1], v8[k]["cc"], "vs", ist[k]["cc"])

def crapnum(m):
    return m["crap"] if isinstance(m["crap"], (int, float)) else None

na_v8 = [k for k in both if crapnum(v8[k]) is None]
na_ist = [k for k in both if crapnum(ist[k]) is None]
print(f"N/A crap: v8={len(na_v8)} istanbul={len(na_ist)}")

scored = [k for k in both if crapnum(v8[k]) is not None and crapnum(ist[k]) is not None]

# --- population split: fully covered cannot disagree ---
partial = [k for k in scored if v8[k]["cov"] < 100 or ist[k]["cov"] < 100]
full = [k for k in scored if k not in set(partial)]
print(f"\nscored={len(scored)}  fully-covered={len(full)}  partially-covered={len(partial)}")

# --- Test 1: threshold sweep 5..60 ---
print("\n=== TEST 1 — threshold sweep (classification flips) ===")
flips_total = 0
flip_detail = {}
for t in range(5, 61):
    flips = [k for k in scored if (crapnum(v8[k]) > t) != (crapnum(ist[k]) > t)]
    if flips:
        flip_detail[t] = flips
        flips_total += len(flips)
    print(f"  threshold {t:>2}: {len(flips)} flips")
print(f"TEST 1 {'PASSES (insignificant): zero flips at every threshold' if flips_total==0 else 'FAILS: ' + str(flips_total) + ' flips'}")

# --- Test 2: relative divergence cap ---
print("\n=== TEST 2 — max relative divergence |v8-ist|/ist ===")
def reldiv(k):
    a, b = crapnum(v8[k]), crapnum(ist[k])
    if b == 0: return 0.0 if a == 0 else float('inf')
    return abs(a - b) / b

rows = sorted(((reldiv(k), k) for k in scored), reverse=True)
for r, k in rows[:12]:
    print(f"  {r*100:8.3f}%  {k[1]:<45} cc={v8[k]['cc']:>3} "
          f"cov v8={v8[k]['cov']:.4g}/{v8[k]['covKind']} ist={ist[k]['cov']:.4g}/{ist[k]['covKind']} "
          f"crap v8={crapnum(v8[k]):.4g} ist={crapnum(ist[k]):.4g}")
maxdiv = rows[0][0] if rows else 0.0
print(f"max over all scored     : {maxdiv*100:.4f}%")
prows = sorted(((reldiv(k), k) for k in partial), reverse=True)
pmax = prows[0][0] if prows else 0.0
print(f"max over PARTIAL only   : {pmax*100:.4f}%  (n={len(partial)})")
print(f"TEST 2 {'PASSES (insignificant): under 5%' if maxdiv < 0.05 else 'FAILS: exceeds 5%'}")

print("\n=== VERDICT ===")
t1p, t2p = flips_total == 0, maxdiv < 0.05
print(f"Test 1 passes={t1p}  Test 2 passes={t2p}")
print("Istanbul kept ONLY if both FAIL ->", ("KEEP Istanbul (then hand-verify)" if (not t1p and not t2p) else "DROP Istanbul, stay on v8"))
