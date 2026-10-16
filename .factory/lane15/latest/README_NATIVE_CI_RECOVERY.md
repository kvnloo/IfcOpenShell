<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 — Native CI recovery path repair

Status: LIMITED / fork-only. The inactive native CI template referenced a
nonexistent factory/evidence/lane15 working directory and artifact paths;
the recovered snapshot actually lives at .factory/lane15/latest/.

Correct the checkout directory and artifact paths; add a source-presence
precheck. Keep the mandatory IFC4 metre/mm gate and a separate native
OpenUSD PASS check. Pin ifcopenshell==0.9.0, usd-core==26.5 and Python 3.11,
record the resolved dependency versions. Do not activate the workflow: GitHub
workflow_dispatch needs a file installed on the default branch, and merging
default requires human authorization under the factory policy.

Local verification: 121 core unittest cases (1 skipped), 19 baseline tests
pass. Strict native gate on residence, clinic and workshop exits 2 / BLOCKED.
Neither native IFC nor OpenUSD nor Bonsai nor EnergyPlus was executed; energy
demand and real-world impact are unknown. The added four checks validate
workflow wiring, not any native runtime.

Origin IFC unit-scale work by joepaddock-uk, aghiless-coder, BIMvoice and
aothms retains credit. Entire note/test/template AI-assisted. This remains
under kvnloo/IfcOpenShell draft PR #1 and oss-factory issue #104.

Next: on an authorized runner, install pinned native libraries and execute
the actual saved-file IFC4 metre/mm kernel + OpenUSD parser gates, then validate
a complete EnergyPlus IDF/EPW run as a separate integration proof.
