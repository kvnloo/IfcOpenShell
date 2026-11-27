# This file was generated with the assistance of an AI coding tool.
"""Deterministic false-positive characterization for IFC fixture shell connectivity.

Only synthetic ideal triangulations. No native IFC/Bonsai/OpenUSD/EnergyPlus.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import random

from test_mesh_volume_gate import triangulated_box, overlapping_disconnected_boxes


def load_gate(path: Path):
    spec = importlib.util.spec_from_file_location("standalone_gate", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load mesh module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transform(vertices, dimensions, origin):
    return [vertices[i] * dimensions[i % 3] + origin[i % 3] for i in range(len(vertices))]


def run(gate_path: Path, cases=256):
    gate = load_gate(gate_path)
    rng = random.Random(1520)
    clean, clean_faces = triangulated_box()
    compound, compound_faces = overlapping_disconnected_boxes()
    accepted_clean = 0
    accepted_invalid = 0
    rejected_invalid = 0
    accepted_point_touching = 0
    rejected_point_touching = 0
    largest_relative_error = 0.0
    for _ in range(cases):
        dimensions = tuple(rng.uniform(.25, 25) for _ in range(3))
        offset = tuple(rng.uniform(-500, 500) for _ in range(3))
        reference = math.prod(dimensions)
        clean_result = gate.verify_solid_volume(transform(clean, dimensions, offset), clean_faces, reference)
        if not math.isclose(clean_result["signed_volume_m3"], reference, rel_tol=5e-4, abs_tol=1e-5):
            raise AssertionError("Clean cuboid false negative")
        accepted_clean += 1
        largest_relative_error = max(largest_relative_error,
                                     abs(clean_result["signed_volume_m3"] - reference) / reference)
        corrupt = transform(compound, dimensions, offset)
        for axis in range(3):
            low, high = min(corrupt[axis::3]), max(corrupt[axis::3])
            if not math.isclose(low, offset[axis], abs_tol=1e-9) or not math.isclose(
                high, offset[axis] + dimensions[axis], abs_tol=1e-9
            ):
                raise AssertionError("Corrupt geometry did not retain expected bounds")
        try:
            gate.verify_solid_volume(corrupt, compound_faces, reference)
        except AssertionError as exc:
            if "Disconnected closed mesh shells" not in str(exc):
                raise
            rejected_invalid += 1
        else:
            accepted_invalid += 1
        # Two otherwise valid cubes touching only at one corner. A vertex-only
        # graph traverses across their shared vertex; edge-connected faces do not.
        touched = transform(clean, dimensions, offset) + transform(
            clean, dimensions, tuple(offset[axis] + dimensions[axis] for axis in range(3)))
        touched_faces = clean_faces + [i + len(clean) // 3 for i in clean_faces]
        try:
            gate.measure_closed_solid(touched, touched_faces)
        except AssertionError as exc:
            if "Disconnected closed mesh shells" not in str(exc):
                raise
            rejected_point_touching += 1
        else:
            accepted_point_touching += 1
    return {
        "scope": "synthetic mesh connectivity; NOT_IFC_NATIVE and NOT_ENERGY_SIMULATION",
        "seed": 1520,
        "cases_per_class": cases,
        "valid_boxes_accepted": accepted_clean,
        "invalid_disconnected_compounds_accepted": accepted_invalid,
        "invalid_disconnected_compounds_rejected": rejected_invalid,
        "invalid_vertex_touching_shells_accepted": accepted_point_touching,
        "invalid_vertex_touching_shells_rejected": rejected_point_touching,
        "maximum_relative_error_valid_boxes": largest_relative_error,
        "energy_kwh": None,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", type=Path, default=Path(__file__).with_name("mesh_volume_gate.py"))
    ap.add_argument("--cases", type=int, default=256)
    args = ap.parse_args()
    if args.cases < 1 or args.cases > 5000:
        ap.error("--cases must be between 1 and 5000")
    print(json.dumps(run(args.gate, args.cases), indent=2, sort_keys=True))
