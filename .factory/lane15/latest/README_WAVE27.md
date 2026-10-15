<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 Wave 27 — EnergyPlus native completion gate

**Status: LIMITED / downstream-only.** Existing fork draft PR #1; no origin writes,
worker claims, default-branch merges, or claimed real-world energy improvements.

## Verified regression

Wave 26 run_engine classified a zero-exit stub and non-severe eplusout.err as
PASS even when eplusout.end was absent, terminated, or contained severe errors.
This is a harness false green, not a reproduced EnergyPlus engine defect.

EnergyPlus 26.2 explicitly documents eplusout.end as the success/failure
receipt; absence means no verified successful simulation:
https://energyplus.readthedocs.io/en/v26.2.0/guides/output-details-and-examples/2.8-eplusout.end.html
Its .err error levels are documented separately:
https://energyplus.readthedocs.io/en/v26.2.0/guides/output-details-and-examples/2.11-eplusout.err.html

## Narrow fix

Preserve Wave 26 isolated output directories. Require a fresh eplusout.end
with Completed Successfully and 0 Severe Errors, alongside a zero exit and
a clean eplusout.err. Record end-file existence, summary and SHA-256.
The five new subprocess-stub regression cases cover missing, terminated,
severe, successful, and contradictory completions. An older stub was updated
to create a valid .end when simulating success.

## Evidence

The local pre-fix source had exact Git blob SHA
438acd97aa817b715e7c2e8f92515b6b21114650 (Wave 26).
Before: 5 focused tests -> 3 failed, 1 errored, 1 passed.
After: 5 focused tests passed. Full reconstructed fork snapshot:
133 tests executed, 132 passed, 1 skipped, 0 failed.
Python subprocess stubs only; no real IfcOpenShell, OpenUSD, Bonsai
or EnergyPlus runtime executed. Energy demand NOT_MEASURED.

## Next

Run native IFC4 metre/mm saved-file and OpenUSD parser gates, then
EnergyPlus 26.2 IDF design-day runs on an authorized native runner.
Keep eplusout.err/eplusout.end + hashes with any runtime receipt.

Credit: EnergyPlus developers for documented completion semantics;
aothms (#9951), BIMvoice (#9295) and IFC issue reporters for prior unit work.
All changes here are AI-assisted.
