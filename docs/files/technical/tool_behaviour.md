# How the PC2Products Tools Run

## How all the tools behave

These points apply to the seven LiDAR tools. Surface Water Mapping, Depth-to-Water from Surface Water and
Seismic Line Disturbance Analysis work on rasters instead (see their own sections), but they install
their R packages the same way:

- **Input**: every `.las` / `.laz` file in `in_las_folder` is read as a lidR `LAScatalog`. If the
  folder is missing or holds no LAS/LAZ files, the tool stops.
- **Noise removal**: points classified as low noise (class 7) are dropped with
  `filter = "-drop_class 7"`.
- **Cell size**: the DTM and CHM/DSM tools don't take a cell size. They calculate it from the point
  density, as described in [Raster Cell size from LiDAR data](../user/cellsize.md).
  The hummock/hollow tool does the same when `cell_size` is `0`.
- **Output folder**: if `out_folder` doesn't exist, it's created. Existing outputs are overwritten.
- **Tiled output and mosaic**: the raster tools write one raster per input tile. When there is more
  than one tile, they also merge the tiles into a single `Merged_*.tif` with `terra::mosaic`.
- **Parallel processing**: the tools use `future::plan(multisession)` and `set_lidr_threads`. The
  number of R workers comes from `r_processes(processes)`:
  - A `processes` value of 0 or less (the default) means "use every CPU core".
  - The worker count is never more than `processes`, the number of CPU cores, or 8.
  - When more than 2 workers would be used, available memory caps the count: 2 workers with about
    50 GB or less free, and 4 workers with about 150 GB or less free.
  - The TIN and kriging DTM tools halve the worker count when the cell size is under 1 map unit.
- **R packages**: the environment provides only R and rpy2. Each tool checks for the R packages it
  needs and installs any missing ones from the CRAN mirror in Canada into the library of the R it
  runs on (`<R_HOME>/library`, inside the conda or pixi environment). The first run of each tool can
  therefore take a while. If a package still can't be installed, the tool stops with
  `R packages could not be installed into <library>: <names>`.

## How R is located

`r_interface.py` looks for R **before** it imports rpy2, and checks these places in order:

1. An existing `R_HOME` environment variable
2. `Rscript` or `R` on the `PATH` (`R_HOME` is set from the output of `<exe> RHOME`)
3. R installed in the conda or pixi environment: `Lib/R` (Windows) or `lib/R` (Linux), next to the
   Python executable or under `sys.prefix`
4. A standard Windows install under `C:\Program Files\R\R-*`

It then adds the environment's `Library\bin`, `Library\mingw-w64\bin`, `Library\usr\bin`, `Scripts`
and `R_HOME\bin` folders to the DLL search path and `PATH`. If it can't find R, it prints
`sys.executable`, `sys.prefix`, `R_HOME` and the `which R` / `which Rscript` results to help with
debugging, then raises an error with installation instructions.

## How the GUI runs a tool

The GUI starts the tool module in a new process and passes the parameters as JSON with `-i/--input`.
The module checks them against `beratools.json` in `BTData.validate_tool_params`: it confirms that
input folders exist, checks list values against the allowed options, and converts numbers and
booleans to the right type. Output parameters aren't checked, because they don't exist yet.

Each module's `compose_tool_kwargs("<tool_api>")` call must use the tool's `tool_api` from
`beratools.json`, or the tool stops with `Tool API '<name>' not found in beratools.json`.
