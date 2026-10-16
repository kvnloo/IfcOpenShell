# This file was generated with the assistance of an AI coding tool.
"""Regression tests for IFC file units versus geometry-kernel output units."""
import importlib.util
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from ifc_author import Dimensions, author, kernel_bounds_metres, pieces, run, verify_ifc


class KernelUnitsTests(unittest.TestCase):
    def test_default_kernel_is_already_si_metres(self):
        for spec in pieces(Dimensions()):
            low, high = np.array(spec["bbox"], dtype=float)
            vertices = np.array([low, high], dtype=float).ravel()
            with self.subTest(spec=spec["name"]):
                observed_low, observed_high = kernel_bounds_metres(vertices, 0.001)
                np.testing.assert_allclose(observed_low, low, rtol=0, atol=1e-12)
                np.testing.assert_allclose(observed_high, high, rtol=0, atol=1e-12)

    def test_explicit_convert_back_units_are_converted_once(self):
        for unit_scale in (1.0, 0.001, 0.01, 0.3048):
            for spec in pieces(Dimensions()):
                expected_low, expected_high = np.array(spec["bbox"], dtype=float)
                file_vertices = np.array([expected_low, expected_high]).ravel() / unit_scale
                with self.subTest(unit_scale=unit_scale, spec=spec["name"]):
                    low, high = kernel_bounds_metres(file_vertices, unit_scale, convert_back_units=True)
                    np.testing.assert_allclose(low, expected_low, rtol=0, atol=1e-10)
                    np.testing.assert_allclose(high, expected_high, rtol=0, atol=1e-10)

    def test_millimetre_fixture_would_fail_old_double_scale(self):
        low, high = np.array(pieces(Dimensions())[0]["bbox"])
        wrongly_scaled = np.array([low, high]) * 0.001
        self.assertFalse(np.allclose(wrongly_scaled[1], high, rtol=0, atol=1e-3))
        observed = kernel_bounds_metres([*low, *high], 0.001)
        np.testing.assert_allclose(observed[1], high)

    def test_bad_scales_and_vertices_fail_closed(self):
        for scale in (0.0, -1.0, math.inf, math.nan):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                kernel_bounds_metres([0, 0, 0], scale)
        for vertices in ([], [1, 2], [0, 0, math.nan], [0, math.inf, 0]):
            with self.subTest(vertices=vertices), self.assertRaises(ValueError):
                kernel_bounds_metres(vertices, 1.0)

    def test_mm_unavailable_runtime_never_claims_ifc(self):
        if importlib.util.find_spec("ifcopenshell") is not None:
            self.skipTest("Native IfcOpenShell installed; use native parity test")
        with TemporaryDirectory() as temp:
            report = run(Path(temp), Dimensions(), length_unit="mm")
            self.assertEqual(report["runtime_checks"]["geometry_kernel"], "NOT_RUN")
            self.assertEqual(report["length_unit"], "mm")
            self.assertFalse((Path(temp) / "single_zone.ifc").exists())


@unittest.skipUnless(importlib.util.find_spec("ifcopenshell"), "Native IfcOpenShell not installed")
class NativeMetreMillimetreRoundtripTests(unittest.TestCase):
    def test_ifc4_kernel_geometry_parity(self):
        with TemporaryDirectory() as temp:
            verified = {}
            for unit in ("m", "mm"):
                path = Path(temp) / f"single_zone_{unit}.ifc"
                author(path, Dimensions(), length_unit=unit)
                verified[unit] = verify_ifc(path, Dimensions(), length_unit=unit)
                self.assertEqual(verified[unit]["kernel_bodies_checked"], 6)
                self.assertEqual(verified[unit]["kernel_closed_manifold_bodies"], 6)
                self.assertEqual(verified[unit]["kernel_single_shell_bodies"], 6)
                self.assertEqual(verified[unit]["validation_errors"], 0)
            self.assertEqual(verified["m"]["geometry_kernel_bounds_m"],
                             verified["mm"]["geometry_kernel_bounds_m"])
            for name in verified["m"]["geometry_kernel_volume_m3"]:
                self.assertAlmostEqual(verified["m"]["geometry_kernel_volume_m3"][name],
                                       verified["mm"]["geometry_kernel_volume_m3"][name], places=4)


if __name__ == "__main__":
    unittest.main()
