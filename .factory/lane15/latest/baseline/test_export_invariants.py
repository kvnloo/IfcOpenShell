# This file was generated with the assistance of an AI coding tool.
"""Independent exported-surface contract for Lane 15's synthetic fixture.

Scope: parse the deliberately small, emitted USDA/IDF grammar. This is not
USD or EnergyPlus parser validation, IFC validation, or an energy simulation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import random
import re
from tempfile import TemporaryDirectory
import unittest

from export_surfaces import export
from single_zone_contract import shell as reference_shell

Point = tuple[float, float, float]


@dataclass(frozen=True)
class Building:
    length_m: float = 10.0
    width_m: float = 8.0
    height_m: float = 3.0

@dataclass(frozen=True)
class Surface:
    name: str
    kind: str
    vertices: tuple[Point, ...]


def diff(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def area_vector(s):
    p, q, r, t = s.vertices
    av1 = cross(diff(q, p), diff(r, p))
    av2 = cross(diff(r, p), diff(t, p))
    return tuple((x + y) / 2 for x, y in zip(av1, av2))


def area(s):
    return math.sqrt(sum(x * x for x in area_vector(s)))

def signed_enclosed_volume(surfaces):
    result = 0
    for s in surfaces:
        c = tuple(sum(v[i] for v in s.vertices) / 4 for i in range(3))
        result += sum(x * y for x, y in zip(area_vector(s), c)) / 3
    return result

def build(path):
    export(path)


def parse_usda(path: Path) -> dict[str, Surface]:
    data = path.read_text(encoding="utf-8")
    # Check the entire metadata values, not just prefixes: the old substring
    # check accepted `metersPerUnit = 1000` and incorrectly certified SI meshes.
    if not data.startswith("#usda 1.0\n"):
        raise AssertionError("USDA header mismatch")
    # This is a deliberately narrow, dependency-free parser. We do not evaluate
    # scene transforms: accepting them would certify untransformed local points
    # as though they were the USD world-space building geometry.
    uncommented = re.sub(r"(?m)#.*$", "", data)
    if re.search(r"\bxformOp(?::|Order\b)", uncommented):
        raise AssertionError("Unsupported USD scene transform in static geometry preflight")
    # This grammar certifies one Xform and exactly six surface meshes. USD can
    # also contain typed prims (Cube, Sphere, etc.) and untyped overrides that
    # a Mesh-only regex would silently drop from the cross-format audit.
    declared = re.findall(
        r'(?m)^\s*(def|over|class)\s+(?:([A-Za-z_][\w:]*)\s+)?"([^"\n]+)"\s*\{',
        uncommented,
    )
    expected_prims = Counter([("def", "Xform", "Building")] + [
        ("def", "Mesh", n) for n in ("Floor", "Roof", "South", "North", "East", "West")
    ])
    # No unparsed/unsupported prim declarations may disappear from this audit.
    all_declarations = re.findall(r"\b(?:def|over|class)\b", uncommented)
    if len(declared) != len(all_declarations) or Counter(declared) != expected_prims:
        raise AssertionError("Unexpected USD primitive declaration in six-face shell")
    metadata = data.split("def Xform", 1)[0]
    axes = re.findall(r'^\s*upAxis\s*=\s*"([^"\n]+)"\s*$', metadata, re.MULTILINE)
    units = re.findall(r'^\s*metersPerUnit\s*=\s*([^\n#]+?)\s*$', metadata, re.MULTILINE)
    if axes != ["Z"] or len(units) != 1:
        raise AssertionError("USDA unit or axis metadata missing, duplicated or invalid")
    try:
        metres_per_unit = float(units[0])
    except ValueError as exc:
        raise AssertionError("USDA metres-per-unit is not numeric") from exc
    if not math.isfinite(metres_per_unit) or metres_per_unit != 1.0:
        raise AssertionError("USDA unit scale must be exactly one metre")
    pattern = re.compile(r'def Mesh "([^"\n]+)"\s*\{([^{}]+)\}', re.MULTILINE)
    result: dict[str, Surface] = {}
    for name, block in pattern.findall(data):
        # The winding-to-outward-normal check below assumes the right-handed
        # USD convention. An authored leftHanded orientation reverses it.
        block_uncommented = re.sub(r"(?m)#.*$", "", block)
        orientations = re.findall(
            r'(?m)^\s*(?:uniform\s+)?token\s+orientation\s*=\s*"([^"\n]+)"\s*$',
            block_uncommented,
        )
        if len(re.findall(r"\borientation\s*=", block_uncommented)) != len(orientations) or (
            orientations and orientations != ["rightHanded"]
        ):
            raise AssertionError(f"Unsupported USD mesh orientation at {name}")
        # Unauthored subdivisionScheme defaults to Catmull-Clark in USD,
        # which does not preserve our intended raw planar polygon contract.
        subdivision = re.findall(
            r'(?m)^\s*(?:uniform\s+)?token\s+subdivisionScheme\s*=\s*"([^"\n]+)"\s*$',
            block_uncommented,
        )
        if subdivision != ["none"] or len(re.findall(r"\bsubdivisionScheme\s*=", block_uncommented)) != 1:
            raise AssertionError(f"Unsupported or missing USD mesh subdivision at {name}")
        if 'faceVertexCounts = [4]' not in block or 'faceVertexIndices = [0, 1, 2, 3]' not in block:
            raise AssertionError(f"Wrong mesh topology for {name}")
        raw = re.search(r'point3f\[\] points = \[([^\]]+)\]', block)
        if raw is None:
            raise AssertionError(f"No points for {name}")
        vertices = [
            tuple(float(x.strip()) for x in group.split(','))
            for group in re.findall(r'\(([^()]+)\)', raw.group(1))
        ]
        if len(vertices) != 4 or any(len(p) != 3 for p in vertices):
            raise AssertionError(f"Wrong face arity for {name}")
        if name in result:
            raise AssertionError(f"Duplicate USDA mesh {name}")
        result[name] = Surface(name, "Floor" if name == "Floor" else "Roof" if name == "Roof" else "Wall",
                               tuple(vertices))
    if len(result) != 6:
        raise AssertionError(f"Expected six USDA meshes, got {len(result)}")
    return result


def parse_idf(path: Path) -> dict[str, Surface]:
    data = "\n".join(line.split("!", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())
    commands = [obj.strip() for obj in data.split(";") if obj.strip()]
    # Verify the objects that make surface vertices meaningful to EnergyPlus.
    # A prefix regex previously admitted `WorldRelative`, and accepting just
    # one matching rule ignored conflicting duplicate GlobalGeometryRules.
    objects = [[part.strip() for part in obj.split(",")] for obj in commands]
    # This parser certifies only the deliberately narrow six-face export.
    # An extra window, shading or load object changes the energy handoff even
    # if the six gross opaque face polygons still match the USDA geometry.
    # A richer IDF needs an EnergyPlus-native audit, not this static PASS.
    allowed_objects = {"GlobalGeometryRules", "Zone", "BuildingSurface:Detailed"}
    unsupported = sorted({fields[0] for fields in objects if fields[0] not in allowed_objects})
    if unsupported:
        raise AssertionError("Unsupported EnergyPlus object(s) in geometry-only fragment: " + ", ".join(unsupported))
    geometry_rules = [parts for parts in objects if parts[0] == "GlobalGeometryRules"]
    if len(geometry_rules) != 1 or geometry_rules[0][1:4] != [
        "UpperLeftCorner", "CounterClockWise", "World"
    ]:
        raise AssertionError("Expected one exact EnergyPlus world-coordinate geometry rule")
    zones = [parts for parts in objects if parts[0] == "Zone"]
    if len(zones) != 1 or len(zones[0]) < 2 or zones[0][1] != "TestZone":
        raise AssertionError("Expected exactly one Zone named TestZone for the exported surfaces")
    result: dict[str, Surface] = {}
    for obj in commands:
        tokens = [x.strip() for x in obj.split(",")]
        if tokens[0] != "BuildingSurface:Detailed":
            continue
        if len(tokens) != 23 or tokens[10] != "4":
            raise AssertionError("Invalid EnergyPlus surface field count or vertex count")
        name, kind, construction, zone, boundary, other_zone, sun, wind, view_factor, numvertices = tokens[1:11]
        if zone != "TestZone" or not construction.endswith("Placeholder"):
            raise AssertionError("Unexpected zone or missing unresolved-construction flag")
        if kind == "Floor":
            if boundary != "Ground" or sun != "NoSun" or wind != "NoWind":
                raise AssertionError("Invalid floor boundary conditions")
        elif boundary != "Outdoors" or sun != "SunExposed" or wind != "WindExposed":
            raise AssertionError("Invalid wall/roof boundary conditions")
        vertices = tuple(tuple(float(tokens[11 + i * 3 + j]) for j in range(3)) for i in range(4))
        if name in result:
            raise AssertionError("Duplicate IDF surface")
        result[name] = Surface(name, kind, vertices)
    if len(result) != 6:
        raise AssertionError(f"Expected six IDF surfaces, got {len(result)}")
    return result


def verify_shell(surfaces: dict[str, Surface], b: Building, atol: float = 2e-5) -> dict[str, float]:
    """Independently verify topology, outward orientation, area and volume."""
    expected = {
        "Floor": ((0, 0, -1), b.length_m * b.width_m),
        "Roof": ((0, 0, +1), b.length_m * b.width_m),
        "South": ((0, -1, 0), b.length_m * b.height_m),
        "North": ((0, +1, 0), b.length_m * b.height_m),
        "East": ((+1, 0, 0), b.width_m * b.height_m),
        "West": ((-1, 0, 0), b.width_m * b.height_m),
    }
    if set(surfaces) != set(expected):
        raise AssertionError("Missing or extra surface")
    edge_use: Counter[tuple[Point, Point]] = Counter()
    directed: Counter[tuple[Point, Point]] = Counter()
    for name, s in surfaces.items():
        normal, surface_area = expected[name]
        av = area_vector(s)
        if not math.isclose(area(s), surface_area, rel_tol=0, abs_tol=atol):
            raise AssertionError(f"Area mismatch: {name}")
        if any(not math.isclose(av[i], normal[i] * surface_area, rel_tol=0, abs_tol=atol) for i in range(3)):
            raise AssertionError(f"Normal mismatch: {name}")
        for a, c in zip(s.vertices, s.vertices[1:] + s.vertices[:1]):
            edge_use[tuple(sorted((a, c)))] += 1
            directed[(a, c)] += 1
    if len(edge_use) != 12 or any(count != 2 for count in edge_use.values()):
        raise AssertionError("Open, non-manifold, or disconnected shell")
    if any(directed[(a, c)] != directed[(c, a)] for a, c in edge_use):
        raise AssertionError("Inconsistent paired edge direction")
    volume = signed_enclosed_volume(tuple(surfaces.values()))
    expected_volume = b.length_m * b.width_m * b.height_m
    if not math.isclose(volume, expected_volume, rel_tol=0, abs_tol=atol):
        raise AssertionError(f"Volume mismatch: {volume} vs {expected_volume}")
    return {"enclosed_volume_m3": volume, "shell_area_m2": sum(area(s) for s in surfaces.values()),
            "closed_undirected_edges": len(edge_use)}


def verify_cross_format(usd: dict[str, Surface], ep: dict[str, Surface], atol: float = 1e-6) -> None:
    if usd.keys() != ep.keys():
        raise AssertionError("Format face set mismatch")
    for name in usd:
        if usd[name].kind != ep[name].kind:
            raise AssertionError(f"Surface category mismatch: {name}")
        # A cyclic shift keeps the same outward-oriented face, unlike reversal.
        uverts, everts = usd[name].vertices, ep[name].vertices
        matches = any(
            all(all(abs(uverts[i][axis] - everts[(i + shift) % 4][axis]) <= atol
                    for axis in range(3)) for i in range(4))
            for shift in range(4)
        )
        if not matches:
            raise AssertionError(f"USDA/IDF geometry or winding mismatch at {name}")


class ExportRoundTrip(unittest.TestCase):
    def test_parse_both_exports(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            b = Building()
            build(out)
            u = parse_usda(out / "single_zone.usda")
            e = parse_idf(out / "single_zone_geometry.idf")
            self.assertEqual(verify_shell(u, b)["closed_undirected_edges"], 12)
            self.assertEqual(verify_shell(e, b)["enclosed_volume_m3"], 240.0)
            verify_cross_format(u, e)

    def test_100_parameterized_reference_shells(self):
        rand = random.Random(15015)
        for i in range(100):
            b = Building(round(rand.uniform(4, 25), 3), round(rand.uniform(4, 25), 3),
                         round(rand.uniform(2.1, 8), 3))
            faces = reference_shell(b.length_m, b.width_m, b.height_m)
            surfaces = {
                name: Surface(name, "Floor" if name == "Floor" else "Roof" if name == "Roof" else "Wall", points)
                for name, points in faces.items()
            }
            with self.subTest(i=i):
                verify_shell(surfaces, b, atol=1e-4)

    def test_detect_usda_winding_corruption(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            src = out / "single_zone.usda"
            text = src.read_text()
            text = text.replace('faceVertexIndices = [0, 1, 2, 3]', 'faceVertexIndices = [0, 3, 2, 1]', 1)
            src.write_text(text)
            with self.assertRaises(AssertionError):
                parse_usda(src)

    def test_detect_idf_coordinate_drift(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            ep = parse_idf(out / "single_zone_geometry.idf")
            usd = parse_usda(out / "single_zone.usda")
            original = ep["Roof"]
            vertices = list(original.vertices)
            vertices[0] = (vertices[0][0], vertices[0][1], vertices[0][2] + 0.25)
            ep["Roof"] = Surface(original.name, original.kind, tuple(vertices))
            with self.assertRaises(AssertionError):
                verify_cross_format(usd, ep)
            with self.assertRaises(AssertionError):
                verify_shell(ep, Building())

    def test_usda_rejects_prefixed_or_duplicated_unit_metadata(self):
        # These values used to pass because all start with the literal `1`.
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            src = out / "single_zone.usda"
            original = src.read_text()
            for unit in ("1000", "1e3", "1.5", "1e-3", "1.0001", "nan"):
                with self.subTest(unit=unit):
                    src.write_text(original.replace("metersPerUnit = 1", f"metersPerUnit = {unit}", 1))
                    with self.assertRaisesRegex(AssertionError, "unit"):
                        parse_usda(src)
            src.write_text(original.replace("metersPerUnit = 1", "metersPerUnit = 1\n    metersPerUnit = 0.001", 1))
            with self.assertRaisesRegex(AssertionError, "unit"):
                parse_usda(src)

    def test_usda_accepts_numeric_syntax_for_exact_si_units(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            src = out / "single_zone.usda"
            original = src.read_text()
            for unit in ("1.0", "1e0", "1.000000"):
                with self.subTest(unit=unit):
                    src.write_text(original.replace("metersPerUnit = 1", f"metersPerUnit = {unit}", 1))
                    self.assertEqual(len(parse_usda(src)), 6)

    def test_usda_rejects_duplicate_or_wrong_up_axis(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            src = out / "single_zone.usda"
            original = src.read_text()
            for value in ('upAxis = "Y"', 'upAxis = "Z"\n    upAxis = "Y"'):
                with self.subTest(value=value):
                    src.write_text(original.replace('upAxis = "Z"', value, 1))
                    with self.assertRaisesRegex(AssertionError, "axis"):
                        parse_usda(src)

    def test_idf_requires_exact_unique_geometry_rule(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone_geometry.idf"
            original = path.read_text()
            rule = "GlobalGeometryRules, UpperLeftCorner, CounterClockWise, World;"
            mutations = (
                original.replace(rule, rule.replace("World;", "WorldRelative;")),
                original.replace(rule, rule + "\nGlobalGeometryRules, LowerLeftCorner, ClockWise, Relative;"),
                original.replace(rule, ""),
            )
            for i, mutated in enumerate(mutations):
                with self.subTest(mutation=i):
                    path.write_text(mutated)
                    with self.assertRaisesRegex(AssertionError, "geometry rule"):
                        parse_idf(path)

    def test_idf_requires_declared_unique_thermal_zone(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone_geometry.idf"
            original = path.read_text()
            zone = "Zone, TestZone, 0, 0, 0, 0, 1, 1, autocalculate, autocalculate;"
            mutations = (
                original.replace(zone, ""),
                original.replace("Zone, TestZone,", "Zone, WrongZone,"),
                original.replace(zone, zone + "\n" + zone),
            )
            for i, mutated in enumerate(mutations):
                with self.subTest(mutation=i):
                    path.write_text(mutated)
                    with self.assertRaisesRegex(AssertionError, "Zone named TestZone"):
                        parse_idf(path)

    def test_usda_requires_non_subdivided_polygon_meshes(self):
        # USD defaults to Catmull-Clark when subdivisionScheme is absent.
        # Checking unchanged control points alone does not prove polygon export.
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            src = out / "single_zone.usda"
            original = src.read_text()
            scheme = '        uniform token subdivisionScheme = "none"'
            self.assertIn(scheme, original)
            roof = 'def Mesh "Roof" {'
            cases = {
                "missing": original.replace(scheme + "\n", "", 1),
                "catmullClark": original.replace(scheme, '        uniform token subdivisionScheme = "catmullClark"', 1),
                "bilinear": original.replace(scheme, '        uniform token subdivisionScheme = "bilinear"', 1),
                "duplicate": original.replace(roof, roof + '\n' + scheme, 1),
            }
            for name, changed in cases.items():
                with self.subTest(case=name):
                    src.write_text(changed)
                    with self.assertRaisesRegex(AssertionError, "subdivision"):
                        parse_usda(src)
            src.write_text(original.replace(scheme, '        token subdivisionScheme = "none"', 1))
            self.assertEqual(len(parse_usda(src)), 6)

    def test_usda_rejects_handedness_flip(self):
        # Changing mesh orientation flips the effective outward-facing normal
        # without editing points or faceVertexIndices.
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone.usda"
            original = path.read_text()
            insertion = 'def Mesh "Roof" {\n        uniform token orientation = "leftHanded"'
            path.write_text(original.replace('def Mesh "Roof" {', insertion, 1))
            with self.assertRaisesRegex(AssertionError, "orientation"):
                parse_usda(path)

    def test_usda_rejects_unaccounted_scene_transforms(self):
        # A USD xform can move or reflect the scene even if local mesh points
        # remain identical to the EnergyPlus surfaces.
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone.usda"
            original = path.read_text()
            mutations = (
                'double3 xformOp:translate = (100, 0, 0)\n    uniform token[] xformOpOrder = ["xformOp:translate"]',
                'float3 xformOp:scale = (1, -1, 1)\n    uniform token[] xformOpOrder = ["xformOp:scale"]',
            )
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    path.write_text(original.replace('def Xform "Building" {',
                                                     'def Xform "Building" {\n    ' + mutation, 1))
                    with self.assertRaisesRegex(AssertionError, "transform"):
                        parse_usda(path)

    def test_usda_explicit_right_handed_is_supported(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone.usda"
            path.write_text(path.read_text().replace('def Mesh "Roof" {',
                                   'def Mesh "Roof" {\n        uniform token orientation = "rightHanded"', 1))
            self.assertEqual(len(parse_usda(path)), 6)

    def test_detect_boundary_condition_drift(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp)
            build(out)
            path = out / "single_zone_geometry.idf"
            path.write_text(path.read_text().replace('Ground,', 'Outdoors,', 1))
            with self.assertRaises(AssertionError):
                parse_idf(path)


if __name__ == "__main__":
    unittest.main()
