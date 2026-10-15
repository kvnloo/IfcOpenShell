# This file was generated with the assistance of an AI coding tool.
"""Fail-closed IFC -> OpenUSD -> EnergyPlus -> Civilization evidence gate.

Wave 6 is a local prototype, not a proof of any real energy performance.
The existing geometry-only IDF fragment must never be called a load model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "baseline"))

from test_export_invariants import Building, Surface, area as face_area, parse_idf, parse_usda, verify_cross_format, verify_shell
from test_crosswalk import crosswalk
from ifc_author import Dimensions, pieces, run as run_ifc
from physical_takeoff_gate import check_assembly


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_openusd_probe(path: Path, building: Building) -> dict:
    """Only real pxr stage parsing can return PASS, not the USDA regex parser."""
    try:
        from pxr import Gf, Usd, UsdGeom
    except ImportError:
        return {"status": "NOT_RUN", "reason": "pxr/OpenUSD Python runtime unavailable"}
    try:
        stage = Usd.Stage.Open(str(path))
        if stage is None:
            raise AssertionError("OpenUSD failed to open USDA stage")
        if not math.isclose(float(UsdGeom.GetStageMetersPerUnit(stage)), 1.0, abs_tol=1e-12):
            raise AssertionError("OpenUSD units are not metres")
        if str(UsdGeom.GetStageUpAxis(stage)) != "Z":
            raise AssertionError("OpenUSD is not Z-up")
        xforms = UsdGeom.XformCache()
        meshes = {}
        for name in ("Floor", "Roof", "South", "North", "East", "West"):
            prim = stage.GetPrimAtPath(f"/Building/{name}")
            if not prim or not prim.IsA(UsdGeom.Mesh):
                raise AssertionError(f"OpenUSD missing/non-mesh prim: {name}")
            mesh = UsdGeom.Mesh(prim)
            if str(mesh.GetOrientationAttr().Get()) != "rightHanded":
                raise AssertionError(f"OpenUSD mesh orientation is not rightHanded: {name}")
            if str(mesh.GetSubdivisionSchemeAttr().Get()) != "none":
                raise AssertionError(f"OpenUSD mesh subdivision is not none: {name}")
            if list(mesh.GetFaceVertexCountsAttr().Get()) != [4]:
                raise AssertionError(f"OpenUSD wrong face topology: {name}")
            if list(mesh.GetFaceVertexIndicesAttr().Get()) != [0, 1, 2, 3]:
                raise AssertionError(f"OpenUSD wrong winding indices: {name}")
            transform = xforms.GetLocalToWorldTransform(prim)
            points = mesh.GetPointsAttr().Get()
            if points is None or len(points) != 4:
                raise AssertionError(f"OpenUSD wrong point count: {name}")
            transformed = tuple(tuple(float(c) for c in transform.Transform(Gf.Vec3d(*p))) for p in points)
            meshes[name] = Surface(name, "Floor" if name == "Floor" else "Roof" if name == "Roof" else "Wall", transformed)
        verified = verify_shell(meshes, building)
        return {"status": "PASS", "checked_faces": 6, "volume_m3": verified["enclosed_volume_m3"]}
    except Exception as exc:
        return {"status": "FAIL", "reason": str(exc)}



def validated_ifc_receipt(result: dict, ifc_path: Path, d: Dimensions, length_unit: str) -> bool:
    """Validate the full saved-IFC receipt, not a self-reported PASS flag.

    This is a receipt integrity check, not a replacement for running the IFC
    geometry kernel. A caller must still obtain ``result`` from ``run_ifc``.
    """
    checks, verified = result.get("runtime_checks", {}), result.get("verified", {})
    if not isinstance(checks, dict) or not isinstance(verified, dict):
        return False
    if result.get("status") != "ifc_authoring_verified" or result.get("length_unit") != length_unit:
        return False
    if any(checks.get(k) != "PASS" for k in ("ifc_roundtrip", "schema_validation", "geometry_kernel")):
        return False
    if verified.get("schema") != "IFC4" or verified.get("kernel_bodies_checked") != 6:
        return False
    if verified.get("validation_errors") != 0 or verified.get("kernel_vertices_unit") != "metres":
        return False
    if verified.get("convert_back_units") is not False:
        return False
    scale = {"m": 1.0, "mm": 0.001}.get(length_unit)
    if scale is None or not isinstance(verified.get("ifc_unit_scale_m"), (int, float)):
        return False
    if not math.isclose(verified["ifc_unit_scale_m"], scale, rel_tol=0, abs_tol=1e-12):
        return False
    if not ifc_path.is_file() or result.get("sha256_ifc") != sha256(ifc_path):
        return False
    # Require native triangulated volume evidence, not just matching extrema.
    if verified.get("kernel_closed_manifold_bodies") != 6:
        return False
    if verified.get("kernel_single_shell_bodies") != 6:
        return False
    actual_volumes = verified.get("geometry_kernel_volume_m3", {})
    library_volumes = verified.get("geometry_kernel_library_volume_m3", {})
    actual = verified.get("geometry_kernel_bounds_m", {})
    targets = {item["name"]: item["bbox"] for item in pieces(d)}
    if not isinstance(actual, dict) or set(actual) != set(targets):
        return False
    if not isinstance(actual_volumes, dict) or set(actual_volumes) != set(targets):
        return False
    if not isinstance(library_volumes, dict) or set(library_volumes) != set(targets):
        return False
    try:
        for name, (low, high) in actual.items():
            target_low, target_high = targets[name]
            volume = actual_volumes[name]
            target_volume = math.prod(b - a for a, b in zip(target_low, target_high))
            if not isinstance(volume, (int, float)) or not math.isfinite(volume):
                return False
            if not math.isclose(volume, target_volume, rel_tol=5e-4, abs_tol=1e-5):
                return False
            other_volume = library_volumes[name]
            if not isinstance(other_volume, (int, float)) or not math.isfinite(other_volume):
                return False
            if not math.isclose(other_volume, volume, rel_tol=5e-4, abs_tol=1e-5):
                return False
            if len(low) != 3 or len(high) != 3:
                return False
            if any(not math.isfinite(v) for v in (*low, *high)):
                return False
            if any(abs(a - b) > 2e-4 for a, b in zip((*low, *high), (*target_low, *target_high))):
                return False
    except (TypeError, ValueError):
        return False
    return True


def validated_boundary_receipt(result: dict, d: Dimensions) -> bool:
    """Only promote verified planar boundary geometry, never bare topology."""
    audit = result.get("energy_space_boundary_audit", {})
    if not isinstance(audit, dict) or result.get("runtime_checks", {}).get("energy_space_boundaries") != "GEOMETRY_READY_ONLY":
        return False
    details = audit.get("boundary_geometry", {})
    if not isinstance(details, dict):
        return False
    expected_areas = {"Floor": d.length * d.width, "Roof": d.length * d.width,
                      "South": d.length * d.height, "North": d.length * d.height,
                      "East": d.width * d.height, "West": d.width * d.height}
    expected_normals = {"Floor": (0, 0, -1), "Roof": (0, 0, 1),
                        "South": (0, -1, 0), "North": (0, 1, 0),
                        "East": (1, 0, 0), "West": (-1, 0, 0)}
    if audit.get("status") != "GEOMETRY_READY_ONLY" or audit.get("geometry_agreement_verified") is not True:
        return False
    # audit_model's semantic topology findings must agree with the promoted status.
    if audit.get("expected_boundaries") != 6 or audit.get("observed_boundaries") != 6:
        return False
    if any(audit.get(key) != [] for key in ("missing", "unexpected", "duplicate", "invalid")):
        return False
    if details.get("status") != "GEOMETRY_READY_ONLY" or details.get("checked_surfaces") != 6:
        return False
    measured, normals = details.get("area_m2"), details.get("normal")
    if not isinstance(measured, dict) or set(measured) != set(expected_areas):
        return False
    if not isinstance(normals, dict) or set(normals) != set(expected_normals):
        return False
    try:
        if not math.isclose(details.get("thermal_volume_m3", -1), d.length * d.width * d.height,
                            rel_tol=0, abs_tol=1e-6):
            return False
        for name, target_area in expected_areas.items():
            if not math.isfinite(measured[name]) or not math.isclose(
                measured[name], target_area, rel_tol=0, abs_tol=1e-5
            ):
                return False
            normal = normals[name]
            if not isinstance(normal, (list, tuple)) or len(normal) != 3:
                return False
            if any(not math.isfinite(component) or
                   not math.isclose(component, expected, rel_tol=0, abs_tol=1e-7)
                   for component, expected in zip(normal, expected_normals[name])):
                return False
        return True
    except (TypeError, ValueError):
        return False

def check_case(directory: Path, allow_ifc_author: bool = False, ifc_units: str = "m") -> dict:
    """Produce a deterministic, locally auditable per-building capability packet."""
    metrics_path = directory / "metrics.json"
    usda_path = directory / "single_zone.usda"
    idf_path = directory / "single_zone_geometry.idf"
    metrics = json.loads(metrics_path.read_text())
    xyz = metrics["dimensions_m"]
    building = Building(*(float(xyz[k]) for k in ("length", "width", "height")))
    dim = Dimensions(building.length_m, building.width_m, building.height_m)
    usd = parse_usda(usda_path)
    idf = parse_idf(idf_path)
    usd_result = verify_shell(usd, building)
    idf_result = verify_shell(idf, building)
    verify_cross_format(usd, idf)
    crosswalk(dim)
    volume = building.length_m * building.width_m * building.height_m
    area = 2 * (building.length_m * building.width_m + building.length_m * building.height_m
                + building.width_m * building.height_m)
    for actual in (metrics["nominal_volume_m3"], usd_result["enclosed_volume_m3"],
                   idf_result["enclosed_volume_m3"]):
        if not math.isclose(actual, volume, rel_tol=1e-9, abs_tol=1e-7):
            raise AssertionError("Cross-format volume mismatch")
    for actual in (metrics["envelope_area_m2"], usd_result["shell_area_m2"],
                   idf_result["shell_area_m2"]):
        if not math.isclose(actual, area, rel_tol=1e-9, abs_tol=1e-7):
            raise AssertionError("Cross-format area mismatch")
    if metrics["energy_demand_kwh"] is not None:
        raise AssertionError("Unverified energy demand inserted in geometry-only metrics")
    if set(metrics["face_areas_m2"]) != set(usd):
        raise AssertionError("Face-area ledger has missing/extra surfaces")
    for name, measured in metrics["face_areas_m2"].items():
        if not isinstance(measured, (int, float)) or not math.isclose(
            measured, face_area(usd[name]), rel_tol=1e-9, abs_tol=1e-7
        ):
            raise AssertionError(f"Face-area ledger mismatch: {name}")
    packet = {
        "building": directory.name,
        "dimensions_m": xyz,
        "sha256": {p.name: sha256(p) for p in (metrics_path, usda_path, idf_path)},
        "analytic_geometry": {"status": "PASS", "faces": 6,
                              "floor_area_m2": building.length_m * building.width_m,
                              "envelope_area_m2": area, "volume_m3": volume,
                              "evidence_level": "synthetic static-geometry only"},
        "analytic_physical_shell": check_assembly(dim),
        "real_openusd_stage": native_openusd_probe(usda_path, building),
        "ifc_authoring": {"status": "NOT_RUN", "reason": "Explicit opt-in required"},
        "ifc_energy_boundary_handoff": {"status": "NOT_RUN", "reason": "Requires authored IFC space boundaries"},
        "bonsai_visual_inspection": {"status": "NOT_RUN", "reason": "Blender/Bonsai GUI not inspected"},
        "energyplus_simulation": {"status": "NOT_RUN", "reason": (
            "IDF is a geometry-only fragment with undefined constructions; "
            "needs real constructions, schedules and simulation inputs"),
            "energyplus_binary_present": bool(shutil.which("energyplus"))},
        "energy_demand_kwh": None,
        "license_scope": "AI-assisted local prototype; review licensing before promotion",
    }
    if allow_ifc_author:
        if ifc_units not in ("m", "mm", "both"):
            raise ValueError("ifc_units must be m, mm, or both")
        units = ("m", "mm") if ifc_units == "both" else (ifc_units,)
        reports = {}
        checks = {}
        boundaries = {}
        for unit in units:
            output = directory / "ifc_runtime"
            if len(units) > 1:
                output = output / unit
            try:
                result = run_ifc(output, dim, length_unit=unit)
                reports[unit] = result
                receipt_complete = validated_ifc_receipt(result, output / "single_zone.ifc", dim, unit)
                checks[unit] = "PASS" if receipt_complete else "NOT_RUN"
                boundaries[unit] = validated_boundary_receipt(result, dim) if receipt_complete else False
            except Exception as exc:
                reports[unit] = {"status": "FAIL", "reason": str(exc)}
                checks[unit] = "FAIL"
                boundaries[unit] = False
        statuses = set(checks.values())
        packet["ifc_authoring"] = {
            "status": "FAIL" if "FAIL" in statuses else "PASS" if statuses == {"PASS"} else "NOT_RUN",
            "units": checks, "evidence": reports,
            **({} if statuses == {"PASS"} else {"reason": "Incomplete or mismatched native IFC receipt"}),
        }
        packet["ifc_energy_boundary_handoff"] = (
            {"status": "GEOMETRY_READY_ONLY", "units": list(units), "evidence": {
                unit: reports[unit]["energy_space_boundary_audit"] for unit in units}}
            if all(boundaries.values()) else
            {"status": "NOT_RUN", "reason": "Complete native IFC boundary geometry evidence unavailable"}
        )
        if len(units) > 1:
            parity = all(checks[unit] == "PASS" for unit in units)
            if parity:
                bboxes_m = reports["m"]["verified"]["geometry_kernel_bounds_m"]
                bboxes_mm = reports["mm"]["verified"]["geometry_kernel_bounds_m"]
                volumes_m = reports["m"]["verified"]["geometry_kernel_volume_m3"]
                volumes_mm = reports["mm"]["verified"]["geometry_kernel_volume_m3"]
                parity = all(math.isclose(volumes_m[name], volumes_mm[name], rel_tol=5e-4, abs_tol=1e-5)
                             for name in volumes_m)
            if parity:
                parity = all(all(abs(a - b) <= 2e-4 for a, b in zip(
                    (*bboxes_m[name][0], *bboxes_m[name][1]),
                    (*bboxes_mm[name][0], *bboxes_mm[name][1]))) for name in bboxes_m)
            packet["ifc_metres_millimetres_parity"] = {
                "status": "PASS" if parity else "NOT_RUN",
                "scope": "IFC kernel solid bounds in metres; not an energy simulation",
            }
            if not parity and packet["ifc_authoring"]["status"] == "PASS":
                packet["ifc_authoring"]["status"] = "NOT_RUN"
                packet["ifc_energy_boundary_handoff"] = {"status": "NOT_RUN", "reason": "IFC unit parity mismatch"}
    required = ("ifc_authoring", "ifc_energy_boundary_handoff", "real_openusd_stage",
                "bonsai_visual_inspection", "energyplus_simulation")
    packet["civilization"] = {"verified_construction_capability": all(packet[k]["status"] == "PASS" for k in required),
                               "status": "UNVERIFIED", "route": "Manufacturing->IFC/Bonsai->OpenUSD->EnergyPlus->Civilization"}
    if packet["civilization"]["verified_construction_capability"]:
        packet["civilization"]["status"] = "VERIFIED"
    return packet


def native_ifc_complete(packet: dict) -> bool:
    """Require separate m/mm saved-kernel and thermal-boundary receipts.

    Called only on packets freshly computed by ``check_case``; each unit's
    ``validated_ifc_receipt`` checks its IFC SHA and the independently measured
    mesh bounds/volume. This does not certify EnergyPlus or Bonsai.
    """
    authoring = packet.get("ifc_authoring", {})
    if not isinstance(authoring, dict) or authoring.get("status") != "PASS":
        return False
    if authoring.get("units") != {"m": "PASS", "mm": "PASS"}:
        return False
    parity = packet.get("ifc_metres_millimetres_parity", {})
    boundary = packet.get("ifc_energy_boundary_handoff", {})
    boundary_units = boundary.get("units") if isinstance(boundary, dict) else None
    return (isinstance(parity, dict) and parity.get("status") == "PASS"
            and isinstance(boundary, dict) and boundary.get("status") == "GEOMETRY_READY_ONLY"
            and boundary_units in (["m", "mm"], ["mm", "m"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path, help="Building fixture directories")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--author-ifc", action="store_true", help="Attempt IfcOpenShell runtime authoring/geometry")
    parser.add_argument("--ifc-units", choices=("m", "mm", "both"), default="m",
                        help="IFC length-unit mode when --author-ifc is used")
    parser.add_argument("--require-native-ifc", action="store_true",
                        help="Fail CI unless fresh IFC4 m/mm saved geometry and thermal boundaries pass")
    args = parser.parse_args()
    if args.require_native_ifc and (not args.author_ifc or args.ifc_units != "both"):
        parser.error("--require-native-ifc needs --author-ifc --ifc-units both")
    packets = [check_case(p, args.author_ifc, args.ifc_units) for p in args.inputs]
    report = {"schema": "lane15-construction-preflight-v1", "cases": packets}
    if args.require_native_ifc:
        missing = [p["building"] for p in packets if not native_ifc_complete(p)]
        report["requirements"] = {"native_ifc_m_mm": {
            "status": "BLOCKED" if missing else "PASS",
            "failing_cases": missing,
            "scope": "Fresh IFC4 m/mm saved roundtrip, kernel geometry and thermal boundaries only",
            "not_verified": ["Bonsai", "OpenUSD", "EnergyPlus", "energy_demand_kwh"],
        }}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(packets)} geometry preflights passed; "
          f"{sum(p['civilization']['verified_construction_capability'] for p in packets)} verified capabilities")
    if any(any(p[gate]["status"] == "FAIL" for gate in
               ("real_openusd_stage", "ifc_authoring", "energyplus_simulation")) for p in packets):
        raise SystemExit(1)
    if args.require_native_ifc and missing:
        print(f"Native IFC4 m/mm gate BLOCKED for: {', '.join(missing)}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
