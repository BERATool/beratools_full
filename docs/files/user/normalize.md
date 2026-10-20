# Normalize LiDAR Data

Height-normalizes the point cloud with `lidR::normalize_height`: the terrain is interpolated from the
ground points (class 2) and subtracted from every point, so Z becomes height above ground. Noise
(class 7) is dropped when the tiles are read. The data must be ground-classified, so run
[Ground Classify Using CSF](gnd_csf.md) first if it isn't.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_las_folder` | directory | Yes | Folder containing the ground-classified LAS/LAZ tiles. |
| `out_folder` | directory (output) | Yes | Folder in which the `Normalized_PC/` subfolder is created. |
| `style` | `tin` \| `idw` \| `kriging` | Yes | Terrain interpolation algorithm: `tin()`, `knnidw()` or `kriging()`. The default is `tin`. An invalid value falls back to `tin`. |
| `processes` | int | No | Requested number of parallel workers. |

Output: one `<out_folder>/Normalized_PC/n_<tile>.las` per input tile. Point
[Generate CHM or DSM from LiDAR Data](chm_dsm.md) at the `Normalized_PC`
folder to get a CHM.

```python
from beratools.tools.rpy_normalized_PC import rpy_normalized_PC

rpy_normalized_PC(in_las_folder="tests/data/LiDAR",
                  out_folder="tests/data/LiDAR",
                  style="tin")
```

## Command line

```bash
bt normalize   # show the parameters
bt normalize --in_las_folder <las_dir> --out_folder <out_dir> --style tin
```
