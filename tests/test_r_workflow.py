"""End-to-end test: run the PC2Products LiDAR tools in sequence, each on the previous output."""

# E2E test for the entire workflow
def test_full_r_workflow(tool_arguments_r_workflow):
    """
    Full E2E test running the entire workflow.

    with real data, ensuring that each tool integrates properly with the next.
    """
    from beratools.utility.spatial_common import (decode_file_layer)
    from beratools.tools.common import has_raster_output, has_lidar_output
    from beratools.tools.rpy_dtm_by import rpy_dtm
    from beratools.tools.rpy_CHM_DSM_by import rpy_chm_dsm_by
    from beratools.tools.rpy_gnd_csf import rpy_gnd_csf
    from beratools.tools.rpy_PC2hummock_hollow import rpy_hh2raster
    from beratools.tools.rpy_normalized_PC import rpy_normalized_PC

    # 1. Test LiDAR data has been classified
    args_rpy_gnd_csf = tool_arguments_r_workflow["args_classify_gnd_csf"]
    rpy_gnd_csf(**args_rpy_gnd_csf)
    out_file, _ = decode_file_layer(args_rpy_gnd_csf["out_folder"])
    assert has_lidar_output(out_file, ), "out_folder no output!"

    # 2. Test for TIN DTM from the LiDAR data tool
    args_rpy_dtm = tool_arguments_r_workflow["args_rpy_dtm"]
    rpy_dtm(**args_rpy_dtm)
    out_file,_ = decode_file_layer(args_rpy_dtm["out_folder"])
    assert has_raster_output(out_file,), "out_folder no output!"

    # 3. Test for TIN DSM from the LiDAR data tool
    args_rpy_dsm = tool_arguments_r_workflow["args_dsm_by"]
    rpy_chm_dsm_by(**args_rpy_dsm)
    out_file, _ = decode_file_layer(args_rpy_dsm["out_folder"])
    assert has_raster_output(out_file, ), "out_folder no output!"

    # 4. Test for PC normalization:
    args_rpy_normalized_PC = tool_arguments_r_workflow["args_normalized_PC"]
    rpy_normalized_PC(**args_rpy_normalized_PC)
    out_file, _ = decode_file_layer(args_rpy_normalized_PC["out_folder"])
    assert has_lidar_output(out_file, ), "out_folder no output!"

    # 5. Test for CHM from the normalized LiDAR data tool
    args_rpy_chm = tool_arguments_r_workflow["args_chm_by"]
    rpy_chm_dsm_by(**args_rpy_chm)
    out_file, _ = decode_file_layer(args_rpy_chm["out_folder"])
    assert has_raster_output(out_file, ), "out_folder no output!"

    # 6. Test for hummock and hollow from LiDAR data tool
    args_rpy_hh2raster = tool_arguments_r_workflow["args_hh"]
    rpy_hh2raster(**args_rpy_hh2raster)
    out_file, _ = decode_file_layer(args_rpy_hh2raster["out_folder"])
    assert has_raster_output(out_file, ), "out_folder no output!"



# CLEANUP TESTS
def test_cleanup_r_output_files(cleanup_r_output_files):
    # Your test code goes here
    # The cleanup will automatically run after the test finishes
    pass
