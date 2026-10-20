# Seismic Line Disturbance Analysis

Compares seismic line segments with the undisturbed peatland ("matrix") beside them, by disturbance
class. It is adapted from the analysis script of Chan, Dabros & McDermid (2026),
[*Microtopographic and Hydrological Response to Repeated Seismic Line Disturbance in a Boreal Fen of
Northern Alberta, Canada*](https://doi.org/10.3390/f17040489), *Forests* 17, 489. On the paper's
published data it gives the same tables as the original script. It needs only the `terra` and
`ggplot2` R packages; the statistical tests are written in base R.

For each segment, the tool summarises the rasters under it. Then, for each line segment, it subtracts
the mean of its matrix segments:

| Attribute | From | Per segment | Deviation |
|-----------|------|-------------|-----------|
| `dtm` | DTM | Mean elevation | Line − matrix (m) |
| `hummock` | Microform raster | Hummock cells / classified cells | Line − matrix |
| `dtw` | Depth-to-water raster | Mean DTW over ground cells (DTW ≠ 0) | Line − matrix (m) |
| `surfacewater` | Depth-to-water raster | Cells with DTW = 0 / all cells | Line − matrix |

For each attribute it compares the disturbance classes with:

- a Kruskal–Wallis test, and pairwise Wilcoxon rank-sum tests with Benjamini–Hochberg (BH) correction.
  The `mean_group` letters come from these.
- a Brown–Forsythe test, and pairwise Brown–Forsythe tests with BH correction. The `bf_group` letters
  come from these. This is the Brown–Forsythe test for equal *means* under unequal variances (the
  statistic of `onewaytests::bf.test`, which the original script uses).

Classes that share a letter don't differ significantly at the chosen `significance`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_segments` | vector (polygon) | Yes | Segment polygons, as `file.gpkg\|layer` for a GeoPackage. Fields: `new_id` links a line segment to its matrix segments, `note` is `original` (line) or `matrix`, and `Class` is the disturbance class. |
| `in_dtm` | raster | Yes | DTM, for example from [Generate DTM from LiDAR Data](dtm.md). |
| `in_microform` | raster | Yes | Hummock (`1`), lawn (`0`) and hollow (`-1`) raster, for example the `HH_` or `Merged_HH_` output of [Detect Hummock and Hollow from LiDAR Data](hummock_hollow.md). |
| `out_folder` | directory (output) | Yes | Folder for the `tables/` and `plots/` outputs. |
| `in_dtw` | raster | No | Depth to water in metres, with `0` for surface water. Without it, `dtw` and `surfacewater` are skipped. |
| `significance` | float | No | Significance level for the letter groupings. The default is `0.05`. |

The segments are projected to the DTM's coordinate system if they differ. Classes named `New
Disturbance`, `Old Disturbance` and `Re-disturbance` keep the paper's order and colours; any other
class names are sorted alphabetically.

| Output | Contents |
|--------|----------|
| `tables/segment_values.csv` | Per-segment summaries for every segment. |
| `tables/segment_deviations.csv` | Per-line-segment deviations from the matrix. |
| `tables/<attribute>_deviation_summary.csv` | By class: n, mean, median, min, max, quartiles, SD, variance, `mean_group` and `bf_group`. |
| `tables/<attribute>_kruskal_wilcoxon.csv` | Kruskal–Wallis result and BH-adjusted pairwise Wilcoxon p-values. |
| `tables/<attribute>_brown_forsythe.csv` | Brown–Forsythe result and pairwise p-values (raw and BH-adjusted). |
| `tables/class_microform_proportions.csv`, `tables/class_surfacewater_proportions.csv` | Cell proportions for the matrix and each class. |
| `plots/<attribute>_violin.png` | Deviation distribution per class, with the class mean (dot) and `mean_group` letters. |
| `plots/microform_barplot.png`, `plots/surfacewater_barplot.png` | Stacked proportions for the matrix and each class. |

```python
from beratools.tools.rpy_seismic_line_analysis import rpy_seismic_line_analysis

rpy_seismic_line_analysis(in_segments="segments.gpkg|segments",
                          in_dtm="dtm.tif", in_microform="microform.tif", in_dtw="dtw.tif",
                          out_folder="analysis")
```

## Reproducing Chan et al. (2026)

The paper's workflow maps onto the PC2Products tools like this:

| Paper step | PC2Products tool | Settings |
|------------|------------------|----------|
| Ground classification (LAStools in the paper) | Ground Classify Using CSF | Defaults |
| 10 cm DTM with `knnidw` (k = 10, p = 2) | Generate DTM from LiDAR Data | `style = idw` (lidR's `knnidw()` defaults are k = 10, p = 2). The cell size comes from the point density and can't be set. |
| Microforms: DTM minus its 3 m focal mean, ±6 cm | Detect Hummock and Hollow from LiDAR Data | `Smooth_by = mean`, `Min_ws = 3`, `lawn_range = 0.06`, `cell_size = 0.1`. The tool builds its own DTM with TIN. |
| Surface water: rpart classification of the orthomosaic's RGB values, CHM mask (> 0.2 m), patches under 20 × 20 cm removed | Surface Water Mapping | Defaults, with the CHM as `in_chm` |
| Water table: minimum water elevation per 10 m cell, ordinary kriging (Matern, 10 nearest), then DTW = DTM − water table | Depth-to-Water from Surface Water | Defaults, with the upland knoll as `in_mask` |
| Segments along mapped centrelines (Forest Line Mapper) | None | Not available; supply `in_segments` from elsewhere. |
| Comparison and statistics | Seismic Line Disturbance Analysis | `significance = 0.05` |

The paper's published data (`dtm.tif`, `dtw.tif`, `microform.tif` and `segments.gpkg`, on
[Zenodo](https://doi.org/10.5281/zenodo.18778508)) can be used directly as the inputs to Seismic Line
Disturbance Analysis.

## Command line

```bash
bt line_analysis   # show the parameters
bt line_analysis --in_segments "segments.gpkg|segments" --in_dtm dtm.tif --in_microform HH.tif --in_dtw dtw.tif --out_folder <out_dir>
```
