# This file was generated with the assistance of an AI coding tool.
"""EnergyPlus 26.2 provenance guard (fake subprocess; no native run)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import subprocess

from energyplus_design_day import run_engine


class EnergyPlusVersionProvenanceTests(TestCase):
    def probe(self, version_line):
        calls = []

        def fake_run(args, **_kwargs):
            calls.append(args)
            if "--version" in args:
                return subprocess.CompletedProcess(args, 0, stdout=version_line, stderr="")
            out = Path(args[args.index("--output-directory") + 1])
            out.mkdir(parents=True, exist_ok=True)
            (out / "eplusout.err").write_text("** Warning ** Synthetic stub\n")
            (out / "eplusout.end").write_text(
                "EnergyPlus Completed Successfully-- 1 Warning; 0 Severe Errors; Elapsed Time=00hr 00min 00sec\n"
            )
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        with TemporaryDirectory() as work:
            with patch("energyplus_design_day.shutil.which", return_value="/fake/energyplus"), patch(
                "energyplus_design_day.subprocess.run", side_effect=fake_run
            ):
                result = run_engine(Path(work) / "fixture.idf", Path(work) / "engine")
        return result, calls

    def test_wrong_binary_must_not_be_accepted_from_unrelated_version_mention(self):
        for header in (
            "EnergyPlus, Version 26.1.0\nAvailable reference schema 26.2.0",
            "EnergyPlus, Version 25.2.0 (compatible model 26.2.0)",
            "Runner-for-EnergyPlus 26.2.0",
        ):
            with self.subTest(header=header):
                result, calls = self.probe(header)
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertEqual(len(calls), 1, "Wrong version must stop before the engine executes")

    def test_official_version_banner_is_accepted_for_the_stub_only(self):
        result, calls = self.probe("EnergyPlus, Version 26.2.0-4bd7a1f26f")
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(result["energy_demand_kwh"])


if __name__ == "__main__":
    import unittest
    unittest.main()
