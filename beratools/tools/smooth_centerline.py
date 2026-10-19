"""
Copyright (C) 2025 Applied Geospatial Research Group.

This script is licensed under the GNU General Public License v3.0.
See <https://gnu.org/licenses/gpl-3.0> for full license details.

Author: Irina Terentieva (original SegLine code)

Description:
    This script is part of the BERA Tools.
    Webpage: https://github.com/BERATool/beratools

    The purpose of this script is to smooth sharp vertices of centerlines.
    Only vertices with an interior angle below the threshold are changed,
    the rest of each line is kept as is.

    Ported from SegLine by Irina Terentieva
    (https://github.com/IrinaTerentieva/SegLine, src/utils/smooth_centerline.py).
"""

import logging

import geopandas as gpd
import pandas as pd

import beratools.utility.spatial_common as sp_common
from beratools.core.algo_geometry import smooth_sharp_vertices
from beratools.core.tool_base import execute_multiprocessing
from beratools.utility.tool_args import CallMode

LOGGER_NAME = "smooth_centerline"
logger = logging.getLogger(LOGGER_NAME)


def smooth_centerline(
    in_line,
    out_line,
    angle_threshold=130.0,
    buffer_distance=2.0,
    processes=0,
    call_mode=CallMode.CLI,
    log_level="INFO",
):
    """
    Define tool entry point.

    Args:
        in_line: input centerlines (encoded as "file|layer")
        out_line: output smoothed centerlines (encoded as "file|layer")
        angle_threshold: vertices with interior angle (degrees) below this are smoothed
        buffer_distance: radius (m) around a sharp vertex that is replaced by a straight cut
        processes: number of processes to use
        call_mode: CLI or GUI
        log_level: logging level

    """
    in_file, in_layer = sp_common.decode_file_layer(in_line)
    out_file, out_layer = sp_common.decode_file_layer(out_line)

    angle_threshold = float(angle_threshold)
    buffer_distance = float(buffer_distance)
    gdf = gpd.read_file(in_file, layer=in_layer)
    if "fid" in gdf.columns:
        gdf = gdf.rename(columns={"fid": "orig_fid"})
    gdf_list = [(gdf.iloc[[i]], angle_threshold, buffer_distance) for i in range(len(gdf))]

    results = execute_multiprocessing(
        smooth_worker, gdf_list, "smooth_centerline", processes, call_mode, logger_name=LOGGER_NAME
    )
    if not results:
        raise RuntimeError("Smooth centerline produced no output.")

    # Workers finish out of order, restore the input order
    smoothed_gdf = gpd.GeoDataFrame(pd.concat(results).sort_index(), crs=gdf.crs)
    changed = int((~smoothed_gdf.geometry.geom_equals(gdf.geometry)).sum())
    print(f"Smoothed {changed} of {len(smoothed_gdf)} lines.", flush=True)
    smoothed_gdf.to_file(out_file, layer=out_layer)


# task executed in a worker process
def smooth_worker(in_args):
    smoothed = in_args[0].copy()
    angle_threshold = in_args[1]
    buffer_distance = in_args[2]
    smoothed["geometry"] = smoothed.geometry.apply(
        smooth_sharp_vertices, angle_threshold=angle_threshold, buffer_distance=buffer_distance
    )
    return smoothed


if __name__ == "__main__":
    import time

    from beratools.utility.tool_args import compose_tool_kwargs

    start_time = time.time()
    kwargs = compose_tool_kwargs("smooth_centerline")
    smooth_centerline(**kwargs)
    print("Elapsed time: {}".format(time.time() - start_time))
