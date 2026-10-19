# Overview


## Project Layout

There are a number of files for build, test, and continuous integration in the root of the project, but in general, the
project is broken up like so.

```
├── beratools
│   ├── cli
│   ├── core
│   ├── gui
│   ├── tools
│   └── utility
├── docs
│   └── files
├── examples
├── notebooks
├── tests
│   └── data/LiDAR          # sample LAS tiles for the PC2Products tools
```

Directory            | Description
-------------------- | -----------
`beratools/cli`      | The `bt` / `beratools` command (`entry.py`), with one subcommand per tool.
`beratools/core`     | Core algorithms and logic, and user-built pipelines (`pipeline.py`).
`beratools/gui`      | GUI components and assets; `assets/beratools.json` defines every tool and its parameters.
`beratools/tools`    | Tool implementations, including the PC2Products tools: a Python wrapper per tool (`rpy_*.py`), the R functions they call (`r_scripts_collection.r`), and the R helpers (`r_interface.py`, `r_common.py`).
`beratools/utility`  | Argument composition (`tool_args.py`), environment checks and spatial helpers.
`examples`           | Example workflows, including `pc2products_pipeline.py`.
`docs/files/developer`   | Developer documentation.
`notebooks`          | Example notebooks and configs.
`tests`              | Unit and integration tests.