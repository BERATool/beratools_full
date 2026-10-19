# PC2Products Tool Overview

Each PC2Products tool is a thin Python wrapper in `beratools/tools/`. It validates the inputs and then
calls an R function in `r_scripts_collection.r` through [rpy2](https://rpy2.github.io/). The R
functions use [lidR](https://r-lidar.github.io/lidRbook/) to do the processing. The algorithm each
tool uses is described on its page in the User Guide.

| Tool | Module | Python function | R function(s) |
|------|--------|-----------------|---------------|
| [LiDAR data info](../user/las_info.md) | `rpy_las_info.py` | `rpy_las_info` | `las_info` |
| [Raster Cell size from LiDAR data](../user/cellsize.md) | `rpy_find_cellsize.py` | `rpy_find_cellsize` | `pd2cellsize` |
| [Ground Classify Using CSF](../user/gnd_csf.md) | `rpy_gnd_csf.py` | `rpy_gnd_csf` | `classify_gnd_csf` |
| [Generate DTM from LiDAR Data](../user/dtm.md) | `rpy_dtm_by.py` | `rpy_dtm` | `dtm_by_tin`, `dtm_by_knnidw`, `dtm_by_kriging` |
| [Normalize LiDAR Data](../user/normalize.md) | `rpy_normalized_PC.py` | `rpy_normalized_PC` | `normalized_lidar_tin`, `normalized_lidar_knnidw`, `normalized_lidar_kriging` |
| [Generate CHM or DSM from LiDAR Data](../user/chm_dsm.md) | `rpy_CHM_DSM_by.py` | `rpy_chm_dsm` | `chm_by_dsmtin`, `chm_by_pitfree` |
| [Detect Hummock and Hollow from LiDAR Data](../user/hummock_hollow.md) | `rpy_PC2hummock_hollow.py` | `rpy_hh2raster` | `hh_function` |
| [Surface Water Mapping](../user/surface_water.md) | `rpy_surface_water.py` | `rpy_surface_water` | `surface_water_map` |
| [Depth-to-Water from Surface Water](../user/dtw.md) | `rpy_dtw.py` | `rpy_dtw` | `dtw_map` |
| [Seismic Line Disturbance Analysis](../user/seismic_line_analysis.md) | `rpy_seismic_line_analysis.py` | `rpy_seismic_line_analysis` | `seismic_line_analysis` |

## Shared helpers

| File | Contents |
|------|----------|
| `r_interface.py` | `configure_r_environment()`: finds R and sets up `R_HOME`, the DLL search path and `PATH` before rpy2 is imported (see [How R is located](tool_behaviour.md#how-r-is-located)). |
| `r_common.py` | Connects rpy2 on first use, and provides `r_processes`, `check_las_files_existence`, `check_las_out_folder_existence` and `check_r_packages_installation`. |
| `common.py` | `has_raster_output` and `has_lidar_output`, used by the tests to check a tool wrote its output. |
| `r_scripts_collection.r` | All the R processing functions, plus `detect_normalized`, `detect_ground_classified` and `mosaic_catalog_outputs`. |

## Where to go next

- [How the Tools Run](tool_behaviour.md)
- Architecture:
  - [System Overview](architecture/system_overview.md)
  - [Execution Pipeline](architecture/execution_pipeline.md)
  - [Tool Runtime Model](architecture/tool_runtime_model.md)
