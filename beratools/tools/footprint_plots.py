"""
Copyright (C) 2025 Applied Geospatial Research Group.

This script is licensed under the GNU General Public License v3.0.
See <https://gnu.org/licenses/gpl-3.0> for full license details.

Author: Irina Terentieva (original SegLine code)

Description:
    This script is part of the BERA Tools.
    Webpage: https://github.com/BERATool/beratools

    The purpose of this script is to split line footprints into plots and
    subplots along their centerlines, with plot, side and subplot IDs.

    Ported from SegLine by Irina Terentieva
    (https://github.com/IrinaTerentieva/SegLine, fixed area and fixed length
    modes). Output columns follow the SegLine subplot layer: UniqueID, side,
    plot_id, subplot_id, area, length, perimeter, plot_area and subplot_area.
"""

import logging
import secrets
import string

import geopandas as gpd
import numpy as np
import shapely

import beratools.core.algo_footprint_plots as algo_fp
import beratools.utility.spatial_common as sp_common
from beratools.core.tool_base import execute_multiprocessing
from beratools.utility.tool_args import CallMode

LOGGER_NAME = "footprint_plots"
logger = logging.getLogger(LOGGER_NAME)

UNIQUE_ID = "UniqueID"
UNIQUE_ID_LENGTH = 6
# Smallest distance (m) a centerline end may be from an overlap to count as ending in it
MIN_END_TOLERANCE = 0.5


def footprint_plots(
    in_footprint,
    in_line,
    out_plot,
    out_subplot,
    mode=algo_fp.MODE_AREA,
    plot_area=100.0,
    subplot_area=10.0,
    plot_length=50.0,
    subplot_length=10.0,
    remove_overlap=False,
    processes=0,
    call_mode=CallMode.CLI,
    log_level="INFO",
):
    """
    Define tool entry point.

    Args:
        in_footprint: input footprint polygons (encoded as "file|layer")
        in_line: input centerlines (encoded as "file|layer")
        out_plot: output plots, one feature per plot side (encoded as "file|layer")
        out_subplot: output subplots (encoded as "file|layer")
        mode: "fixed_area" or "fixed_length"
        plot_area: fixed area, target plot area covering both sides of the line (m2)
        subplot_area: fixed area, target subplot area on one side of the line (m2)
        plot_length: fixed length, plot length along the centerline (m)
        subplot_length: fixed length, subplot length along the centerline (m)
        remove_overlap: cut overlaps between footprints so each area is counted once;
            a line ending in an overlap always loses it and is trimmed back, otherwise
            north-south and east-west lines keep it, then the longer centerline
        processes: number of processes to use
        call_mode: CLI or GUI
        log_level: logging level

    """
    if mode == algo_fp.MODE_AREA:
        size = (float(plot_area), float(subplot_area))
        if size[1] <= 0 or size[0] < 2 * size[1]:
            raise ValueError("subplot_area must be > 0 and plot_area must be at least 2 x subplot_area.")
    elif mode == algo_fp.MODE_LENGTH:
        size = (float(plot_length), float(subplot_length))
        if size[1] <= 0 or size[0] < size[1]:
            raise ValueError("subplot_length must be > 0 and plot_length must be at least subplot_length.")
    else:
        raise ValueError(f"mode must be '{algo_fp.MODE_AREA}' or '{algo_fp.MODE_LENGTH}', got '{mode}'.")

    fp_file, fp_layer = sp_common.decode_file_layer(in_footprint)
    line_file, line_layer = sp_common.decode_file_layer(in_line)
    footprints = gpd.read_file(fp_file, layer=fp_layer)
    lines = gpd.read_file(line_file, layer=line_layer)
    if footprints.crs != lines.crs:
        raise ValueError("Footprint and centerline must use the same coordinate reference system.")
    footprints = _rename_fid(footprints).reset_index(drop=True)
    lines = _rename_fid(lines).reset_index(drop=True)
    footprints[UNIQUE_ID] = assign_unique_ids(footprints)

    matches = match_lines_to_footprints(footprints, lines)
    print(f"Matched {len(matches)} of {len(footprints)} footprints to centerlines.", flush=True)

    end_claims, cut_claims = {}, {}
    if _to_bool(remove_overlap):
        end_claims, cut_claims = overlap_claims(footprints, lines, matches)
    if end_claims or cut_claims:
        print(
            f"Removing overlaps: {len(end_claims)} footprints trimmed at line ends, "
            f"{len(cut_claims)} cut at crossings.",
            flush=True,
        )

    fp_geoms, line_geoms = footprints.geometry, lines.geometry
    inputs = {
        fp_idx: (fp_geoms.iloc[fp_idx], line_geoms.iloc[line_idx])
        for fp_idx, line_idx in matches.items()
    }
    if end_claims:
        inputs = trim_ending_lines(inputs, end_claims)

    line_columns = [col for col in lines.columns if col != "geometry" and col not in footprints.columns]
    tasks = []
    for fp_idx, line_idx in matches.items():
        footprint, line = inputs[fp_idx]
        if footprint is None:
            uid = footprints.at[fp_idx, UNIQUE_ID]
            logger.info(f"Footprint {uid}: lies inside overlaps it gives up, skipped.")
            continue
        attrs = footprints.iloc[fp_idx].drop("geometry").to_dict()
        attrs.update(lines.iloc[line_idx][line_columns].to_dict())
        attrs["_fp"] = int(fp_idx)
        tasks.append((attrs, footprint, line, mode, size, cut_claims.get(fp_idx)))

    results = execute_multiprocessing(
        footprint_plots_worker, tasks, "footprint_plots", processes, call_mode, logger_name=LOGGER_NAME
    )
    if not results:
        raise RuntimeError("Footprint plots produced no output.")

    plot_records = [rec for plots, _ in results for rec in plots]
    subplot_records = [rec for _, subplots in results for rec in subplots]
    plot_gdf, subplot_gdf = _to_segline_layers(plot_records, subplot_records, footprints.crs)

    out_file, out_layer = sp_common.decode_file_layer(out_plot)
    plot_gdf.to_file(out_file, layer=out_layer)
    out_file, out_layer = sp_common.decode_file_layer(out_subplot)
    subplot_gdf.to_file(out_file, layer=out_layer)
    print(
        f"Created {len(plot_gdf)} plot sides and {len(subplot_gdf)} subplots ({mode}, "
        f"mean subplot area {subplot_gdf['area'].mean():.1f} m2).",
        flush=True,
    )


def assign_unique_ids(footprints):
    """Keep an existing unique UniqueID column, otherwise generate random IDs like SegLine."""
    if UNIQUE_ID in footprints.columns:
        ids = footprints[UNIQUE_ID]
        if ids.notna().all() and ids.is_unique:
            return ids.astype(str)
        logger.warning(f"{UNIQUE_ID} column is missing values or not unique, new IDs are generated.")

    alphabet = string.ascii_letters + string.digits
    ids = set()
    while len(ids) < len(footprints):
        ids.add("".join(secrets.choice(alphabet) for _ in range(UNIQUE_ID_LENGTH)))
    return list(ids)


def match_lines_to_footprints(footprints, lines):
    """Return {footprint index: line index} using the line with the longest overlap."""
    fp_idx, line_idx = lines.sindex.query(footprints.geometry, predicate="intersects")
    if len(fp_idx) == 0:
        return {}

    overlap = shapely.length(
        shapely.intersection(footprints.geometry.values[fp_idx], lines.geometry.values[line_idx])
    )
    best = {}
    for order in np.argsort(-overlap, kind="stable"):
        if overlap[order] > 0:
            best.setdefault(int(fp_idx[order]), int(line_idx[order]))
    return dict(sorted(best.items()))


def overlap_claims(footprints, lines, matches):
    """
    Return (end_claims, cut_claims), each {footprint index: overlap area it gives up}.

    Each overlap between two footprints is decided on its own:

    - a line that ends in the overlap gives it up to a line that passes through;
    - otherwise a north-south or east-west line keeps it over a line in another
      direction, then the longer centerline (inside its footprint), then the
      lower index.

    A loser that ends in the overlap is trimmed back before splitting
    (end_claims); a loser that passes through has the overlap cut out of its
    plots and subplots after splitting (cut_claims).
    """
    idx = sorted(matches)
    if not idx:
        return {}, {}
    geoms = shapely.force_2d(footprints.geometry.values[idx])
    line_geoms = lines.geometry
    info = [_overlap_line_info(geoms[k], line_geoms.iloc[matches[i]], i) for k, i in enumerate(idx)]
    left, right = shapely.STRtree(geoms).query(geoms, predicate="intersects")

    end_claims, cut_claims = {}, {}
    for i, j in zip(left, right):
        if i >= j:
            continue
        for part in shapely.get_parts(shapely.intersection(geoms[i], geoms[j])):
            if part.geom_type != "Polygon" or part.area <= algo_fp.MIN_PIECE_AREA:
                continue
            i_ends, j_ends = _ends_in(info[i], part), _ends_in(info[j], part)
            if i_ends != j_ends:
                loser, loser_ends = (i if i_ends else j), True
            else:
                loser, loser_ends = (j if info[i][2] < info[j][2] else i), i_ends
            claims = end_claims if loser_ends else cut_claims
            claims.setdefault(int(idx[loser]), []).append(part)
    return _union_claims(end_claims), _union_claims(cut_claims)


def trim_ending_lines(inputs, end_claims):
    """
    Trim footprints and centerlines that end in overlaps they give up.

    Args:
        inputs: {footprint index: (footprint, line)}
        end_claims: {footprint index: overlap area it gives up at its line ends}

    Returns:
        inputs with trimmed footprints and centerlines; footprint is None when
        nothing is left. Pieces cut off beyond the far side of the other
        footprint are dropped, so every plot holds only its own footprint.

    """
    trimmed = dict(inputs)
    for fp_idx, claim in end_claims.items():
        footprint, line = inputs[fp_idx]
        centerline = algo_fp.prepare_centerline(line, footprint)
        if centerline is None:
            continue
        footprint, centerline, leftovers = algo_fp.trim_line_ends(footprint, centerline, claim)
        trimmed[fp_idx] = (footprint, centerline)
        if leftovers:
            area = sum(piece.area for piece in leftovers)
            logger.info(f"Footprint {fp_idx}: dropped {area:.2f} m2 beyond the overlap it gives up.")
    return trimmed


def _union_claims(claims):
    return {fp_idx: shapely.union_all(parts) for fp_idx, parts in claims.items()}


def _overlap_line_info(footprint, line, fp_idx):
    """Return (centerline end points, end tolerance, priority key) of one footprint for overlap_claims."""
    centerline = algo_fp.prepare_centerline(line, footprint)
    if centerline is None:
        return [], 0.0, (True, 0.0, int(fp_idx))

    ends = [shapely.Point(centerline.coords[0]), shapely.Point(centerline.coords[-1])]
    # a footprint reaches about half its width past the centerline end
    tolerance = max(algo_fp.estimate_width(footprint, centerline) / 2, MIN_END_TOLERANCE)
    priority = (not algo_fp.is_cardinal(centerline), -centerline.length, int(fp_idx))
    return ends, tolerance, priority


def _ends_in(line_info, part):
    ends, tolerance, _ = line_info
    return any(part.distance(end) <= tolerance for end in ends)


def _to_bool(value):
    return value.lower() in ("true", "1", "yes", "on") if isinstance(value, str) else bool(value)


# task executed in a worker process
def footprint_plots_worker(in_args):
    attrs, footprint, line, mode, size, cut_claim = in_args
    centerline = algo_fp.prepare_centerline(line, footprint)
    if centerline is None:
        logger.warning(f"Footprint {attrs[UNIQUE_ID]}: no usable centerline inside footprint, skipped.")
        return [], []

    width = algo_fp.estimate_width(footprint, centerline)
    if width <= 0:
        return [], []
    lengths = algo_fp.area_mode_lengths(width, *size) if mode == algo_fp.MODE_AREA else size

    plots, subplots = algo_fp.split_footprint(footprint, centerline, *lengths)
    if cut_claim is not None:
        subplots = algo_fp.remove_overlap(subplots, cut_claim)
        plots = algo_fp.plots_from_subplots(plots, subplots)
    plots = _clean_pieces(plots)
    subplots = _clean_pieces(subplots)
    plot_records = [
        {**attrs, "side": side, "plot_id": plot_idx, "length": length, "est_width": width, "geometry": geom}
        for plot_idx, side, length, geom in plots
    ]
    subplot_records = [
        {
            **attrs,
            "side": side,
            "plot_id": plot_idx,
            "subplot_id": subplot_idx,
            "length": length,
            "est_width": width,
            "geometry": geom,
        }
        for plot_idx, side, subplot_idx, length, geom in subplots
    ]
    return plot_records, subplot_records


def _clean_pieces(pieces):
    """Remove zero-width spikes from plot or subplot geometries (the last tuple item)."""
    cleaned = []
    for *keys, geom in pieces:
        geom = algo_fp.clean_polygon(geom)
        if geom is not None:
            cleaned.append((*keys, geom))
    return cleaned


def _rename_fid(gdf):
    return gdf.rename(columns={"fid": "orig_fid"}) if "fid" in gdf.columns else gdf


def _to_segline_layers(plot_records, subplot_records, crs):
    """
    Number plots and subplots and add the SegLine measure columns.

    As in SegLine, plot_id and subplot_id are unique across the whole output and
    increase along each line. length is measured along the centerline, perimeter
    is the polygon perimeter, plot_area is the area of the plot side and
    subplot_area the subplot's own area.
    """
    plots = gpd.GeoDataFrame(plot_records, geometry="geometry", crs=crs)
    subplots = gpd.GeoDataFrame(subplot_records, geometry="geometry", crs=crs)
    if subplots.empty:
        return plots, subplots

    plot_keys = ["_fp", "plot_id"]
    subplots = subplots.sort_values([*plot_keys, "side", "subplot_id"]).reset_index(drop=True)
    plot_ids = {key: i for i, key in enumerate(subplots[plot_keys].drop_duplicates().itertuples(index=False))}
    subplots["plot_id"] = [plot_ids[key] for key in subplots[plot_keys].itertuples(index=False)]
    subplots["subplot_id"] = subplots.index
    plots["plot_id"] = [plot_ids[key] for key in plots[plot_keys].itertuples(index=False)]
    plots = plots.sort_values(["plot_id", "side"]).reset_index(drop=True)

    for gdf in (plots, subplots):
        gdf["area"] = gdf.geometry.area.round(1)
        gdf["length"] = gdf["length"].round(1)
        gdf["perimeter"] = gdf.geometry.length.round(1)
        gdf["est_width"] = gdf["est_width"].round(2)
    plots["plot_area"] = plots["area"]
    subplots["plot_area"] = subplots.groupby([UNIQUE_ID, "plot_id", "side"])["area"].transform("sum").round(1)
    subplots["subplot_area"] = subplots["area"]

    return plots.drop(columns="_fp"), subplots.drop(columns="_fp")


if __name__ == "__main__":
    import time

    from beratools.utility.tool_args import compose_tool_kwargs

    start_time = time.time()
    kwargs = compose_tool_kwargs("footprint_plots")
    footprint_plots(**kwargs)
    print("Elapsed time: {}".format(time.time() - start_time))
