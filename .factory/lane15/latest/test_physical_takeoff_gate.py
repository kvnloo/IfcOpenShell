# This file was generated with the assistance of an AI coding tool.
"""Negative controls for synthetic IFC-physical-to-thermal geometry preflight."""
import unittest
from unittest.mock import patch

from ifc_author import Dimensions, bounds_from_endpoints, pieces
from physical_takeoff_gate import check_assembly


class PhysicalTakeoffTests(unittest.TestCase):
    def test_default_material_quantities_and_cavity(self):
        r = check_assembly(Dimensions())
        self.assertAlmostEqual(r['physical_wall_volume_m3'], 22.08)
        self.assertAlmostEqual(r['physical_slab_volume_m3'], 34.944)
        self.assertAlmostEqual(r['total_shell_material_volume_m3'], 57.024)
        self.assertAlmostEqual(r['nominal_air_volume_m3'], 240.)
        self.assertAlmostEqual(r['outer_volume_m3'], 297.024)
        self.assertEqual(r['material_intersections_m3'], 0)
        self.assertIsNone(r['energy_demand_kwh'])
        self.assertIsNone(r['embodied_carbon_kgco2e'])

    def test_representative_buildings(self):
        for d in (Dimensions(6, 8, 2.7), Dimensions(18, 12, 3.6), Dimensions(30, 20, 7)):
            with self.subTest(d=d):
                self.assertEqual(check_assembly(d)['component_count'], 6)

    def test_100_parametric_buildings(self):
        for i in range(100):
            d = Dimensions(4+i/8, 5+i/10, 2.4+i/50, .1+i/1000, .12+i/2000)
            with self.subTest(i=i):
                self.assertEqual(check_assembly(d)['wall_corner_face_contacts'], 4)

    def _mutate(self, name, fn):
        d = Dimensions()
        items = pieces(d)
        fn(next(x for x in items if x['name'] == name), d)
        with patch('physical_takeoff_gate.pieces', return_value=items):
            return check_assembly(d)

    def test_catches_wall_collision(self):
        def mutate(x, d):
            x['p2'] = (d.length+d.wall/2, 0.)
            x['bbox'] = bounds_from_endpoints(x['p1'], x['p2'], d.wall, d.height)
        with self.assertRaisesRegex(AssertionError, 'Material overlap'):
            self._mutate('South', mutate)

    def test_catches_detached_roof(self):
        def mutate(x, d):
            x['z'] += 0.05
            low, high = x['bbox']
            x['bbox'] = ((low[0], low[1], low[2]+.05), (high[0], high[1], high[2]+.05))
        with self.assertRaisesRegex(AssertionError, 'Detached component'):
            self._mutate('Roof', mutate)

    def test_catches_wrong_slab_winding(self):
        def mutate(x, d):
            x['polyline'] = list(reversed(x['polyline']))
        with self.assertRaisesRegex(AssertionError, 'slab winding'):
            self._mutate('Floor', mutate)

    def test_catches_corrupted_declared_bounds(self):
        def mutate(x, d):
            low, high = x['bbox']
            x['bbox'] = ((low[0]+0.01, low[1], low[2]), high)
        with self.assertRaisesRegex(AssertionError, 'declared and reconstructed'):
            self._mutate('East', mutate)

    def test_catches_skewed_wall(self):
        def mutate(x, d):
            x['p2'] = (0.05, -d.wall)
        with self.assertRaisesRegex(AssertionError, 'not axis-aligned'):
            self._mutate('West', mutate)

    def test_catches_missing_slab(self):
        d = Dimensions()
        items = [x for x in pieces(d) if x['name'] != 'Roof']
        with patch('physical_takeoff_gate.pieces', return_value=items):
            with self.assertRaisesRegex(AssertionError, 'Missing/duplicated'):
                check_assembly(d)

    def test_rejects_wrong_extrusion_sense(self):
        def mutate(x, d):
            x['sense'] = 'POSITIVE'
        with self.assertRaisesRegex(AssertionError, 'wrong slab extrusion'):
            self._mutate('Floor', mutate)


if __name__ == '__main__':
    unittest.main()
