"""
Copyright (C) 2025 Applied Geospatial Research Group.

This script is licensed under the GNU General Public License v3.0.
See <https://gnu.org/licenses/gpl-3.0> for full license details.

Author: Irina Terentieva (original SegLine code)

Description:
    This script is part of the BERA Tools.
    Webpage: https://github.com/BERATool/beratools

    Split a line footprint into plots and subplots along its centerline.
    Ported from SegLine by Irina Terentieva
    (https://github.com/IrinaTerentieva/SegLine, src/utils/split_to_plots.py,
    split_to_sides.py and split_to_subplots.py).

    The footprint is cut by its extended centerline (left/right sides) and by
    cross cuts at regular stations along the centerline. Every resulting face is
    labelled by its side and by the station interval it projects to, and faces
    with the same label are dissolved. Labelling by geometry, not by split order,
    keeps sides consistent and gives exactly one geometry per plot and subplot.
"""

from __future__ import annotations

import logging
import math

import shapely
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, polygonize, substring, unary_union

LOGGER_NAME = "footprint_plots"
logger = logging.getLogger(LOGGER_NAME)

SIDE_LEFT = "L"
SIDE_RIGHT = "R"

# A tail shorter than this fraction of the subplot spacing joins the last subplot
MIN_TAIL_FRACTION = 0.5
TANGENT_STEP = 0.5


def prepare_centerline(line, footprint):
    """Merge line parts and trim the line to the stretch that overlaps the footprint."""
    if line is None or line.is_empty or footprint is None or footprint.is_empty:
        return None

    line = shapely.force_2d(line)
    if line.geom_type == "MultiLineString":
        line = linemerge(line)
        if line.geom_type == "MultiLineString":
            line = max(line.geoms, key=lambda part: part.intersection(footprint).length)
    if line.geom_type != "LineString":
        return None

    inside = line.intersection(footprint)
    if inside.is_empty:
        return None
    distances = [line.project(Point(xy)) for xy in shapely.get_coordinates(inside)]
    start, end = min(distances), max(distances)
    if end - start <= 0:
        return None
    return substring(line, start, end)


def estimate_width(footprint, centerline) -> float:
    """
    Return the average footprint width: footprint area over trimmed centerline length.

    Using this width makes the mean subplot area match the target.
    """
    return footprint.area / centerline.length if centerline.length > 0 else 0.0


def subplot_spacing(width, plot_area, subplot_area):
    """
    Return (station spacing, subplots per plot side).

    A plot covers both sides of the line, a subplot covers one side, so a subplot
    is spacing * width / 2. Subplots per side is rounded so subplots nest in plots.
    """
    subplots_per_side = max(1, round(plot_area / (2 * subplot_area)))
    spacing = 2 * subplot_area / width
    return spacing, subplots_per_side


def split_footprint(footprint, centerline, plot_area, subplot_area):
    """
    Split one footprint into plots and subplots.

    Args:
        footprint: footprint Polygon or MultiPolygon
        centerline: centerline of the footprint (trimmed with prepare_centerline)
        plot_area: target plot area covering both sides of the line (m2)
        subplot_area: target subplot area on one side of the line (m2)

    Returns:
        (plots, subplots, width): plots is a list of (plot_id, side, geometry),
        subplots is a list of (plot_id, side, subplot_id, geometry).

    """
    footprint = shapely.force_2d(footprint)
    width = estimate_width(footprint, centerline)
    if width <= 0:
        return [], [], width

    spacing, subplots_per_side = subplot_spacing(width, plot_area, subplot_area)
    length = centerline.length
    full_count = int(length // spacing)
    tail = length - full_count * spacing
    station_count = full_count + (1 if full_count == 0 or tail >= MIN_TAIL_FRACTION * spacing else 0)

    # Cuts must cross the whole footprint; extra cuts at bends are healed by the dissolve
    reach = footprint.hausdorff_distance(centerline) + width + 1.0
    cuts = [_cross_cut(centerline, k * spacing, reach) for k in range(1, station_count)]
    edges = unary_union([footprint.boundary, _extend_line(centerline, reach), *cuts])

    shapely.prepare(footprint)
    pieces = {}
    for face in polygonize(edges):
        point = face.representative_point()
        if not footprint.contains(point):
            continue
        distance = centerline.project(point)
        station = min(int(distance // spacing), station_count - 1)
        key = (_side_of(centerline, distance, point), station)
        pieces.setdefault(key, []).append(face)

    subplots = []
    plot_pieces = {}
    for (side, station), faces in sorted(pieces.items(), key=lambda item: (item[0][1], item[0][0])):
        geom = unary_union(faces)
        plot_id, subplot_id = divmod(station, subplots_per_side)
        subplots.append((plot_id, side, subplot_id, geom))
        plot_pieces.setdefault((plot_id, side), []).append(geom)

    plots = [(plot_id, side, unary_union(geoms)) for (plot_id, side), geoms in plot_pieces.items()]
    return plots, subplots, width


def _tangent(line, distance):
    start = line.interpolate(max(distance - TANGENT_STEP, 0))
    end = line.interpolate(min(distance + TANGENT_STEP, line.length))
    dx, dy = end.x - start.x, end.y - start.y
    norm = math.hypot(dx, dy)
    return (dx / norm, dy / norm) if norm > 0 else (1.0, 0.0)


def _side_of(line, distance, point):
    origin = line.interpolate(distance)
    tx, ty = _tangent(line, distance)
    cross = tx * (point.y - origin.y) - ty * (point.x - origin.x)
    return SIDE_LEFT if cross > 0 else SIDE_RIGHT


def _cross_cut(line, distance, reach):
    origin = line.interpolate(distance)
    tx, ty = _tangent(line, distance)
    return LineString(
        [(origin.x + ty * reach, origin.y - tx * reach), (origin.x - ty * reach, origin.y + tx * reach)]
    )


def _extend_line(line, distance):
    """Extend both ends straight along the end tangents so the line crosses the footprint."""
    start, end = line.interpolate(0), line.interpolate(line.length)
    sx, sy = _tangent(line, 0)
    ex, ey = _tangent(line, line.length)
    coords = list(line.coords)
    return LineString(
        [
            (start.x - sx * distance, start.y - sy * distance),
            *coords,
            (end.x + ex * distance, end.y + ey * distance),
        ]
    )
