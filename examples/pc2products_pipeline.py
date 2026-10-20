"""
Turn a folder of LiDAR tiles into DTM, DSM and CHM rasters, skipping steps the data does not need.

    1. Ground classified?  no -> classify ground with CSF
    2. Generate DTM from the ground-classified tiles
    3. Normalized?         no -> generate DSM, normalize the tiles, then generate CHM
                           yes -> generate CHM straight away

Usage:
    python examples/pc2products_pipeline.py IN_LAS_FOLDER OUT_FOLDER [--processes 4] [--style tin]

Outputs (inside OUT_FOLDER):
    Classified_PC/   ground-classified tiles (only when the input was not classified)
    Normalized_PC/   height-normalized tiles (only when the input was not normalized)
    Raster_Output/   Merged_*_DTM.tif, Merged_*_DSM.tif and Merged_*_CHM.tif
"""

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.append(Path(__file__).resolve().parents[1].as_posix())

import beratools.tools.r_common as r_common
from beratools.tools.rpy_CHM_DSM_by import rpy_chm_dsm_by
from beratools.tools.rpy_dtm_by import rpy_dtm
from beratools.tools.rpy_gnd_csf import rpy_gnd_csf
from beratools.tools.rpy_normalized_PC import rpy_normalized_PC

R_SCRIPT = Path(r_common.__file__).with_name("r_scripts_collection.r")
GROUND_CLASS = 2
# Every R package the pipeline's tools need, installed up front so the checks below can run.
R_PACKAGES = ["lidR", "RCSF", "gstat", "rlas", "future", "terra", "sp", "raster", "stars", "sf"]


def print_message(msg):
    print("\n" + "-" * 50)
    print(msg)
    print("-" * 50)


def load_r_functions():
    r_common.check_r_packages_installation(R_PACKAGES)
    r_common.r["source"](R_SCRIPT.as_posix())


def is_ground_classified(in_las_folder):
    """True when every tile has ground points (class 2)."""
    tiles = r_common.robjects.globalenv["detect_class"](in_las_folder, GROUND_CLASS)
    return False not in [list(tile)[0] for tile in tiles]


def is_normalized(in_las_folder):
    """True when the ground points sit near zero height."""
    return bool(r_common.robjects.globalenv["detect_normalized"](in_las_folder)[0])


def run_pipeline(in_las_folder, out_folder, processes=0, style="tin", cell_size=0.0,
                 slope=False, class_threshold=0.3, cloth_resolution=1.0, rigidness=1):
    r_common.check_las_files_existence(in_las_folder)
    classified_folder = os.path.join(out_folder, "Classified_PC")
    normalized_folder = os.path.join(out_folder, "Normalized_PC")
    raster_folder = os.path.join(out_folder, "Raster_Output")
    # The DTM and normalization accept tin/idw/kriging; the DSM and CHM accept tin/pitfree.
    ground_style = style if style in ("tin", "idw", "kriging") else "tin"
    canopy_style = style if style in ("tin", "pitfree") else "tin"

    load_r_functions()

    print_message("1. Checking ground classification")
    if is_ground_classified(in_las_folder):
        print("Ground points found in every tile; skipping CSF classification.")
        ground_folder = in_las_folder
    else:
        print("Ground points missing; running CSF ground classification.")
        rpy_gnd_csf(in_las_folder, classified_folder, slope=slope, class_threshold=class_threshold,
                    cloth_resolution=cloth_resolution, rigidness=rigidness, processes=processes)
        ground_folder = classified_folder

    print_message("2. Checking normalization")
    normalized = is_normalized(ground_folder)

    print_message("3. Generating DTM")
    if normalized:
        # Heights are already above ground, so the terrain is flat at ~0 m.
        print("[Warning!] Data is already normalized; the DTM will be a normalized (flat) DTM.")
    rpy_dtm(ground_folder, raster_folder, ground_style, cell_size=cell_size, processes=processes)

    if normalized:
        print("Data is already normalized; no DSM can be made, going straight to CHM.")
        chm_source = ground_folder
    else:
        print_message("4. Generating DSM")
        rpy_chm_dsm_by(ground_folder, raster_folder, canopy_style, cell_size=cell_size, processes=processes)

        print_message("5. Normalizing point cloud")
        rpy_normalized_PC(ground_folder, normalized_folder, ground_style, processes=processes)
        chm_source = normalized_folder

    print_message("6. Generating CHM")
    # rpy_chm_dsm_by detects the normalized tiles itself and writes a CHM instead of a DSM.
    rpy_chm_dsm_by(chm_source, raster_folder, canopy_style, cell_size=cell_size, processes=processes)

    print_message(f"Pipeline completed; rasters are in {raster_folder}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("in_las_folder", help="folder of input .las/.laz tiles")
    parser.add_argument("out_folder", help="folder for classified/normalized tiles and rasters")
    parser.add_argument("--processes", type=int, default=0, help="worker count (0 = all CPU cores)")
    parser.add_argument("--style", default="tin", choices=["tin", "idw", "kriging", "pitfree"],
                        help="interpolation for DTM/normalization (tin/idw/kriging) and DSM/CHM (tin/pitfree)")
    parser.add_argument("--cell-size", type=float, default=0.0, help="raster cell size (0 = estimate from data)")
    parser.add_argument("--slope", action="store_true", help="CSF slope post-processing for steep terrain")
    parser.add_argument("--class-threshold", type=float, default=0.3)
    parser.add_argument("--cloth-resolution", type=float, default=1.0)
    parser.add_argument("--rigidness", type=int, default=1, choices=[1, 2, 3])
    args = parser.parse_args()

    start_time = time.time()
    run_pipeline(**vars(args))
    print(f"Done in {round(time.time() - start_time, 1)} seconds")


if __name__ == "__main__":
    main()
