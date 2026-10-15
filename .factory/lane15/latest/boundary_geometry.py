# This file was generated with the assistance of an AI coding tool.
"""One-zone IFC4 space-boundary geometry contract.

The six thermal faces are derived from the independent reference shell, not
from material-solid tessellation. Real IFC authoring/round-trip is mandatory
before labelling the handoff verified. No energy loads are inferred.
"""
from __future__ import annotations

import math

from baseline.single_zone_contract import shell

NAMES = ("Floor", "Roof", "South", "North", "East", "West")


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def unit(a):
    length = math.sqrt(dot(a, a))
    if not math.isfinite(length) or length < 1e-12:
        raise ValueError("Degenerate boundary axis")
    return tuple(x / length for x in a)


def boundary_frame(points):
    """Construct IFC plane from a CCW-in-plane rectangular thermal face.

    IFC IfcAxis2Placement3D.Axis is the plane Z normal; RefDirection is X.
    The IfcOpenShell boundary API's parameter prose swaps these labels,
    but its v0.9.0 implementation passes them to Axis2Placement3D in
    this order. The basis is verified here rather than blindly assumed.
    """
    if len(points) != 4 or any(len(p) != 3 for p in points):
        raise ValueError("Expected four 3D vertices")
    if any(not math.isfinite(v) for p in points for v in p):
        raise ValueError("Non-finite face coordinates")
    p0, p1, p2, p3 = points
    u = sub(p1, p0)
    v = sub(p3, p0)
    ref = unit(u)
    axis = unit(cross(u, v))
    y_axis = unit(cross(axis, ref))
    if abs(dot(ref, y_axis)) > 1e-9:
        raise ValueError("Skewed plane")
    if not math.isclose(dot(unit(v), y_axis), 1.0, abs_tol=1e-9):
        raise ValueError("Invalid face winding")
    xy = tuple((dot(sub(p, p0), ref), dot(sub(p, p0), y_axis)) for p in points)
    rebuilt = world_points(p0, axis, ref, xy)
    if not same_cycle(rebuilt, points):
        raise ValueError("Non-planar or distorted rectangle")
    if not math.isclose(xy[2][0], xy[1][0], abs_tol=1e-7) or not math.isclose(
        xy[2][1], xy[3][1], abs_tol=1e-7
    ):
        raise ValueError("Non-rectangular face")
    return {"outer_boundary": xy, "location": p0, "axis": axis, "ref_direction": ref}


def world_points(location, axis, ref_direction, xy):
    z = unit(axis)
    x = unit(ref_direction)
    if abs(dot(x, z)) > 1e-8:
        raise ValueError("IFC plane axes not orthogonal")
    y = unit(cross(z, x))
    return tuple(tuple(location[i] + u*x[i] + v*y[i] for i in range(3)) for u, v in xy)


def same_cycle(actual, expected, tolerance=1e-6):
    """Require same winding, allowing only cyclic first-vertex rotation."""
    if len(actual) != len(expected):
        return False
    n = len(actual)
    return any(all(math.dist(actual[(i + shift) % n], expected[i]) <= tolerance
                   for i in range(n)) for shift in range(n))


def expected_faces(d):
    return shell(d.length, d.width, d.height)


def create_boundary_links(model, space, elements, d):
    """Make explicit IFC4 first-level relationships using upstream API 0.9.0."""
    import ifcopenshell.api.boundary
    import ifcopenshell.api.root

    for name, points in expected_faces(d).items():
        frame = boundary_frame(points)
        relationship = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcRelSpaceBoundary1stLevel", name=f"{name} thermal boundary"
        )
        ifcopenshell.api.boundary.edit_attributes(
            model, entity=relationship, relating_space=space,
            related_building_element=elements[name], physical_or_virtual="PHYSICAL",
            internal_or_external="EXTERNAL_EARTH" if name == "Floor" else "EXTERNAL",
        )
        ifcopenshell.api.boundary.assign_connection_geometry(
            model, rel_space_boundary=relationship, **frame
        )


def verify_boundary_geometry(model, d, scale):
    """Validate saved/reopened IfcConnectionSurfaceGeometry against thermal faces."""
    spaces = [x for x in model.by_type("IfcSpace") if x.Name == "TestZone"]
    if len(spaces) != 1:
        raise AssertionError("Expected one TestZone")
    space = spaces[0]
    rows = {}
    for boundary in model.by_type("IfcRelSpaceBoundary"):
        if boundary.RelatingSpace != space:
            continue
        if boundary.is_a() != "IfcRelSpaceBoundary1stLevel":
            raise AssertionError(f"Unsupported IFC boundary level: {boundary.is_a()}")
        product = boundary.RelatedBuildingElement
        name = product.Name if product else None
        if name in rows:
            raise AssertionError(f"Duplicate IFC boundary: {name}")
        rows[name] = boundary
    expected = expected_faces(d)
    if set(rows) != set(expected):
        raise AssertionError(f"IFC thermal boundary names mismatch: {sorted(rows)}")
    stats = {}
    for name, target in expected.items():
        conn = rows[name].ConnectionGeometry
        if conn is None or not conn.is_a("IfcConnectionSurfaceGeometry"):
            raise AssertionError(f"Missing IFC connection surface: {name}")
        surface = conn.SurfaceOnRelatingElement
        if surface is None or not surface.is_a("IfcCurveBoundedPlane"):
            raise AssertionError(f"IFC connection is not a curve bounded plane: {name}")
        if surface.InnerBoundaries:
            raise AssertionError(f"Unexpected openings in one-zone fixture: {name}")
        plane = surface.BasisSurface
        if not plane.is_a("IfcPlane"):
            raise AssertionError(f"IFC boundary basis is not planar: {name}")
        placement = plane.Position
        loc = tuple(float(v) * scale for v in placement.Location.Coordinates)
        z_axis = tuple(float(v) for v in placement.Axis.DirectionRatios)
        x_axis = tuple(float(v) for v in placement.RefDirection.DirectionRatios)
        loop = surface.OuterBoundary
        if not loop.is_a("IfcPolyline"):
            raise AssertionError(f"IFC boundary is not a polyline: {name}")
        vertices_2d = [tuple(float(v) * scale for v in p.Coordinates) for p in loop.Points]
        if len(vertices_2d) != 5 or math.dist(vertices_2d[0], vertices_2d[-1]) > 1e-7:
            raise AssertionError(f"IFC boundary loop not quadrilateral and closed: {name}")
        points = world_points(loc, z_axis, x_axis, vertices_2d[:-1])
        if not same_cycle(points, target):
            raise AssertionError(f"IFC thermal geometry differs from USD/IDF face: {name}")
        generated = boundary_frame(points)
        if dot(unit(generated["axis"]), unit(boundary_frame(target)["axis"])) < 1 - 1e-9:
            raise AssertionError(f"Inverted thermal normal: {name}")
        a, b = math.dist(points[0], points[1]), math.dist(points[0], points[3])
        stats[name] = {"area_m2": a * b, "normal": list(generated["axis"])}
    return {"status": "GEOMETRY_READY_ONLY", "checked_surfaces": 6,
            "area_m2": {name: entry["area_m2"] for name, entry in stats.items()},
            "thermal_volume_m3": d.length * d.width * d.height,
            "scope": "IFC space-boundary planar coordinates versus synthetic USDA/IDF shell",
            "energy_simulation_verified": False}
