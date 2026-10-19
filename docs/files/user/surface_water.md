# Surface Water Mapping

Maps surface water from a true-colour orthomosaic, following section 2.4 of Chan, Dabros & McDermid
(2026):

1. Draws `points_per_polygon` random points inside each training polygon and reads the orthomosaic's
   red, green and blue values (bands 1–3) at each point.
2. Trains an `rpart` decision tree on those values, and estimates its accuracy with 5-fold
   cross-validation on the training points.
3. Classifies every cell of the orthomosaic. Cells the tree labels `water` become `1`, all others `0`.
4. If a CHM is given, sets cells with canopy taller than `max_canopy_height` to `0`. The CHM is
   resampled to the orthomosaic's grid first.
5. Sets water patches (8-connected) smaller than `min_patch_area` to `0`.

The training polygons need a `class` field. Polygons labelled `water` (in any case) are surface water;
use any other labels for the rest, for example `ground` and `shadow` as in the paper. rpart needs at
least 20 training points before it splits, so the tool warns if the tree ends up with no splits.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_ortho` | raster | Yes | True-colour orthomosaic; bands 1–3 are red, green and blue. |
| `in_training` | vector (polygon) | Yes | Training polygons with a `class` field, as `file.gpkg\|layer` for a GeoPackage. |
| `out_folder` | directory (output) | Yes | Folder for the outputs. |
| `in_chm` | raster | No | Canopy height model, for example from [Generate CHM or DSM from LiDAR Data](chm_dsm.md). |
| `max_canopy_height` | float | No | Cells with a CHM above this height (m) can't be water. The default is `0.2`. |
| `min_patch_area` | float | No | Water patches smaller than this area (m²) are removed; `0` keeps them all. The default is `0.04` (20 × 20 cm). |
| `points_per_polygon` | int | No | Random training points per polygon. The default is `2`. |
| `seed` | int | No | Seed for the training points and cross-validation folds. The default is `1`. |

| Output | Contents |
|--------|----------|
| `surface_water.tif` | `1` for surface water, `0` for everything else. |
| `cv_accuracy.csv`, `cv_confusion_matrix.csv` | 5-fold cross-validation accuracy and confusion matrix. |
| `training_points.gpkg` | The random training points and their classes. |
| `decision_tree.txt` | The fitted tree's splits. |

```python
from beratools.tools.rpy_surface_water import rpy_surface_water

rpy_surface_water(in_ortho="ortho.tif", in_training="training.gpkg|training",
                  in_chm="chm.tif", out_folder="surface_water")
```

## Command line

```bash
bt surface_water   # show the parameters
bt surface_water --in_ortho ortho.tif --in_training "training.gpkg|training" --in_chm chm.tif --out_folder <out_dir>
```
