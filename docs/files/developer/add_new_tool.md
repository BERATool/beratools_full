# How to Add a New Tool

This page focuses on the **practical contributor workflow** for adding a new tool.

For runtime internals (CLI/GUI call modes, argument composition, multiprocessing), see:
- [Tool Runtime Model](../technical/architecture/tool_runtime_model.md)

## 1) Create the tool script

Add a new script in `beratools/tools` (you can start from `tool_template.py`).

Typical API pattern:

```python
def my_tool(..., processes=0, call_mode=CallMode.CLI, log_level="INFO"):
    ...
```

Add `__main__` entrypoint:

```python
if __name__ == "__main__":
    from beratools.utility.tool_args import compose_tool_kwargs
    kwargs = compose_tool_kwargs("my_tool")
    my_tool(**kwargs)
```

## 2) Register in GUI metadata

Update `beratools/gui/assets/beratools.json` and add your tool definition in the proper category.

At minimum, define:

- `name`, `info`, `tool_type`, `tool_api`, `icon`, `tech_link`
- parameter list (`variable`, `label`, `description`, `type`, `subtype`, `default`, `output`, `optional`)

`tool_api` must match the module name and the string passed to `compose_tool_kwargs`, or the tool
stops with `Tool API '<name>' not found in beratools.json`.

### Field parameters

A `text` parameter that names a field of a vector input can show that layer's fields in a
drop-down. Add `field_of` with the `variable` of the vector input; add `"field_check": "year"` to
also check that the field holds years:

```json
{
  "variable": "year_field",
  "field_of": "in_line",
  "field_check": "year",
  "type": "text",
  "subtype": "string",
  ...
}
```

The list refreshes when the input file or layer changes, and a name can still be typed. A field that
isn't in the layer, or a year field with no years between 1900 and the current year, blocks **Run**;
a year field with some empty or invalid values shows a warning. The command line still takes the
field as text.

### Taking part in pipelines

Every registered `python` tool can be a step in a GUI pipeline. To let its inputs be linked to an
earlier step's output, tag the parameters with a *kind*:

- an input parameter gets `"accepts": "<kind>"`;
- an output parameter gets `"produces": {"<kind>": [patterns]}`. An empty list means the output value
  itself (an output file such as `lines.gpkg|centerline`, or a folder of point clouds); otherwise the
  pipeline uses the first glob pattern that matches files in the output folder, newest file first.

```json
{"variable": "in_chm", "accepts": "chm", ...}
{"variable": "out_line", "produces": {"line": []}, ...}
{"variable": "out_folder", "produces": {"dtm": ["Merged_*_DTM.tif", "*_DTM.tif"]}, ...}
```

The kinds in use are `line`, `footprint`, `chm`, `las`, `dtm`, `dsm`, `microform`, `water` and
`dtw`; add a new one when a tool writes something new. `tests/test_pipeline.py` checks that every
accepted kind has a producer. For the pipeline to stop when your tool fails, exit with a non-zero
code (`sys.exit(1)` or an uncaught exception), not a plain `exit()`.

### Adding the CLI subcommand

In `beratools/cli/entry.py`, add a short alias to `TOOL_ALIASES` (for example
`"my_tool": "my_tool"`) and teach `_resolve_tool_function` to import and return the tool function.

## 3) Keep tools thin; move heavy logic to core

- Put high-level tool wiring in `beratools/tools/*`
- Put algorithm-heavy logic in `beratools/core/*`

This keeps code easier to test and maintain.

## 4) Test from CLI first

Run help and a sample execution before validating in GUI:

```bash
python beratools/tools/my_tool.py --help
```

Then test via GUI once CLI behavior is stable.

## 5) Add docs and tests

- Add/update user docs if end-user behavior changed
- Add/update technical docs for algorithm/runtime internals
- Add tests in `tests/` for new behavior and edge cases

## 6) Submit PR

- Follow branching and contribution guidance in [Development](development.md)
- Request review and ensure CI passes

## Adding a PC2Products (R) tool

A PC2Products tool is a thin Python wrapper that validates its inputs and calls an R function through
rpy2. The steps above still apply; these are the differences.

### Write the R function

Add the processing function to `beratools/tools/r_scripts_collection.r`. Follow the existing
functions: read the input folder as a lidR `LAScatalog`, drop noise with `filter = "-drop_class 7"`,
use `future::plan(multisession)` with the worker count passed in from Python, and call
`mosaic_catalog_outputs` to merge tiled raster outputs.

```r
my_function <- function(in_las_folder, out_folder, rprocesses) {
    ...
}
```

### Create the Python wrapper

Add `beratools/tools/rpy_my_tool.py`. `configure_r_environment()` must run **before** `r_common` is
imported, because it sets up `R_HOME` and the DLL search path that rpy2 needs.
`rpy_find_cellsize.py` is the smallest complete example.

```python
import os

from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


def rpy_my_tool(in_las_folder, out_folder, processes=0, **kwargs):
    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    r_common.check_r_packages_installation(["lidR", "rlas", "future", "terra"])

    rprocesses = r_common.r_processes(processes)

    r_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r_scripts_collection.r")
    r_common.r["source"](r_script)
    r_common.robjects.globalenv["my_function"](in_las_folder, out_folder, rprocesses)


if __name__ == "__main__":
    kwargs = compose_tool_kwargs("rpy_my_tool")
    rpy_my_tool(**kwargs)
```

`check_r_packages_installation` installs any missing R packages from CRAN the first time the tool
runs, so list every package the R function uses.

### Register, document and test it

- Add the tool to the `PC2Products` category of `beratools.json`.
- Add a page under `docs/files/user/`, add it to the PC2Products section of `nav` in
  `docs/mkdocs.yml`, add the module to `docs/files/api.md`, and add a row to the tool table in
  `docs/files/technical/pc2products_overview.md`.
- `tests/test_cli_entry.py` checks every R alias against `beratools.json`, so add the new alias to
  `R_ALIASES` there. Add a case to `tests/test_r_tools.py` that runs on the sample tiles in
  `tests/data/LiDAR/`.
