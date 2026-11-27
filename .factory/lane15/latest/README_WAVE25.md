<!-- Generated with the assistance of an AI coding tool. -->
# Lane 15 Wave 25 — fix standalone EnergyPlus export

Status: LIMITED / fork-local. Continue existing draft PR #1; no origin action or worker lease.

## Reproduced

Published `energyplus_design_day.py` failed when run directly:
`ModuleNotFoundError: No module named 'test_export_invariants'`.
The baseline helpers reside in a sibling `baseline/` directory, and full-suite
imports could mask this because other tests modify process-wide `sys.path`.

## Fix and measured evidence

- Explicitly import from the sibling baseline directory, as `runtime_gate.py` does.
- Test the CLI from an unrelated working directory with `PYTHONPATH` cleared.
- Local Python 3 tests: 126 run, 1 skipped, 0 failures; baseline: 19 passed.
- Independent static CLI: 3/3 benchmark fixtures generated six-surface IDFs.
- Strict native gate: all 3 exited 2 / BLOCKED (no EnergyPlus executable).
- No actual IFC/OpenUSD/Bonsai/EnergyPlus runtime result or energy-demand claim.

Next: run native IFC4 metre/mm saved-file, OpenUSD parser and EnergyPlus 26.2
candidate IDFs on an authorized runner; preserve engine error logs.

AI-assisted source/tests. Credit upstream IFC unit work to aothms (#9951),
BIMvoice (#9295), original issue reporters, and EnergyPlus example authors.
