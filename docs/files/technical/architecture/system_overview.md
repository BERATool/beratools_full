# System Overview

BERA Tools is organized into clear layers:

- `beratools/tools`: thin tool entry points (CLI/GUI-facing), including the PC2Products LiDAR tools
  (`rpy_*.py`) and their R processing (`r_scripts_collection.r`)
- `beratools/core`: core algorithms and processing logic, and user-built pipelines (`pipeline.py`)
- `beratools/cli`: the `bt` command
- `beratools/gui`: desktop GUI and parameter widgets
- `beratools/utility`: shared helpers (arguments, environment checks, spatial helpers)

## Design principles

- **Separation of concerns**: tool wrappers stay lightweight; heavy logic remains in core modules.
- **Single source of tool metadata**: GUI and CLI parameter behavior derives from tool configuration.
- **Consistent execution model**: tools support CLI and GUI call modes with shared runtime behaviors.

## Module responsibilities

- `tools/*`: validate/collect inputs, call corresponding core logic, write outputs.
- `core/*`: geometric/raster algorithms, optimization, line processing.
- `tools/rpy_*.py`: validate inputs, check R packages, call the tool's R function through rpy2.
- `tools/r_interface.py`, `tools/r_common.py`: locate R and connect rpy2.
- `core/pipeline.py`: save, load, link and run pipelines of tool steps.
- `cli/*`: the `bt` subcommands, built from tool metadata.
- `gui/*`: exposes tools and parameters for interactive use.

See also: [Execution Pipeline](execution_pipeline.md)
