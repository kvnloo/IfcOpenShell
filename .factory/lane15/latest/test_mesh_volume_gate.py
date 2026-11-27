# This file was generated with the assistance of an AI coding tool.
"""Wedge-with-box-bounds regression and independent triangle-volume controls."""
import math
import unittest

from mesh_volume_gate import measure_closed_solid, verify_solid_volume


def triangulated_box():
    v = [(0,0,0), (1,0,0), (1,1,0), (0,1,0),
         (0,0,1), (1,0,1), (1,1,1), (0,1,1)]
    # Right-handed, outward. Each quadrilateral split into two triangles.
    quads = [(0,3,2,1), (4,5,6,7), (0,1,5,4),
             (1,2,6,5), (2,3,7,6), (3,0,4,7)]
    triangles = [i for a,b,c,d in quads for i in (a,b,c,a,c,d)]
    return [x for point in v for x in point], triangles


def triangulated_wedge():
    # Same [0,1]^3 bounding box as a cube, but volume is only 0.5 m3.
    v = [(0,0,0), (1,0,0), (0,1,0), (0,0,1), (1,0,1), (0,1,1)]
    faces = [(0,2,1), (3,4,5),
             (0,1,4), (0,4,3), (0,3,5), (0,5,2),
             (1,2,5), (1,5,4)]
    return [x for point in v for x in point], [i for tri in faces for i in tri]


def overlapping_disconnected_boxes():
    """Two closed shells: nominal 1 m³ summed volume, but intersect/gap.

    Box A volume is 0.6 m³. Box B volume is 0.4 m³ and overlaps A.
    Aggregate bounds are [0, 1]³, but the physical union is smaller.
    """
    base, face_indices = triangulated_box()
    solids = []
    for low, high in (((0, 0, 0), (0.6, 1, 1)),
                      ((0.4, 0.2, 0), (1, 0.2 + 2 / 3, 1))):
        coords = [base[i] * (high[i % 3] - low[i % 3]) + low[i % 3]
                  for i in range(len(base))]
        solids.append(coords)
    vertices = solids[0] + solids[1]
    faces = face_indices + [i + len(solids[0]) // 3 for i in face_indices]
    return vertices, faces


class SolidVolumeTests(unittest.TestCase):
    def test_closed_outward_cube_is_one_cubic_metre(self):
        vertices, faces = triangulated_box()
        result = verify_solid_volume(vertices, faces, 1.0)
        self.assertAlmostEqual(result['signed_volume_m3'], 1.0)
        self.assertTrue(result['closed_manifold'])
        self.assertEqual(result['triangles'], 12)

    def test_wedge_matches_extents_but_not_volume(self):
        vertices, faces = triangulated_wedge()
        self.assertEqual([min(vertices[i::3]) for i in range(3)], [0,0,0])
        self.assertEqual([max(vertices[i::3]) for i in range(3)], [1,1,1])
        self.assertAlmostEqual(measure_closed_solid(vertices, faces)['signed_volume_m3'], 0.5)
        with self.assertRaisesRegex(AssertionError, 'volume mismatch'):
            verify_solid_volume(vertices, faces, 1.0)

    def test_same_bounds_and_total_volume_but_disconnected_shells_fail(self):
        vertices, faces = overlapping_disconnected_boxes()
        self.assertEqual([min(vertices[i::3]) for i in range(3)], [0, 0, 0])
        self.assertEqual([max(vertices[i::3]) for i in range(3)], [1, 1, 1])
        with self.assertRaisesRegex(AssertionError, 'Disconnected closed mesh shells'):
            verify_solid_volume(vertices, faces, 1.0)

    def test_vertex_touching_shells_do_not_count_as_one_manifold(self):
        base, faces = triangulated_box()
        shifted = [base[i] + 1.0 for i in range(len(base))]
        aggregate = base + shifted  # Cubes share only (1, 1, 1).
        aggregate_faces = faces + [i + len(base) // 3 for i in faces]
        with self.assertRaisesRegex(AssertionError, 'Disconnected closed mesh shells'):
            measure_closed_solid(aggregate, aggregate_faces)

    def test_unreferenced_vertices_do_not_create_a_second_shell(self):
        vertices, faces = triangulated_box()
        result = verify_solid_volume(vertices + [100, 100, 100], faces, 1.0)
        self.assertTrue(result['single_connected_shell'])

    def test_duplicated_edge_vertices_weld_cleanly(self):
        vertices, faces = triangulated_box()
        # Mimic independently triangulated faces with repeated edge vertices.
        repeated = []
        for index in faces:
            repeated.extend(vertices[index*3:index*3+3])
        result = verify_solid_volume(repeated, list(range(len(faces))), 1.0)
        self.assertEqual(result['welded_vertices'], 8)

    def test_origin_shift_and_rectangular_scales_do_not_change_volume(self):
        for width, height, depth, offset in (
            (12.4, 0.2, 3.7, (-100, 250, 30)),
            (0.12, 15.0, 0.3, (1000, -2000, 50)),
            (3.0, 2.5, 3.1, (0, 0, 0)),
        ):
            base, faces = triangulated_box()
            verts = [base[i] * (width, height, depth)[i % 3] + offset[i % 3]
                     for i in range(len(base))]
            with self.subTest(dimensions=(width, height, depth)):
                actual = verify_solid_volume(verts, faces, width * height * depth)
                self.assertAlmostEqual(actual['signed_volume_m3'], width * height * depth, places=7)

    def test_reverse_winding_rejected(self):
        vertices, faces = triangulated_box()
        flipped = [x for i in range(0, len(faces), 3)
                   for x in (faces[i], faces[i+2], faces[i+1])]
        with self.assertRaisesRegex(AssertionError, 'Nonpositive'):
            measure_closed_solid(vertices, flipped)

    def test_missing_face_rejected(self):
        vertices, faces = triangulated_box()
        with self.assertRaisesRegex(AssertionError, 'mesh edge'):
            measure_closed_solid(vertices, faces[:-3])

    def test_duplicated_face_rejected(self):
        vertices, faces = triangulated_box()
        with self.assertRaisesRegex(AssertionError, 'mesh edge'):
            measure_closed_solid(vertices, faces + faces[:3])

    def test_one_flipped_triangle_rejected(self):
        vertices, faces = triangulated_box()
        faces[:3] = [faces[0], faces[2], faces[1]]
        with self.assertRaisesRegex(AssertionError, 'mesh edge'):
            measure_closed_solid(vertices, faces)

    def test_out_of_range_or_fractional_face_rejected(self):
        vertices, faces = triangulated_box()
        for invalid in (99, -1, 0.25, math.nan):
            with self.subTest(invalid=invalid), self.assertRaises(AssertionError):
                measure_closed_solid(vertices, [invalid, *faces[1:]])

    def test_degenerate_triangle_rejected(self):
        vertices, faces = triangulated_box()
        with self.assertRaisesRegex(AssertionError, 'Degenerate'):
            measure_closed_solid(vertices, [0,0,0,*faces[3:]])

    def test_nonfinite_coordinate_rejected(self):
        vertices, faces = triangulated_box()
        vertices[0] = math.inf
        with self.assertRaisesRegex(AssertionError, 'Non-finite'):
            measure_closed_solid(vertices, faces)

    def test_negative_or_nan_target_rejected(self):
        vertices, faces = triangulated_box()
        for volume in (-1, 0, math.nan, math.inf):
            with self.subTest(volume=volume), self.assertRaises(ValueError):
                verify_solid_volume(vertices, faces, volume)


if __name__ == '__main__':
    unittest.main()
