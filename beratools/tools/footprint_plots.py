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
    (https://github.com/IrinaTerentieva/SegLine, src/utils/split_to_plots.py,
    split_to_sides.py and split_to_subplots.py).
"""

import logging

import geopandas as gpd
import numpy as np
import shapely

import beratools.core.algo_footprint_plots as algo_fp
import beratools.utility.spatial_common as sp_common
from beratools.core.tool_base import execute_multiprocessing
from beratools.utility.tool_args import CallMode

LOGGER_NAME = "footprint_plots"
logger = logging.getLogger(LOGGER_NAME)


def footprint_plots(
    in_footprint,
    in_line,
    out_plot,
    out_subplot,
    plot_area=100.0,
    subplot_area=10.0,
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
        plot_area: target plot area covering both sides of the line (m2)
        subplot_area: target subplot area on one side of the line (m2)
        processes: number of processes to use
        call_mode: CLI or GUI
        log_level: logging level

    """
    plot_area = float(plot_area)
    subplot_area = float(subplot_area)
    if subplot_area <= 0 or plot_area < 2 * subplot_area:
        raise ValueError("subplot_area must be > 0 and plot_area must be at least 2 x subplot_area.")

    fp_file, fp_layer = sp_common.decode_file_layer(in_footprint)
    line_file, line_layer = sp_common.decode_file_layer(in_line)
    footprints = gpd.read_file(fp_file, layer=fp_layer)
    lines = gpd.read_file(line_file, layer=line_layer)
    if footprints.crs != lines.crs:
        raise ValueError("Footprint and centerline must use the same coordinate reference system.")
    footprints = _rename_fid(footprints).reset_index(drop=True)
    lines = _rename_fid(lines).reset_index(drop=True)

    matches = match_lines_to_footprints(footprints, lines)
    print(f"Matched {len(matches)} of {len(footprints)} footprints to centerlines.", flush=True)

    line_columns = [col for col in lines.columns if col != "geometry" and col not in footprints.columns]
    tasks = []
    for fp_idx, line_idx in matches.items():
        attrs = footprints.iloc[fp_idx].drop("geometry").to_dict()
        attrs.update(lines.iloc[line_idx][line_columns].to_dict())
        attrs["FP_ID"] = int(fp_idx)
        tasks.append(
            (attrs, footprints.geometry.iloc[fp_idx], lines.geometry.iloc[line_idx], plot_area, subplot_area)
        )

    results = execute_multiprocessing(
        footprint_plots_worker, tasks, "footprint_plots", processes, call_mode, logger_name=LOGGER_NAME
    )
    if not results:
        raise RuntimeError("Footprint plots produced no output.")

    plot_records = [rec for plots, _ in results for rec in plots]
    subplot_records = [rec for _, subplots in results for rec in subplots]
    plot_gdf = _to_gdf(plot_records, footprints.crs, ["FP_ID", "plot_id", "side"])
    subplot_gdf = _to_gdf(subplot_records, footprints.crs, ["FP_ID", "plot_id", "side", "subplot_id"])

    out_file, out_layer = sp_common.decode_file_layer(out_plot)
    plot_gdf.to_file(out_file, layer=out_layer)
    out_file, out_layer = sp_common.decode_file_layer(out_subplot)
    subplot_gdf.to_file(out_file, layer=out_layer)
    print(
        f"Created {len(plot_gdf)} plot sides and {len(subplot_gdf)} subplots "
        f"(mean subplot area {subplot_gdf['area'].mean():.1f} m2).",
        flush=True,
    )


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


# task executed in a worker process
def footprint_plots_worker(in_args):
    attrs, footprint, line, plot_area, subplot_area = in_args
    centerline = algo_fp.prepare_centerline(line, footprint)
    if centerline is None:
        logger.warning(f"Footprint {attrs['FP_ID']}: no usable centerline inside footprint, skipped.")
        return [], []

    plots, subplots, width = algo_fp.split_footprint(footprint, centerline, plot_area, subplot_area)
    plot_records = [
        {**attrs, "plot_id": plot_id, "side": side, "est_width": width, "geometry": geom}
        for plot_id, side, geom in plots
    ]
    subplot_records = [
        {
            **attrs,
            "plot_id": plot_id,
            "side": side,
            "subplot_id": subplot_id,
            "est_width": width,
            "geometry": geom,
        }
        for plot_id, side, subplot_id, geom in subplots
    ]
    return plot_records, subplot_records


def _rename_fid(gdf):
    return gdf.rename(columns={"fid": "orig_fid"}) if "fid" in gdf.columns else gdf


def _to_gdf(records, crs, sort_columns):
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)
    if gdf.empty:
        return gdf
    gdf = gdf.sort_values(sort_columns).reset_index(drop=True)
    gdf["area"] = gdf.geometry.area.round(2)
    gdf["est_width"] = gdf["est_width"].round(2)
    return gdf


if __name__ == "__main__":
    import time

    from beratools.utility.tool_args import compose_tool_kwargs

    start_time = time.time()
    kwargs = compose_tool_kwargs("footprint_plots")
    footprint_plots(**kwargs)
    print("Elapsed time: {}".format(time.time() - start_time))
