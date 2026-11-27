<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 — Construction digital twin recovery (Waves 1–22)

All 22 prior Lane 15 artifacts are preserved byte-for-byte in `archives/`, including historical patch files, tests, logs, and three synthetic building fixtures. Unpack Wave 22 for the consolidated latest code; the historical waves must not be interpreted as 22 independent upstream contributions.

**Reproduced in recovery (2026-10-15):** 117 core unittest cases run, 1 skipped; 19 baseline unittest cases passed. The required native IFC4 metre/mm gate reported BLOCKED (expected: IfcOpenShell unavailable). Prior analytic nominal single-zone dimensions 10×8×3 m, floor 80 m², volume 240 m³. No actual Bonsai, native OpenUSD or EnergyPlus performance/energy claim.

**Scope:** This is fork-local experimental evidence only. No default-branch merge, no origin writes, no global worker claim. The approved coordination thread remains https://github.com/kvnloo/oss-factory/issues/104 and the provisional project registry PR is https://github.com/kvnloo/oss-factory/pull/100 . Origin unit-scale fixes are tracked separately (including BIMvoice's #9295 and aothms's #9951); credit original reporters/developers.

To reproduce the Wave 22 tests:
```bash
unzip archives/lane15_bim_wave22_evidence.zip -d /tmp/lane15
cd /tmp/lane15
PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q
(cd baseline && PYTHONPATH=..:. python -m unittest discover -s . -p 'test_*.py' -q)
```
The contained `CI_TEMPLATE_native_ifc4.yml` is review-only; it has not been activated.
