<!-- AI-assisted Lane 15 fork-local research note. -->
# Wave 29 — Restore IFC thermal-boundary handoff

Status: LIMITED / fork-only. This fixes an actual producer/consumer contract defect in
the local IFC4 geometry-to-energy handoff, **not** a bug in upstream IfcOpenShell.

## Finding

`verify_boundary_geometry()` computed six surface outward normals but dropped
the `normal` map from its returned receipt. `runtime_gate.validated_boundary_receipt()`
requires those six normals, so even a fully correct native IFC space-boundary
geometry result would have been downgraded to `NOT_RUN`. The producer now
returns the existing computed normal map without weakening consumer validation.

## Reproducer and evidence

Source snapshot: recovered Wave 22 geometry harness with later branch's
consumer contract reviewed. Test `test_boundary_handoff_integration.py`
passes the producer's actual mock-IFC output directly to the real receipt
validator for 10×8×3 m, 4×3×2.5 m, and 20×15×6 m buildings. Missing or
inverted normals remain rejected.

- Red: `PYTHONPATH=baseline:. python -m unittest test_boundary_handoff_integration -v`
  failed three positive dimension subtests plus a missing-key negative check.
- Green: the same focused two tests passed (including all three dimension cases).
- Regression: `PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q`
  ran 119 cases: 118 passed, 1 skipped; zero failures.
- Baseline: `PYTHONPATH=baseline:. python -m unittest discover -s baseline -p 'test_*.py' -q`
  passed 19 tests.
- Strict native IFC metre/mm preflight on three fixtures: exit 2 / BLOCKED;
  no `ifcopenshell`, OpenUSD/`pxr`, Bonsai or EnergyPlus runtime in sandbox.

**Scope:** unit-level mock IFC producer/consumer integration proof; not
saved-file IFC4, geometry-kernel, OpenUSD, or EnergyPlus execution.
`energy_demand_kwh` and verified Civilization impact remain unmeasured.

Upstream geometry authoring APIs and design credits: IfcOpenShell/Bonsai
maintainers. Existing unit investigations/fixes: aothms (#9951), BIMvoice
(#9295), original issue reporters. EnergyPlus example schema reference:
NatLabRockies/EnergyPlus v26.2.0 `testfiles/1ZoneUncontrolled.idf`.
All new changes in this wave were AI-assisted.

Next: pinned native saved-file IFC4 m/mm round-trip, OpenUSD 26.5 stage parse,
then separate EnergyPlus 26.2 parser and design-day execution on an authorized
runner. No upstream action, default-branch merge or factory worker claim.
