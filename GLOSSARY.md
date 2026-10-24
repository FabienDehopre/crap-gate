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

### Kinds of code

**Vendored code**:
Third-party source a CLI copied into the repo (e.g. spartan-ng helm components); treated as a dependency, not as the project's own code.
_Avoid_: Library code, UI kit, generated code
