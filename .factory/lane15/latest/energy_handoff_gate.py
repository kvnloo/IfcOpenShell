# This file was generated with the assistance of an AI coding tool.
"""Fail-closed IFC space-boundary handoff audit for a one-zone thermal model.

This only audits semantic boundary links. It DOES NOT validate boundary
polygons, construction properties, loads, or an EnergyPlus run.
"""
from __future__ import annotations

TARGETS = {
    "South": ("IfcWall", "EXTERNAL"),
    "East": ("IfcWall", "EXTERNAL"),
    "North": ("IfcWall", "EXTERNAL"),
    "West": ("IfcWall", "EXTERNAL"),
    "Floor": ("IfcSlab", "EXTERNAL_EARTH"),
    "Roof": ("IfcSlab", "EXTERNAL"),
}


def evaluate(rows: list[dict]) -> dict:
    """Check the one-to-one thermal surface → spatial-boundary contract."""
    found: dict[str, list[dict]] = {}
    for row in rows:
        found.setdefault(row["element_name"], []).append(row)
    missing = sorted(set(TARGETS) - set(found))
    unexpected = sorted(set(found) - set(TARGETS))
    duplicate = sorted(name for name, entries in found.items() if len(entries) > 1)
    invalid = []
    for name in sorted(set(found) & set(TARGETS)):
        element_type, classification = TARGETS[name]
        for row in found[name]:
            if row.get("boundary_level") != "IfcRelSpaceBoundary1stLevel":
                invalid.append(f"{name}: not an explicit first-level IFC boundary")
            if row.get("element_type") != element_type:
                invalid.append(f"{name}: wrong element type")
            if row.get("physical_or_virtual") != "PHYSICAL":
                invalid.append(f"{name}: non-physical boundary")
            if row.get("internal_or_external") != classification:
                invalid.append(f"{name}: wrong environmental classification")
            if not row.get("has_connection_geometry"):
                invalid.append(f"{name}: missing connection geometry")
    ready = not (missing or unexpected or duplicate or invalid)
    return {
        "status": "TOPOLOGY_READY_ONLY" if ready else "BLOCKED",
        "expected_boundaries": len(TARGETS),
        "observed_boundaries": len(rows),
        "missing": missing,
        "unexpected": unexpected,
        "duplicate": duplicate,
        "invalid": invalid,
        "geometry_agreement_verified": False,
        "energy_simulation_verified": False,
    }


def audit_model(model) -> dict:
    """Read real IfcOpenShell entities; no geometry or simulation imports needed."""
    spaces = [s for s in model.by_type("IfcSpace") if s.Name == "TestZone"]
    if len(spaces) != 1:
        return {"status": "BLOCKED", "reason": f"Expected exactly one TestZone, found {len(spaces)}"}
    space = spaces[0]
    rows = []
    for boundary in model.by_type("IfcRelSpaceBoundary"):
        related_space = boundary.RelatingSpace
        if related_space is None or related_space.GlobalId != space.GlobalId:
            continue
        element = boundary.RelatedBuildingElement
        rows.append({
            "element_name": getattr(element, "Name", None),
            "boundary_level": boundary.is_a(),
            "element_type": element.is_a() if element is not None else None,
            "physical_or_virtual": boundary.PhysicalOrVirtualBoundary,
            "internal_or_external": boundary.InternalOrExternalBoundary,
            "has_connection_geometry": boundary.ConnectionGeometry is not None,
        })
    return evaluate(rows)
