"""Tests for the Footprint Plots and Subplots tool (ported from SegLine)."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from beratools.core.algo_footprint_plots import prepare_centerline, split_footprint
from beratools.tools.footprint_plots import footprint_plots, match_lines_to_footprints

WIDTH = 5.0


def _split(line, footprint, plot_area=100, subplot_area=10):
    return split_footprint(footprint, prepare_centerline(line, footprint), plot_area, subplot_area)


def _assert_partition(footprint, subplots):
    geoms = [geom for *_, geom in subplots]
    union = unary_union(geoms)
    assert union.area == pytest.approx(footprint.area, abs=1e-3)
    assert sum(geom.area for geom in geoms) == pytest.approx(union.area, abs=1e-3)
    keys = [(plot_id, side, subplot_id) for plot_id, side, subplot_id, _ in subplots]
    assert len(keys) == len(set(keys))


def test_straight_footprint_gives_equal_plots_and_subplots():
    line = LineString([(0, 0), (200, 0)])
    footprint = line.buffer(WIDTH / 2, cap_style="flat")

    plots, subplots, width = _split(line, footprint)

    assert width == pytest.approx(WIDTH)
    assert len(plots) == 20
    assert len(subplots) == 100
    assert all(geom.area == pytest.approx(50) for *_, geom in plots)
    assert all(geom.area == pytest.approx(10) for *_, geom in subplots)
    assert {subplot_id for _, _, subplot_id, _ in subplots} == {0, 1, 2, 3, 4}
    _assert_partition(footprint, subplots)


def test_sides_follow_line_direction_with_uneven_footprint():
    line = LineString([(0, 0), (200, 0)])
    lobe = LineString([(60, 0), (60, 8)]).buffer(1.5, cap_style="flat")
    footprint = line.buffer(WIDTH / 2, cap_style="flat").union(lobe)

    plots, subplots, _ = _split(line, footprint)

    assert all(geom.centroid.y > 0 for _, side, geom in plots if side == "L")
    assert all(geom.centroid.y < 0 for _, side, geom in plots if side == "R")
    _assert_partition(footprint, subplots)


@pytest.mark.parametrize(
    "coords",
    [
        [(0, 0), (100, 0), (160, 60)],
        [(0, 0), (100, 0), (100, 12), (0, 12)],
    ],
)
def test_bent_footprint_is_partitioned(coords):
    line = LineString(coords)
    footprint = line.buffer(WIDTH / 2, cap_style="flat", join_style="mitre")

    _, subplots, _ = _split(line, footprint)

    _assert_partition(footprint, subplots)
    mean_area = sum(geom.area for *_, geom in subplots) / len(subplots)
    assert mean_area == pytest.approx(10, rel=0.05)


def test_short_tail_joins_last_subplot():
    line = LineString([(0, 0), (203, 0)])
    footprint = line.buffer(WIDTH / 2, cap_style="flat")

    _, subplots, _ = _split(line, footprint)

    assert min(geom.area for *_, geom in subplots) >= 5
    _assert_partition(footprint, subplots)


def test_centerline_longer_than_footprint_is_trimmed():
    line = LineString([(-500, 0), (700, 0)])
    footprint = LineString([(0, 0), (100, 0)]).buffer(WIDTH / 2, cap_style="flat")

    plots, subplots, width = _split(line, footprint)

    assert width == pytest.approx(WIDTH)
    assert min(plot_id for plot_id, *_ in plots) == 0
    assert len(subplots) == 50


def test_match_lines_to_footprints_uses_longest_overlap():
    footprints = gpd.GeoDataFrame(geometry=[LineString([(0, 0), (100, 0)]).buffer(2.5, cap_style="flat")])
    lines = gpd.GeoDataFrame(
        geometry=[
            LineString([(50, -10), (50, 10)]),
            LineString([(0, 0), (100, 0)]),
            LineString([(0, 50), (9, 50)]),
        ]
    )

    assert match_lines_to_footprints(footprints, lines) == {0: 1}


def test_footprint_plots_tool_writes_plots_and_subplots(tmp_path):
    lines = [LineString([(0, 0), (200, 0)]), LineString([(0, 100), (100, 100), (160, 160)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [7, 8]}, geometry=lines, crs="EPSG:2956")
    fp_gdf = gpd.GeoDataFrame(
        geometry=[line.buffer(WIDTH / 2, cap_style="flat", join_style="mitre") for line in lines],
        crs="EPSG:2956",
    )
    in_file = tmp_path / "input.gpkg"
    out_file = tmp_path / "output.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")

    footprint_plots(
        in_footprint=f"{in_file.as_posix()}|footprint",
        in_line=f"{in_file.as_posix()}|centerline",
        out_plot=f"{out_file.as_posix()}|plots",
        out_subplot=f"{out_file.as_posix()}|subplots",
        plot_area=100,
        subplot_area=10,
        processes=1,
    )

    plots = gpd.read_file(out_file, layer="plots")
    subplots = gpd.read_file(out_file, layer="subplots")
    assert set(plots["line_id"]) == {7, 8}
    assert set(subplots["side"]) == {"L", "R"}
    assert not subplots.duplicated(["FP_ID", "plot_id", "side", "subplot_id"]).any()
    assert subplots.area.sum() == pytest.approx(fp_gdf.area.sum(), abs=1e-2)


def test_footprint_plots_rejects_too_small_plot_area(tmp_path):
    with pytest.raises(ValueError):
        footprint_plots("a.gpkg|fp", "a.gpkg|cl", "o.gpkg|p", "o.gpkg|s", plot_area=10, subplot_area=10)
