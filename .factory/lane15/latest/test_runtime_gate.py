# This file was generated with the assistance of an AI coding tool.
"""Negative controls for fail-closed construction capability reporting."""
import json
import hashlib
import math
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "baseline"))
from export_surfaces import export
from runtime_gate import check_case, native_openusd_probe
from ifc_author import Dimensions, pieces
from test_export_invariants import Building


class RuntimeGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "residence"
        export(self.folder, 6, 8, 2.7)

    def test_real_files_have_static_pass_and_capability_unverified(self):
        report = check_case(self.folder)
        self.assertEqual(report['analytic_geometry']['status'], 'PASS')
        self.assertEqual(report['analytic_physical_shell']['component_count'], 6)
        self.assertEqual(report['analytic_physical_shell']['material_intersections_m3'], 0)
        self.assertIsNone(report['analytic_physical_shell']['embodied_carbon_kgco2e'])
        self.assertFalse(report['civilization']['verified_construction_capability'])
        self.assertIsNone(report['energy_demand_kwh'])
        self.assertEqual(report['energyplus_simulation']['status'], 'NOT_RUN')
        self.assertEqual(report['ifc_energy_boundary_handoff']['status'], 'NOT_RUN')
        self.assertEqual(len(report['sha256']), 3)

    def test_disabled_ifc_author_is_not_a_pass(self):
        report = check_case(self.folder)
        self.assertEqual(report['ifc_authoring']['status'], 'NOT_RUN')

    def test_report_rejects_injected_energy_claim(self):
        p = self.folder / 'metrics.json'
        data = json.loads(p.read_text())
        data['energy_demand_kwh'] = 12.5
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(AssertionError, 'energy'):
            check_case(self.folder)

    def test_report_rejects_tampered_single_face_area(self):
        p = self.folder / 'metrics.json'
        data = json.loads(p.read_text())
        data['face_areas_m2']['South'] += 1
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(AssertionError, 'Face-area'):
            check_case(self.folder)

    def test_runtime_failure_cannot_verify_capability(self):
        with patch('runtime_gate.native_openusd_probe', return_value={'status': 'FAIL', 'reason': 'bad USD'}):
            report = check_case(self.folder)
        self.assertEqual(report['real_openusd_stage']['status'], 'FAIL')
        self.assertFalse(report['civilization']['verified_construction_capability'])

    def test_report_rejects_tampered_floor_area(self):
        p = self.folder / 'metrics.json'
        data = json.loads(p.read_text())
        data['envelope_area_m2'] = 200.0
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(AssertionError, 'area'):
            check_case(self.folder)

    def test_report_rejects_usd_unit_mutation(self):
        p = self.folder / 'single_zone.usda'
        p.write_text(p.read_text().replace('metersPerUnit = 1', 'metersPerUnit = 0.001'))
        with self.assertRaisesRegex(AssertionError, 'unit'):
            check_case(self.folder)

    def test_report_rejects_usda_unit_prefix_false_pass(self):
        # Prior static preflight accepted scale 1000 by substring matching "1".
        p = self.folder / "single_zone.usda"
        p.write_text(p.read_text().replace("metersPerUnit = 1", "metersPerUnit = 1000", 1))
        with self.assertRaisesRegex(AssertionError, "unit"):
            check_case(self.folder)

    def test_report_rejects_implicit_usd_subdivision(self):
        p = self.folder / "single_zone.usda"
        p.write_text(p.read_text().replace('        uniform token subdivisionScheme = "none"\n', '', 1))
        with self.assertRaisesRegex(AssertionError, "subdivision"):
            check_case(self.folder)

    def test_report_rejects_idf_coordinate_mutation(self):
        p = self.folder / 'single_zone_geometry.idf'
        p.write_text(p.read_text().replace('6.000000', '6000.000000', 1))
        with self.assertRaises(AssertionError):
            check_case(self.folder)

    def test_report_rejects_dangling_idf_thermal_zone(self):
        p = self.folder / "single_zone_geometry.idf"
        p.write_text(p.read_text().replace("Zone, TestZone,", "Zone, WrongZone,", 1))
        with self.assertRaisesRegex(AssertionError, "Zone named TestZone"):
            check_case(self.folder)

    def test_report_rejects_conflicting_idf_geometry_rules(self):
        p = self.folder / "single_zone_geometry.idf"
        text = p.read_text()
        rule = "GlobalGeometryRules, UpperLeftCorner, CounterClockWise, World;"
        p.write_text(text.replace(rule, rule + "\nGlobalGeometryRules, LowerLeftCorner, ClockWise, Relative;", 1))
        with self.assertRaisesRegex(AssertionError, "geometry rule"):
            check_case(self.folder)

    def test_report_rejects_missing_geometry_file(self):
        (self.folder / 'single_zone.usda').unlink()
        with self.assertRaises(FileNotFoundError):
            check_case(self.folder)

    def test_px_runtime_missing_is_explicit(self):
        with patch.dict('sys.modules', {'pxr': None}):
            result = native_openusd_probe(self.folder / 'single_zone.usda', Building(6, 8, 2.7))
        self.assertEqual(result['status'], 'NOT_RUN')

    def test_ifc_opt_in_reports_missing_wheel(self):
        with patch.dict('sys.modules', {'ifcopenshell': None}):
            result = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(result['ifc_authoring']['status'], 'NOT_RUN')
        self.assertEqual(result['ifc_energy_boundary_handoff']['status'], 'NOT_RUN')
        self.assertFalse(result['civilization']['verified_construction_capability'])


    def test_mock_ifc_kernel_pass_cannot_bypass_missing_space_boundaries(self):
        fake = {"runtime_checks": {"geometry_kernel": "PASS"},
                "energy_space_boundary_audit": {"status": "BLOCKED", "missing": ["South"]}}
        with patch("runtime_gate.run_ifc", return_value=fake):
            report = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(report["ifc_authoring"]["status"], "NOT_RUN")
        self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")
        self.assertFalse(report["civilization"]["verified_construction_capability"])


    def _synthetic_ifc_receipt(self, length_unit="m", output=None):
        """Stub a receipt for gate *logic* only; not native IFC verification."""
        if output is None:
            output = self.folder / "ifc_runtime"
        output.mkdir(parents=True, exist_ok=True)
        path = output / "single_zone.ifc"
        path.write_bytes(b"FAKE IFC TEST RECEIPT - NOT A REAL MODEL: " + length_unit.encode())
        dimensions = Dimensions(6, 8, 2.7)
        bounds = {spec["name"]: [list(spec["bbox"][0]), list(spec["bbox"][1])]
                  for spec in pieces(dimensions)}
        areas = {"Floor": 48.0, "Roof": 48.0, "South": 16.2, "North": 16.2,
                 "East": 21.6, "West": 21.6}
        normals = {"Floor": [0.0, 0.0, -1.0], "Roof": [0.0, 0.0, 1.0],
                   "South": [0.0, -1.0, 0.0], "North": [0.0, 1.0, 0.0],
                   "East": [1.0, 0.0, 0.0], "West": [-1.0, 0.0, 0.0]}
        return {
            "status": "ifc_authoring_verified", "length_unit": length_unit,
            "runtime_checks": {
                "ifc_roundtrip": "PASS", "schema_validation": "PASS", "geometry_kernel": "PASS",
                "energy_space_boundaries": "GEOMETRY_READY_ONLY"
            },
            "verified": {
                "schema": "IFC4", "ifc_unit_scale_m": 0.001 if length_unit == "mm" else 1.0,
                "kernel_bodies_checked": 6, "kernel_closed_manifold_bodies": 6,
                "kernel_single_shell_bodies": 6,
                "validation_errors": 0,
                "kernel_vertices_unit": "metres", "convert_back_units": False,
                "geometry_kernel_bounds_m": bounds,
                "geometry_kernel_volume_m3": {
                    name: math.prod(b - a for a, b in zip(*bounds[name])) for name in bounds
                },
                "geometry_kernel_library_volume_m3": {
                    name: math.prod(b - a for a, b in zip(*bounds[name])) for name in bounds
                },
            },
            "sha256_ifc": hashlib.sha256(path.read_bytes()).hexdigest(),
            "energy_space_boundary_audit": {
                "status": "GEOMETRY_READY_ONLY", "geometry_agreement_verified": True,
                "expected_boundaries": 6, "observed_boundaries": 6,
                "missing": [], "unexpected": [], "duplicate": [], "invalid": [],
                "boundary_geometry": {
                    "status": "GEOMETRY_READY_ONLY", "checked_surfaces": 6,
                    "area_m2": areas, "normal": normals, "thermal_volume_m3": 129.6,
                },
            },
        }

    def test_native_receipt_contract_accepts_complete_stub_only(self):
        receipt = self._synthetic_ifc_receipt()
        with patch("runtime_gate.run_ifc", return_value=receipt):
            packet = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(packet["ifc_authoring"]["status"], "PASS")
        self.assertEqual(packet["ifc_energy_boundary_handoff"]["status"], "GEOMETRY_READY_ONLY")
        self.assertFalse(packet["civilization"]["verified_construction_capability"])

    def test_missing_native_proofs_never_pass_authoring(self):
        complete = self._synthetic_ifc_receipt()
        for field in ("ifc_roundtrip", "schema_validation", "geometry_kernel"):
            with self.subTest(field=field):
                receipt = {**complete, "runtime_checks": {**complete["runtime_checks"], field: "NOT_RUN"}}
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    packet = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")
                self.assertEqual(packet["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")

    def test_stale_sha_or_missing_ifc_file_never_passes_authoring(self):
        complete = self._synthetic_ifc_receipt()
        stale = {**complete, "sha256_ifc": "a" * 64}
        with patch("runtime_gate.run_ifc", return_value=stale):
            packet = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")
        (self.folder / "ifc_runtime" / "single_zone.ifc").unlink()
        with patch("runtime_gate.run_ifc", return_value=complete):
            packet = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")

    def test_unverified_model_dimensions_and_schema_never_pass_authoring(self):
        complete = self._synthetic_ifc_receipt()
        for field, bad in (("schema", "IFC2X3"), ("kernel_bodies_checked", 5),
                           ("validation_errors", 1), ("ifc_unit_scale_m", 0.001)):
            with self.subTest(field=field):
                receipt = {**complete, "verified": {**complete["verified"], field: bad}}
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    packet = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")

    def test_missing_or_incorrect_mesh_volume_cannot_pass_ifc_receipt(self):
        import copy
        good = self._synthetic_ifc_receipt()
        for mutation in ("missing", "wrong", "nan", "unclosed", "disconnected", "library_disagrees"):
            with self.subTest(mutation=mutation):
                receipt = copy.deepcopy(good)
                verified = receipt["verified"]
                if mutation == "missing":
                    del verified["geometry_kernel_volume_m3"]
                elif mutation == "wrong":
                    verified["geometry_kernel_volume_m3"]["Roof"] *= 0.5
                elif mutation == "nan":
                    verified["geometry_kernel_volume_m3"]["Roof"] = float("nan")
                elif mutation == "unclosed":
                    verified["kernel_closed_manifold_bodies"] = 5
                elif mutation == "disconnected":
                    verified["kernel_single_shell_bodies"] = 5
                else:
                    verified["geometry_kernel_library_volume_m3"]["Roof"] *= 0.5
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    packet = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")

    def test_legacy_or_nonconnected_shell_receipt_cannot_pass(self):
        import copy
        good = self._synthetic_ifc_receipt()
        for value in (None, 5, 0, True, "6"):
            with self.subTest(value=value):
                receipt = copy.deepcopy(good)
                if value is None:
                    del receipt["verified"]["kernel_single_shell_bodies"]
                else:
                    receipt["verified"]["kernel_single_shell_bodies"] = value
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    packet = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(packet["ifc_authoring"]["status"], "NOT_RUN")

    def test_native_mm_receipt_proof_accepts_matching_units_only(self):
        receipt = self._synthetic_ifc_receipt("mm")
        with patch("runtime_gate.run_ifc", return_value=receipt):
            report = check_case(self.folder, allow_ifc_author=True, ifc_units="mm")
        self.assertEqual(report["ifc_authoring"]["status"], "PASS")
        receipt["verified"]["ifc_unit_scale_m"] = 1.0
        with patch("runtime_gate.run_ifc", return_value=receipt):
            report = check_case(self.folder, allow_ifc_author=True, ifc_units="mm")
        self.assertEqual(report["ifc_authoring"]["status"], "NOT_RUN")

    def test_incomplete_boundary_geom_cannot_be_promoted(self):
        complete = self._synthetic_ifc_receipt()
        for change in (lambda audit: audit.pop("geometry_agreement_verified"),
                       lambda audit: audit.pop("boundary_geometry"),
                       lambda audit: audit["boundary_geometry"]["area_m2"].update({"Roof": 47})):
            with self.subTest(change=change):
                import copy
                receipt = copy.deepcopy(complete)
                change(receipt["energy_space_boundary_audit"])
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    report = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(report["ifc_authoring"]["status"], "PASS")
                self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")

    def test_inverted_or_missing_thermal_normal_cannot_pass(self):
        import copy
        good = self._synthetic_ifc_receipt()
        for mutation in ("inverted", "non_unit", "missing", "nan"):
            with self.subTest(mutation=mutation):
                receipt = copy.deepcopy(good)
                normals = receipt["energy_space_boundary_audit"]["boundary_geometry"]["normal"]
                if mutation == "inverted":
                    normals["Roof"] = [0.0, 0.0, -1.0]
                elif mutation == "non_unit":
                    normals["Roof"] = [0.0, 0.0, 2.0]
                elif mutation == "missing":
                    del normals["Roof"]
                else:
                    normals["Roof"] = [0.0, 0.0, float("nan")]
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    report = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")
                self.assertFalse(report["civilization"]["verified_construction_capability"])

    def test_inconsistent_boundary_topology_receipt_cannot_pass(self):
        import copy
        good = self._synthetic_ifc_receipt()
        for key, bad in (("invalid", ["Roof: missing geometry"]),
                         ("missing", ["East"]), ("unexpected", ["Window"]),
                         ("duplicate", ["Roof"]), ("observed_boundaries", 5),
                         ("expected_boundaries", 5)):
            with self.subTest(key=key):
                receipt = copy.deepcopy(good)
                receipt["energy_space_boundary_audit"][key] = bad
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    report = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")

    def test_boundary_runtime_check_must_agree_with_geometry_receipt(self):
        receipt = self._synthetic_ifc_receipt()
        receipt["runtime_checks"]["energy_space_boundaries"] = "NOT_RUN"
        with patch("runtime_gate.run_ifc", return_value=receipt):
            packet = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(packet["ifc_authoring"]["status"], "PASS")
        self.assertEqual(packet["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")

    def test_missing_or_wrong_kernel_bounds_never_pass(self):
        complete = self._synthetic_ifc_receipt()
        import copy
        for mutation in ("missing", "bad_box", "wrong_normalized_units", "nan"):
            with self.subTest(mutation=mutation):
                receipt = copy.deepcopy(complete)
                bounds = receipt["verified"]["geometry_kernel_bounds_m"]
                if mutation == "missing":
                    del bounds["Roof"]
                elif mutation == "bad_box":
                    bounds["Roof"][1][2] += 0.5
                elif mutation == "wrong_normalized_units":
                    receipt["verified"]["kernel_vertices_unit"] = "file"
                else:
                    bounds["Roof"][1][2] = float("nan")
                with patch("runtime_gate.run_ifc", return_value=receipt):
                    report = check_case(self.folder, allow_ifc_author=True)
                self.assertEqual(report["ifc_authoring"]["status"], "NOT_RUN")

    def test_both_units_parity_contract_and_drift_detection(self):
        def emit(output, _dimensions, *, length_unit):
            return self._synthetic_ifc_receipt(length_unit, output)
        with patch("runtime_gate.run_ifc", side_effect=emit):
            packet = check_case(self.folder, allow_ifc_author=True, ifc_units="both")
        self.assertEqual(packet["ifc_authoring"]["status"], "PASS")
        self.assertEqual(packet["ifc_metres_millimetres_parity"]["status"], "PASS")
        self.assertEqual(packet["ifc_energy_boundary_handoff"]["status"], "GEOMETRY_READY_ONLY")

        def drift(output, _dimensions, *, length_unit):
            result = emit(output, _dimensions, length_unit=length_unit)
            delta = 0.00015 if length_unit == "m" else -0.00015
            result["verified"]["geometry_kernel_bounds_m"]["South"][1][0] += delta
            return result
        with patch("runtime_gate.run_ifc", side_effect=drift):
            report = check_case(self.folder, allow_ifc_author=True, ifc_units="both")
        self.assertEqual(report["ifc_metres_millimetres_parity"]["status"], "NOT_RUN")
        self.assertEqual(report["ifc_authoring"]["status"], "NOT_RUN")
        self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")

    def test_both_units_unavailable_are_explicit_not_run(self):
        with patch.dict("sys.modules", {"ifcopenshell": None}):
            report = check_case(self.folder, allow_ifc_author=True, ifc_units="both")
        self.assertEqual(report["ifc_authoring"]["units"], {"m": "NOT_RUN", "mm": "NOT_RUN"})
        self.assertEqual(report["ifc_metres_millimetres_parity"]["status"], "NOT_RUN")

    def test_mock_semantic_topology_pass_still_is_not_model_verification(self):
        fake = {"runtime_checks": {"geometry_kernel": "PASS"},
                "energy_space_boundary_audit": {"status": "TOPOLOGY_READY_ONLY"}}
        with patch("runtime_gate.run_ifc", return_value=fake):
            report = check_case(self.folder, allow_ifc_author=True)
        self.assertEqual(report["ifc_energy_boundary_handoff"]["status"], "NOT_RUN")
        self.assertFalse(report["civilization"]["verified_construction_capability"])

if __name__ == '__main__':
    unittest.main()
