# This file was generated with the assistance of an AI coding tool.
"""Positive + mutation controls for IFC energy-handoff semantic boundary coverage."""
from types import SimpleNamespace
import unittest

from energy_handoff_gate import TARGETS, audit_model, evaluate


def valid_rows():
    return [dict(element_name=name, element_type=element_type,
                 boundary_level="IfcRelSpaceBoundary1stLevel", physical_or_virtual="PHYSICAL",
                 internal_or_external=external, has_connection_geometry=True)
            for name, (element_type, external) in TARGETS.items()]


class MockProduct:
    def __init__(self, name, kind, gid):
        self.Name, self.kind, self.GlobalId = name, kind, gid

    def is_a(self):
        return self.kind


class MockModel:
    def __init__(self, rows, space_override=None):
        self.space = MockProduct("TestZone", "IfcSpace", "zone-id")
        self.spaces = space_override if space_override is not None else [self.space]
        self.relations = [SimpleNamespace(is_a=lambda kind=r["boundary_level"]: kind,
                         RelatingSpace=self.space,
                         RelatedBuildingElement=MockProduct(r["element_name"], r["element_type"], r["element_name"]),
                         PhysicalOrVirtualBoundary=r["physical_or_virtual"],
                         InternalOrExternalBoundary=r["internal_or_external"],
                         ConnectionGeometry=object() if r["has_connection_geometry"] else None)
                          for r in rows]

    def by_type(self, kind):
        return self.spaces if kind == "IfcSpace" else self.relations


class EnergyBoundaryTests(unittest.TestCase):
    def test_positive_semantic_topology_is_not_energy_verification(self):
        packet = evaluate(valid_rows())
        self.assertEqual(packet["status"], "TOPOLOGY_READY_ONLY")
        self.assertFalse(packet["geometry_agreement_verified"])
        self.assertFalse(packet["energy_simulation_verified"])

    def test_current_author_missing_boundaries_blocks(self):
        packet = evaluate([])
        self.assertEqual(packet["missing"], sorted(TARGETS))
        self.assertEqual(packet["status"], "BLOCKED")

    def test_missing_one_boundary(self):
        self.assertIn("Roof", evaluate(valid_rows()[:-1])["missing"])

    def test_duplicate_boundary(self):
        packet = evaluate(valid_rows() + [valid_rows()[0]])
        self.assertIn("South", packet["duplicate"])

    def test_unexpected_boundary(self):
        packet = evaluate(valid_rows() + [{**valid_rows()[0], "element_name": "Window"}])
        self.assertIn("Window", packet["unexpected"])

    def test_missing_connection_geometry(self):
        rows = valid_rows()
        rows[0]["has_connection_geometry"] = False
        self.assertTrue(any("connection geometry" in err for err in evaluate(rows)["invalid"]))

    def test_reject_virtual_boundaries(self):
        rows = valid_rows()
        rows[0]["physical_or_virtual"] = "VIRTUAL"
        self.assertEqual(evaluate(rows)["status"], "BLOCKED")

    def test_wrong_ground_classification(self):
        rows = valid_rows()
        next(r for r in rows if r["element_name"] == "Floor")["internal_or_external"] = "EXTERNAL"
        self.assertEqual(evaluate(rows)["status"], "BLOCKED")

    def test_wrong_related_element_type(self):
        rows = valid_rows()
        rows[0]["element_type"] = "IfcSlab"
        self.assertEqual(evaluate(rows)["status"], "BLOCKED")

    def test_generic_base_boundary_is_rejected(self):
        rows = valid_rows()
        rows[0]["boundary_level"] = "IfcRelSpaceBoundary"
        self.assertEqual(evaluate(rows)["status"], "BLOCKED")
        self.assertTrue(any("first-level" in issue for issue in evaluate(rows)["invalid"]))

    def test_second_level_requires_separate_explicit_contract(self):
        rows = valid_rows()
        rows[0]["boundary_level"] = "IfcRelSpaceBoundary2ndLevel"
        self.assertEqual(audit_model(MockModel(rows))["status"], "BLOCKED")

    def test_ifc_like_objects_are_read_through(self):
        self.assertEqual(audit_model(MockModel(valid_rows()))["status"], "TOPOLOGY_READY_ONLY")

    def test_wrong_or_missing_testzone(self):
        packet = audit_model(MockModel(valid_rows(), space_override=[]))
        self.assertEqual(packet["status"], "BLOCKED")
        self.assertIn("exactly one", packet["reason"])

    def test_other_spatial_zone_boundaries_not_counted(self):
        m = MockModel(valid_rows())
        m.relations[0].RelatingSpace = MockProduct("Elsewhere", "IfcSpace", "different")
        self.assertIn("South", audit_model(m)["missing"])


if __name__ == '__main__':
    unittest.main()
