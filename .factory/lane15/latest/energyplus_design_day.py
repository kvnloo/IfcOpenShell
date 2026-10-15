# This file was generated with the assistance of an AI coding tool.
"""Build a version-pinned, *candidate* EnergyPlus design-day IDF from a checked shell.

Uses a 2026 EnergyPlus 26.2 field layout (including the optional Space Name
before Outside Boundary Condition). Design-day inputs and materials are
synthetic; this is neither an EPW weather run nor a measured energy result.
The separate native gate must execute EnergyPlus before any runtime PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / "baseline"))

from test_export_invariants import Building, parse_idf, verify_shell

VERSION = "26.2"
# Conservative, explicit material hypotheses matching the published EnergyPlus
# 1ZoneUncontrolled reference structure; not calibrated building properties.
HEADER = f"""! AI-assisted Lane 15 synthetic validation scenario (NOT a real building).
! Design days only. No EPW/weather-file period; no HVAC, occupants or energy demand.
! Source for compatible object field layout: EnergyPlus 26.2.0 1ZoneUncontrolled.idf.
Version,{VERSION};
Timestep,4;
Building,Lane15 Synthetic One Zone,0,Suburbs,0.04,0.004,MinimalShadowing,30,6;
SimulationControl,No,No,No,Yes,No,No,1;
Site:Location,Reference Denver Site,39.74,-105.18,-7,1829;
SizingPeriod:DesignDay,Reference Winter,12,21,WinterDesignDay,-15.5,0,,,Wetbulb,-15.5,,,,,81198,3,340,No,No,No,ASHRAEClearSky,,,,,0;
SizingPeriod:DesignDay,Reference Summer,7,21,SummerDesignDay,32,15.2,,,Wetbulb,15.5,,,,,81198,4.9,0,No,No,No,ASHRAEClearSky,,,,,1;
Material:NoMass,ReferenceWallLayer,Rough,2.290965,0.9,0.75,0.75;
Material:NoMass,ReferenceRoofLayer,Rough,5.456,0.9,0.75,0.75;
Material,ReferenceSlabLayer,MediumRough,0.1014984,1.729577,2242.585,836.8,0.9,0.65,0.65;
Construction,WallConstruction,ReferenceWallLayer;
Construction,RoofConstruction,ReferenceRoofLayer;
Construction,FloorConstruction,ReferenceSlabLayer;
! Synthetic soil boundary assumed constant for the two design days.
Site:GroundTemperature:BuildingSurface,18,18,18,18,18,18,18,18,18,18,18,18;
Zone,TestZone,0,0,0,0,1,1,autocalculate,autocalculate;
GlobalGeometryRules,UpperLeftCorner,CounterClockWise,World;
"""
FOOTER = "Output:Variable,*,Zone Mean Air Temperature,Hourly;\n"
CONSTRUCTION = {"Floor": "FloorConstruction", "Roof": "RoofConstruction"}


def objects(text: str) -> list[list[str]]:
    # Only use this minimal split for the controlled, generated fixture; this
    # is NOT a general IDF parser (e.g. embedded separators aren't supported).
    without_comments = "\n".join(line.split("!", 1)[0] for line in text.splitlines())
    return [[part.strip() for part in obj.split(",")]
            for obj in without_comments.split(";") if obj.strip()]


def candidate(fragment: Path, metrics: Path) -> str:
    """Transcribe *verified* six-face geometry into EnergyPlus 26.2 fields."""
    from single_zone_contract import measurements

    expected = json.loads(metrics.read_text(encoding="utf-8"))
    xyz = expected["dimensions_m"]
    building = Building(*(float(xyz[k]) for k in ("length", "width", "height")))
    old_surfaces = parse_idf(fragment)  # rejects unaccounted openings, loads, etc.
    verified = verify_shell(old_surfaces, building)
    if abs(verified["enclosed_volume_m3"] - expected["nominal_volume_m3"]) > 1e-6:
        raise ValueError("Geometry and reference volume disagree")
    if any(abs(float(expected["face_areas_m2"][n]) -
               measurements(building.length_m, building.width_m, building.height_m)["face_areas_m2"][n]) > 1e-6
           for n in old_surfaces):
        raise ValueError("Geometry and reference face-area ledger disagree")
    if expected.get("energy_demand_kwh") is not None:
        raise ValueError("Source is no longer a geometry-only reference")

    parts = []
    for fields in objects(fragment.read_text(encoding="utf-8")):
        if fields[0] != "BuildingSurface:Detailed":
            continue
        if len(fields) != 23 or fields[10] != "4":
            raise ValueError("Unexpected legacy source surface field layout")
        name, kind = fields[1:3]
        fields[3] = CONSTRUCTION.get(name, "WallConstruction")
        fields.insert(5, "")  # 26.2 Space Name (after Zone Name, before Outside Boundary Condition)
        if len(fields) != 24 or fields[11] != "4":
            raise AssertionError("Modern IDF field layout corrupted")
        if (kind == "Floor") != (name == "Floor") or (kind == "Roof") != (name == "Roof"):
            raise ValueError("Surface category mismatch")
        parts.append(",\n  ".join(fields) + ";")
    if len(parts) != 6:
        raise ValueError("Not exactly six surfaces")
    text = HEADER + "\n" + "\n\n".join(parts) + "\n" + FOOTER
    audit(text, fragment)
    return text


def audit(model: str, fragment: Path) -> dict:
    """Independent structural sanity checks, NOT an EnergyPlus parser."""
    source = {row["name"]: row for row in (
        {"name": parts[1], "vertices": parts[11:]} for parts in objects(fragment.read_text())
        if parts[0] == "BuildingSurface:Detailed"
    )}
    parsed = objects(model)
    counts = {}
    for fields in parsed:
        counts[fields[0]] = counts.get(fields[0], 0) + 1
    must = {"BuildingSurface:Detailed": 6, "SizingPeriod:DesignDay": 2, "Zone": 1,
            "GlobalGeometryRules": 1, "Building": 1, "SimulationControl": 1,
            "Material:NoMass": 2, "Material": 1, "Construction": 3}
    if any(counts.get(k) != n for k, n in must.items()):
        raise AssertionError("Design-day object population mismatch")
    if counts.get("RunPeriod", 0) or any(k.startswith("ZoneHVAC") or k.startswith("ZoneInfiltration")
                                      for k in counts):
        raise AssertionError("Unexpected weather-period or HVAC/load objects")
    for day in (row for row in parsed if row[0] == "SizingPeriod:DesignDay"):
        # Verify the 26.2 IDD positional structure, not just object presence.
        if (len(day) != 27 or day[7:9] != ["", ""] or day[9] != "Wetbulb" or
                day[11:15] != ["", "", "", ""] or day[21] != "ASHRAEClearSky"):
            raise AssertionError("Invalid EnergyPlus 26.2 design-day field layout")
    if parsed[0] != ["Version", VERSION]:
        raise AssertionError("Unpinned EnergyPlus schema")
    controls = [row for row in parsed if row[0] == "SimulationControl"][0]
    if controls[1:6] != ["No", "No", "No", "Yes", "No"]:
        raise AssertionError("Simulation must run design days, not EPW")
    constructions = {row[1]: row[2] for row in parsed if row[0] == "Construction"}
    layers = {row[1] for row in parsed if row[0] in {"Material", "Material:NoMass"}}
    if not set(constructions.values()) <= layers:
        raise AssertionError("Undefined material")
    checked = set()
    for fields in parsed:
        if fields[0] != "BuildingSurface:Detailed":
            continue
        if len(fields) != 24 or fields[11] != "4" or fields[4] != "TestZone" or fields[5] != "":
            raise AssertionError("EnergyPlus 26.2 surface/space field mismatch")
        if fields[3] not in constructions or fields[1] in checked:
            raise AssertionError("Undefined construction or duplicate surface")
        if fields[1] not in source or fields[12:] != source[fields[1]]["vertices"]:
            raise AssertionError("Geometry changed during IDF handoff")
        checked.add(fields[1])
    if checked != set(source) or len(checked) != 6:
        raise AssertionError("Surface source mismatch")
    return {"status": "STATIC_ONLY", "energyplus_schema": VERSION, "surfaces": 6,
            "materials": len(layers), "constructions": len(constructions),
            "sizing_days": 2, "native_engine": "NOT_RUN", "weather_file": "NOT_PROVIDED",
            "energy_demand_kwh": None}


def run_engine(idf: Path, out: Path, executable: str = "energyplus") -> dict:
    """Execute native EnergyPlus and explicitly reject missing/error logs."""
    binary = shutil.which(executable)
    if binary is None:
        return {"status": "BLOCKED", "reason": f"EnergyPlus executable unavailable: {executable}"}
    try:
        version = subprocess.run([binary, "--version"], capture_output=True, text=True,
                                 timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "FAIL", "reason": f"Cannot inspect EnergyPlus version: {e}"}
    declared = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or not re.search(r"\b26\.2(?:\.0)?\b", declared):
        return {"status": "BLOCKED", "reason": "Expected native EnergyPlus 26.2; refusing wrong IDD version",
                "reported_engine_version": declared[-250:]}
    out.mkdir(parents=True, exist_ok=True)
    # Isolate each engine invocation from all prior output (no stale-log PASS).
    # Keep the unique directory and its error log for reproducible evidence.
    run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=out))
    try:
        proc = subprocess.run([binary, "--output-directory", str(run_dir), str(idf.resolve())],
                              capture_output=True, text=True, timeout=240, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"status": "FAIL", "reason": str(e), "engine_output_directory": str(run_dir)}
    err = run_dir / "eplusout.err"
    log = err.read_text(errors="replace") if err.exists() else ""
    severe = len(re.findall(r"(?im)^\s*\*\*\s*(?:Severe|Fatal)\s*\*\*", log))
    result = {"status": "PASS" if proc.returncode == 0 and err.exists() and severe == 0 else "FAIL",
              "engine_version": declared[-250:], "engine_exit_code": proc.returncode,
              "engine_error_log_exists": err.exists(),
              "engine_output_directory": str(run_dir),
              "severe_or_fatal_lines": severe, "stdout_tail": proc.stdout[-500:],
              "stderr_tail": proc.stderr[-500:], "engine_error_log_sha256":
              hashlib.sha256(err.read_bytes()).hexdigest() if err.exists() else None,
              "energy_demand_kwh": None}
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("fixture", type=Path, help="Existing generated benchmark directory")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--require-native", action="store_true")
    p.add_argument("--energyplus-bin", default="energyplus")
    ns = p.parse_args()
    ns.out.mkdir(parents=True, exist_ok=True)
    model = candidate(ns.fixture / "single_zone_geometry.idf", ns.fixture / "metrics.json")
    idf = ns.out / "design_day_26_2.idf"
    idf.write_text(model, encoding="utf-8")
    report = audit(model, ns.fixture / "single_zone_geometry.idf")
    report["sha256_idf"] = hashlib.sha256(idf.read_bytes()).hexdigest()
    report["source_fixture"] = ns.fixture.name
    if ns.require_native:
        report["native"] = run_engine(idf, ns.out / "engine", ns.energyplus_bin)
    (ns.out / "design_day_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if ns.require_native and report["native"]["status"] != "PASS":
        return 2 if report["native"]["status"] == "BLOCKED" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
