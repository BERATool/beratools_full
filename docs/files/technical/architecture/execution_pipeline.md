# Execution Pipeline

This page describes the high-level runtime flow from user input to final outputs.

## At a glance

```mermaid
flowchart LR
    A[Input collection] --> B[Argument normalization]
    B --> C[Preprocessing and validation]
    C --> D[Core algorithm execution]
    D --> E[Post-processing and output writing]
```

## Pipeline stages

### 1) Input collection

**Purpose**

Capture tool parameters from the selected runtime interface.

**Main actions**

- GUI mode: parameters are collected from form widgets.
- CLI mode: parameters are parsed from command-line arguments.

**Inputs**

- User-provided tool parameters
- Runtime context (GUI/CLI)

**Outputs**

- Raw, mode-specific parameter payload

### 2) Argument normalization

**Purpose**

Build a consistent runtime argument set independent of call mode.

**Main actions**

- Tool metadata defines required/optional parameters.
- Framework options (`processes`, `call_mode`, `log_level`) are applied consistently.

**Inputs**

- Raw parameter payload
- Tool metadata/schema

**Outputs**

- Normalized tool kwargs ready for execution

### 3) Preprocessing and validation

**Purpose**

Verify that inputs are usable and compatible before expensive computation starts.

**Main actions**

- Read vector/raster inputs.
- Validate geometry types, CRS compatibility, and required values.

**Inputs**

- Normalized kwargs
- Source data files

**Outputs**

- Validated in-memory inputs
- Early validation errors (if any)

### 4) Core algorithm execution

**Purpose**

Run the selected tool’s core processing logic.

**Main actions**

- Tool wrapper dispatches to core modules in `beratools/core`.
- Optional multiprocessing is used for suitable workloads.

**Inputs**

- Validated inputs
- Execution options (including `processes`)

**Outputs**

- Intermediate/final computed geometries and attributes

### 5) Post-processing and output writing

**Purpose**

Finalize results and persist outputs for downstream use.

**Main actions**

- Build output geometries/attributes.
- Write result files.
- Emit logs/progress information.

**Inputs**

- Core algorithm outputs

**Outputs**

- Saved output datasets
- Runtime logs and progress signals

## Typical workflow chain

```mermaid
flowchart LR
    A[Check Seed Lines] --> B[Vertex Optimization]
    A --> C[Centerline]
    B --> C
    C --> D[Canopy Footprint]
    D --> E[Ground Footprint]
```

The PC2Products (LiDAR) tools follow the same stages, but stage 3 checks that the input folder holds
LAS/LAZ files and installs any missing R packages, stage 4 runs the tool's R function tile by tile
with parallel R workers, and stage 5 merges per-tile rasters into a `Merged_*.tif` mosaic. A typical
chain:

```mermaid
flowchart LR
    A[LiDAR data info] --> B[Ground Classify Using CSF]
    B --> C[Generate DTM]
    B --> D[Normalize LiDAR Data]
    D --> E[Generate CHM or DSM]
    B --> F[Detect Hummock and Hollow]
    E --> G[Surface Water Mapping]
    C --> H[Depth-to-Water]
    G --> H
    C --> I[Seismic Line Disturbance Analysis]
    F --> I
    H --> I
```

The CHM can also be the CHM raster input of the mapping tools above, for example in a GUI pipeline.

## Failure points to monitor

| Failure signal | Likely cause | Pipeline stage | Mitigation |
|---|---|---|---|
| Invalid or empty geometries in seed inputs | Corrupt source features, unintended clipping, or null geometries | Preprocessing and validation | Run seed line QA first; filter invalid/null geometries before execution |
| CRS mismatch or geographic CRS used for meter-based operations | Mixed layer CRS or unprojected data in distance/area workflows | Preprocessing and validation | Reproject all layers to a suitable projected CRS before running tools |
| Most features removed unexpectedly | Over-aggressive thresholds/filters | Core algorithm execution | Revisit parameter thresholds and test with a smaller AOI for calibration |
| Missing raster coverage for clipping/corridor steps | AOI extends beyond raster bounds or wrong raster source | Preprocessing and validation / Core algorithm execution | Verify raster extent and alignment with vector AOI before processing |
| Error finding R, or rpy2 fails to import (PC2Products tools) | R not installed in the environment, or `R_HOME` points elsewhere | Preprocessing and validation | See [How R is located](../tool_behaviour.md#how-r-is-located); run from an activated environment |
| `R packages could not be installed` | No internet access, or missing system libraries on Linux | Preprocessing and validation | Run `tests/test_r_environment.py`; install the GDAL/GEOS/PROJ/udunits development libraries |
| Hummock/hollow stops without output, or a CHM comes out as a DSM | Input not ground-classified, or not height-normalized | Core algorithm execution | Run Ground Classify Using CSF, then Normalize LiDAR Data; check with LiDAR data info |
| Out of memory or very slow LiDAR processing | Too many R workers for a small cell size | Core algorithm execution | Lower `processes`; the TIN and kriging DTM tools already halve the workers below a 1 m cell size |
| Missing CRS reported as `Unknown` | LAS files without a CRS | Preprocessing and validation | Assign the CRS to the LAS files before processing |

See also: [Tool Runtime Model](tool_runtime_model.md)
