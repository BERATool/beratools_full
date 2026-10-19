# Generate CHM or DSM from LiDAR Data

Builds a height surface from the point cloud with `lidR::rasterize_canopy`. The tool decides what to
produce by calling `detect_normalized`, which reads the **first** LAS/LAZ file in the folder:

- If the mean |Z| of the ground points (class 2) is **below 1**, the data counts as
  height-normalized and the tool produces a **CHM**.
- Otherwise, including when there are no ground points, the tool produces a **DSM**.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_las_folder` | directory | Yes | Folder containing the input LAS/LAZ tiles. |
| `out_folder` | directory (output) | Yes | Folder for the output rasters. |
| `style` | `tin` \| `pitfree` | Yes | Surface algorithm. The default is `tin`. An invalid value falls back to `tin`. |
| `processes` | int | No | Requested number of parallel workers. |

| `style` | lidR algorithm | Tile output | Merged output |
|---------|----------------|-------------|---------------|
| `tin` | `dsmtin(max_edge = 3 × cell_size)` | `<tile>_TIN_CHM.tif` / `<tile>_TIN_DSM.tif` | `Merged_TIN_CHM.tif` / `Merged_TIN_DSM.tif` |
| `pitfree` | `pitfree(thresholds = c(0, 3, 5, 10, 15, 20), max_edge = c(0, 3 × cell_size), subcircle = cell_size)`. Overlap points are also dropped. | `<tile>_PitF_CHM.tif` / `<tile>_PitF_DSM.tif` | `Merged_PitF_CHM.tif` / `Merged_PitF_DSM.tif` |

```python
from beratools.tools.rpy_CHM_DSM_by import rpy_chm_dsm

# DSM from the original tiles
rpy_chm_dsm(in_las_folder="tests/data/LiDAR",
            out_folder="tests/data/LiDAR/Raster_Output",
            style="pitfree")

# CHM from the output of Normalize LiDAR Data
rpy_chm_dsm(in_las_folder="tests/data/LiDAR/Normalized_PC",
            out_folder="tests/data/LiDAR/Raster_Output",
            style="tin")
```

## Command line

```bash
bt chm_dsm   # show the parameters
bt chm_dsm --in_las_folder <las_dir> --out_folder <out_dir> --style pitfree
```
