# This file was generated with the assistance of an AI coding tool.
"""Portable reference-geometry gates; IFC kernel tests run only when installed."""
import math
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from ifc_author import Dimensions, bounds_from_endpoints, pieces, expected, matrix_for_wall, run
import numpy as np


class IFCContractTests(unittest.TestCase):
    def test_default_nominal_shell_metrics(self):
        e = expected(Dimensions())
        self.assertEqual((e['zone_floor_area_m2'], e['zone_volume_m3'], e['zone_shell_area_m2']),
                         (80, 240, 268))
        self.assertIsNone(e['energy_demand_kwh'])

    def test_physical_shell_not_identical_to_thermal_shell(self):
        d = Dimensions()
        self.assertEqual(expected(d)['physical_bbox_m'], [[-.2, -.2, -.2], [10.2, 8.2, 3.2]])

    def test_six_physical_products(self):
        p = pieces(Dimensions())
        self.assertEqual([x['name'] for x in p], ['South', 'East', 'North', 'West', 'Floor', 'Roof'])
        self.assertEqual((sum(x['kind']=='IfcWall' for x in p), sum(x['kind']=='IfcSlab' for x in p)), (4, 2))

    def test_south_and_north_walls_outside_nominal_zone(self):
        p = {x['name']: x for x in pieces(Dimensions())}
        self.assertEqual(p['South']['bbox'], ((0., -.2, 0.), (10., 0., 3.)))
        self.assertEqual(p['North']['bbox'], ((0., 8., 0.), (10., 8.2, 3.)))

    def test_east_west_bounds_complete_corner_ring(self):
        p = {x['name']: x for x in pieces(Dimensions())}
        self.assertEqual(p['East']['bbox'], ((10., -.2, 0.), (10.2, 8.2, 3.)))
        self.assertEqual(p['West']['bbox'], ((-.2, -.2, 0.), (0., 8.2, 3.)))

    def test_slabs_on_external_side_of_thermal_boundaries(self):
        p = {x['name']: x for x in pieces(Dimensions())}
        self.assertEqual(p['Floor']['bbox'], ((-.2, -.2, -.2), (10.2, 8.2, 0.)))
        self.assertEqual(p['Roof']['bbox'], ((-.2, -.2, 3.), (10.2, 8.2, 3.2)))

    def test_wall_frames_preserve_lengths_and_handedness(self):
        for s in pieces(Dimensions()):
            if s['kind'] == 'IfcWall':
                m = matrix_for_wall(s['p1'], s['p2'], np)
                self.assertAlmostEqual(np.linalg.det(m[:3, :3]), 1.0)
                self.assertTrue(np.allclose(m[:2, 3], s['p1']))
                self.assertTrue(np.allclose(m[:2, 0] * math.dist(s['p1'], s['p2']) + m[:2, 3], s['p2']))

    def test_nonstandard_dimensions(self):
        d = Dimensions(12, 4, 2.5, .1, .15)
        self.assertEqual(expected(d)['zone_volume_m3'], 120)
        self.assertEqual(expected(d)['physical_bbox_m'], [[-.1, -.1, -.15], [12.1, 4.1, 2.65]])

    def test_reject_invalid_dimensions(self):
        for kwargs in ({'length': 0}, {'wall': float('nan')}, {'slab': 3}, {'wall': -1},
                       {'width': float('inf')}, {'wall': 9}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Dimensions(**kwargs)

    def test_zero_length_wall_rejected(self):
        with self.assertRaises(ValueError):
            bounds_from_endpoints((2, 2), (2, 2), .2, 3)

    def test_runtime_evidence_never_claims_energy_results(self):
        with TemporaryDirectory() as tmp:
            with patch.dict('sys.modules', {'ifcopenshell': None}):
                report = run(Path(tmp), Dimensions())
            self.assertEqual(report['status'], 'blocked')
            self.assertEqual(report['runtime_checks']['ifc_roundtrip'], 'NOT_RUN')
            self.assertIsNone(report['reference']['energy_demand_kwh'])
            self.assertFalse((Path(tmp)/'single_zone.ifc').exists())


if __name__ == '__main__':
    unittest.main()
