# This file was generated with the assistance of an AI coding tool.
"""Experimental IFC4 authoring + geometry-kernel gate for one thermal box.

Nominal thermal shell is 10 x 8 x 3 m. Physical IFC walls extend outside
its faces; slabs extend outside top/bottom. Thermal geometry is intentionally
not equated with material geometry. No energy loads are inferred.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Dimensions:
    length: float = 10.0
    width: float = 8.0
    height: float = 3.0
    wall: float = 0.2
    slab: float = 0.2

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in vars(self).values()):
            raise ValueError("All dimensions must be finite and positive")
        if self.wall >= min(self.length, self.width) / 2 or self.slab >= self.height:
            raise ValueError("Thickness implausible relative to clear dimensions")


def bounds_from_endpoints(p1, p2, outward_thickness, height):
    """Compute bounds without the IFC geometry kernel: left is interior."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length == 0:
        raise ValueError("Zero-length wall")
    outside = (dy / length * outward_thickness, -dx / length * outward_thickness)
    corners = [p1, p2, (p1[0] + outside[0], p1[1] + outside[1]),
               (p2[0] + outside[0], p2[1] + outside[1])]
    return ((min(p[0] for p in corners), min(p[1] for p in corners), 0.0),
            (max(p[0] for p in corners), max(p[1] for p in corners), height))


def pieces(d: Dimensions):
    l, w, h, t, s = d.length, d.width, d.height, d.wall, d.slab
    # CCW centerline tour: interior is on left, physical wall extends right.
    walls = {
        "South": ((0., 0.), (l, 0.)),
        "East": ((l, -t), (l, w+t)),
        "North": ((l, w), (0., w)),
        "West": ((0., w+t), (0., -t)),
    }
    result = []
    for name, (a, b) in walls.items():
        result.append({"name": name, "kind": "IfcWall", "p1": a, "p2": b,
                       "bbox": bounds_from_endpoints(a, b, t, h)})
    slab_xy = [(-t, -t), (l+t, -t), (l+t, w+t), (-t, w+t), (-t, -t)]
    result.extend([
        {"name": "Floor", "kind": "IfcSlab", "z": 0.0, "sense": "NEGATIVE",
         "polyline": slab_xy, "bbox": ((-t, -t, -s), (l+t, w+t, 0.0))},
        {"name": "Roof", "kind": "IfcSlab", "z": h, "sense": "POSITIVE",
         "polyline": slab_xy, "bbox": ((-t, -t, h), (l+t, w+t, h+s))},
    ])
    return result


def expected(d: Dimensions):
    return {
        "zone_floor_area_m2": d.length * d.width,
        "zone_shell_area_m2": 2 * (d.length * d.width + d.length * d.height + d.width * d.height),
        "zone_volume_m3": d.length * d.width * d.height,
        "physical_bbox_m": [[-d.wall, -d.wall, -d.slab],
                             [d.length+d.wall, d.width+d.wall, d.height+d.slab]],
        "physical_solid_count": 6,
        "energy_demand_kwh": None,
    }


def kernel_bounds_metres(flat_vertices, file_length_unit_scale: float, *, convert_back_units: bool = False):
    """Normalize geometry-kernel vertex bounds to metres.

    IfcOpenShell geometry is in SI metres by default, regardless of IFC file
    units. Its ``convert-back-units`` option instead returns file units.
    Multiplying default kernel vertices by the IFC unit scale a second time
    produces an incorrect bbox for millimetre-based models.
    """
    import numpy as np

    if not math.isfinite(file_length_unit_scale) or file_length_unit_scale <= 0:
        raise ValueError("Invalid IFC length-unit scale")
    raw = np.asarray(flat_vertices, dtype=float)
    if not raw.size or raw.size % 3:
        raise ValueError("Geometry must contain XYZ vertices")
    coords = raw.reshape((-1, 3))
    if not np.isfinite(coords).all():
        raise ValueError("Non-finite geometry vertices")
    if convert_back_units:
        coords = coords * file_length_unit_scale
    return coords.min(axis=0), coords.max(axis=0)


def matrix_for_wall(p1, p2, np):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        raise ValueError("Zero-length wall")
    ux, uy = dx / length, dy / length
    return np.array([[ux, -uy, 0, p1[0]], [uy, ux, 0, p1[1]],
                     [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)


def author(path: Path, d: Dimensions, *, length_unit: str = "m"):
    import numpy as np
    import ifcopenshell
    import ifcopenshell.api.project
    import ifcopenshell.api.root
    import ifcopenshell.api.unit
    import ifcopenshell.api.context
    import ifcopenshell.api.aggregate
    import ifcopenshell.api.geometry
    import ifcopenshell.api.spatial
    import ifcopenshell.util.unit
    from boundary_geometry import create_boundary_links

    model = ifcopenshell.api.project.create_file(version="IFC4")
    project = ifcopenshell.api.root.create_entity(model, ifc_class="IfcProject", name="Lane15 Reference")
    if length_unit not in ("m", "mm"):
        raise ValueError("length_unit must be m or mm")
    # Area and volume remain in m² and m³; only length uses mm in this variant.
    length = ifcopenshell.api.unit.add_si_unit(
        model, unit_type="LENGTHUNIT", prefix="MILLI" if length_unit == "mm" else None
    )
    area = ifcopenshell.api.unit.add_si_unit(model, unit_type="AREAUNIT")
    volume = ifcopenshell.api.unit.add_si_unit(model, unit_type="VOLUMEUNIT")
    ifcopenshell.api.unit.assign_unit(model, units=[length, area, volume])
    target_scale = 0.001 if length_unit == "mm" else 1.0
    assert math.isclose(ifcopenshell.util.unit.calculate_unit_scale(model), target_scale, abs_tol=1e-12)
    context = ifcopenshell.api.context.add_context(model, context_type="Model")
    body = ifcopenshell.api.context.add_context(model, context_type="Model", context_identifier="Body",
                                               target_view="MODEL_VIEW", parent=context)
    site = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSite", name="Reference Site")
    building = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuilding", name="Reference Building")
    storey = ifcopenshell.api.root.create_entity(model, ifc_class="IfcBuildingStorey", name="Ground")
    space = ifcopenshell.api.root.create_entity(model, ifc_class="IfcSpace", name="TestZone")
    for child, parent in ((site, project), (building, site), (storey, building), (space, storey)):
        ifcopenshell.api.aggregate.assign_object(model, products=[child], relating_object=parent)
    elements = {}
    for spec in pieces(d):
        element = ifcopenshell.api.root.create_entity(model, ifc_class=spec["kind"], name=spec["name"])
        if spec["kind"] == "IfcWall":
            p1, p2 = spec["p1"], spec["p2"]
            rep = ifcopenshell.api.geometry.add_wall_representation(
                model, context=body, length=math.dist(p1, p2),
                height=d.height, thickness=d.wall, direction_sense="NEGATIVE")
            matrix = matrix_for_wall(p1, p2, np)
        else:
            rep = ifcopenshell.api.geometry.add_slab_representation(
                model, context=body, depth=d.slab,
                polyline=spec["polyline"], direction_sense=spec["sense"])
            matrix = np.eye(4)
            matrix[2, 3] = spec["z"]
        ifcopenshell.api.geometry.assign_representation(model, product=element, representation=rep)
        ifcopenshell.api.spatial.assign_container(model, products=[element], relating_structure=storey)
        ifcopenshell.api.geometry.edit_object_placement(model, product=element, matrix=matrix)
        elements[spec["name"]] = element
    ifcopenshell.api.geometry.edit_object_placement(model, product=space, matrix=np.eye(4))
    create_boundary_links(model, space, elements, d)
    path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(path))
    return path


def verify_ifc(path: Path, d: Dimensions, *, length_unit: str = "m"):
    """Saved/reloaded EXPRESS validation and independently meshed solid bounds."""
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.unit
    import ifcopenshell.util.shape
    import ifcopenshell.validate
    import numpy as np
    from mesh_volume_gate import verify_solid_volume

    reopened = ifcopenshell.open(str(path))
    if reopened.schema != "IFC4":
        raise AssertionError(f"Unexpected schema: {reopened.schema}")
    counts = {k: len(reopened.by_type(k)) for k in
              ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcWall", "IfcSlab")}
    if counts != {"IfcProject": 1, "IfcSite": 1, "IfcBuilding": 1, "IfcBuildingStorey": 1,
                  "IfcSpace": 1, "IfcWall": 4, "IfcSlab": 2}:
        raise AssertionError(f"IFC population mismatch: {counts}")
    scale = ifcopenshell.util.unit.calculate_unit_scale(reopened)
    target_scale = {"m": 1.0, "mm": 0.001}.get(length_unit)
    if target_scale is None or not math.isclose(scale, target_scale, abs_tol=1e-12):
        raise AssertionError(f"Wrong IFC length unit scale: {scale} for {length_unit}")
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(str(path), logger)
    if logger.statements:
        raise AssertionError(f"IFC validation errors: {logger.statements[:3]}")
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    # Explicitly request metres, not the project's original length units.
    settings.set("convert-back-units", False)
    bboxes = {}
    volumes = {}
    library_volumes = {}
    for spec in pieces(d):
        products = [o for o in reopened.by_type(spec["kind"]) if o.Name == spec["name"]]
        if len(products) != 1:
            raise AssertionError(f"Missing/duplicate named product: {spec['name']}")
        shape = ifcopenshell.geom.create_shape(settings, products[0])
        low, high = kernel_bounds_metres(shape.geometry.verts, scale, convert_back_units=False)
        target_low, target_high = spec["bbox"]
        if not np.allclose(low, target_low, atol=2e-4, rtol=0) or not np.allclose(high, target_high,
                                                                                   atol=2e-4, rtol=0):
            raise AssertionError(f"IFC solid bbox mismatch {spec['name']}: {low}/{high}, expected {spec['bbox']}")
        bboxes[spec["name"]] = [low.tolist(), high.tolist()]
        # Bbox parity alone accepts hollow/half-filled solids with the same
        # extents. Verify the actual triangulated kernel volume and manifoldness.
        target_volume = math.prod(b - a for a, b in zip(target_low, target_high))
        volumes[spec["name"]] = verify_solid_volume(
            shape.geometry.verts, shape.geometry.faces, target_volume
        )
        # Independent implementation supplied by IfcOpenShell itself.
        library_volume = ifcopenshell.util.shape.get_volume(shape.geometry)
        if not math.isfinite(library_volume) or not math.isclose(
            library_volume, volumes[spec["name"]]["signed_volume_m3"], rel_tol=5e-4, abs_tol=1e-5
        ):
            raise AssertionError(f"Independent IFC library volume disagreement: {spec['name']}")
        library_volumes[spec["name"]] = library_volume
    return {"schema": reopened.schema, "ifc_unit_scale_m": scale, "ifc_entities": counts,
            "validation_errors": 0, "geometry_kernel_bounds_m": bboxes, "geometry_kernel_volume_m3": {
                name: measurement["signed_volume_m3"] for name, measurement in volumes.items()
            }, "geometry_kernel_library_volume_m3": library_volumes,
            "kernel_closed_manifold_bodies": len(volumes),
            "kernel_single_shell_bodies": sum(v["single_connected_shell"] is True for v in volumes.values()),
            "kernel_bodies_checked": 6,
            "kernel_vertices_unit": "metres", "convert_back_units": False}


def run(output: Path, d: Dimensions, *, length_unit: str = "m"):
    if length_unit not in ("m", "mm"):
        raise ValueError("length_unit must be m or mm")
    report = {"status": "blocked", "reference": expected(d), "tool": "IfcOpenShell authoring/runtime gate",
              "length_unit": length_unit,
              "runtime_checks": {"ifc_roundtrip": "NOT_RUN", "schema_validation": "NOT_RUN",
                                 "geometry_kernel": "NOT_RUN", "bonsai": "NOT_RUN",
                                 "openusd": "NOT_RUN", "energyplus": "NOT_RUN", "energy_space_boundaries": "NOT_RUN"}}
    output.mkdir(parents=True, exist_ok=True)
    try:
        import ifcopenshell
    except ImportError:
        report["blocker"] = "ifcopenshell Python package not installed; no .ifc file produced"
    else:
        detected = getattr(ifcopenshell, "version", None)
        if detected != "0.9.0":
            report["blocker"] = f"Expected IfcOpenShell 0.9.0; found {detected!r}"
            (output / "ifc_report.json").write_text(json.dumps(report, indent=2) + "\n")
            return report
        path = author(output / "single_zone.ifc", d, length_unit=length_unit)
        details = verify_ifc(path, d, length_unit=length_unit)
        from energy_handoff_gate import audit_model
        from boundary_geometry import verify_boundary_geometry
        reopened = ifcopenshell.open(str(path))
        boundary_report = audit_model(reopened)
        if boundary_report["status"] != "TOPOLOGY_READY_ONLY":
            raise AssertionError(f"IFC semantic boundary mismatch: {boundary_report}")
        geometry_report = verify_boundary_geometry(reopened, d, details["ifc_unit_scale_m"])
        boundary_report["geometry_agreement_verified"] = True
        boundary_report["status"] = "GEOMETRY_READY_ONLY"
        boundary_report["boundary_geometry"] = geometry_report
        report["energy_space_boundary_audit"] = boundary_report
        report["runtime_checks"]["energy_space_boundaries"] = boundary_report["status"]
        report.update({"status": "ifc_authoring_verified", "ifcopenshell_version": ifcopenshell.version,
                       "verified": details, "sha256_ifc": hashlib.sha256(path.read_bytes()).hexdigest()})
        report["runtime_checks"].update({"ifc_roundtrip": "PASS", "schema_validation": "PASS",
                                          "geometry_kernel": "PASS"})
    (output / "ifc_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("out"))
    ap.add_argument("--length-unit", choices=("m", "mm"), default="m")
    args = ap.parse_args()
    print(json.dumps(run(args.output, Dimensions(), length_unit=args.length_unit), indent=2))
