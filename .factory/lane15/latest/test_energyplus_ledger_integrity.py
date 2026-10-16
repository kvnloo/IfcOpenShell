# This file was generated with the assistance of an AI coding tool.
"""Check the actual geometry-only fixture -> design-day IDF ledger handoff."""
import json
from pathlib import Path
import tempfile
import unittest

from energyplus_design_day import candidate


FIXTURE = Path(__file__).resolve().parent / "benchmarks" / "small_residence"


class LedgerIntegrityTests(unittest.TestCase):
    def test_valid_ledger_is_accepted(self):
        model = candidate(FIXTURE / "single_zone_geometry.idf", FIXTURE / "metrics.json")
        self.assertEqual(model.count("BuildingSurface:Detailed"), 6)

    def test_unaccounted_or_missing_face_is_rejected(self):
        for change in ("extra", "missing"):
            with self.subTest(change=change):
                metrics = json.loads((FIXTURE / "metrics.json").read_text())
                if change == "extra":
                    metrics["face_areas_m2"]["HiddenFacade"] = 20.0
                else:
                    metrics["face_areas_m2"].pop("West")
                with tempfile.TemporaryDirectory() as work:
                    path = Path(work) / "metrics.json"
                    path.write_text(json.dumps(metrics))
                    with self.assertRaisesRegex(ValueError, "face-area ledger"):
                        candidate(FIXTURE / "single_zone_geometry.idf", path)

    def test_nonfinite_reference_metrics_are_rejected(self):
        for field in ("nominal_volume_m3", "face_areas_m2"):
            for invalid in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, invalid=str(invalid)):
                    metrics = json.loads((FIXTURE / "metrics.json").read_text())
                    if field == "face_areas_m2":
                        metrics[field]["Roof"] = invalid
                    else:
                        metrics[field] = invalid
                    with tempfile.TemporaryDirectory() as work:
                        path = Path(work) / "metrics.json"
                        path.write_text(json.dumps(metrics))
                        with self.assertRaises(ValueError):
                            candidate(FIXTURE / "single_zone_geometry.idf", path)


if __name__ == "__main__":
    unittest.main()
