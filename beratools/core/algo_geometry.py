"""Reusable vector geometry post-processing helpers."""

from __future__ import annotations

import logging
import math

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon
from shapely.ops import linemerge, substring

LOGGER_NAME = "algo_geometry"
logger = logging.getLogger(LOGGER_NAME)

def chaikin_smooth_line(line: LineString, *, iterations: int) -> LineString:
    if line is None or line.is_empty or iterations <= 0 or len(line.coords) < 3:
        return line

    points = [(float(x), float(y)) for x, y, *_ in line.coords]
    for _ in range(iterations):
        smoothed = [points[0]]
        for point, next_point in zip(points, points[1:]):
            smoothed.append((0.75 * point[0] + 0.25 * next_point[0], 0.75 * point[1] + 0.25 * next_point[1]))
            smoothed.append((0.25 * point[0] + 0.75 * next_point[0], 0.25 * point[1] + 0.75 * next_point[1]))
        smoothed.append(points[-1])
        points = smoothed
    return LineString(points)


def vertex_interior_angle(p1, p2, p3) -> float:
    """Return the interior angle in degrees at p2; 180 is straight, smaller is sharper."""
    dx1, dy1 = p1[0] - p2[0], p1[1] - p2[1]
    dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
    magnitude1 = math.hypot(dx1, dy1)
    magnitude2 = math.hypot(dx2, dy2)
    if magnitude1 == 0 or magnitude2 == 0:
        return 180.0

    cos_angle = (dx1 * dx2 + dy1 * dy2) / (magnitude1 * magnitude2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_angle))))


def smooth_sharp_vertices(line, *, angle_threshold: float, buffer_distance: float):
    """
    Cut sharp corners of a line and leave the rest of the line unchanged.

    Each vertex with an interior angle below angle_threshold is replaced by a straight
    chord between the points where the line enters and leaves a circle of radius
    buffer_distance around that vertex.

    Ported from SegLine by Irina Terentieva
    (https://github.com/IrinaTerentieva/SegLine, src/utils/smooth_centerline.py).
    """
    if line is None or line.is_empty or buffer_distance <= 0:
        return line
    if line.geom_type == "MultiLineString":
        line = linemerge(line)
        if line.geom_type == "MultiLineString":
            return MultiLineString(
                [
                    smooth_sharp_vertices(
                        part, angle_threshold=angle_threshold, buffer_distance=buffer_distance
                    )
                    for part in line.geoms
                ]
            )
    if line.geom_type != "LineString" or len(line.coords) < 3:
        return line

    coords = list(line.coords)
    smoothed = line
    next_index = 1
    for i in range(1, len(coords) - 1):
        # Skip the vertex right after a cut corner to avoid over-smoothing
        if i < next_index:
            continue
        if vertex_interior_angle(coords[i - 1], coords[i], coords[i + 1]) < angle_threshold:
            smoothed = _cut_corner(smoothed, Point(coords[i]), buffer_distance)
            next_index = i + 2
    return smoothed


def _cut_corner(line: LineString, vertex: Point, buffer_distance: float) -> LineString:
    piece = line.intersection(vertex.buffer(buffer_distance))
    if piece.geom_type != "LineString" or piece.is_empty:
        return line

    chord_start, chord_end = piece.coords[0], piece.coords[-1]
    start_dist = line.project(Point(chord_start))
    end_dist = line.project(Point(chord_end))
    if start_dist >= end_dist:
        return line

    new_coords = []
    if start_dist > 0:
        new_coords.extend(substring(line, 0, start_dist).coords[:-1])
    new_coords.extend([chord_start, chord_end])
    if end_dist < line.length:
        new_coords.extend(substring(line, end_dist, line.length).coords[1:])
    return LineString(new_coords) if len(new_coords) >= 2 else line


def chaikin_smooth_polygon(geometry, *, iterations: int):
    if geometry is None or geometry.is_empty or iterations <= 0:
        return geometry
    if geometry.geom_type == "Polygon":
        exterior = _chaikin_smooth_ring(geometry.exterior.coords, iterations=iterations)
        interiors = [_chaikin_smooth_ring(interior.coords, iterations=iterations) for interior in geometry.interiors]
        return Polygon(exterior, interiors)
    if geometry.geom_type == "MultiPolygon":
        return MultiPolygon([chaikin_smooth_polygon(part, iterations=iterations) for part in geometry.geoms])
    return geometry


def process_corridor_polygon(
    polygon,
    cid=None,
    *,
    delete_holes=False,
    simplify=False,
    simplify_length=0.0,
    smooth=False,
    smooth_iterations=0,
):
    """Apply stage-8 style polygon cleanup, simplification, and smoothing."""

    if polygon is None or polygon.is_empty:
        return polygon

    processed = polygon
    if delete_holes:
        processed = _delete_polygon_holes(processed)
        processed = processed.buffer(0.5)
        processed = processed.buffer(-0.5)
    if simplify and float(simplify_length) > 0:
        area_before = processed.area
        processed = processed.simplify(float(simplify_length), preserve_topology=True)
        logger.debug(
        f"{cid} simplify "
        f"area_change="
        f"{100 * (processed.area - area_before) / area_before:.2f}%")
    if smooth and int(smooth_iterations) > 0:
        processed = chaikin_smooth_polygon(processed, iterations=int(smooth_iterations))
    if processed is not None and not processed.is_valid:
        processed = processed.buffer(0)
    return processed


def _delete_polygon_holes(geometry):
    if geometry.geom_type == "Polygon":
        return Polygon(geometry.exterior)
    if geometry.geom_type == "MultiPolygon":
        return MultiPolygon([Polygon(poly.exterior) for poly in geometry.geoms])
    return geometry


def _chaikin_smooth_ring(coords, *, iterations: int) -> list[tuple[float, float]]:
    points = [(float(x), float(y)) for x, y, *_ in coords]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3 or iterations <= 0:
        return points + points[:1]

    for _ in range(iterations):
        smoothed = []
        for index, point in enumerate(points):
            next_point = points[(index + 1) % len(points)]
            smoothed.append((0.75 * point[0] + 0.25 * next_point[0], 0.75 * point[1] + 0.25 * next_point[1]))
            smoothed.append((0.25 * point[0] + 0.75 * next_point[0], 0.25 * point[1] + 0.75 * next_point[1]))
        points = smoothed
    return points + points[:1]
