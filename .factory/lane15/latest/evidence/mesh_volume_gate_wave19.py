# This file was generated with the assistance of an AI coding tool.
"""Independent closed-solid and volume checks for triangulated IFC kernel meshes.

Inputs are IfcOpenShell ``shape.geometry.verts`` and ``.faces`` in metres.
This does NOT substitute for IFC schema validation or kernel execution.
"""
from __future__ import annotations

from collections import Counter
import math


def measure_closed_solid(flat_vertices, triangle_indices, *, weld_tolerance_m: float = 1e-7) -> dict:
    """Return signed volume only for a consistently outward, manifold mesh.

    Vertices are welded at a small fixed spatial tolerance because independently
    triangulated IFC faces can repeat coincident edge vertices. This is specific
    to the small, rectilinear fixture, not an arbitrary IFC healing algorithm.
    """
    if not math.isfinite(weld_tolerance_m) or weld_tolerance_m <= 0:
        raise ValueError("Invalid vertex-weld tolerance")
    if len(flat_vertices) == 0 or len(flat_vertices) % 3:
        raise AssertionError("Expected nonempty XYZ vertex triples")
    if len(triangle_indices) == 0 or len(triangle_indices) % 3:
        raise AssertionError("Expected nonempty triangle index triples")
    coordinates = []
    for i in range(0, len(flat_vertices), 3):
        point = tuple(float(x) for x in flat_vertices[i:i+3])
        if not all(math.isfinite(x) for x in point):
            raise AssertionError("Non-finite mesh coordinate")
        coordinates.append(point)

    unique: list[tuple[float, float, float]] = []
    coordinate_to_id = {}
    ids = []
    for point in coordinates:
        key = tuple(round(x / weld_tolerance_m) for x in point)
        if key not in coordinate_to_id:
            coordinate_to_id[key] = len(unique)
            unique.append(point)
        ids.append(coordinate_to_id[key])

    edges = Counter()
    faces = []
    for i in range(0, len(triangle_indices), 3):
        raw_indices = triangle_indices[i:i+3]
        try:
            indices = [int(x) for x in raw_indices]
        except (TypeError, ValueError, OverflowError) as exc:
            raise AssertionError("Invalid triangle index") from exc
        if any(x != raw or x < 0 or x >= len(ids) for x, raw in zip(indices, raw_indices)):
            raise AssertionError("Triangle index out of range or fractional")
        a, b, c = (ids[j] for j in indices)
        if len({a, b, c}) != 3:
            raise AssertionError("Degenerate triangle")
        faces.append((a, b, c))
        edges.update(((a, b), (b, c), (c, a)))
    for (a, b) in edges:
        if edges[(a, b)] != 1 or edges[(b, a)] != 1:
            raise AssertionError("Open, duplicate, or inconsistently oriented mesh edge")

    center = tuple(math.fsum(p[i] for p in unique) / len(unique) for i in range(3))

    def relative(p):
        return tuple(p[i] - center[i] for i in range(3))

    parts = []
    for a, b, c in faces:
        u, v, w = relative(unique[a]), relative(unique[b]), relative(unique[c])
        # Signed tetrahedron volume. A positive sum requires outward winding.
        parts.append((u[0] * (v[1]*w[2] - v[2]*w[1])
                     + u[1] * (v[2]*w[0] - v[0]*w[2])
                     + u[2] * (v[0]*w[1] - v[1]*w[0])) / 6.0)
    volume = math.fsum(parts)
    if not math.isfinite(volume) or volume <= 0:
        raise AssertionError("Nonpositive oriented solid volume (inverted or degenerate)")
    return {"closed_manifold": True, "triangles": len(faces),
            "welded_vertices": len(unique), "signed_volume_m3": volume}


def verify_solid_volume(flat_vertices, triangle_indices, expected_volume_m3: float) -> dict:
    """Fail if kernel mesh volume disagrees with the analytic physical solid."""
    if not math.isfinite(expected_volume_m3) or expected_volume_m3 <= 0:
        raise ValueError("Invalid analytic reference volume")
    result = measure_closed_solid(flat_vertices, triangle_indices)
    actual = result["signed_volume_m3"]
    if not math.isclose(actual, expected_volume_m3, rel_tol=5e-4, abs_tol=1e-5):
        raise AssertionError(f"IFC kernel solid-volume mismatch: {actual} vs {expected_volume_m3} m3")
    return {**result, "analytic_reference_volume_m3": expected_volume_m3}
