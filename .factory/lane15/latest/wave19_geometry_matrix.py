# This file was generated with the assistance of an AI coding tool.
"""Deterministic synthetic correctness matrix: convex boxes versus bbox-identical wedges.

This is an analytic mesh test, NOT a native IFC4 or energy-system benchmark.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import random

from mesh_volume_gate import verify_solid_volume
from test_mesh_volume_gate import triangulated_box, triangulated_wedge


def run(cases=256):
    rng = random.Random(1519)
    box_base, box_faces = triangulated_box()
    wedge_base, wedge_faces = triangulated_wedge()
    accepted, rejected = 0, 0
    worst_box_relative_error = 0.0
    for _ in range(cases):
        dimensions = tuple(rng.uniform(0.15, 25) for _ in range(3))
        origin = tuple(rng.uniform(-2000, 2000) for _ in range(3))
        expected = math.prod(dimensions)
        box = [box_base[i] * dimensions[i % 3] + origin[i % 3]
               for i in range(len(box_base))]
        wedge = [wedge_base[i] * dimensions[i % 3] + origin[i % 3]
                 for i in range(len(wedge_base))]
        verified = verify_solid_volume(box, box_faces, expected)
        worst_box_relative_error = max(
            worst_box_relative_error,
            abs(verified['signed_volume_m3'] - expected) / expected,
        )
        accepted += 1
        try:
            verify_solid_volume(wedge, wedge_faces, expected)
        except AssertionError as exc:
            assert 'volume mismatch' in str(exc), str(exc)
            rejected += 1
        else:
            raise AssertionError('Half-volume wedge incorrectly accepted')
    return {
        'scope': 'synthetic geometry-only; no IFC native runtime or energy simulation',
        'seed': 1519,
        'box_cases_expected_pass': cases,
        'box_cases_accepted': accepted,
        'bbox_identical_wedges_expected_reject': cases,
        'bbox_identical_wedges_rejected': rejected,
        'worst_box_relative_volume_error': worst_box_relative_error,
        'energy_kwh': None,
    }


if __name__ == '__main__':
    report = run()
    output = Path('evidence/wave19-geometry-matrix.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
