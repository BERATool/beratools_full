"""Tests for the Footprint Plots and Subplots tool (ported from SegLine)."""

import math

import geopandas as gpd
import pytest
import shapely
from shapely.geometry import GeometryCollection, LineString, Point, Polygon
from shapely.ops import unary_union

from beratools.core.algo_footprint_plots import (
    SIDE_LEFT,
    SIDE_RIGHT,
    area_mode_lengths,
    estimate_width,
    is_cardinal,
    line_orientation,
    prepare_centerline,
    split_footprint,
    clean_polygon,
    polygon_parts,
    remove_overlap,
    subplot_stations,
    trim_line_ends,
)
from beratools.tools.footprint_plots import footprint_plots, match_lines_to_footprints, overlap_claims

WIDTH = 5.0
SEGLINE_COLUMNS = [
    "UniqueID",
    "side",
    "plot_id",
    "subplot_id",
    "area",
    "length",
    "perimeter",
    "plot_area",
    "subplot_area",
]


def _split_area(line, footprint, plot_area=100, subplot_area=10):
    centerline = prepare_centerline(line, footprint)
    lengths = area_mode_lengths(estimate_width(footprint, centerline), plot_area, subplot_area)
    return split_footprint(footprint, centerline, *lengths)


def _split_length(line, footprint, plot_length=50, subplot_length=10):
    return split_footprint(footprint, prepare_centerline(line, footprint), plot_length, subplot_length)


def _assert_partition(footprint, subplots):
    geoms = [geom for *_, geom in subplots]
    union = unary_union(geoms)
    assert union.area == pytest.approx(footprint.area, abs=1e-3)
    assert sum(geom.area for geom in geoms) == pytest.approx(union.area, abs=1e-3)
    keys = [(plot_id, side, subplot_id) for plot_id, side, subplot_id, *_ in subplots]
    assert len(keys) == len(set(keys))


def test_straight_footprint_gives_equal_plots_and_subplots():
    line = LineString([(0, 0), (200, 0)])
    footprint = line.buffer(WIDTH / 2, cap_style="flat")

    plots, subplots = _split_area(line, footprint)

    assert len(plots) == 20
    assert len(subplots) == 100
    assert all(geom.area == pytest.approx(50) for *_, geom in plots)
    assert all(geom.area == pytest.approx(10) for *_, geom in subplots)
    assert {subplot_id for _, _, subplot_id, *_ in subplots} == {0, 1, 2, 3, 4}
    assert all(length == pytest.approx(4) for *_, length, _ in subplots)
    assert all(length == pytest.approx(20) for *_, length, _ in plots)
    _assert_partition(footprint, subplots)


def test_fixed_length_plots_keep_length_on_wider_line():
    line = LineString([(0, 0), (200, 0)])
    footprint = line.buffer(4.0, cap_style="flat")

    plots, subplots = _split_length(line, footprint)

    assert len(plots) == 8
    assert len(subplots) == 40
    assert all(geom.area == pytest.approx(200) for *_, geom in plots)
    assert all(geom.area == pytest.approx(40) for *_, geom in subplots)
    assert all(length == pytest.approx(10) for *_, length, _ in subplots)
    _assert_partition(footprint, subplots)


def test_subplots_restart_at_each_plot_boundary():
    stations = subplot_stations(100, 50, 20)

    assert stations == [(0, 0), (20, 0), (40, 0), (50, 1), (70, 1), (90, 1)]


def test_short_pieces_join_previous_subplot():
    # 4 m pieces after 45 m and 95 m are shorter than half a subplot
    stations = subplot_stations(99, 49, 15)

    assert stations == [(0, 0), (15, 0), (30, 0), (49, 1), (64, 1), (79, 1)]


def test_sides_follow_line_direction_with_uneven_footprint():
    line = LineString([(0, 0), (200, 0)])
    lobe = LineString([(60, 0), (60, 8)]).buffer(1.5, cap_style="flat")
    footprint = line.buffer(WIDTH / 2, cap_style="flat").union(lobe)

    plots, subplots = _split_area(line, footprint)

    assert all(geom.centroid.y > 0 for _, side, _, geom in plots if side == SIDE_LEFT)
    assert all(geom.centroid.y < 0 for _, side, _, geom in plots if side == SIDE_RIGHT)
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

    _, subplots = _split_area(line, footprint)
    _assert_partition(footprint, subplots)
    for side in (SIDE_LEFT, SIDE_RIGHT):
        side_length = sum(length for _, s, _, length, _ in subplots if s == side)
        assert side_length == pytest.approx(line.length)
    mean_area = sum(geom.area for *_, geom in subplots) / len(subplots)
    assert mean_area == pytest.approx(10, rel=0.05)

    _, subplots = _split_length(line, footprint)
    _assert_partition(footprint, subplots)


def test_short_tail_joins_last_subplot():
    line = LineString([(0, 0), (203, 0)])
    footprint = line.buffer(WIDTH / 2, cap_style="flat")

    _, subplots = _split_area(line, footprint)

    assert min(geom.area for *_, geom in subplots) >= 5
    _assert_partition(footprint, subplots)


def test_centerline_longer_than_footprint_is_trimmed():
    line = LineString([(-500, 0), (700, 0)])
    footprint = LineString([(0, 0), (100, 0)]).buffer(WIDTH / 2, cap_style="flat")

    plots, subplots = _split_area(line, footprint)

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


@pytest.mark.parametrize(
    ("coords", "angle", "cardinal"),
    [
        ([(0, 0), (100, 0)], 0, True),
        ([(100, 0), (0, 0)], 0, True),
        ([(0, 0), (0, 100)], 90, True),
        ([(0, 0), (100, 10)], 5.71, True),
        ([(0, 0), (100, 100)], 45, False),
        ([(0, 0), (100, -60)], 149.04, False),
    ],
)
def test_line_orientation(coords, angle, cardinal):
    line = LineString(coords)
    assert line_orientation(line) == pytest.approx(angle, abs=0.01)
    assert is_cardinal(line) is cardinal


def _claims(lines):
    footprints = gpd.GeoDataFrame(geometry=[line.buffer(WIDTH / 2, cap_style="flat") for line in lines])
    end_claims, cut_claims = overlap_claims(
        footprints, gpd.GeoDataFrame(geometry=lines), {i: i for i in range(len(lines))}
    )
    return footprints, end_claims, cut_claims


def _overlap_area(footprints):
    return footprints.geometry[0].intersection(footprints.geometry[1]).area


def test_cardinal_line_keeps_overlap_over_longer_diagonal():
    short_east_west = LineString([(0, 0), (100, 0)])
    long_diagonal = LineString([(-50, -150), (150, 150)])
    footprints, end_claims, cut_claims = _claims([long_diagonal, short_east_west])

    assert not end_claims
    assert set(cut_claims) == {0}
    assert cut_claims[0].area == pytest.approx(_overlap_area(footprints))


@pytest.mark.parametrize(
    "lines",
    [
        # both cardinal
        [LineString([(100, -40), (100, 40)]), LineString([(0, 0), (200, 0)])],
        # both diagonal
        [LineString([(80, -20), (120, 20)]), LineString([(0, 100), (200, -100)])],
    ],
)
def test_longer_centerline_keeps_overlap_in_same_direction_class(lines):
    footprints, end_claims, cut_claims = _claims(lines)

    assert not end_claims
    assert set(cut_claims) == {0}
    assert cut_claims[0].area == pytest.approx(_overlap_area(footprints))


def test_line_ending_in_overlap_always_loses():
    # a short north-south line ends on a long diagonal line, which would lose a crossing
    ending_north_south = LineString([(100, 0), (100, 100)])
    through_diagonal = LineString([(0, 0), (200, 200)])
    footprints, end_claims, cut_claims = _claims([ending_north_south, through_diagonal])

    assert set(end_claims) == {0}
    assert not cut_claims
    assert end_claims[0].area == pytest.approx(_overlap_area(footprints))


def test_line_end_just_short_of_other_line_counts_as_ending():
    ending_north_south = LineString([(100, 0), (100, 95)])
    through_diagonal = LineString([(0, 0), (200, 200)])
    _, end_claims, _ = _claims([ending_north_south, through_diagonal])

    assert set(end_claims) == {0}


def test_rule_decides_at_corner_and_loser_is_trimmed():
    # both lines end at the corner, so the east-west line keeps it
    diagonal = LineString([(0, 0), (100, 100)])
    east_west = LineString([(100, 100), (300, 100)])
    _, end_claims, cut_claims = _claims([diagonal, east_west])

    assert set(end_claims) == {0}
    assert not cut_claims


def test_footprint_inside_another_loses_overlap():
    footprints, end_claims, _ = _claims([LineString([(10, 0), (20, 0)]), LineString([(0, 0), (200, 0)])])

    assert end_claims[0].equals(footprints.geometry[0])


def test_trim_line_ends_cuts_footprint_and_centerline():
    centerline = LineString([(100, 0), (100, 105)])
    footprint = centerline.buffer(WIDTH / 2, cap_style="flat")
    # an east-west line footprint across the end, the centerline pokes 2.5 m past it
    claimed = LineString([(0, 100), (200, 100)]).buffer(WIDTH / 2, cap_style="flat").intersection(footprint)

    trimmed_fp, trimmed_line, leftovers = trim_line_ends(footprint, centerline, claimed)

    assert trimmed_line.length == pytest.approx(97.5)
    assert trimmed_line.coords[0] == (100, 0)
    assert trimmed_fp.area == pytest.approx(97.5 * WIDTH)
    assert trimmed_fp.intersection(claimed).area == pytest.approx(0, abs=1e-6)
    # the 2.5 m poking out beyond the other line is cut off, not kept
    assert [piece.area for piece in leftovers] == pytest.approx([2.5 * WIDTH])


def test_trim_line_ends_keeps_fragments_away_from_overlap():
    centerline = LineString([(100, 0), (100, 100)])
    fragment = Point(110, 50).buffer(1)
    footprint = centerline.buffer(WIDTH / 2, cap_style="flat").union(fragment)
    claimed = LineString([(0, 100), (200, 100)]).buffer(WIDTH / 2, cap_style="flat").intersection(footprint)

    trimmed_fp, _, leftovers = trim_line_ends(footprint, centerline, claimed)

    assert trimmed_fp.contains(fragment.buffer(-0.01))
    assert not leftovers


def test_crossing_cut_keeps_pieces_in_their_subplot():
    # an east-west line with 10 m subplots, crossed by a 3 m wide north-south footprint
    line = LineString([(0, 0), (100, 0)])
    footprint = line.buffer(WIDTH / 2, cap_style="flat")
    _, subplots = _split_length(line, footprint, plot_length=50, subplot_length=10)
    # the crossing leaves a 0.1 m strip of the 20-30 m subplot before it
    claimed = LineString([(21.6, -10), (21.6, 10)]).buffer(1.5, cap_style="flat").intersection(footprint)

    result = remove_overlap(subplots, claimed)

    by_key = {(plot_idx, side, subplot_idx): geom for plot_idx, side, subplot_idx, _, geom in result}
    for side in (SIDE_LEFT, SIDE_RIGHT):
        # the 20-30 m subplot keeps both pieces and stays between its cross cuts
        pieces = shapely.get_parts(by_key[(0, side, 2)])
        assert sorted(piece.area for piece in pieces) == pytest.approx([0.1 * WIDTH / 2, 6.9 * WIDTH / 2])
        assert by_key[(0, side, 2)].bounds[0] == pytest.approx(20)
        assert by_key[(0, side, 2)].bounds[2] == pytest.approx(30)
        assert by_key[(0, side, 1)].area == pytest.approx(10 * WIDTH / 2)
    total = sum(geom.area for geom in by_key.values())
    assert total == pytest.approx(footprint.area - claimed.area)


def test_clean_polygon_removes_zero_width_spike():
    # a square with a 5 m spike that runs out and straight back
    spiky = Polygon([(0, 0), (2, 0), (2, 1), (7, 1), (2, 1.0000000001), (2, 2), (0, 2)])

    cleaned = clean_polygon(spiky)

    assert cleaned.area == pytest.approx(4)
    assert cleaned.length == pytest.approx(8, abs=1e-5)


def _spikes(geoms):
    """Count polygon parts whose outline has zero-width spikes (outline lost by a tiny opening)."""
    count = 0
    for geom in geoms:
        for part in shapely.get_parts(geom):
            opened = part.buffer(-0.01, join_style="mitre").buffer(0.01, join_style="mitre")
            if part.length - opened.length > 0.2 and part.area - opened.area < 0.01:
                count += 1
    return count


@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
@pytest.mark.parametrize("angle", [20, 35, 60])
def test_remove_overlap_leaves_no_spikes_at_shallow_angles(tmp_path, mode, angle):
    # a through line, a line crossing it and a line ending on it, both at a shallow angle
    dx, dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    through = LineString([(0, 0), (300, 0)])
    crossing = LineString([(60 - 40 * dx, -40 * dy), (60 + 40 * dx, 40 * dy)])
    ending = LineString([(200 - 60 * dx, -60 * dy), (200, 0)])
    lines = [through, crossing, ending]
    line_gdf = gpd.GeoDataFrame({"line_id": [1, 2, 3]}, geometry=lines, crs="EPSG:2956")
    footprints = [line.buffer(WIDTH / 2, cap_style="flat") for line in lines]
    fp_gdf = gpd.GeoDataFrame(geometry=footprints, crs="EPSG:2956")
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")

    plots, subplots = _run(tmp_path, in_file, mode=mode, remove_overlap=True)

    assert _spikes(subplots.geometry) == 0
    assert _spikes(plots.geometry) == 0
    assert subplots.area.sum() == pytest.approx(fp_gdf.union_all().area, abs=1e-2)
    # the trimmed end keeps a subplot on both sides
    ending_plots = subplots.loc[subplots["line_id"] == 3].groupby("plot_id")["side"].nunique()
    assert (ending_plots == 2).all()


def test_polygon_parts_drops_line_like_leftovers():
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    sliver = Polygon([(2, 0), (5, 0), (5, 1e-9), (2, 1e-9)])
    mixed = GeometryCollection([square, sliver, LineString([(0, 5), (3, 5)])])

    parts = polygon_parts(mixed)
    assert len(parts) == 1
    assert parts[0].equals(square)


def _write_crossing_inputs(tmp_path):
    lines = [LineString([(0, 0), (200, 0)]), LineString([(100, -50), (100, 50)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [1, 2]}, geometry=lines, crs="EPSG:2956")
    footprints = [line.buffer(WIDTH / 2, cap_style="flat") for line in lines]
    fp_gdf = gpd.GeoDataFrame(geometry=footprints, crs="EPSG:2956")
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")
    return in_file, fp_gdf


@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
def test_remove_overlap_counts_crossing_once(tmp_path, mode):
    in_file, fp_gdf = _write_crossing_inputs(tmp_path)
    union_area = fp_gdf.union_all().area

    plots, subplots = _run(tmp_path, in_file, mode=mode, remove_overlap=True)

    assert subplots.area.sum() == pytest.approx(union_area, abs=1e-2)
    assert plots.area.sum() == pytest.approx(union_area, abs=1e-2)
    assert subplots.union_all().area == pytest.approx(union_area, abs=1e-2)
    # both lines are cardinal, so the longer one keeps the crossing
    assert subplots.loc[subplots["line_id"] == 1].area.sum() == pytest.approx(fp_gdf.area[0], abs=1e-2)
    by_plot = subplots.groupby(["plot_id", "side"])
    assert by_plot["plot_area"].first().values == pytest.approx(by_plot["area"].sum().values, abs=0.1)


# GEOS raises a floating-point flag on the edge-on check along the diagonal cut; geometries are valid
@pytest.mark.filterwarnings("ignore:invalid value encountered:RuntimeWarning")
@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
def test_remove_overlap_trims_line_ending_on_other_line(tmp_path, mode):
    # T-junction: a north-south line ends on a diagonal line
    lines = [LineString([(0, 0), (200, 200)]), LineString([(100, 0), (100, 100)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [1, 2]}, geometry=lines, crs="EPSG:2956")
    footprints = [line.buffer(WIDTH / 2, cap_style="flat") for line in lines]
    fp_gdf = gpd.GeoDataFrame(geometry=footprints, crs="EPSG:2956")
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")

    _, subplots = _run(tmp_path, in_file, mode=mode, remove_overlap=True)

    through = subplots.loc[subplots["line_id"] == 1]
    ending = subplots.loc[subplots["line_id"] == 2]
    # the through line keeps its whole footprint, the ending line stops at it
    assert through.area.sum() == pytest.approx(fp_gdf.area[0], abs=1e-2)
    assert ending.union_all().intersection(fp_gdf.geometry[0]).area == pytest.approx(0, abs=1e-3)
    for side in (0, 1):
        assert ending.loc[ending["side"] == side, "length"].sum() < 100 - WIDTH / 2
    assert subplots.union_all().area == pytest.approx(subplots.area.sum(), abs=1e-2)


@pytest.mark.filterwarnings("ignore:invalid value encountered:RuntimeWarning")
@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
def test_remove_overlap_drops_piece_where_line_end_pokes_through(tmp_path, mode):
    # the north-south line runs 1 m past the far side of the east-west footprint
    lines = [LineString([(0, 100), (200, 100)]), LineString([(100, 0), (100, 103.5)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [1, 2]}, geometry=lines, crs="EPSG:2956")
    footprints = [line.buffer(WIDTH / 2, cap_style="flat") for line in lines]
    fp_gdf = gpd.GeoDataFrame(geometry=footprints, crs="EPSG:2956")
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")

    _, subplots = _run(tmp_path, in_file, mode=mode, remove_overlap=True)

    # the 1 m poke-through piece is dropped, it doesn't join the east-west line
    union_area = fp_gdf.union_all().area
    assert subplots.area.sum() == pytest.approx(union_area - 1.0 * WIDTH, abs=1e-2)
    assert subplots.union_all().area == pytest.approx(subplots.area.sum(), abs=1e-2)
    through = subplots.loc[subplots["line_id"] == 1]
    assert through.area.sum() == pytest.approx(fp_gdf.area[0], abs=1e-2)
    assert through.union_all().difference(fp_gdf.geometry[0]).area == pytest.approx(0, abs=1e-3)
    parts = [part for geom in subplots.geometry for part in shapely.get_parts(geom)]
    assert min(part.area for part in parts) > 1e-3


@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
def test_remove_overlap_keeps_subplots_in_their_slot_at_crossings(tmp_path, mode):
    # a diagonal line loses a crossing with a long east-west line, so its subplots are cut at an angle
    lines = [LineString([(0, 0), (200, 0)]), LineString([(60, -30), (120, 30)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [1, 2]}, geometry=lines, crs="EPSG:2956")
    footprints = [line.buffer(WIDTH / 2, cap_style="flat") for line in lines]
    fp_gdf = gpd.GeoDataFrame(geometry=footprints, crs="EPSG:2956")
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")

    _, subplots = _run(tmp_path, in_file, mode=mode, remove_overlap=True)

    crossed = subplots.loc[subplots["line_id"] == 2]
    for geom, length in zip(crossed.geometry, crossed["length"]):
        along = [lines[1].project(Point(xy)) for xy in shapely.get_coordinates(geom)]
        assert max(along) - min(along) <= length + 0.05
    # both sides of each slot still end on the same cross cuts
    assert crossed.groupby("plot_id")["side"].nunique().min() == 2
    assert subplots.area.sum() == pytest.approx(fp_gdf.union_all().area, abs=1e-2)


def test_overlap_is_kept_by_default(tmp_path):
    in_file, fp_gdf = _write_crossing_inputs(tmp_path)

    _, subplots = _run(tmp_path, in_file)

    assert subplots.area.sum() == pytest.approx(fp_gdf.area.sum(), abs=1e-2)


def _write_inputs(tmp_path, fp_columns=None):
    lines = [LineString([(0, 0), (200, 0)]), LineString([(0, 100), (100, 100), (160, 160)])]
    line_gdf = gpd.GeoDataFrame({"line_id": [7, 8]}, geometry=lines, crs="EPSG:2956")
    fp_gdf = gpd.GeoDataFrame(
        fp_columns,
        geometry=[line.buffer(WIDTH / 2, cap_style="flat", join_style="mitre") for line in lines],
        crs="EPSG:2956",
    )
    in_file = tmp_path / "input.gpkg"
    line_gdf.to_file(in_file, layer="centerline")
    fp_gdf.to_file(in_file, layer="footprint")
    return in_file, fp_gdf


def _run(tmp_path, in_file, **kwargs):
    out_file = tmp_path / "output.gpkg"
    footprint_plots(
        in_footprint=f"{in_file.as_posix()}|footprint",
        in_line=f"{in_file.as_posix()}|centerline",
        out_plot=f"{out_file.as_posix()}|plots",
        out_subplot=f"{out_file.as_posix()}|subplots",
        processes=1,
        **kwargs,
    )
    return gpd.read_file(out_file, layer="plots"), gpd.read_file(out_file, layer="subplots")


@pytest.mark.parametrize("mode", ["fixed_area", "fixed_length"])
def test_footprint_plots_tool_writes_segline_columns(tmp_path, mode):
    in_file, fp_gdf = _write_inputs(tmp_path)

    plots, subplots = _run(tmp_path, in_file, mode=mode)

    assert set(SEGLINE_COLUMNS) <= set(subplots.columns)
    assert set(plots["line_id"]) == {7, 8}
    assert subplots["UniqueID"].nunique() == 2
    assert set(subplots["side"]) == {0, 1}
    assert subplots["subplot_id"].is_unique
    assert not plots.duplicated(["plot_id", "side"]).any()
    assert subplots.groupby("plot_id")["UniqueID"].nunique().max() == 1
    assert (subplots["subplot_area"] == subplots["area"]).all()
    by_plot = subplots.groupby(["plot_id", "side"])
    assert by_plot["plot_area"].first().values == pytest.approx(by_plot["area"].sum().values, abs=0.1)
    assert subplots["perimeter"].values == pytest.approx(subplots.geometry.length.values, abs=0.05)
    for side in (0, 1):
        side_length = subplots.loc[subplots["side"] == side].groupby("line_id")["length"].sum()
        assert side_length.values == pytest.approx([200, 100 + 60 * 2**0.5], abs=0.5)
        plot_length = plots.loc[plots["side"] == side].groupby("line_id")["length"].sum()
        assert plot_length.values == pytest.approx(side_length.values, abs=0.5)
    assert subplots.area.sum() == pytest.approx(fp_gdf.area.sum(), abs=1e-2)


def test_footprint_plots_keeps_input_unique_ids(tmp_path):
    in_file, _ = _write_inputs(tmp_path, {"UniqueID": ["abc", "xyz"]})

    plots, subplots = _run(tmp_path, in_file, mode="fixed_length")

    assert set(subplots["UniqueID"]) == {"abc", "xyz"}
    assert set(subplots.loc[subplots["line_id"] == 7, "UniqueID"]) == {"abc"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"plot_area": 10, "subplot_area": 10},
        {"mode": "fixed_length", "plot_length": 5, "subplot_length": 10},
        {"mode": "fixed_volume"},
    ],
)
def test_footprint_plots_rejects_bad_options(kwargs):
    with pytest.raises(ValueError):
        footprint_plots("a.gpkg|fp", "a.gpkg|cl", "o.gpkg|p", "o.gpkg|s", **kwargs)
