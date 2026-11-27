# This file was generated with the assistance of an AI coding tool.
"""EnergyPlus 26.2 surface-schema/design-day candidate tests (no engine claims)."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from energyplus_design_day import audit, candidate, objects, run_engine

ROOT = Path(__file__).parent / "benchmarks"


class EnergyPlusDesignDayTests(unittest.TestCase):
    def test_all_buildings_preserve_six_surfaces_and_volume(self):
        for name in ("small_residence", "field_clinic", "workshop"):
            src = ROOT / name
            with self.subTest(name=name):
                output = candidate(src / "single_zone_geometry.idf", src / "metrics.json")
                receipt = audit(output, src / "single_zone_geometry.idf")
                self.assertEqual((receipt["surfaces"], receipt["sizing_days"], receipt["native_engine"]),
                                 (6, 2, "NOT_RUN"))
                self.assertIsNone(receipt["energy_demand_kwh"])
                objects_ = objects(output)
                self.assertEqual(len([s for s in objects_ if s[0] == "BuildingSurface:Detailed"]), 6)
                self.assertEqual([s for s in objects_ if s[0] == "Version"], [["Version", "26.2"]])

    def test_2026_surface_space_field_is_required(self):
        src = ROOT / "small_residence"
        output = candidate(src / "single_zone_geometry.idf", src / "metrics.json")
        modified = output.replace("TestZone,\n  ,\n  Outdoors", "TestZone,\n  Outdoors", 1)
        with self.assertRaisesRegex(AssertionError, "surface/space field"):
            audit(modified, src / "single_zone_geometry.idf")

    def test_design_day_follows_energyplus_26_2_idd(self):
        src = ROOT / "small_residence"
        day_models = candidate(src / "single_zone_geometry.idf", src / "metrics.json")
        for day in (row for row in objects(day_models) if row[0] == "SizingPeriod:DesignDay"):
            self.assertEqual(len(day), 27)
            self.assertEqual(day[9], "Wetbulb")
            self.assertEqual(day[21], "ASHRAEClearSky")

    def test_handoff_does_not_accidentally_attach_weather_loads(self):
        src = ROOT / "field_clinic"
        output = candidate(src / "single_zone_geometry.idf", src / "metrics.json")
        self.assertNotIn("RunPeriod,", output)
        self.assertNotIn("ZoneHVAC:", output)
        self.assertEqual([s for s in objects(output) if s[0] == "SimulationControl"][0][1:6],
                         ["No", "No", "No", "Yes", "No"])

    def test_source_with_unaccounted_window_rejected(self):
        src = ROOT / "small_residence"
        with TemporaryDirectory() as td:
            idf = Path(td) / "geo.idf"
            idf.write_text((src / "single_zone_geometry.idf").read_text() +
                           "\nFenestrationSurface:Detailed, Bad, Window, Clear, South;\n")
            with self.assertRaisesRegex(AssertionError, "Unsupported EnergyPlus object"):
                candidate(idf, src / "metrics.json")

    def test_missing_engine_is_blocked_not_passed(self):
        with TemporaryDirectory() as td:
            receipt = run_engine(Path(td) / "missing.idf", Path(td) / "engine", "lane15-no-such-energyplus")
            self.assertEqual(receipt["status"], "BLOCKED")

    def test_wrong_energyplus_version_is_blocked(self):
        with TemporaryDirectory() as td:
            binary = Path(td) / "fake-energyplus"
            binary.write_text("#!/bin/sh\necho 'EnergyPlus, Version 26.1.0'\n", encoding="utf-8")
            binary.chmod(0o755)
            receipt = run_engine(Path(td) / "unused.idf", Path(td) / "engine", str(binary))
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertIn("26.1.0", receipt["reported_engine_version"])

    def test_cli_static_export_from_unrelated_cwd(self):
        # A fresh CLI process must find the bundled baseline package itself,
        # without relying on another test to modify sys.path first.
        with TemporaryDirectory() as td:
            out = Path(td) / "out"
            env = dict(os.environ, PYTHONPATH="")
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).parent / "energyplus_design_day.py"),
                 str(ROOT / "field_clinic"), "--out", str(out)],
                cwd=td, env=env, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            receipt = json.loads((out / "design_day_report.json").read_text())
            self.assertEqual(receipt["status"], "STATIC_ONLY")
            self.assertEqual(receipt["native_engine"], "NOT_RUN")
            self.assertEqual(receipt["surfaces"], 6)
            self.assertIsNone(receipt["energy_demand_kwh"])
            self.assertTrue((out / "design_day_26_2.idf").is_file())

    def test_cli_strict_native_exits_two_and_writes_receipt(self):
        with TemporaryDirectory() as td:
            out = Path(td) / "out"
            p = subprocess.run([sys.executable, str(Path(__file__).parent / "energyplus_design_day.py"),
                                str(ROOT / "workshop"), "--out", str(out), "--require-native",
                                "--energyplus-bin", "lane15-no-such-energyplus"],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            receipt = json.loads((out / "design_day_report.json").read_text())
            self.assertEqual(receipt["native"]["status"], "BLOCKED")
            self.assertTrue((out / "design_day_26_2.idf").is_file())


if __name__ == "__main__":
    unittest.main()
