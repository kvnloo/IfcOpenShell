# This file was generated with the assistance of an AI coding tool.
"""IFC boundary geometry output must satisfy the downstream evidence gate.

Mock IFC entities exercise the inter-module contract, not the native kernel.
"""
from copy import deepcopy
import unittest

from boundary_geometry import verify_boundary_geometry
from ifc_author import Dimensions
from runtime_gate import validated_boundary_receipt
from test_boundary_geometry import mock_geometry


class BoundaryHandoffIntegrationTests(unittest.TestCase):
    def make_packet(self, dimensions):
        model, _ = mock_geometry(dimensions)
        geometry = verify_boundary_geometry(model, dimensions, 1.0)
        return {
            "runtime_checks": {"energy_space_boundaries": "GEOMETRY_READY_ONLY"},
            "energy_space_boundary_audit": {
                "status": "GEOMETRY_READY_ONLY", "geometry_agreement_verified": True,
                "expected_boundaries": 6, "observed_boundaries": 6,
                "missing": [], "unexpected": [], "duplicate": [], "invalid": [],
                "boundary_geometry": geometry,
            },
        }

    def test_producer_receipt_is_consumable_for_three_buildings(self):
        for dimensions in (Dimensions(), Dimensions(4, 3, 2.5), Dimensions(20, 15, 6)):
            with self.subTest(dimensions=dimensions):
                packet = self.make_packet(dimensions)
                detail = packet["energy_space_boundary_audit"]["boundary_geometry"]
                self.assertFalse(detail["energy_simulation_verified"])
                self.assertTrue(validated_boundary_receipt(packet, dimensions))

    def test_missing_or_inverted_normal_blocks_handoff(self):
        d = Dimensions()
        packet = self.make_packet(d)
        missing = deepcopy(packet)
        missing["energy_space_boundary_audit"]["boundary_geometry"].pop("normal", None)
        self.assertFalse(validated_boundary_receipt(missing, d))
        flipped = deepcopy(packet)
        flipped["energy_space_boundary_audit"]["boundary_geometry"]["normal"]["South"] = [0, 1, 0]
        self.assertFalse(validated_boundary_receipt(flipped, d))


if __name__ == "__main__":
    unittest.main()
