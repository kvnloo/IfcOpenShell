# This file was generated with assistance from an AI coding tool.
"""Three real file-output checks (not a simulation/runtime interpreter)."""
import json
import math
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).with_name('baseline')))
from export_surfaces import export
from test_export_invariants import Building, parse_idf, parse_usda, verify_shell, verify_cross_format
from ifc_author import Dimensions, expected
from test_crosswalk import crosswalk


CASES = {
    # Representative synthetic structures, not real surveyed buildings.
    "small_residence": (6.0, 8.0, 2.7),
    "field_clinic": (18.0, 12.0, 3.6),
    "workshop": (30.0, 20.0, 7.0),
}


def verify_case(name, dimensions, root):
    l, w, h = dimensions
    path = root / name
    result = export(path, l, w, h)
    b = Building(l, w, h)
    usd = parse_usda(path / 'single_zone.usda')
    idf = parse_idf(path / 'single_zone_geometry.idf')
    usd_contract = verify_shell(usd, b)
    idf_contract = verify_shell(idf, b)
    verify_cross_format(usd, idf)
    d = Dimensions(l, w, h)
    assert crosswalk(d)['thermal_surfaces_mapped'] == 6
    assert math.isclose(expected(d)['zone_volume_m3'], result['nominal_volume_m3'], abs_tol=1e-7)
    assert math.isclose(usd_contract['enclosed_volume_m3'], idf_contract['enclosed_volume_m3'], abs_tol=1e-7)
    assert result['energy_demand_kwh'] is None
    return {"name": name, "dimensions_m": list(dimensions),
            "floor_area_m2": round(l*w, 6),
            "shell_area_m2": round(usd_contract['shell_area_m2'], 6),
            "volume_m3": round(usd_contract['enclosed_volume_m3'], 6),
            "checked_faces": len(usd), "status": "GEOMETRY_ONLY",
            "energy_demand_kwh": None}


class ParametricExportTests(unittest.TestCase):
    def test_three_buildings_emit_real_files(self):
        with TemporaryDirectory() as td:
            for name, dimensions in CASES.items():
                with self.subTest(name=name):
                    got = verify_case(name, dimensions, Path(td))
                    self.assertEqual(got['checked_faces'], 6)

    def test_default_backward_compatibility(self):
        with TemporaryDirectory() as td:
            got = export(Path(td))
            self.assertEqual(got['nominal_volume_m3'], 240)
            self.assertEqual(got['envelope_area_m2'], 268)

    def test_invalid_inputs_do_not_create_output(self):
        for triple in ((0, 8, 3), (-2, 8, 3), (10, float('inf'), 3),
                       (10, float('nan'), 3), (10, 8, -1)):
            with self.subTest(dimensions=triple), TemporaryDirectory() as td:
                dest = Path(td) / 'out'
                with self.assertRaises(ValueError):
                    export(dest, *triple)
                self.assertFalse(dest.exists())

    def test_schema_disallows_energy_claim(self):
        with TemporaryDirectory() as td:
            result = verify_case('field_clinic', CASES['field_clinic'], Path(td))
            self.assertIsNone(result['energy_demand_kwh'])
            self.assertEqual(result['status'], 'GEOMETRY_ONLY')

    def test_unit_scale_mutation_detected(self):
        with TemporaryDirectory() as td:
            path = Path(td)
            export(path, 6, 8, 2.7)
            scene = path/'single_zone.usda'
            scene.write_text(scene.read_text().replace('metersPerUnit = 1', 'metersPerUnit = 0.001'))
            with self.assertRaisesRegex(AssertionError, 'unit'):
                parse_usda(scene)

    def test_cross_format_coordinate_drift_detected(self):
        with TemporaryDirectory() as td:
            path = Path(td)
            export(path, 30, 20, 7)
            idf = path/'single_zone_geometry.idf'
            idf.write_text(idf.read_text().replace('30.000000', '30000.000000', 1))
            with self.assertRaises(AssertionError):
                verify_cross_format(parse_usda(path/'single_zone.usda'), parse_idf(idf))


if __name__ == '__main__':
    unittest.main()
