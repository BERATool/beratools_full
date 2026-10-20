# Examples

- [Full Workflow (Hydra)](#full-workflow-example-hydra): `full_workflow.py` + `config.yaml`, runs the line mapping tools.
- [PC2Products Workflow (Hydra)](#pc2products-workflow-example-hydra): `pc2products_workflow.py` + `pc2products_config.yaml`, runs the LiDAR tools from raw tiles to rasters.
- [DTM, DSM and CHM Pipeline](#dtm-dsm-and-chm-pipeline): `pc2products_pipeline.py`, checks the LiDAR data and runs only the steps it needs.

# Full Workflow Example (Hydra)

This folder contains a Hydra-driven example that runs a full processing workflow using BERA tools:

1. `check_seed_line`
2. `centerline`
3. `footprint_abs`
4. `footprint_ground`

## Files

- `full_workflow.py`: workflow entrypoint.
- `config.yaml`: Hydra config for inputs, outputs, and step selection.

## Requirements

- Python environment with BERA Tools dependencies installed.
- `hydra-core` and `omegaconf` available in the environment.
- Input data available at the paths configured in `config.yaml`.

## Configure Input Data

Edit `config.yaml` and set at least:

- `DATA_DIR`
- `CHM`
- `SEEDLINE_ORIGINAL`
- `SEEDLINE_ORIGINAL_LAYER`

The workflow uses `file|layer` syntax for vector layer references.

Example:

```yaml
in_line: ${DATA_DIR}/${SEEDLINE_ORIGINAL}|${SEEDLINE_ORIGINAL_LAYER}
```

## Run

From the repository root:

```bash
python examples/full_workflow.py
```

Run with Hydra overrides:

```bash
python examples/full_workflow.py processes=8
python examples/full_workflow.py steps_to_run=[centerline,footprint_abs]
python examples/full_workflow.py DATA_DIR="D:/my_data"
```

## Common Overrides

- `processes=<int>`: number of worker processes; defaults to all CPU cores when `null`.
- `steps_to_run=[...]`: run only selected steps in order.
- Any nested argument, for example:

```bash
python examples/full_workflow.py args_centerline.line_radius=20
python examples/full_workflow.py args_footprint_ground.width_percentile=75
```

## Output

Outputs are written to paths defined in `config.yaml`, including:

- `centerline.gpkg|centerline`
- `footprint_abs.gpkg|footprint_abs`
- `footprint_ground.gpkg|footprint_ground`

# PC2Products Workflow Example (Hydra)

`pc2products_workflow.py` is a [Hydra](https://hydra.cc/)-driven example that runs the PC2Products
(LiDAR) tools in sequence, from raw LiDAR tiles to raster products:

| Step | Tool | Reads | Writes |
|------|------|-------|--------|
| `las_info` | LiDAR data info | `DATA_DIR` | Console only |
| `cellsize` | Raster Cell size from LiDAR data | `DATA_DIR` | Console only |
| `gnd_csf` | Ground Classify Using CSF | `DATA_DIR` | `CLASSIFIED_DIR` |
| `dtm` | Generate DTM from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |
| `chm_dsm` | Generate CHM or DSM from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |
| `hh` | Detect Hummock and Hollow from LiDAR Data | `CLASSIFIED_DIR` | `RASTER_DIR` |

Steps always run in this order. `steps_to_run` only chooses which of them run.

## Files

- `pc2products_workflow.py`: workflow entrypoint.
- `pc2products_config.yaml`: Hydra config for folders, step selection and each tool's arguments
  (`args_<step>`).

## Requirements

An environment with R (see [Installation](../docs/files/user/installation.md#r-for-the-pc2products-lidar-tools)).
Both `environment.yml` and `pixi.toml` include what the workflow needs: `hydra-core` (which brings in
`omegaconf`), `rpy2`, `psutil` and R.

## Configure Input Data

`pc2products_config.yaml` defines three folders:

| Key | Default | Contents |
|-----|---------|----------|
| `DATA_DIR` | `tests/data/LiDAR` | Input LAS/LAZ tiles |
| `CLASSIFIED_DIR` | `${DATA_DIR}/Classified_PC` | Ground-classified tiles written by `gnd_csf` |
| `RASTER_DIR` | `${DATA_DIR}/Raster_Output` | DTM, CHM/DSM and hummock/hollow rasters |

The defaults point at the sample tiles, so the workflow runs as-is from the repository root.
Relative paths are resolved from the folder you run the script from (`hydra.job.chdir` is `false`).

If your data is already ground-classified, skip `gnd_csf` and point `CLASSIFIED_DIR` at the input
folder:

```bash
python examples/pc2products_workflow.py steps_to_run=[dtm,chm_dsm,hh] CLASSIFIED_DIR=D:/my_data/LiDAR
```

## Run

From the repository root:

```bash
python examples/pc2products_workflow.py
```

Run with Hydra overrides:

```bash
python examples/pc2products_workflow.py processes=4
python examples/pc2products_workflow.py steps_to_run=[gnd_csf,dtm]
python examples/pc2products_workflow.py DATA_DIR=D:/my_data/LiDAR
```

## Common Overrides

- `processes=<int>`: number of worker processes. `null` (the default) uses all CPU cores, and the
  tools then apply their own limits.
- `steps_to_run=[...]`: run only the selected steps. An unknown step name stops the workflow before
  anything runs.
- Any tool argument, for example:

```bash
python examples/pc2products_workflow.py args_dtm.style=kriging
python examples/pc2products_workflow.py args_chm_dsm.style=pitfree
python examples/pc2products_workflow.py args_hh.Min_ws=5.0 args_hh.lawn_range=0.2
python examples/pc2products_workflow.py args_gnd_csf.rigidness=3
```

## Output

With the default `style: tin` and `Smooth_by: median`, `Min_ws: 3.0`:

- `CLASSIFIED_DIR`: `<tile>_gnd_classified.las` for each input tile.
- `RASTER_DIR`:
  - `<tile>_gnd_classified_TIN_DTM.tif` and `Merged_TIN_DTM.tif`
  - `<tile>_gnd_classified_TIN_DSM.tif` and `Merged_TIN_DSM.tif` (`_CHM` instead of `_DSM` if the
    data is height-normalized)
  - `CHH_<tile>_gnd_classified_median_3m.tif`, `HH_<tile>_gnd_classified_median_3m.tif`,
    `Merged_CHH_median_3m.tif` and `Merged_HH_median_3m.tif`

Hydra also writes its run log and resolved config to `outputs/<date>/<time>/` in the current folder.

# DTM, DSM and CHM Pipeline

`pc2products_pipeline.py` is a plain `argparse` script (no Hydra) that builds DTM, DSM and CHM rasters
and checks the data first, so it skips the steps the data doesn't need:

```text
1. Ground classified?  no  -> classify ground with CSF
2. Generate DTM from the ground-classified tiles
3. Normalized?         no  -> generate DSM, normalize the tiles, then generate CHM
                       yes -> generate CHM straight away (the DTM will be flat, ~0 m)
```

## Run

From the repository root:

```bash
python examples/pc2products_pipeline.py IN_LAS_FOLDER OUT_FOLDER [options]
python examples/pc2products_pipeline.py tests/data/LiDAR D:/my_output
python examples/pc2products_pipeline.py D:/my_data/LiDAR D:/my_output --processes 4 --style pitfree
```

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `--processes` | `0` | Worker processes (`0` = all CPU cores). |
| `--style` | `tin` | `tin`, `idw` or `kriging` for the DTM and normalization; `tin` or `pitfree` for the DSM and CHM. A style that doesn't apply to a step falls back to `tin` for it. |
| `--cell-size` | `0.0` | Raster cell size (`0` = estimate from the data). |
| `--slope` | off | CSF slope post-processing for steep terrain. |
| `--class-threshold` | `0.3` | CSF classification threshold. |
| `--cloth-resolution` | `1.0` | CSF cloth resolution. |
| `--rigidness` | `1` | CSF cloth rigidness (`1`, `2` or `3`). |

The CSF options are used only when the input isn't ground-classified.

## Output

Inside `OUT_FOLDER`:

- `Classified_PC/`: ground-classified tiles (only when the input wasn't classified).
- `Normalized_PC/`: height-normalized tiles (only when the input wasn't normalized).
- `Raster_Output/`: `Merged_*_DTM.tif`, `Merged_*_DSM.tif` (not made for normalized input) and
  `Merged_*_CHM.tif`, plus the per-tile rasters.

`run_pipeline()` can also be imported and called from Python with the same arguments.
