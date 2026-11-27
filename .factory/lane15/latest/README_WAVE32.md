<!-- This document was generated with the assistance of an AI coding tool. -->
# Lane 15 / Wave 32 — reject incomplete or nonfinite design-day ledgers

Status: **LIMITED**, local-only (GitHub commit blocked by connector safety check). Do not claim native interoperability, EnergyPlus simulation or physical energy results.

## Reproduction

The design-day candidate handoff converts six IDF reference surfaces but accepted a `metrics.json` with a seventh unaccounted face and silently ignored `NaN` geometry metrics. It also raised raw `KeyError` for a missing face entry. Python's default `json.loads` accepts `NaN`/`Infinity`, so `abs(NaN - expected) > tolerance` is **false** and the previous numeric guard silently certified invalid evidence.

The source and consumer are existing files under `.factory/lane15/latest/`, not an origin IfcOpenShell defect. A synthetic field-clinic/residence is not a production building model.

## Minimal fix

Before emitting a candidate IDF, require precisely the six reference face names and reject all nonfinite volume/area values. Preserve existing area and volume numerical tolerances. Added `test_energyplus_ledger_integrity.py` against the existing small-residence fixture.

## Local tests (reconstructed Wave 22 + Wave 24 + new test)

```
PYTHONPATH=baseline:. python -m unittest test_energyplus_ledger_integrity -v
PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q
cd baseline && python -m unittest discover -s . -p 'test_*.py' -q
```

- Before fix: 3 failures, 1 error across 3 test methods (extra face accepted, missing face KeyError, NaN volume accepted, NaN area accepted); finite baseline accepted. Infinity cases already failed before fix but are now explicitly rejected.
- After fix: 3/3 methods pass; full reconstructed local suite **127 passed / 1 skipped / 128 run**; baseline **19 passed**.
- Full most-recent Wave 25–30 supplemental modules **NOT_RUN** here; the candidate/metric code section was compared with the current fork file. Native IfcOpenShell 0.9.0, OpenUSD 26.5, Bonsai, and EnergyPlus 26.2 **NOT_RUN** (runtimes absent).
- No worker lease claimed; no origin write, new PR, branch merge, energy-demand number or building-performance claim.

## Provenance

Synthetic fixture and tests were written with AI assistance. Original IfcOpenShell unit evidence: contributors aothms, BIMvoice, and issue reporters. EnergyPlus model format and semantics credit the NatLabRockies/EnergyPlus team, with upstream project copyright and licensing unchanged.

Factory thread: kvnloo/oss-factory #104. Continue **existing** fork draft kvnloo/IfcOpenShell #1 only if connector writes are authorized. Wave31's separate version-identity patch remains unpublished.
