<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 — Wave 31: exact EnergyPlus executable identity

Status: LIMITED / downstream only, no native engine validation.

## Reproduced correctness defect
The existing design-day runner accepted any output of `energyplus --version`
containing the substring `26.2`, even when the executable identified itself
as EnergyPlus 25.2 or 26.1, or was only a wrapper. Consequently a fake clean
`.err`/`.end` stub could report PASS against the wrong input-data dictionary.
This is a provenance/semantic-compatibility defect in our integration harness,
not an upstream EnergyPlus bug.

## Change
Require the entire CLI banner to identify `EnergyPlus, Version 26.2[.0]`
with an optional build SHA. Mismatches return BLOCKED *before* starting any
simulation. The format is based on EnergyPlus Essentials documentation.

## Reproduction
From `.factory/lane15/latest`:

    PYTHONPATH=baseline:. python -m unittest test_energyplus_version_provenance -v
    PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q

Before the fix: three wrong-version subtests FAIL because they are accepted
and launch a fake engine. After: three BLOCKED; valid-looking 26.2 header
passes **the stub only**, not a real engine.

Local Wave22-derived suite plus new tests: 119 methods, 118 passed and 1
skipped. Full later-wave supplemental tests were not rerun. Actual
IfcOpenShell 0.9.0, pxr/OpenUSD 26.5, Bonsai and EnergyPlus 26.2 are NOT_RUN;
no energy demand or physical improvements are measured.

## Attribution / next gate
EnergyPlus command-line banner:
https://energyplus.readthedocs.io/en/v26.2.0/essentials/essentials.html
Original IFC unit work: aothms (#9951), BIMvoice (#9295) and issue reporters.
This patch and test were AI-assisted. Fork draft: kvnloo/IfcOpenShell #1;
coordination: kvnloo/oss-factory #104.

Next: execute actual EnergyPlus 26.2 design-day inputs with fresh `.err` and
`.end` receipts, IFC4 metre/mm saved-kernel roundtrip, native OpenUSD stage.
