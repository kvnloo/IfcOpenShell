# This file was generated with the assistance of an AI coding tool.
"""Regression: geometry-only EnergyPlus packets must not certify hidden loads or openings."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from test_export_invariants import parse_idf
from runtime_gate import check_case


SOURCE = Path(__file__).resolve().parent / "benchmarks" / "small_residence"


class GeometryOnlyObjectScope(unittest.TestCase):
    def test_extra_energyplus_objects_cannot_pass_opaque_shell_gate(self):
        extra_objects = {
            # Both detailed and legacy fenestration subtract gross opaque area.
            "detailed_window": "FenestrationSurface:Detailed, Window1, Window, WindowConstruction, South, , autocalculate, , 1, 4, 1,0,2, 2,0,2, 2,0,1, 1,0,1;",
            "legacy_window": "Window, Window1, WindowConstruction, South, , 1, 1, 1, 1;",
            "legacy_door": "Door, Door1, DoorConstruction, South, , 1, 0, 1, 2;",
            "shading": "Shading:Building:Detailed, Shade1, , 4, 0,-1,3, 1,-1,3, 1,-1,4, 0,-1,4;",
            "internal_mass": "InternalMass, Furniture, InternalMassConstruction, TestZone, 10;",
            "infiltration": "ZoneInfiltration:DesignFlowRate, Leak, TestZone, AnySchedule, Flow/Zone, 0.1;",
            "infiltration_mixed_case": "zOnEiNfIlTrAtIoN:DesignFlowRate, Leak, TestZone, AnySchedule, Flow/Zone, 0.1;",
            "lights": "Lights, AddedLoad, TestZone, AnySchedule, LightingLevel, 200;",
        }
        for label, addition in extra_objects.items():
            with self.subTest(label=label), TemporaryDirectory() as td:
                target = Path(td) / "model.idf"
                target.write_text((SOURCE / "single_zone_geometry.idf").read_text() + "\n" + addition + "\n")
                with self.assertRaisesRegex(AssertionError, "Unsupported EnergyPlus object"):
                    parse_idf(target)

    def test_runtime_cannot_certify_geometry_packet_with_window(self):
        with TemporaryDirectory() as td:
            directory = Path(td) / "case"
            shutil.copytree(SOURCE, directory)
            with (directory / "single_zone_geometry.idf").open("a", encoding="utf-8") as handle:
                handle.write("\nFenestrationSurface:Detailed, Aperture, Window, Glass, South, , autocalculate, , 1, 4, 1,0,2, 2,0,2, 2,0,1, 1,0,1;\n")
            with self.assertRaisesRegex(AssertionError, "Unsupported EnergyPlus object"):
                check_case(directory)

    def test_comments_and_exact_six_surface_export_remain_accepted(self):
        with TemporaryDirectory() as td:
            target = Path(td) / "fragment.idf"
            target.write_text((SOURCE / "single_zone_geometry.idf").read_text() + "\n! Lights, Fake, Zone;\n")
            self.assertEqual(set(parse_idf(target)), {"Floor", "Roof", "North", "South", "East", "West"})


if __name__ == "__main__":
    unittest.main()
