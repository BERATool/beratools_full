"""Integration tests: run each PC2Products LiDAR tool on the sample tiles and check its output."""

from pprint import pprint

from utils import check_file_exists

from beratools.utility.spatial_common import decode_file_layer
from beratools.tools.common import has_raster_output,has_lidar_output,list_files_in_folder
from beratools.tools.rpy_dtm_by import rpy_dtm
from beratools.tools.rpy_CHM_DSM_by import rpy_chm_dsm_by
from beratools.tools.rpy_las_info import rpy_las_info
from beratools.tools.rpy_find_cellsize import rpy_find_cellsize
from beratools.tools.rpy_PC2hummock_hollow import rpy_hh2raster
from beratools.tools.rpy_gnd_csf import rpy_gnd_csf
from beratools.tools.rpy_normalized_PC import rpy_normalized_PC

import pytest


# Integration TESTS
def test_rpy_dtm(tool_r_arguments_integration):
    """Test for DTM from the LiDAR data tool."""
    args_rpy_dtm = tool_r_arguments_integration["args_rpy_dtm"]
    pprint(args_rpy_dtm)

    rpy_dtm(**args_rpy_dtm)

    out_file_list = list_files_in_folder(args_rpy_dtm["out_folder"])#,"*_TIN_DTM.tif")
    assert has_raster_output(out_file_list,"Merged_*_DTM.tif"), "out_folder no output!"



def test_rpy_dsm(tool_r_arguments_integration):
    """Test for CHM/DSM from the LiDAR tool."""
    args_rpy_dsm = tool_r_arguments_integration["args_dsm_by"]
    pprint(args_rpy_dsm)

    rpy_chm_dsm_by(**args_rpy_dsm)

    out_file_list = list_files_in_folder(args_rpy_dsm["out_folder"])
    assert has_raster_output(out_file_list,"Merged_*_DSM.tif"), "out_folder no output!"


def test_rpy_las_info(tool_r_arguments_integration):
    """Test for LiDAR metadata from the LiDAR tool."""
    args_rpy_las_info = tool_r_arguments_integration["args_las_info"]
    pprint(args_rpy_las_info)

    rpy_las_info(**args_rpy_las_info)

def test_rpy_find_cellsize(tool_r_arguments_integration):
    """"Test for finding cell size from LiDAR data in the LiDAR tool."""
    args_rpy_find_cellsize = tool_r_arguments_integration["args_find_cellsize"]
    pprint(args_rpy_find_cellsize)

    rpy_find_cellsize(**args_rpy_find_cellsize)


def test_rpy_PC2hummock_hollow(tool_r_arguments_integration):
    """"Test for finding cell size from LiDAR data in the LiDAR tool."""
    args_rpy_hh2raster = tool_r_arguments_integration["args_hh"]
    pprint(args_rpy_hh2raster)

    rpy_hh2raster(**args_rpy_hh2raster)
    out_file_list = list_files_in_folder(args_rpy_hh2raster["out_folder"])

    assert (has_raster_output(out_file_list,"Merged_CHH*.tif" )
            and has_raster_output(out_file_list,"Merged_HH*.tif")), "out_folder no output!"

def test_classified_lidar(tool_r_arguments_integration):
    """Test for LiDAR classification output."""
    args_rpy_gnd_csf = tool_r_arguments_integration["args_classify_gnd_csf"]
    pprint(args_rpy_gnd_csf)

    rpy_gnd_csf(**args_rpy_gnd_csf)

    out_file, _ = decode_file_layer(args_rpy_gnd_csf["out_folder"])

    assert has_lidar_output(out_file, ), "out_folder no output!"

def test_normalized_PC(tool_r_arguments_integration):
    """Test for normalized LiDAR output."""
    args_rpy_normalized_PC = tool_r_arguments_integration["args_normalized_PC"]
    pprint(args_rpy_normalized_PC)

    rpy_normalized_PC(**args_rpy_normalized_PC)

    out_file, _ = decode_file_layer(args_rpy_normalized_PC["out_folder"])

    assert has_lidar_output(out_file, ), "out_folder no output!"


# Runs after test_normalized_PC: it reads the normalized tiles that test writes.
def test_rpy_chm(tool_r_arguments_integration):
    """Test for CHM/DSM from the LiDAR tool."""
    args_rpy_chm = tool_r_arguments_integration["args_chm_by"]
    pprint(args_rpy_chm)

    rpy_chm_dsm_by(**args_rpy_chm)

    out_file_list = list_files_in_folder(args_rpy_chm["out_folder"])
    assert has_raster_output(out_file_list,"Merged_*_CHM.tif"), "out_folder no output!"


# CLEANUP TESTS
def test_cleanup_r_output_files(cleanup_r_output_files):
    # Your test code goes here
    # The cleanup will automatically run after the test finishes
    pass


# R TESTS
def test_r_packages():
    """Verify required R packages are available."""

    try:
        from rpy2.robjects.packages import importr
    except Exception as exc:
        pytest.fail(f"rpy2 not available: {exc}")

    packages = [
        "lidR",
        "terra",
        "stars",
        "future",
        "gstat",
        "rlas",
    ]

    missing = []

    for pkg in packages:
        try:
            importr(pkg)
        except Exception:
            missing.append(pkg)

    assert not missing, f"Missing R packages: {', '.join(missing)}"
