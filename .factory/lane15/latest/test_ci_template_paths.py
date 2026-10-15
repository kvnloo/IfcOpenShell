# This file was generated with the assistance of an AI coding tool.
"""Regression guard for recovered Lane 15 native CI paths."""
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SOURCE_PREFIX = ".factory/lane15/latest"


def check_template(template: str) -> None:
    locations = re.findall(r"(?m)^\s*working-directory:\s*(\S+)\s*$", template)
    if locations != [SOURCE_PREFIX]:
        raise AssertionError(f"Workflow must use recovered source path {SOURCE_PREFIX}: {locations}")
    if "--author-ifc --ifc-units both --require-native-ifc" not in template:
        raise AssertionError("Native verification must be mandatory in CI")
    if "['real_openusd_stage']['status'] != 'PASS'" not in template:
        raise AssertionError("OpenUSD cannot pass through skipped native parsing")
    for rel in ("runtime_gate.py", "benchmarks/small_residence/single_zone.usda",
                "benchmarks/field_clinic/metrics.json", "benchmarks/workshop/metrics.json"):
        if not (ROOT / rel).is_file():
            raise AssertionError(f"Missing source: {rel}")
    artifacts = re.search(r"(?m)^\s*path: \|\s*\n((?:\s+[^\n]+\n)+)", template)
    if not artifacts:
        raise AssertionError("No evidence-artifact paths")
    paths = [s.strip() for s in artifacts.group(1).splitlines()]
    for target in (f"{SOURCE_PREFIX}/reports/", f"{SOURCE_PREFIX}/benchmarks/*/ifc_runtime/"):
        if target not in paths:
            raise AssertionError(f"Evidence path missing: {target}")
    if "factory/evidence/lane15" in template:
        raise AssertionError("Stale pre-recovery path")


class NativeCITemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "CI_TEMPLATE_native_ifc4.yml").read_text(encoding="utf8")

    def test_recovered_snapshot_paths_and_native_requirement(self):
        check_template(self.template)

    def test_reject_stale_working_directory(self):
        wrong = self.template.replace("working-directory: .factory/lane15/latest",
                                      "working-directory: factory/evidence/lane15")
        with self.assertRaisesRegex(AssertionError, "recovered source path"):
            check_template(wrong)

    def test_reject_stale_artifact_destination(self):
        wrong = self.template.replace(".factory/lane15/latest/benchmarks/*/ifc_runtime/",
                                      "factory/evidence/lane15/benchmarks/*/ifc_runtime/")
        with self.assertRaisesRegex(AssertionError, "Evidence path missing"):
            check_template(wrong)

    def test_reject_skipped_native_or_usd_stage(self):
        for removed in ("--require-native-ifc", "['real_openusd_stage']['status'] != 'PASS'"):
            with self.subTest(removed=removed), self.assertRaises(AssertionError):
                check_template(self.template.replace(removed, ""))


if __name__ == "__main__":
    unittest.main()
