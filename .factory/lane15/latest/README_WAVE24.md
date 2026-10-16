<!-- Generated with the assistance of an AI coding tool. -->
# Lane 15: EnergyPlus 26.2 design-day handoff

Status: LIMITED / downstream only. No native EnergyPlus, IFC4, OpenUSD, or Bonsai execution.

This candidate converts the existing six-face geometry-only fragment into a separate EnergyPlus 26.2 IDF. It adds the optional **Space Name** positional field absent from the old fragment, three named constructions, reference materials, a ground-temperature assumption, and two synthetic sizing days. It does not add an EPW run period, HVAC, occupants, or measured energy demand.

Source of the positional field layout and synthetic example assumptions: [EnergyPlus 26.2.0 reference one-zone model](https://github.com/NatLabRockies/EnergyPlus/blob/v26.2.0/testfiles/1ZoneUncontrolled.idf). The EnergyPlus team retains source credit.

Local evidence: 125 core tests run (one skipped), 19 baseline tests passed; 8 targeted design-day tests passed. All three building fixtures produced candidate IDFs with six surfaces; strict native gate returned code 2 (BLOCKED) for all because the executable is absent. Engine parsing/simulation remains unverified. Receipts and generated files are included under `design_day_26_2/`.

The work continues existing fork draft PR #1 and factory issue kvnloo/oss-factory#104. No worker lease acquired, upstream changes, or default branch merge. Existing IFC unit work remains credited to aothms (#9951), BIMvoice (#9295), and original issue reporters.

Next proof: EnergyPlus 26.2 executable run with a captured .err log, separately from pinned IFC4 metre/mm and OpenUSD runtime checks.
