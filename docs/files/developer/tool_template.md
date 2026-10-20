# Tool Template (Reference)

This page remains as a reference pointer for historical links and the sample `tool_template.py` workflow.

## Recommended reading

- Contributor workflow: [How to Add a New Tool](add_new_tool.md)
- Runtime internals: [Tool Runtime Model](../technical/architecture/tool_runtime_model.md)

## Minimal template recap

`tool_template.py` demonstrates:

- a standard tool API pattern with framework args (`processes`, `call_mode`, `log_level`)
- metadata-driven argument composition via `compose_tool_kwargs`
- optional multiprocessing through `execute_multiprocessing`
- separation of lightweight tool wrappers from heavy core logic

## PC2Products (R) tools

`beratools/tools/rpy_find_cellsize.py` is the smallest complete PC2Products tool. It shows:

- calling `configure_r_environment()` before importing `r_common`
- checking the inputs and installing the R packages the tool needs
- converting `processes` to an R worker count with `r_common.r_processes`
- sourcing `r_scripts_collection.r` and calling an R function from `robjects.globalenv`
- metadata-driven argument composition via `compose_tool_kwargs`

## Where to place content

- Put contributor step-by-step instructions in `developer/add_new_tool.md`
- Put architecture/runtime mechanics in `technical/architecture/tool_runtime_model.md`

