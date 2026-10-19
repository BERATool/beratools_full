# Ground Classify Using CSF

Classifies ground points with the Cloth Simulation Filter (Zhang et al., 2016), using
`lidR::classify_ground` with `RCSF`'s `csf()` algorithm. The cloth runs for 500 iterations with a
time step of 0.65. Noise (class 7) and overlap points are dropped when the tiles are read.

If the input is already ground-classified (the first file has any class 2 points), the existing
classification is replaced and lidR's progress messages are hidden.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `in_las_folder` | directory | Yes | Folder containing the input LAS/LAZ tiles. |
| `out_folder` | directory (output) | Yes | Folder for the classified point clouds. |
| `slope` | bool | No | Set to `True` when steep slopes exist, to reduce errors in post-processing. The default is `False`. |
| `class_threshold` | float | No | Distance to the simulated cloth that separates ground from non-ground points. The default is `0.5`. |
| `cloth_resolution` | float | No | Distance between cloth particles. This is usually the average point spacing. The default is `1.0`. |
| `rigidness` | `1` \| `2` \| `3` | No | Cloth stiffness: `1` is very soft (rugged terrain), `2` is medium, and `3` is hard (flat terrain). The default is `1`. |
| `processes` | int | No | Requested number of parallel workers. |

Output: one uncompressed `<tile>_gnd_classified.las` per input tile.

```python
from beratools.tools.rpy_gnd_csf import rpy_gnd_csf

rpy_gnd_csf(in_las_folder="tests/data/LiDAR",
            out_folder="tests/data/LiDAR/Classified_PC",
            slope=False, class_threshold=0.3, cloth_resolution=1.0, rigidness=1)
```

## Command line

```bash
bt gnd_csf   # show the parameters
bt gnd_csf --in_las_folder <las_dir> --out_folder <out_dir> --slope false --rigidness 2
```
