# CRAP gate

Scoring methods by Change Risk Anti-Patterns (CRAP) in CI, one lane per language, to surface code that is both complex and poorly tested.

## Language

### Structure

**Lane**:
One language's independent scoring path, with its own tool, complexity scale and report; never merged or compared with another lane.
_Avoid_: Pipeline, gate (as a synonym), track

### Scoring outcomes

**Excluded**:
Code the exclusion policy removes from scoring altogether; it does not appear in the report at all, only in the policy that excludes it.
_Avoid_: Skipped, ignored, suppressed

**Unscored**:
Code inside the gate's scope for which no coverage data exists, so no CRAP score can be computed; a third outcome beside pass and fail, always counted.
_Avoid_: N/A (as a term; fine as the report's cell value), passing, 0% covered

### Gating

**Threshold**:
The CRAP score a method must not exceed, set per lane on that lane's own scale; a score exactly at the threshold passes.
_Avoid_: Limit, max score, cutoff

**Warn-only**:
The mode in which going over the threshold is reported but never fails the run; the default, and a legitimate permanent state.
_Avoid_: Soft gate, advisory, dry run

**Enforcing**:
The mode in which any method over the threshold fails the run; the threshold is the same number as in warn-only, only the consequence changes.
_Avoid_: Hard gate, strict mode, blocking

**Ratchet**:
Enforcing at a raised threshold, then lowering it toward the lane default as methods are fixed.
_Avoid_: Baseline, grandfathering

### Kinds of code

**Vendored code**:
Third-party source a CLI copied into the repo (e.g. spartan-ng helm components); treated as a dependency, not as the project's own code.
_Avoid_: Library code, UI kit, generated code
