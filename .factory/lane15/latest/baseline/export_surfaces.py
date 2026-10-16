# This file was generated with the assistance of an AI coding tool.
"""Emit a geometry-only OpenUSD/IDF preflight from one nominal building shell.

The EnergyPlus file is an *incomplete fragment*, not a runnable load model.
Only reference polygons are exported, not physical IFC wall-face geometry.
"""
from pathlib import Path
import argparse
import json
from single_zone_contract import measurements, self_test, shell


def write_usda(path, length=10.0, width=8.0, height=3.0):
    lines = ['#usda 1.0', '(', '    upAxis = "Z"', '    metersPerUnit = 1', ')', '', 'def Xform "Building" {']
    for name, vertices in shell(length, width, height).items():
        points = ", ".join("(" + ", ".join(f"{n:.6f}" for n in vertex) + ")" for vertex in vertices)
        lines += [f'    def Mesh "{name}" {{', '        int[] faceVertexCounts = [4]',
                  '        int[] faceVertexIndices = [0, 1, 2, 3]',
                  f'        point3f[] points = [{points}]',
                  '        uniform token subdivisionScheme = "none"', '    }']
    lines += ['}', '']
    path.write_text("\n".join(lines), encoding="utf-8")


def write_idf_fragment(path, length=10.0, width=8.0, height=3.0):
    lines = ["! Geometry-only fragment. Not an energy model or simulation result.",
             "! Constructions below are undefined placeholders, by design.",
             "GlobalGeometryRules, UpperLeftCorner, CounterClockWise, World;",
             "Zone, TestZone, 0, 0, 0, 0, 1, 1, autocalculate, autocalculate;", ""]
    for name, vertices in shell(length, width, height).items():
        kind = "Floor" if name == "Floor" else "Roof" if name == "Roof" else "Wall"
        external = "Ground" if kind == "Floor" else "Outdoors"
        sun = "NoSun" if kind == "Floor" else "SunExposed"
        wind = "NoWind" if kind == "Floor" else "WindExposed"
        # The IDF declares UpperLeftCorner; begin vertical walls at their upper-left.
        # Rotating the cycle preserves outward normals and polygon geometry.
        if kind == "Wall":
            vertices = vertices[-1:] + vertices[:-1]
        fields = [name, kind, f"{kind}Placeholder", "TestZone", external, "", sun, wind, "autocalculate", "4"]
        for xyz in vertices:
            fields.extend(f"{v:.6f}" for v in xyz)
        lines += ["BuildingSurface:Detailed,", "  " + ",\n  ".join(fields) + ";", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def export(out, length=10.0, width=8.0, height=3.0):
    # Validate before creating files; keeps invalid inputs fail-closed.
    shell(length, width, height)
    self_test()
    out.mkdir(parents=True, exist_ok=True)
    usd_path = out / "single_zone.usda"
    idf_path = out / "single_zone_geometry.idf"
    write_usda(usd_path, length, width, height)
    write_idf_fragment(idf_path, length, width, height)
    data = measurements(length, width, height)
    data["dimensions_m"] = {"length": length, "width": width, "height": height}
    (out / "metrics.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    assert usd_path.read_text().count('def Mesh "') == 6
    assert idf_path.read_text().count("BuildingSurface:Detailed,") == 6
    assert data["energy_demand_kwh"] is None
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--length", type=float, default=10.0)
    parser.add_argument("--width", type=float, default=8.0)
    parser.add_argument("--height", type=float, default=3.0)
    args = parser.parse_args()
    print(json.dumps(export(args.out, args.length, args.width, args.height), indent=2))
