<!-- This document was generated with the assistance of an AI coding tool. -->
<!-- oss-factory:v1
{"id":"20261015-lane15-native-ci-exit-022","kind":"result","project":"oss-factory","from":"chatgpt","to":["factory"],"status":"done","civ":{"city_id":"oss:oss-factory"},"parent_id":"20261014-lane15-ifc-preflight-001","dedupe_key":"lane15-ifc-single-zone-interoperability"}
-->

# Lane 15 — Wave 22: native IFC4 metre/mm CI must fail if not executed

**Disposition: LOCAL_ONLY / LIMITED. No GitHub writes, no claim/lease, no upstream publication.**

## Actual problem reproduced

The Wave 21 command below exited **0** even though IfcOpenShell is absent and both IFC4 unit round-trips were `NOT_RUN`. This can make a job named "native IFC validation" appear green while testing only dependency-free geometry.

```bash
PYTHONPATH=baseline:. python runtime_gate.py benchmarks/field_clinic \
  --author-ifc --ifc-units both --report /tmp/lane15-before.json
# Observed: exit 0, IFC = NOT_RUN, metre/mm parity = NOT_RUN.
```

This is a **downstream preflight exit-code defect**, not an origin IfcOpenShell or EnergyPlus defect. It arose from conflating an optional probe with an explicitly required verification in CI. The static geometry preflight intentionally retains its original successful exit behavior.

## Change

`runtime_gate.py` accepts `--require-native-ifc`, only with `--author-ifc --ifc-units both`. It validates both saved-file geometry receipts, both unit statuses, kernel parity, and the existing thermal-boundary report before permitting **native IFC proof**. A run with missing/incomplete evidence writes a complete `requirements.native_ifc_m_mm` report and exits **2**; a true probe failure exits **1**, and a completed native gate exits **0**. Existing static-only mode continues to exit **0** for clean synthetic fixtures and never upgrades Civilization to verified.

Portable `CI_TEMPLATE_native_ifc4.yml` is an **unpublished, opt-in** GitHub Actions workflow proposal: manual dispatch, Python 3.11, `ifcopenshell==0.9.0`, `usd-core==26.5`, source tests, native IFC m/mm parity, native OpenUSD verification, and evidence upload even on failed jobs. It **does not** run EnergyPlus: the IDF file is deliberately missing constructions, material properties, loads, schedules, and weather inputs. It requires placing the extracted source in `factory/evidence/lane15/` on an authorized branch and human review before activation. Do not interpret workflow YAML as CI evidence.

## Evidence (2026-10-15)

| Check | Prior behavior | Current behavior |
| --- | --- | --- |
| Both native units absent, optional probing | **exit 0**, both `NOT_RUN` | unchanged, intentionally optional |
| Both native units absent, explicitly required | no such mode | **exit 2**, JSON `BLOCKED`, all three building names captured |
| Required native mode without both unit flags | unrecognized | parser rejects invalid request, exit 2 |
| Dependency-free regression suite | 112 run, 1 skipped | **117 run, 1 skipped** |
| Independent baseline suite | 19 pass | **19 pass** |
| New focused tests | 0 | **5 pass** (including negative receipt variations) |
| Real IfcOpenShell round-trip | NOT_RUN | **NOT_RUN** (package/network unavailable here) |
| Real OpenUSD/Bonsai/EnergyPlus | NOT_RUN | **NOT_RUN** |
| Actual energy demand / reductions | unknown | **unknown** |

Reproduce:

```bash
unzip lane15_bim_wave22_evidence.zip -d wave22
cd wave22
PYTHONPATH=baseline:. python -m unittest discover -s . -p 'test_*.py' -q
(cd baseline && PYTHONPATH=..:. python -m unittest discover -s . -p 'test_*.py' -q)
PYTHONPATH=baseline:. python runtime_gate.py \
  benchmarks/small_residence benchmarks/field_clinic benchmarks/workshop \
  --author-ifc --ifc-units both --require-native-ifc \
  --report evidence/native-required-repeat.json
# Exits 2 here without ifcopenshell, and records native_ifc_m_mm = BLOCKED.
```

Patch against Wave 21: `wave22-local.patch` (changes `runtime_gate.py`, adds `test_native_cli_exit.py`). Clean-apply tests should pass in a clean Wave 21 extraction. The 3 benchmark fixtures have independent IDs/geometry, but **only synthetic geometry**, not native IFC verification. Reference 10 × 8 × 3 m room: floor 80 m², total zone shell 268 m², volume 240 m³. Physical building solids and zone thermal surfaces remain explicitly different representations.

## Canonical control plane and current dedupe

- Read [`AGENTS.md`](https://github.com/kvnloo/oss-factory/blob/main/AGENTS.md), [`factory/projects.json`](https://github.com/kvnloo/oss-factory/blob/main/factory/projects.json), [`CONTROL_PLANE.md`](https://github.com/kvnloo/oss-factory/blob/main/factory/CONTROL_PLANE.md), [`HITL.md`](https://github.com/kvnloo/oss-factory/blob/main/factory/HITL.md), and [IfcOpenShell v0.9.0 AGENTS.md](https://github.com/IfcOpenShell/IfcOpenShell/blob/v0.9.0/AGENTS.md).
- Existing coordination: [Lane 15 #104](https://github.com/kvnloo/oss-factory/issues/104). `ifcopenshell` is **not yet on canonical main registry**; [draft #100](https://github.com/kvnloo/oss-factory/pull/100) is open, registry merge unauthorized here. Source code fork `kvnloo/IfcOpenShell` exists; coordination still routes to `kvnloo/oss-factory` pending registry approval.
- Upstream duplicate avoidance: unit bug reports by `joepaddock-uk` [#9294](https://github.com/IfcOpenShell/IfcOpenShell/issues/9294) and `aghiless-coder` [#9926](https://github.com/IfcOpenShell/IfcOpenShell/issues/9926), fix by `aothms` [#9951](https://github.com/IfcOpenShell/IfcOpenShell/pull/9951) **merged 2026-10-15**, plus older open work by `BIMvoice` [#9295](https://github.com/IfcOpenShell/IfcOpenShell/pull/9295). **Do not submit a duplicate origin fix.** ProjectLibrary regression is separate from the basic six-product metre/mm fixture; a future runtime test can explicitly exercise it.
- Factory global six-worker budget: **no claim acquired**, no lease mutated, no unapproved origin action. This continues the existing #104 leaf locally; it does not open a separate tracked contribution. No external PR, comment, workflow activation, or fork push.
- AI assistance: new files and patched code generated with AI assistance. Original IfcOpenShell, Bonsai/Blender, OpenUSD, and EnergyPlus authors retain credit and respective licenses (IfcOpenShell library LGPL-3.0-or-later; Bonsai GPL-3.0-or-later). The authored evidence/patch is not a contribution to upstream libraries yet.

## Next highest-value step

Human-reviewed, authorized downstream branch: copy bundle code under `factory/evidence/lane15/`, adapt/review the manual CI template, run **fresh actual** IFC4 metre/mm + native USDA gate on Python 3.11 with package SHA/version capture, and inspect the two `.ifc` files in Bonsai. Only then prepare a minimal valid EnergyPlus model with constructions/weather/schedules and run it; do **not** equate a parsed IDF fragment with a simulated energy result. Prioritize native integration over more synthetic mutation tests.

**Civilization handoff:** `Manufacturing (modelled analytical quantities) → IFC4 (NOT_RUN) → OpenUSD (static PASS, native NOT_RUN) → EnergyPlus (geometry fragment only) → Civilization (UNVERIFIED)`. No energy, cost, emissions, or construction productivity claims.
