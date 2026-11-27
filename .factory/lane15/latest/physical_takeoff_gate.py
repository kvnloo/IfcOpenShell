# This file was generated with the assistance of an AI coding tool.
"""Independent axis-aligned material-solid preflight for the Lane 15 IFC fixture.

Analytic geometry only: this does not parse/mesh an IFC file or establish
real quantities, load-bearing fitness, procurement, embodied carbon or energy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ifc_author import Dimensions, bounds_from_endpoints, pieces


@dataclass(frozen=True)
class Box:
    name: str
    low: tuple[float, float, float]
    high: tuple[float, float, float]

    @property
    def volume(self) -> float:
        return math.prod(b - a for a, b in zip(self.low, self.high))


def _close(a: float, b: float, tolerance: float = 1e-8) -> bool:
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=tolerance)


def _equal_bounds(actual, expected) -> bool:
    return all(_close(a, b) for face1, face2 in zip(actual, expected) for a, b in zip(face1, face2))


def _box(spec: dict, dimensions: Dimensions) -> Box:
    name = spec['name']
    if spec['kind'] == 'IfcWall':
        p1, p2 = spec['p1'], spec['p2']
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        if not (math.isclose(dx, 0, abs_tol=1e-9) ^ math.isclose(dy, 0, abs_tol=1e-9)):
            raise AssertionError(f'{name}: wall is not axis-aligned')
        actual = bounds_from_endpoints(p1, p2, dimensions.wall, dimensions.height)
    elif spec['kind'] == 'IfcSlab':
        vertices = spec['polyline']
        if len(vertices) != 5 or vertices[0] != vertices[-1]:
            raise AssertionError(f'{name}: slab polygon is not a closed four-corner loop')
        corners = vertices[:-1]
        x0, x1 = min(p[0] for p in corners), max(p[0] for p in corners)
        y0, y1 = min(p[1] for p in corners), max(p[1] for p in corners)
        if set(corners) != {(x0, y0), (x1, y0), (x1, y1), (x0, y1)}:
            raise AssertionError(f'{name}: slab is not a rectangular footprint')
        signed_area = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(vertices, vertices[1:])) / 2
        if not _close(signed_area, (x1-x0)*(y1-y0)):
            raise AssertionError(f'{name}: slab winding or area is incorrect')
        z = spec['z']
        sense = spec['sense']
        if name == 'Floor' and sense == 'NEGATIVE':
            actual = ((x0, y0, z-dimensions.slab), (x1, y1, z))
        elif name == 'Roof' and sense == 'POSITIVE':
            actual = ((x0, y0, z), (x1, y1, z+dimensions.slab))
        else:
            raise AssertionError(f'{name}: wrong slab extrusion sense')
    else:
        raise AssertionError(f'{name}: unexpected type {spec["kind"]}')
    if not _equal_bounds(actual, spec['bbox']):
        raise AssertionError(f'{name}: declared and reconstructed material bounds disagree')
    if any(b <= a for a, b in zip(*actual)):
        raise AssertionError(f'{name}: degenerate material solid')
    return Box(name, actual[0], actual[1])


def _intersection_length(a: Box, b: Box, axis: int) -> float:
    return max(0., min(a.high[axis], b.high[axis]) - max(a.low[axis], b.low[axis]))


def _contact_area(a: Box, b: Box) -> float:
    area = 0.
    for axis in range(3):
        if _close(a.high[axis], b.low[axis]) or _close(b.high[axis], a.low[axis]):
            side_axes = [i for i in range(3) if i != axis]
            area += math.prod(_intersection_length(a, b, i) for i in side_axes)
    return area


def check_assembly(d: Dimensions) -> dict:
    """Reject overlapping/detached solids; report synthetic volumes in m³."""
    components = pieces(d)
    by_name = {spec['name']: spec for spec in components}
    expected_names = {'South', 'East', 'North', 'West', 'Floor', 'Roof'}
    if set(by_name) != expected_names or len(components) != 6:
        raise AssertionError('Missing/duplicated physical components')
    solids = {name: _box(spec, d) for name, spec in by_name.items()}
    all_solids = list(solids.values())
    for n, a in enumerate(all_solids):
        for b in all_solids[n+1:]:
            collision = math.prod(_intersection_length(a, b, axis) for axis in range(3))
            if collision > 1e-8:
                raise AssertionError(f'Material overlap: {a.name}/{b.name}: {collision} m3')
    for wall in ('South', 'East', 'North', 'West'):
        for slab in ('Floor', 'Roof'):
            if _contact_area(solids[wall], solids[slab]) <= 1e-8:
                raise AssertionError(f'Detached component: {wall} does not meet {slab}')
    for a, b in (('South', 'East'), ('East', 'North'), ('North', 'West'), ('West', 'South')):
        if _contact_area(solids[a], solids[b]) <= 1e-8:
            raise AssertionError(f'Detached corner: {a}/{b}')
    outside_low = tuple(min(x.low[i] for x in all_solids) for i in range(3))
    outside_high = tuple(max(x.high[i] for x in all_solids) for i in range(3))
    true_outer = ((-d.wall, -d.wall, -d.slab),
                  (d.length+d.wall, d.width+d.wall, d.height+d.slab))
    if not _equal_bounds((outside_low, outside_high), true_outer):
        raise AssertionError('Outer building bounds mismatch')
    wall_volume = sum(solids[name].volume for name in ('South','East','North','West'))
    slab_volume = solids['Floor'].volume + solids['Roof'].volume
    expected_wall = 2*d.wall*d.height*(d.length+d.width+2*d.wall)
    expected_slab = 2*d.slab*(d.length+2*d.wall)*(d.width+2*d.wall)
    if not _close(wall_volume, expected_wall) or not _close(slab_volume, expected_slab):
        raise AssertionError('Independent material volume identity failed')
    void = d.length*d.width*d.height
    outer = math.prod(b-a for a,b in zip(outside_low, outside_high))
    if not _close(outer - void, wall_volume + slab_volume):
        raise AssertionError('Outer-minus-clear-volume identity failed')
    return {
        'scope': 'analytical fixture quantities, NOT_IFC_MEASURED',
        'component_count': len(solids),
        'material_intersections_m3': 0,
        'physical_wall_volume_m3': round(wall_volume, 9),
        'physical_slab_volume_m3': round(slab_volume, 9),
        'total_shell_material_volume_m3': round(wall_volume + slab_volume, 9),
        'nominal_air_volume_m3': round(void, 9),
        'outer_volume_m3': round(outer, 9),
        'wall_slab_face_contacts': 8,
        'wall_corner_face_contacts': 4,
        'ifc_kernel_check': 'NOT_RUN',
        'embodied_carbon_kgco2e': None,
        'energy_demand_kwh': None,
    }
