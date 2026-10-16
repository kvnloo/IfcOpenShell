<!-- AI-assisted Lane 15 research note. -->
# Wave 28 — IFC version provenance gate

The native IFC authoring runner and receipt validator previously accepted
non-0.9.0 or unreported IfcOpenShell versions. This is a harness provenance gap,
not an upstream IfcOpenShell bug.

On the recovered Wave 22 snapshot, two new focused tests failed before the
change (5 assertions, 1 import error). After the change: 2 passed. The Wave 22
suite ran 119 cases: 118 passed, 1 skipped. Strict IFC/OpenUSD execution
remains BLOCKED (exit 2); native packages and EnergyPlus are unavailable here.

This work is fork-local; no worker claims, upstream writes or default merges.
Original unit contributors aothms, BIMvoice and issue reporters retain credit.
