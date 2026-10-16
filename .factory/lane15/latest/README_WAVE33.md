<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 Wave 33 — integrated W31/W32 handoff fixes

Status: LIMITED, **LOCAL ONLY / NOT PUBLISHED**. Existing downstream draft kvnloo/IfcOpenShell #1 has verified head `85cc9c9c85141191967c5f0aee1b03b9af017e93` (Wave 30). Do not report Wave 31/32/33 as pushed.

## Integrated corrections

- EnergyPlus 26.2 binary identity now requires a full, official-looking `--version` banner rather than accepting a wrong version with an unrelated mention of 26.2 (Wave 31).
- Geometry-to-IDF handoff now rejects incomplete/extra face ledgers and nonfinite face-area/volume metrics (Wave 32).
- Both patches were applied **together** to the exact Wave 30 `energyplus_design_day.py` Git blob `2060bb204a1564ea1aaf6f02aac9338e987b47fa`, without conflicts. This integrated patch is a portable offline artifact.

## Evidence and scope

- `python -m py_compile .factory/lane15/latest/*.py` succeeded.
- `python -m unittest test_energyplus_ledger_integrity test_energyplus_version_provenance -v` — **5/5 methods passed**, with controlled subprocess stubs and a local-only six-face fixture reconstructed from Wave24 candidate IDF plus analytic metrics. The actual baseline modules/fixtures were not available in this sandbox, so stand-in geometry parser functions were used *only for this regression run*. They are NOT part of the patch. No native IFC/USD/EnergyPlus validation occurred.
- Red/green on the **exact Wave30 source blob** (same isolated fixture and stubs): before fixes **6 failed assertions + 1 error / 5 methods**, after combined fixes **5 passed / 0 failed**. Failed cases: wrong 26.1/25.2/wrapper version banners, NaN face area/volume, extra face; absent face raised KeyError.
- Wave 32 independent local reproduction previously reported **3 test methods passed** after the geometry-ledger fix; **127 passed / 1 skipped** from the reconstructed Wave 22+24 suite, and 19 independent baseline passed. These historical outcomes were NOT rerun on the integrated checkout.
- Both combined changes are from existing source/consumer code; no origin IfcOpenShell bug or energy saving is implied.
- IfcOpenShell 0.9.0, OpenUSD 26.5, Bonsai, and EnergyPlus 26.2 native executable validation: **NOT RUN**. No energy demand measured.
- An attempted official IfcOpenShell 0.9.0 wheel download for Python 3.13 / Linux x86_64 was inaccessible in this sandbox. Published PyPI SHA256: `604123cc9d5e8c9a3a3ccd7135c689fe529a24c21e19984216e1a75c78209c03` (62 MB wheel, released 2026-09-29), but this digest was **not independently verified against downloaded bytes**.
- No global worker claim, origin write, new PR, default merge, workflow activation, or branch publication.

## Next validation

Use an authorized runner with official, verifiably pinned runtime wheels and binaries. Execute saved-file IFC4 metre/mm geometry-kernel round-trip, OpenUSD 26.5 Stage.Open, EnergyPlus 26.2 design-day parsing/simulation with fresh `eplusout.err` / `eplusout.end`. Persist exact versions, commands, native outputs, SHA256 input hashes, and exit codes. Do not treat static test green as native green.

## Attribution

AI-assisted integration and tests. Upstream IFC provenance: aothms, BIMvoice and original issue reporters; EnergyPlus source/schema: NatLabRockies/EnergyPlus developers; OpenUSD parsing work: OpenUSD contributors. Follow IfcOpenShell's LGPL-3.0-or-later / Bonsai GPL-3.0-or-later and AI-disclosure requirements. Factory coordination issue: kvnloo/oss-factory #104; registry PR #100 remains draft.
