# This file was generated with the assistance of an AI coding tool.
"""CLI exit-code contracts for a native IFC4 metre/mm verification job."""
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from baseline.export_surfaces import export
from runtime_gate import main, native_ifc_complete


class NativeIfcCliExitTests(unittest.TestCase):
    def test_no_native_runtime_is_a_hard_ci_failure_with_report(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'clinic'
            export(directory, 10, 8, 3)
            report = Path(tmp) / 'report.json'
            argv = ['runtime_gate.py', str(directory), '--report', str(report),
                    '--author-ifc', '--ifc-units', 'both', '--require-native-ifc']
            with patch.object(sys, 'argv', argv), patch.dict('sys.modules', {'ifcopenshell': None}):
                with self.assertRaises(SystemExit) as caught:
                    main()
            self.assertEqual(caught.exception.code, 2)
            packet = json.loads(report.read_text())
            self.assertEqual(packet['requirements']['native_ifc_m_mm']['status'], 'BLOCKED')
            self.assertEqual(packet['cases'][0]['analytic_geometry']['status'], 'PASS')
            self.assertEqual(packet['cases'][0]['ifc_metres_millimetres_parity']['status'], 'NOT_RUN')
            self.assertFalse(packet['cases'][0]['civilization']['verified_construction_capability'])

    def test_no_opt_in_still_allows_static_preflight(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'clinic'
            export(directory, 10, 8, 3)
            report = Path(tmp) / 'report.json'
            with patch.object(sys, 'argv', ['runtime_gate.py', str(directory), '--report', str(report)]):
                main()
            packet = json.loads(report.read_text())
            self.assertNotIn('native_ifc_m_mm', packet.get('requirements', {}))
            self.assertEqual(packet['cases'][0]['analytic_geometry']['status'], 'PASS')

    def test_strict_mode_rejects_skipping_either_unit(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'clinic'
            export(directory, 10, 8, 3)
            for invalid in ([], ['--author-ifc'], ['--author-ifc', '--ifc-units', 'mm']):
                with self.subTest(invalid=invalid):
                    report = Path(tmp) / 'unwritten.json'
                    argv = ['runtime_gate.py', str(directory), '--report', str(report),
                            '--require-native-ifc', *invalid]
                    with patch.object(sys, 'argv', argv), self.assertRaises(SystemExit) as caught:
                        main()
                    self.assertEqual(caught.exception.code, 2)
                    self.assertFalse(report.exists())

    def test_strict_receipt_requires_both_units_and_boundary_geometry(self):
        complete = {
            'ifc_authoring': {'status': 'PASS', 'units': {'m': 'PASS', 'mm': 'PASS'}},
            'ifc_metres_millimetres_parity': {'status': 'PASS'},
            'ifc_energy_boundary_handoff': {'status': 'GEOMETRY_READY_ONLY', 'units': ['m', 'mm']},
        }
        self.assertTrue(native_ifc_complete(complete))
        for field, altered in [
            ('ifc_authoring', {'status': 'PASS', 'units': {'m': 'PASS'}}),
            ('ifc_metres_millimetres_parity', {'status': 'NOT_RUN'}),
            ('ifc_energy_boundary_handoff', {'status': 'NOT_RUN'}),
            ('ifc_energy_boundary_handoff', {'status': 'GEOMETRY_READY_ONLY', 'units': ['m', 'm', 'mm']}),
            ('ifc_energy_boundary_handoff', {'status': 'GEOMETRY_READY_ONLY', 'units': None}),
        ]:
            with self.subTest(field=field):
                self.assertFalse(native_ifc_complete({**complete, field: altered}))

    def test_strict_report_only_certifies_native_not_simulated_energy(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'clinic'
            export(directory, 10, 8, 3)
            report = Path(tmp) / 'report.json'
            result = {
                'building': 'clinic',
                'ifc_authoring': {'status': 'PASS', 'units': {'m': 'PASS', 'mm': 'PASS'}},
                'ifc_metres_millimetres_parity': {'status': 'PASS'},
                'ifc_energy_boundary_handoff': {'status': 'GEOMETRY_READY_ONLY', 'units': ['m', 'mm']},
                'real_openusd_stage': {'status': 'NOT_RUN'},
                'energyplus_simulation': {'status': 'NOT_RUN'},
                'civilization': {'status': 'UNVERIFIED', 'verified_construction_capability': False},
            }
            argv = ['runtime_gate.py', str(directory), '--report', str(report),
                    '--author-ifc', '--ifc-units', 'both', '--require-native-ifc']
            with patch.object(sys, 'argv', argv), patch('runtime_gate.check_case', return_value=result):
                main()
            saved = json.loads(report.read_text())
            self.assertEqual(saved['requirements']['native_ifc_m_mm']['status'], 'PASS')
            self.assertFalse(saved['cases'][0]['civilization']['verified_construction_capability'])


if __name__ == '__main__':
    unittest.main()
