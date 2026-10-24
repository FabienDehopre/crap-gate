# TODO

Open questions left over from the wayfinder map
[CRAP gate for TypeScript and C# (#1)](https://github.com/FabienDehopre/crap-gate/issues/1).
None is worth deciding until something real needs it.

- [ ] **Standard local command.** Some convention (`npm run crap`, a Claude skill) so the local command is
      the same in every repo. Maybe unnecessary: every run's summary already prints the exact command under
      "Run it locally".
- [ ] **TypeScript monorepos.** Angular's `@angular/build:unit-test` deletes `test.projects`, so it runs one
      project per `ng test`: a monorepo needs N invocations and a coverage merge. Analog has no such limit.
      `triple-yahtzee-score-board`'s `worker/` project is covered by no test run, so it shows as 11 unscored
      methods (12.5%), enough to trip the unscored warning. Revisit when an Angular repo needs several projects.
- [ ] **xunit v2 / VSTest projects.** No eligible repo uses them today (all the hits were forks). Decide whether
      the backend lane serves VSTest-based projects when one exists.
- [ ] **Non-Angular TypeScript.** A future project uses React and `.tsx`. Decide then whether the frontend lane
      stays tool-agnostic enough to cover it or is openly Angular-only.
- [ ] **Backend projects missing from coverage.** ReportGenerator only sees what is in the Cobertura files, so a
      project no test loads silently disappears; the report says "unscored: not detectable". Possible detection:
      compare `.slnx` projects with Cobertura packages.
