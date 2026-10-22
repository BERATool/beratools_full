# Overview

## BERA Tools

BERA Tools is a suite of utilities for mapping, analyzing, and processing forest linear disturbances. It provides both command-line and GUI interfaces, along with a set of modular tools for various workflows.
![BERA logo](screenshots/bt_gui.png)

BERA Tools provide tools for enhanced delineation and attribution of
linear disturbances in forests.

## Key Features

- Line cleanup and quality control
- Vertex optimization using raster guidance
- Automatic centerline generation
- Multiple footprint methods: absolute, relative, fixed-width
- Small, scriptable command-line tools for batch processing
- LiDAR point cloud processing (PC2Products): ground classification, DTM, height normalization,
  CHM/DSM, hummock/hollow mapping, surface water, depth to water and seismic line statistics
- Drag-and-drop pipelines in the GUI that chain tools and link each step's inputs to earlier outputs

## Data Formats & Conventions

- Supported vector: GeoPackage, Shapefile
- Supported raster: GeoTIFF
- Supported point clouds: LAS / LAZ, read from a folder as a lidR `LAScatalog`
- Vector layers in a GeoPackage are given as `file.gpkg|layer`
- Use a projected coordinate system in metres

## Support & Contributions

- See the repository README for detailed examples.
- Contributions welcome via issues and pull requests. Include tests and minimal reproducible examples.

## Tool Boxes

### Mapping

| Tool | Details |
|------|---------|
| [Check Seed Line](user/check_seed_line.md) | Groups and splits input lines for seed line quality control. |
| [Vertex Optimization](user/vertex_optimization.md) | Optimizes line vertices using raster data for improved delineation. |
| [Centerline](user/centerline.md) | Generates centerlines from input lines and raster data. |
| [Line Footprint (Absolute)](user/canopy_footprint_abs.md) | Generates line footprints based on absolute canopy thresholds. |
| [Line Footprint (Relative)](user/canopy_footprint_rel.md) | Creates dynamic line footprints using least-cost corridor and relative thresholds. |
| [Line Footprint (Fixed Width)](user/ground_footprint.md) | Computes fixed-width line footprints and associated statistics. |

### PC2Products (LiDAR)

These tools run R and [lidR](https://r-lidar.github.io/lidRbook/) through
[rpy2](https://rpy2.github.io/), so they need R in the environment (see
[Installation](user/installation.md)).

| Tool | `bt` subcommand | Details |
|------|-----------------|---------|
| [LiDAR data info](user/las_info.md) | `las_info` | Prints the CRS, extent, density and normalization status of a dataset. |
| [Raster Cell size from LiDAR data](user/cellsize.md) | `cellsize` | Recommends a raster cell size from the point density. |
| [Ground Classify Using CSF](user/gnd_csf.md) | `gnd_csf` | Classifies ground points with the Cloth Simulation Filter. |
| [Generate DTM from LiDAR Data](user/dtm.md) | `dtm` | Builds a bare-earth DTM with TIN, IDW or kriging. |
| [Normalize LiDAR Data](user/normalize.md) | `normalize` | Subtracts the terrain so that Z is height above ground. |
| [Generate CHM or DSM from LiDAR Data](user/chm_dsm.md) | `chm_dsm` | Builds a CHM from normalized data, or a DSM from the original data. |
| [Detect Hummock and Hollow from LiDAR Data](user/hummock_hollow.md) | `hh` | Maps hummocks, hollows and lawns relative to a smoothed terrain. |
| [Surface Water Mapping](user/surface_water.md) | `surface_water` | Classifies surface water from a true-colour orthomosaic. |
| [Depth-to-Water from Surface Water](user/dtw.md) | `dtw` | Kriges a water table from surface water and computes depth to water. |
| [Seismic Line Disturbance Analysis](user/seismic_line_analysis.md) | `line_analysis` | Compares seismic line segments with the surrounding peatland by disturbance class. |

### Restoration

| Tool | `bt` subcommand | Details |
|------|-----------------|---------|
| [Seismic Line Recovery Predictor](user/seismic_line_recovery.md) | `line_recovery` | Predicts passive tree recovery on seismic lines from regeneration lags and growth curves by forest type. |
