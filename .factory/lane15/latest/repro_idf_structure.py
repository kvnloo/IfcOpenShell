# This file was generated with the assistance of an AI coding tool.
"""Reproduce the Wave 14 -> Wave 15 IDF static-preflight false-accept matrix.

Usage: PYTHONPATH=baseline:. python repro_idf_structure.py
Uses only the supplied files; does not execute EnergyPlus.
"""
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "baseline"))
from test_export_invariants import parse_idf as new_parse

spec = importlib.util.spec_from_file_location("wave14_export_invariants", ROOT / "provenance" / "wave14_test_export_invariants.py")
old_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old_module
spec.loader.exec_module(old_module)
old_parse = old_module.parse_idf
source = (ROOT / "benchmarks/small_residence/single_zone_geometry.idf").read_text()
zone = "Zone, TestZone, 0, 0, 0, 0, 1, 1, autocalculate, autocalculate;"
rule = "GlobalGeometryRules, UpperLeftCorner, CounterClockWise, World;"
mutants = {
    "missing_zone": source.replace(zone, ""),
    "dangling_zone": source.replace("Zone, TestZone,", "Zone, WrongZone,", 1),
    "duplicate_zone": source.replace(zone, zone + "\n" + zone, 1),
    "invalid_world_prefix": source.replace("CounterClockWise, World;", "CounterClockWise, WorldRelative;", 1),
    "duplicate_geometry_rules": source.replace(rule, rule + "\nGlobalGeometryRules, LowerLeftCorner, ClockWise, Relative;", 1),
}


def outcome(parser, file):
    try:
        parser(file)
        return "ACCEPT"
    except AssertionError:
        return "REJECT"


matrix = []
with TemporaryDirectory() as dirname:
    file = Path(dirname) / "case.idf"
    file.write_text(source)
    assert outcome(old_parse, file) == outcome(new_parse, file) == "ACCEPT"
    for name, contents in mutants.items():
        assert contents != source, name
        file.write_text(contents)
        row = {"mutation": name, "wave14": outcome(old_parse, file), "wave15": outcome(new_parse, file)}
        assert row["wave14"] == "ACCEPT" and row["wave15"] == "REJECT", row
        matrix.append(row)
report = {"test": "static IDF fixture parser (not real EnergyPlus)", "baseline_fixture": "small_residence",
          "defects_confirmed": len(matrix), "matrix": matrix}
print(json.dumps(report, indent=2))
