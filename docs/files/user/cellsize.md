# Raster Cell size from LiDAR data

Calculates the recommended raster cell size from the average point density:

```text
point_density = total point records / catalog area
cell_size     = sqrt(3 / point_density), rounded to the nearest 0.05 map units
```

The cell size is printed along with the map units of the CRS. The R function `pd2cellsize` returns
`cell_size`, `map_units` and `point_density`, and the DTM and CHM/DSM tools call it to set their
output resolution.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_las_folder` | directory | Yes | Folder containing the input LAS/LAZ tiles. |
| `processes` | int | No | Requested number of parallel workers. |

```python
from beratools.tools.rpy_find_cellsize import rpy_find_cellsize

rpy_find_cellsize(in_las_folder="tests/data/LiDAR")
```

## Command line

```bash
bt cellsize   # show the parameters
bt cellsize --in_las_folder <las_dir>
```
