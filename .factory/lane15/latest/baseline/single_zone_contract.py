# This file was generated with the assistance of an AI coding tool.
"""Reference geometry QA for Lane 15's synthetic one-zone building.

This is a geometrical contract, NOT an IFC validator or an energy model.
The reference shell is zero thickness. IFC physical walls are not.
"""
import json
import math


def shell(length=10.0, width=8.0, height=3.0):
    """Faces have outward winding and coordinates in metres."""
    if not all(math.isfinite(x) and x > 0 for x in (length, width, height)):
        raise ValueError("dimensions must be finite and positive")
    l, w, h = length, width, height
    return {
        "Floor": ((0, 0, 0), (0, w, 0), (l, w, 0), (l, 0, 0)),
        "Roof": ((0, 0, h), (l, 0, h), (l, w, h), (0, w, h)),
        "South": ((0, 0, 0), (l, 0, 0), (l, 0, h), (0, 0, h)),
        "North": ((l, w, 0), (0, w, 0), (0, w, h), (l, w, h)),
        "East": ((l, 0, 0), (l, w, 0), (l, w, h), (l, 0, h)),
        "West": ((0, w, 0), (0, 0, 0), (0, 0, h), (0, w, h)),
    }


def area_vector(face):
    p, q, r, s = face
    def diff(a, b):
        return tuple(x - y for x, y in zip(a, b))
    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    a = cross(diff(q, p), diff(r, p))
    b = cross(diff(r, p), diff(s, p))
    return tuple((x + y) / 2 for x, y in zip(a, b))


def measurements(length=10.0, width=8.0, height=3.0):
    faces = shell(length, width, height)
    areas = {}
    volume = 0.0
    for name, face in faces.items():
        vec = area_vector(face)
        areas[name] = math.sqrt(sum(x * x for x in vec))
        center = tuple(sum(p[i] for p in face) / 4 for i in range(3))
        volume += sum(x * y for x, y in zip(vec, center)) / 3
    return {"units": "m", "face_areas_m2": areas, "envelope_area_m2": sum(areas.values()),
            "nominal_volume_m3": volume, "energy_demand_kwh": None}


def self_test():
    m = measurements()
    assert m["face_areas_m2"] == {"Floor": 80.0, "Roof": 80.0, "South": 30.0, "North": 30.0,
                                      "East": 24.0, "West": 24.0}
    assert m["envelope_area_m2"] == 268.0
    assert math.isclose(m["nominal_volume_m3"], 240.0)
    expected = {"Floor": (0, 0, -1), "Roof": (0, 0, 1), "South": (0, -1, 0),
                "North": (0, 1, 0), "East": (1, 0, 0), "West": (-1, 0, 0)}
    for name, face in shell().items():
        vec = area_vector(face)
        assert tuple(round(v / m["face_areas_m2"][name]) for v in vec) == expected[name]
    for invalid in (0, -1, math.nan, math.inf):
        try:
            shell(length=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid dimension accepted")


if __name__ == "__main__":
    self_test()
    print(json.dumps(measurements(), indent=2))
