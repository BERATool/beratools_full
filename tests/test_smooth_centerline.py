"""Tests for the Smooth Centerline tool (ported from SegLine)."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString

from beratools.core.algo_geometry import smooth_sharp_vertices, vertex_interior_angle
from beratools.tools.smooth_centerline import smooth_centerline


def test_vertex_interior_angle_straight_and_right_angle():
    assert vertex_interior_angle((0, 0), (1, 0), (2, 0)) == pytest.approx(180.0)
    assert vertex_interior_angle((0, 0), (1, 0), (1, 1)) == pytest.approx(90.0)


def test_smooth_sharp_vertices_cuts_hairpin():
    line = LineString([(0, 0), (50, 0), (5, 25)])

    smoothed = smooth_sharp_vertices(line, angle_threshold=130, buffer_distance=2)

    assert not smoothed.equals(line)
    assert smoothed.is_valid
    assert smoothed.hausdorff_distance(line) <= 2
    assert smoothed.coords[0] == line.coords[0]
    assert smoothed.coords[-1] == line.coords[-1]


def test_smooth_sharp_vertices_keeps_gentle_bend():
    line = LineString([(0, 0), (50, 0), (100, 18)])

    smoothed = smooth_sharp_vertices(line, angle_threshold=130, buffer_distance=2)

    assert smoothed.equals(line)


def test_smooth_sharp_vertices_only_changes_area_near_corner():
    line = LineString([(0, 0), (50, 0), (50, 50)])

    smoothed = smooth_sharp_vertices(line, angle_threshold=130, buffer_distance=2)

    assert len(smoothed.coords) == 4
    assert smoothed.coords[1] == pytest.approx((48, 0))
    assert smoothed.coords[2] == pytest.approx((50, 2))


def test_smooth_sharp_vertices_keeps_z():
    line = LineString([(0, 0, 5), (50, 0, 6), (50, 50, 7)])

    smoothed = smooth_sharp_vertices(line, angle_threshold=130, buffer_distance=2)

    assert smoothed.has_z


def test_smooth_sharp_vertices_handles_disjoint_multilinestring():
    line = MultiLineString([[(0, 0), (50, 0), (50, 50)], [(100, 0), (150, 0)]])

    smoothed = smooth_sharp_vertices(line, angle_threshold=130, buffer_distance=2)

    assert smoothed.geom_type == "MultiLineString"
    assert len(smoothed.geoms) == 2
    assert not smoothed.geoms[0].equals(line.geoms[0])


def test_smooth_centerline_tool_keeps_order_and_attributes(tmp_path):
    lines = [
        LineString([(0, 0), (50, 0), (50, 50)]),
        LineString([(0, 100), (50, 100), (100, 118)]),
        LineString([(0, 200), (50, 200), (5, 225)]),
    ]
    gdf = gpd.GeoDataFrame({"line_id": [10, 20, 30]}, geometry=lines, crs="EPSG:2956")
    in_file = tmp_path / "lines.gpkg"
    out_file = tmp_path / "smoothed.gpkg"
    gdf.to_file(in_file, layer="centerline")

    smooth_centerline(
        in_line=f"{in_file.as_posix()}|centerline",
        out_line=f"{out_file.as_posix()}|centerline_smooth",
        angle_threshold=130,
        buffer_distance=2,
        processes=1,
    )

    out = gpd.read_file(out_file, layer="centerline_smooth")
    assert list(out["line_id"]) == [10, 20, 30]
    assert [geom.equals(src) for geom, src in zip(out.geometry, lines)] == [False, True, False]
