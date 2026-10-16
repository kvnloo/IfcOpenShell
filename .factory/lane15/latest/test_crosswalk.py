# This file was generated with the assistance of an AI coding tool.
"""Test IFC physical inner faces against existing USDA/IDF thermal shell.

Pure-Python preflight only: this does not measure meshed IFC surfaces.
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).with_name('baseline')))
from single_zone_contract import shell, area_vector
from ifc_author import Dimensions, pieces


def crosswalk(d: Dimensions):
    reference = shell(d.length, d.width, d.height)
    solids = {item['name']: item for item in pieces(d)}
    if reference.keys() != solids.keys():
        raise AssertionError('IFC piece names differ from thermal shell')
    for name, vertices in reference.items():
        obj = solids[name]
        low, high = obj['bbox']
        for v in vertices:
            if not all(low[i] - 1e-8 <= v[i] <= high[i] + 1e-8 for i in range(3)):
                raise AssertionError(f'{name} thermal vertex lies outside physical extent')
        if obj['kind'] == 'IfcWall':
            a, b = obj['p1'], obj['p2']
            dx, dy = b[0]-a[0], b[1]-a[1]
            length2 = dx*dx + dy*dy
            # Reference wall must lie on the inner physical face, not material centroid.
            for x, y, _ in vertices:
                if abs((x-a[0])*dy - (y-a[1])*dx) > 1e-8:
                    raise AssertionError(f'{name}: reference is not on inside wall face')
                along = ((x-a[0])*dx + (y-a[1])*dy) / length2
                if not 0 <= along <= 1:
                    raise AssertionError(f'{name}: reference exceeds wall end')
            av = area_vector(vertices)
            # Thermal outward normal is the right normal of the CCW wall axis.
            nx, ny = dy, -dx
            if abs(av[0]*dx + av[1]*dy) > 1e-8 or av[0]*nx + av[1]*ny <= 0:
                raise AssertionError(f'{name}: thermal normal points into the zone')
        else:
            boundary_z = obj['z']
            if not all(abs(v[2] - boundary_z) < 1e-8 for v in vertices):
                raise AssertionError(f'{name}: thermal surface misses inside slab face')
            if (name == 'Floor' and obj['sense'] != 'NEGATIVE') or (name == 'Roof' and obj['sense'] != 'POSITIVE'):
                raise AssertionError(f'{name}: physical slab intrudes into nominal thermal volume')
    return {'thermal_surfaces_mapped': 6, 'reference_is_physical_interior': True}


class IFCIDFCrosswalkTests(unittest.TestCase):
    def test_default_reference_fits_physical_inner_faces(self):
        self.assertEqual(crosswalk(Dimensions())['thermal_surfaces_mapped'], 6)

    def test_parametric_reference_fits_100_boxes(self):
        for i in range(100):
            d = Dimensions(4 + i/10, 8 + i/20, 2.5 + i/100, .1 + i/1000, .15)
            with self.subTest(i=i):
                crosswalk(d)

    def test_detect_misplaced_wall(self):
        # Independent negative test: alter physical plan while preserving thermal shell.
        old_pieces = pieces
        def corrupt(d):
            data = old_pieces(d)
            data[0]['p1'] = (0., 0.02)
            return data
        import unittest.mock
        with unittest.mock.patch('test_crosswalk.pieces', side_effect=corrupt):
            with self.assertRaisesRegex(AssertionError, 'South'):
                crosswalk(Dimensions())

    def test_detect_wrong_slab_direction(self):
        old_pieces = pieces
        def corrupt(d):
            data = old_pieces(d)
            data[-2]['sense'] = 'POSITIVE'
            return data
        import unittest.mock
        with unittest.mock.patch('test_crosswalk.pieces', side_effect=corrupt):
            with self.assertRaisesRegex(AssertionError, 'Floor'):
                crosswalk(Dimensions())


if __name__ == '__main__':
    unittest.main()
