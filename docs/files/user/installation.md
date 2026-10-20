# Advanced Installation

Welcome to **BERA Tools**! This guide will give you advanced installation options and configurations.

## Prerequisites

- Python 3.12 - 3.14
- conda or pip

## Installation Methods

### Windows Installer

Download the standalone Windows installer from the [latest BERA Tools release](https://github.com/BERATool/beratools/releases/latest). Signing is currently off by default; maintainers can enable it per run according to the project [Code signing policy](https://github.com/BERATool/beratools/blob/main/CODE_SIGNING_POLICY.md).

Only installers attached to an official GitHub Release are intended for users. Artifacts from manual signing tests use a self-signed test certificate and must not be distributed.

When signing is skipped, the release includes `beratools-installer-x.y.z-unsigned.exe` and release notes identifying it as unsigned. These assets have no Authenticode signature, so Windows may display an unknown-publisher or SmartScreen warning. Prefer the signed installer when available.

#### Verify the Installer Signature

For a signed installer (without the `-unsigned` suffix), check its signature before running it on Windows:

1. Right-click the installer and select **Properties**.
2. Open the **Digital Signatures** tab.
3. Select the SignPath Foundation signature and click **Details**.
4. Confirm Windows reports **This digital signature is OK**.

You can also verify the installer with PowerShell:

```powershell
Get-AuthenticodeSignature .\beratools-installer-x.y.z.exe |
    Format-List Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

For a signed release asset, `Status` must be `Valid`. Do not run an asset advertised as signed if its signature is missing or invalid. Explicitly labeled `-unsigned.exe` assets instead report `NotSigned`; they are not verified by SignPath.

### Using conda

Have Miniconda installed on your system, then create an environment from the provided [environment.yml](https://raw.githubusercontent.com/BERATool/beratools/main/environment.yml):

```bash
conda env create -f environment.yml
conda activate bera
```

### Using Pip

BERA Tools is published to Pypi and can be installed by pip. On Windows, if you use the standalone installer, GDAL/PROJ are bundled. For pip-based installs, GDAL should be installed first. Please refer to [GDAL for Windows](https://gdal.org/en/stable/download.html#windows) for more information.

Example: install GDAL from a Windows wheel (adjust the URL/version as needed):

```bash
pip install "gdal @ https://github.com/cgohlke/geospatial-wheels/releases/download/v2026.2.26/gdal-3.12.2-cp312-cp312-win_amd64.whl"
```

[OSGeo4W](https://trac.osgeo.org/osgeo4w/https://trac.osgeo.org/osgeo4w/) is recommended for Windows, alongside conda.

```bash
pip install beratools
```

## R for the PC2Products (LiDAR) tools

The PC2Products tools (the `rpy_*` tools in the **PC2Products** category) run R through
[rpy2](https://rpy2.github.io/). The other tools don't need R.

- **conda** and **pixi**: `environment.yml` and `pixi.toml` already include `r-base` 4.5.x and rpy2.
- **pip**: install R 4.5 yourself, then install the `r` extra:

    ```bash
    pip install "beratools[r]"
    ```

On the R side the environments contain only R and rpy2. Every R package comes from CRAN, installed by
the tools into the environment's R the first time they need it (see
[How all the tools behave](../technical/tool_behaviour.md#how-all-the-tools-behave)).

R is held at 4.5.x because conda-forge builds rpy2 for R 4.5 on Linux only, and for nothing newer
than R 4.4 on Windows, which is why rpy2 comes from PyPI on Windows. On Windows, CRAN provides
prebuilt packages for R 4.5. On Linux, CRAN packages such as `sf` and `terra` are compiled from
source, which needs the GDAL, GEOS, PROJ and udunits development libraries (for example
`libgdal-dev libgeos-dev libproj-dev libudunits2-dev` on Ubuntu) and takes a while on the first run;
`pixi.toml` takes prebuilt conda-forge builds of them on `linux-64` instead.

To install every R package up front and confirm that they load, run the R environment test from a
source checkout:

```bash
python -m pytest tests/test_r_environment.py -v
```

The tools install these R packages the first time they need them:

| R package | Purpose |
|-----------|---------|
| `lidR` | LAScatalog processing, `rasterize_terrain`, `rasterize_canopy` |
| `rlas` | Reading LAS/LAZ files |
| `future` | Parallel processing of catalogs |
| `terra` | Raster output and mosaicking |
| `sf`, `units` | CRS, area and map-unit reporting |
| `RCSF` | Cloth Simulation Filter for ground classification |
| `gstat` | Kriging interpolation (DTM and water table) |
| `sp`, `raster`, `stars` | Spatial and raster support |
| `ggplot2` | Plots from Seismic Line Disturbance Analysis |
| `rpart` | Decision tree in Surface Water Mapping |

!!! note "Windows"
    Run the tools from an *activated* environment. If you call the environment's `python.exe`
    directly without activating it, GDAL can fail to load its DLLs.

!!! note "Windows: rpy2 and Git Bash"
    Run the PC2Products tools and the R tests from **PowerShell or cmd, not Git Bash**. Under Git
    Bash, rpy2 crashes while locating R (`IndexError` in `rpy2/situation`), because Git Bash's `sh`
    makes `R CMD config` return empty output instead of failing.

## Verify Installation

After installation, verify that BERA Tools is installed correctly:

```bash
beratools
```

This will start the main GUI.

## Install From Source

[Developer Guide](../developer_guide.md) — Detailed instructions for installing from source, running tests, and contributing.

## Update BERA Tools

Run the following commands to update BERA Tools.

=== "conda"

    ```bash
    conda update beratools
    ```

=== "pip"

    ```bash
    pip install --upgrade beratools
    ```

## Remove BERA Tools

Remove BERA Tools from environment:

=== "conda"

    ```bash
    conda remove beratools
    ```

=== "pip"

    ```bash
    pip uninstall beratools
    ```

Remove whole conda environment:

```bash
conda activate  # go to base env
conda env remove -n bera
```
