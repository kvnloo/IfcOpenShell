# This file was generated with the assistance of an AI coding tool.
"""Independent mesh and IDF corner-convention checks, not engine validation."""

import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import trimesh

from export_surfaces import export
from test_export_invariants import parse_usda, parse_idf, verify_cross_format


def triangulated_shell(surfaces):
    vertices, faces, indices = [], [], {}
    for surface in surfaces.values():
        quad = []
        for v in surface.vertices:
            if v not in indices:
                indices[v] = len(vertices)
                vertices.append(v)
            quad.append(indices[v])
        faces += [[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]]
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


class IndependentGeometry(unittest.TestCase):
    def test_wall_start_vertex_matches_upper_left_corner_header(self):
        with TemporaryDirectory() as td:
            out = Path(td)
            export(out)
            surfaces = parse_idf(out / "single_zone_geometry.idf")
            expected_upper_left = {
                "South": (0.0, 0.0, 3.0),
                "North": (10.0, 8.0, 3.0),
                "East": (10.0, 0.0, 3.0),
                "West": (0.0, 8.0, 3.0),
            }
            for s in surfaces.values():
                if s.kind == "Wall":
                    with self.subTest(wall=s.name):
                        top_z = max(v[2] for v in s.vertices)
                        bottom_z = min(v[2] for v in s.vertices)
                        self.assertGreater(top_z, bottom_z)
                        self.assertEqual(s.vertices[0][2], top_z)
                        self.assertEqual(s.vertices[0], expected_upper_left[s.name])

    def test_independent_watertight_shell_usd_and_idf(self):
        with TemporaryDirectory() as td:
            out = Path(td)
            export(out)
            usd = parse_usda(out / "single_zone.usda")
            idf = parse_idf(out / "single_zone_geometry.idf")
            verify_cross_format(usd, idf)
            for name, surfaces in (("USD", usd), ("IDF", idf)):
                with self.subTest(format=name):
                    mesh = triangulated_shell(surfaces)
                    self.assertEqual(len(mesh.faces), 12)
                    self.assertEqual(len(mesh.vertices), 8)
                    self.assertTrue(mesh.is_watertight)
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertTrue(mesh.is_volume)
                    self.assertEqual(mesh.euler_number, 2)
                    self.assertTrue(math.isclose(mesh.volume, 240.0, abs_tol=1e-9))
                    self.assertTrue(math.isclose(mesh.area, 268.0, abs_tol=1e-9))
                    self.assertEqual(mesh.extents.tolist(), [10.0, 8.0, 3.0])

    def test_independent_mesh_detects_missing_face(self):
        with TemporaryDirectory() as td:
            out = Path(td)
            export(out)
            idf = parse_idf(out / "single_zone_geometry.idf")
            idf.pop("Roof")
            self.assertFalse(triangulated_shell(idf).is_watertight)

    def test_independent_mesh_detects_reversed_winding(self):
        with TemporaryDirectory() as td:
            out = Path(td)
            export(out)
            idf = parse_idf(out / "single_zone_geometry.idf")
            face = idf["South"]
            idf["South"] = type(face)(face.name, face.kind, tuple(reversed(face.vertices)))
            mesh = triangulated_shell(idf)
            self.assertFalse(mesh.is_winding_consistent)
            self.assertFalse(mesh.is_volume)

    def test_independent_mesh_detects_unit_scale_drift(self):
        with TemporaryDirectory() as td:
            out = Path(td)
            export(out)
            idf = parse_idf(out / "single_zone_geometry.idf")
            inflated = {}
            for name, face in idf.items():
                verts = tuple(tuple(1000 * c for c in v) for v in face.vertices)
                inflated[name] = type(face)(face.name, face.kind, verts)
            volume = triangulated_shell(inflated).volume
            self.assertTrue(math.isclose(volume / 240.0, 1e9, rel_tol=1e-10))
            self.assertNotAlmostEqual(volume, 240.0)


if __name__ == "__main__":
    unittest.main()
