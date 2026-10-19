# Depth-to-Water from Surface Water

Estimates the water table and depth to water (DTW), following section 2.4 of Chan, Dabros & McDermid
(2026), which adapts Rahman et al. (2017). In peatlands, surface water is closely linked to the
groundwater, so the elevation of the many small pools traces the water table. The tool:

1. Puts the surface water raster on the DTM grid (by majority if the water raster is finer) and masks
   the DTM to the water cells.
2. Splits the area into `grid_size` cells (10 m in the paper). In each cell that contains water, the
   minimum water elevation becomes one point at the cell centre. Cells without water give no point.
3. Fits a variogram (`variogram_model`, Matern with M. Stein's parameterization by default, plus a
   nugget) and kriges the water table with ordinary kriging from the `nmax` nearest points (gstat).
4. Computes DTW = DTM − water table. Values below 0 and surface water cells are set to `0`.
5. Leaves out the exclusion polygons, if any: they give no water points and are NA in the outputs.
   The paper excluded an upland knoll this way, because it had too little surface water.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_dtm` | raster | Yes | DTM. The water table and DTW are produced on its grid. |
| `in_water` | raster | Yes | `1` for surface water, for example `surface_water.tif` from [Surface Water Mapping](surface_water.md). |
| `out_folder` | directory (output) | Yes | Folder for the outputs. |
| `in_mask` | vector (polygon) | No | Areas to leave out, as `file.gpkg\|layer` for a GeoPackage. |
| `grid_size` | float | No | Grid cell size (m) for the water points. The default is `10`. |
| `nmax` | int | No | Nearest water points used for each prediction. The default is `10`. |
| `variogram_model` | `Ste` \| `Sph` \| `Exp` \| `Gau` | No | Variogram model. The default is `Ste` (Matern, as in the paper). |
| `kriging_cell_size` | float | No | Krige on a coarser grid (m), then resample bilinearly to the DTM. `0` (the default) kriges on the DTM grid, which is slow for a large 10 cm DTM. |

| Output | Contents |
|--------|----------|
| `water_table.tif` | Kriged water table elevation. |
| `dtw.tif` | Depth to water (m): positive below ground, `0` on surface water. |
| `water_points.gpkg` | The water elevation points used for kriging. |
| `variogram_model.csv`, `variogram.png` | Fitted variogram parameters and plot. |
| `water_table_cv.csv` | Leave-one-out cross-validation of the water table at the water points (MAE, RMSE). |

On the paper's data, with the surface water taken from the published `dtw.tif` (cells equal to `0`)
and `kriging_cell_size = 1`, the tool's DTW correlates with the published DTW at r = 0.97, and its
leave-one-out MAE is 3.9 cm. It is about 4 cm deeper on average, probably because cells the paper set
to `0` for lying below the water table were treated as water in that test.

```python
from beratools.tools.rpy_dtw import rpy_dtw

rpy_dtw(in_dtm="dtm.tif", in_water="surface_water/surface_water.tif",
        in_mask="exclude.gpkg|exclude", out_folder="dtw", kriging_cell_size=1.0)
```

## Command line

```bash
bt dtw   # show the parameters
bt dtw --in_dtm dtm.tif --in_water surface_water.tif --out_folder <out_dir> --kriging_cell_size 1
```

## Reference

Chan, Dabros & McDermid (2026),
[*Microtopographic and Hydrological Response to Repeated Seismic Line Disturbance in a Boreal Fen of
Northern Alberta, Canada*](https://doi.org/10.3390/f17040489), *Forests* 17, 489.
