# This file was generated with the assistance of an AI coding tool.
"""Contract tests. Mock IFC entities prove logic only, not the native runtime."""
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace as NS
from unittest.mock import patch
import sys
import unittest

from boundary_geometry import (
    NAMES, boundary_frame, create_boundary_links, expected_faces, same_cycle,
    verify_boundary_geometry, world_points,
)
from ifc_author import Dimensions


@dataclass
class IfcEntity:
    type_name: str

    def is_a(self, klass=None):
        return self.type_name == klass if klass else self.type_name


def mock_geometry(d):
    space = NS(Name="TestZone")
    space.GlobalId = "zone-guid"
    relations = []
    for name, pts in expected_faces(d).items():
        f = boundary_frame(pts)
        position = NS(Location=NS(Coordinates=f["location"]),
                      Axis=NS(DirectionRatios=f["axis"]),
                      RefDirection=NS(DirectionRatios=f["ref_direction"]))
        plane = IfcEntity("IfcPlane")
        plane.Position = position
        curve = IfcEntity("IfcCurveBoundedPlane")
        curve.BasisSurface = plane
        curve.InnerBoundaries = ()
        outer = IfcEntity("IfcPolyline")
        outer.Points = [NS(Coordinates=p) for p in (*f["outer_boundary"], f["outer_boundary"][0])]
        curve.OuterBoundary = outer
        conn = IfcEntity("IfcConnectionSurfaceGeometry")
        conn.SurfaceOnRelatingElement = curve
        rel = NS(is_a=lambda: "IfcRelSpaceBoundary1stLevel", RelatingSpace=space,
                 RelatedBuildingElement=NS(Name=name), ConnectionGeometry=conn)
        relations.append(rel)
    model = NS(by_type=lambda kind: [space] if kind == "IfcSpace" else relations)
    return model, relations


class BoundaryGeometryTests(unittest.TestCase):
    def setUp(self):
        self.d = Dimensions()

    def test_six_reference_frames_roundtrip_world_geometry(self):
        faces = expected_faces(self.d)
        self.assertEqual(set(faces), set(NAMES))
        for name, vertices in faces.items():
            with self.subTest(face=name):
                frame = boundary_frame(vertices)
                actual = world_points(frame["location"], frame["axis"],
                                      frame["ref_direction"], frame["outer_boundary"])
                self.assertTrue(same_cycle(actual, vertices))

    def test_supported_authoring_api_invoked_for_six_surfaces(self):
        pkg, api = ModuleType("ifcopenshell"), ModuleType("ifcopenshell.api")
        boundary, root = ModuleType("ifcopenshell.api.boundary"), ModuleType("ifcopenshell.api.root")
        pkg.__path__, api.__path__ = [], []
        pkg.api, api.boundary, api.root = api, boundary, root
        relationships = []

        def create_entity(model, ifc_class, name):
            self.assertEqual(ifc_class, "IfcRelSpaceBoundary1stLevel")
            relationship = NS(Name=name)
            relationships.append(relationship)
            return relationship

        def edit_attributes(model, entity, **kwargs):
            entity.attributes = kwargs

        def assign_geometry(model, rel_space_boundary, **kwargs):
            rel_space_boundary.frame = kwargs

        root.create_entity = create_entity
        boundary.edit_attributes = edit_attributes
        boundary.assign_connection_geometry = assign_geometry
        elements = {name: NS(Name=name) for name in NAMES}
        fake = {name: module for name, module in (
            ("ifcopenshell", pkg), ("ifcopenshell.api", api),
            ("ifcopenshell.api.boundary", boundary), ("ifcopenshell.api.root", root))}
        with patch.dict(sys.modules, fake):
            create_boundary_links(NS(), NS(Name="TestZone"), elements, self.d)
        self.assertEqual(len(relationships), 6)
        self.assertEqual({r.attributes["related_building_element"].Name for r in relationships}, set(NAMES))
        for r in relationships:
            name = r.attributes["related_building_element"].Name
            self.assertEqual(r.attributes["physical_or_virtual"], "PHYSICAL")
            expected_class = "EXTERNAL_EARTH" if name == "Floor" else "EXTERNAL"
            self.assertEqual(r.attributes["internal_or_external"], expected_class)
            frame = r.frame
            actual = world_points(frame["location"], frame["axis"],
                                  frame["ref_direction"], frame["outer_boundary"])
            self.assertTrue(same_cycle(actual, expected_faces(self.d)[name]))

    def test_mock_ifc_connection_surfaces(self):
        model, _ = mock_geometry(self.d)
        report = verify_boundary_geometry(model, self.d, 1.0)
        self.assertEqual(report["status"], "GEOMETRY_READY_ONLY")
        self.assertFalse(report["energy_simulation_verified"])
        self.assertAlmostEqual(sum(report["area_m2"].values()), 268.0)
        self.assertEqual(report["thermal_volume_m3"], 240)

    def test_other_dimensions(self):
        for d in [Dimensions(4, 3, 2.5), Dimensions(20, 15, 6)]:
            with self.subTest(dimensions=d):
                model, _ = mock_geometry(d)
                packet = verify_boundary_geometry(model, d, 1.0)
                self.assertAlmostEqual(sum(packet["area_m2"].values()),
                                       2*(d.length*d.width+d.length*d.height+d.width*d.height))

    def test_corrupt_coordinate_rejected(self):
        model, rels = mock_geometry(self.d)
        rels[2].ConnectionGeometry.SurfaceOnRelatingElement.OuterBoundary.Points[1].Coordinates = (11.0, 0.0)
        with self.assertRaisesRegex(AssertionError, "differs"):
            verify_boundary_geometry(model, self.d, 1.0)

    def test_unit_mismatch_rejected(self):
        model, _ = mock_geometry(self.d)
        with self.assertRaisesRegex(AssertionError, "differs"):
            verify_boundary_geometry(model, self.d, 0.001)

    def test_reversed_winding_rejected(self):
        vertices = expected_faces(self.d)["South"]
        self.assertFalse(same_cycle(vertices, vertices[::-1]))
        model, rels = mock_geometry(self.d)
        curve = rels[2].ConnectionGeometry.SurfaceOnRelatingElement.OuterBoundary
        initial = [p.Coordinates for p in curve.Points[:-1]]
        curve.Points = [NS(Coordinates=p) for p in (*initial[::-1], initial[-1])]
        with self.assertRaisesRegex(AssertionError, "differs|closed"):
            verify_boundary_geometry(model, self.d, 1.0)

    def test_generic_and_second_level_rejected(self):
        for cls in ("IfcRelSpaceBoundary", "IfcRelSpaceBoundary2ndLevel"):
            model, rels = mock_geometry(self.d)
            rels[0].is_a = lambda cls=cls: cls
            with self.subTest(cls=cls), self.assertRaisesRegex(AssertionError, "boundary level"):
                verify_boundary_geometry(model, self.d, 1.0)

    def test_missing_boundary_rejected(self):
        model, rels = mock_geometry(self.d)
        rels.pop()
        with self.assertRaisesRegex(AssertionError, "names mismatch"):
            verify_boundary_geometry(model, self.d, 1.0)

    def test_duplicate_boundary_rejected(self):
        model, rels = mock_geometry(self.d)
        rels.append(rels[0])
        with self.assertRaisesRegex(AssertionError, "Duplicate"):
            verify_boundary_geometry(model, self.d, 1.0)

    def test_nonplanar_input_rejected(self):
        pts = list(expected_faces(self.d)["Roof"])
        pts[2] = (pts[2][0], pts[2][1], pts[2][2] + 0.01)
        with self.assertRaises(ValueError):
            boundary_frame(pts)

    def test_opening_and_wrong_entity_rejected(self):
        for change in ("openings", "wrong-connection"):
            model, rels = mock_geometry(self.d)
            conn = rels[0].ConnectionGeometry
            if change == "openings":
                conn.SurfaceOnRelatingElement.InnerBoundaries = (object(),)
            else:
                conn.type_name = "IfcConnectionCurveGeometry"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_boundary_geometry(model, self.d, 1.0)


if __name__ == "__main__":
    unittest.main()
