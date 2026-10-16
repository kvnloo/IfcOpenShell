# This file was generated with the assistance of an AI coding tool.
"""One-zone USD/IDF handoff rejects extra non-mesh scene prims."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from baseline.test_export_invariants import parse_usda
from runtime_gate import check_case, native_openusd_probe
from baseline.test_export_invariants import Building


class OneZonePrimitiveAccounting(unittest.TestCase):
    def setUp(self):
        self.scratch = TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.fixture = Path(self.scratch.name) / "field_clinic"
        shutil.copytree(Path(__file__).parent / "benchmarks" / "field_clinic", self.fixture)
        self.usda = self.fixture / "single_zone.usda"

    def add_prim(self, block):
        # Appends a legal additional top-level USD prim without changing the six thermal mesh faces.
        self.usda.write_text(self.usda.read_text(encoding="utf-8") + "\n" + block + "\n", encoding="utf-8")

    def test_clean_six_surface_stage(self):
        self.assertEqual(len(parse_usda(self.usda)), 6)
        self.assertEqual(check_case(self.fixture)["analytic_geometry"]["status"], "PASS")

    def test_extra_native_cube_is_not_silently_ignored(self):
        self.add_prim('def Cube "UnaccountedSolid" {}')
        with self.assertRaisesRegex(AssertionError, "unexpected.*prim|primitive|USD.*declaration"):
            parse_usda(self.usda)

    def test_extra_xform_is_not_silently_ignored_by_cross_format_gate(self):
        self.add_prim('def Xform "AnotherBuilding" {}')
        with self.assertRaisesRegex(AssertionError, "unexpected.*prim|primitive|USD.*declaration"):
            check_case(self.fixture)

    def test_prim_override_is_not_certified(self):
        self.add_prim('over "HiddenContext" {}')
        with self.assertRaisesRegex(AssertionError, "unexpected.*prim|primitive|USD.*declaration"):
            parse_usda(self.usda)

    def test_native_openusd_rejects_extra_cube_if_installed(self):
        try:
            from pxr import Usd
        except ImportError:
            self.skipTest("Native pxr/OpenUSD is unavailable")
        self.add_prim('def Cube "UnaccountedSolid" {}')
        probe = native_openusd_probe(self.usda, Building(10, 8, 3))
        self.assertEqual(probe["status"], "FAIL")
        self.assertRegex(probe["reason"], "unexpected.*prim|primitive|USD.*declaration")


if __name__ == "__main__":
    unittest.main()
