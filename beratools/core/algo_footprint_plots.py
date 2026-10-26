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
    (https://github.com/IrinaTerentieva/SegLine, src/fixed_area and
    src/fixed_length).

    Two modes choose the plot and subplot lengths along the centerline:
    fixed area derives them from target areas and the footprint width, fixed
    length uses them directly.

    The footprint is cut by its extended centerline (left/right sides) and by
    cross cuts at subplot stations along the centerline. Every resulting face is
    labelled by its side and by the station interval it projects to, and faces
    with the same label are dissolved. Labelling by geometry, not by split order,
    keeps sides consistent and gives exactly one geometry per plot and subplot.
"""

from __future__ import annotations

import bisect
import logging
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, polygonize, substring, unary_union

LOGGER_NAME = "footprint_plots"
logger = logging.getLogger(LOGGER_NAME)

MODE_AREA = "fixed_area"
MODE_LENGTH = "fixed_length"

# SegLine stores side as 0/1; here 0 is left and 1 is right of the line direction
SIDE_LEFT = 0
SIDE_RIGHT = 1

# A tail shorter than this fraction of the subplot spacing joins the last subplot
MIN_TAIL_FRACTION = 0.5
TANGENT_STEP = 0.5
# Pieces smaller than this (m2) left by cuts or by removing overlaps are dropped
MIN_PIECE_AREA = 1e-3
# Pieces closer than this (m) count as touching after an overlay
TOUCH_TOLERANCE = 1e-6
# Output coordinates are snapped to this grid (m); it removes zero-width spikes overlays leave
GRID_SIZE = 1e-6
# A line within this angle (degrees) of north-south or east-west counts as cardinal
CARDINAL_TOLERANCE = 15.0


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


def area_mode_lengths(width, plot_area, subplot_area):
    """
    Return (plot length, subplot length) along the line for fixed area mode.

    A plot covers both sides of the line, a subplot covers one side, so a subplot
    is length * width / 2. Subplots per side is rounded so subplots nest in plots.
    """
    subplots_per_side = max(1, round(plot_area / (2 * subplot_area)))
    subplot_length = 2 * subplot_area / width
    return subplots_per_side * subplot_length, subplot_length


def subplot_stations(length, plot_length, subplot_length):
    """
    Return [(start distance, plot index)] of the subplots along a line.

    Plots start every plot_length and subplots restart at each plot start. A
    piece shorter than MIN_TAIL_FRACTION of a subplot joins the previous subplot.
    """
    stations = []
    for plot_idx in range(max(1, math.ceil(length / plot_length))):
        plot_start = plot_idx * plot_length
        plot_end = min(plot_start + plot_length, length)
        count = max(1, math.ceil((plot_end - plot_start) / subplot_length))
        stations.extend((plot_start + k * subplot_length, plot_idx) for k in range(count))

    ends = [start for start, _ in stations[1:]] + [length]
    return [
        station
        for i, (station, end) in enumerate(zip(stations, ends))
        if i == 0 or end - station[0] >= MIN_TAIL_FRACTION * subplot_length
    ]


def split_footprint(footprint, centerline, plot_length, subplot_length):
    """
    Split one footprint into plots and subplots.

    Args:
        footprint: footprint Polygon or MultiPolygon
        centerline: centerline of the footprint (trimmed with prepare_centerline)
        plot_length: plot length along the centerline (m)
        subplot_length: subplot length along the centerline (m)

    Returns:
        (plots, subplots): plots is a list of (plot_idx, side, length, geometry),
        subplots is a list of (plot_idx, side, subplot_idx, length, geometry).
        length is measured along the centerline. Indexes count from 0 along the
        line; subplot_idx restarts in each plot.

    """
    footprint = shapely.force_2d(footprint)
    if plot_length <= 0 or subplot_length <= 0:
        return [], []

    stations = subplot_stations(centerline.length, plot_length, subplot_length)
    starts = [start for start, _ in stations]
    station_lengths = [end - start for start, end in zip(starts, [*starts[1:], centerline.length])]
    subplot_idx = []
    for i, (_, plot_idx) in enumerate(stations):
        first = i == 0 or stations[i - 1][1] != plot_idx
        subplot_idx.append(0 if first else subplot_idx[-1] + 1)

    # Cuts must cross the whole footprint; extra cuts at bends are healed by the dissolve
    width = estimate_width(footprint, centerline)
    reach = footprint.hausdorff_distance(centerline) + width + 1.0
    cuts = [_cross_cut(centerline, start, reach) for start in starts[1:]]
    edges = unary_union([footprint.boundary, _extend_line(centerline, reach), *cuts])

    shapely.prepare(footprint)
    pieces = {}
    for face in polygonize(edges):
        # crumbs where a cut clips the corner of a small footprint fragment
        if face.area <= MIN_PIECE_AREA:
            continue
        point = face.representative_point()
        if not footprint.contains(point):
            continue
        distance = centerline.project(point)
        station = max(bisect.bisect_right(starts, distance) - 1, 0)
        key = (_side_of(centerline, distance, point), station)
        pieces.setdefault(key, []).append(face)

    subplots = []
    plot_pieces = {}
    for (side, station), faces in sorted(pieces.items(), key=lambda item: (item[0][1], item[0][0])):
        geom = unary_union(faces)
        plot_idx = stations[station][1]
        subplots.append((plot_idx, side, subplot_idx[station], station_lengths[station], geom))
        plot_pieces.setdefault((plot_idx, side), []).append((station_lengths[station], geom))

    plots = [
        (plot_idx, side, sum(length for length, _ in parts), unary_union([geom for _, geom in parts]))
        for (plot_idx, side), parts in plot_pieces.items()
    ]
    return plots, subplots


def line_orientation(line) -> float:
    """
    Return the main direction of a line in degrees, 0 to 180 counter-clockwise from east.

    Segment directions are averaged as axes (angles doubled), weighted by length,
    so a line and its reverse give the same result and short wiggles count little.
    """
    coords = shapely.get_coordinates(line)
    dx, dy = np.diff(coords[:, 0]), np.diff(coords[:, 1])
    weights = np.hypot(dx, dy)
    doubled = 2 * np.arctan2(dy, dx)
    angle = math.atan2((weights * np.sin(doubled)).sum(), (weights * np.cos(doubled)).sum())
    # rounding keeps an angle a hair below 0 from wrapping to 180
    return round(math.degrees(angle) / 2, 9) % 180


def is_cardinal(line, tolerance=CARDINAL_TOLERANCE) -> bool:
    """Return True if the line runs within tolerance degrees of north-south or east-west."""
    offset = line_orientation(line) % 90
    return min(offset, 90 - offset) <= tolerance


def trim_line_ends(footprint, centerline, claimed):
    """
    Cut claimed area off the ends of a footprint and trim its centerline to match.

    Used where the centerline ends in an overlap another footprint keeps. The
    centerline keeps its longest stretch outside the claimed area, in its
    original direction. Footprint pieces that touch the claimed area but are not
    crossed by that stretch, such as bits poking out beyond the other line, are
    returned as leftovers. Other pieces, such as fragments of a multipart
    footprint, are kept.

    Returns:
        (footprint, centerline, leftovers). footprint and centerline are None if
        nothing is left.

    """
    stretches = [
        part
        for part in shapely.get_parts(centerline.difference(claimed))
        if part.geom_type == "LineString" and part.length > 0
    ]
    if not stretches:
        return None, None, polygon_parts(shapely.force_2d(footprint).difference(claimed))

    trimmed = max(stretches, key=lambda part: part.length)
    start, end = (centerline.project(Point(xy)) for xy in (trimmed.coords[0], trimmed.coords[-1]))
    if start > end:
        trimmed = trimmed.reverse()

    kept, leftovers = [], []
    for part in polygon_parts(shapely.force_2d(footprint).difference(claimed)):
        cut_off = part.distance(claimed) <= TOUCH_TOLERANCE and not part.intersects(trimmed)
        (leftovers if cut_off else kept).append(part)
    if not kept:
        return None, None, leftovers
    return unary_union(kept), trimmed, leftovers


def remove_overlap(subplots, claimed):
    """
    Cut the claimed area out of subplots.

    Subplots keep their place along the line: a subplot the claimed area cuts
    in two keeps both pieces, one on each side of the crossing, so its edges
    stay on the cross cuts. Subplots left empty are dropped.

    Args:
        subplots: list of (plot_idx, side, subplot_idx, length, geometry)
        claimed: area kept by other footprints, or None

    """
    if claimed is None or claimed.is_empty:
        return subplots

    shapely.prepare(claimed)
    result = []
    for plot_idx, side, subplot_idx, length, geom in subplots:
        if claimed.intersects(geom):
            parts = polygon_parts(geom.difference(claimed))
            if not parts:
                continue
            geom = unary_union(parts)
        result.append((plot_idx, side, subplot_idx, length, geom))
    return result


def plots_from_subplots(plots, subplots):
    """Rebuild plot geometries as the union of their subplots, keeping plot lengths."""
    lengths = {(plot_idx, side): length for plot_idx, side, length, _ in plots}
    geoms = {}
    for plot_idx, side, _, _, geom in subplots:
        geoms.setdefault((plot_idx, side), []).append(geom)
    return [
        (plot_idx, side, lengths[(plot_idx, side)], unary_union(parts))
        for (plot_idx, side), parts in geoms.items()
    ]


def clean_polygon(geom):
    """
    Snap geom to GRID_SIZE and keep its polygon parts, or None if nothing is left.

    Cutting and merging pieces whose edges almost coincide leaves zero-width
    spikes in the outline; snapping to a fine grid removes them. Neighbouring
    pieces snap to the same grid, so their shared edges still match.
    """
    parts = polygon_parts(geom)
    return unary_union(parts) if parts else None


def polygon_parts(geom):
    """
    Return the polygon parts of an overlay result, dropping line-like and tiny leftovers.

    The result is snapped to GRID_SIZE first: cutting along an edge that almost
    coincides with another leaves zero-width spikes, which would otherwise carry
    into the plots and confuse the inside test when splitting.
    """
    return [
        part
        for part in shapely.get_parts(shapely.set_precision(geom, GRID_SIZE))
        if part.geom_type == "Polygon" and part.area > MIN_PIECE_AREA
    ]


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
