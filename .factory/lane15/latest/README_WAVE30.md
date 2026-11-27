<!-- AI-assisted downstream research note. -->
# Wave 30 — Reject unaccounted USD scene prims

**Status: LIMITED / fork-only.** This repairs the local six-face shell
auditor, not an upstream IfcOpenShell issue or a native simulation.

## Reproduced defect

The static USDA parser checked six named Mesh prims but ignored extra
non-mesh scene geometry, Xforms, and overrides. As a result,
`runtime_gate.check_case` could report a synthetic six-face geometry PASS
while the USD scene also contained unaccounted building content absent
from its EnergyPlus surface handoff. The native pxr probe likewise
iterated six named meshes without checking other stage prims.

Require exactly one `/Building` Xform and six named Mesh prims in both
the static parser and native Stage.Traverse() check. This is deliberately
not a general-purpose USD validator: richer scenes need their own contract.

## Repro and verification

In `.factory/lane15/latest`:

```sh
PYTHONPATH=baseline:. python -m unittest test_usd_primitive_accounting -v
PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q
```

- Before: 3 focused negative tests failed; 1 native-pxr case skipped.
- After: 4 focused tests passed; 1 native-pxr case skipped.
- Reconstructed Wave22 core, with Wave28 version-guard fixture and the new
  module: **122 run, 120 passed, 2 skipped, 0 failures**.
- Independent baseline: **19 passed**.
- Latest Wave23–29 supplemental test suites were not all rerun here.
- Actual IfcOpenShell 0.9.0, OpenUSD 26.5, Bonsai and EnergyPlus 26.2:
  **NOT_RUN**. No native IFC geometry, energy demand or performance claims.

The code and evidence are AI-assisted. Credit IfcOpenShell/Bonsai/OpenUSD
maintainers, EnergyPlus developers, unit-fix contributors aothms (#9951)
and BIMvoice (#9295), and original issue reporters. No worker claim,
origin action, default-branch merge or new PR.

Next: validate the stricter scene contract on an authorized OpenUSD 26.5
runner, along with IFC4 m/mm saved-file kernel and EnergyPlus 26.2
design-day parser and .err/.end logs.
