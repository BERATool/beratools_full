# Code Testing

BERA Tools employs a `pytest` framework to ensure code quality and reliability. This document outlines the testing strategies, tools, and workflows used in the repository.

## Testing Workflows

- **pytest**: Tests use pytest and are located in the `tests` directory. The automated workflows described below run only `tests/test_workflow.py`, not the complete test suite.
- **Automatic integration testing**: The `python-integration-tests.yml` workflow runs `tests/test_workflow.py`, then `tests/test_r_environment.py` and `tests/test_r_workflow.py` for the PC2Products tools, on pushes to `main` and on qualifying pull requests targeting `main` when its configured path filters match.
- **Coverage**: Coverage from `tests/test_workflow.py` is printed in the GitHub Actions job log; it is not uploaded to an external service.
- **Runtime environment**: The automatic integration workflow uses the Pixi-managed Python 3.12/GDAL environment.
- **Manual compatibility testing**: The dispatch-only `python-compatibility-tests.yml` workflow runs `tests/test_workflow.py` through tox in Python 3.12, 3.13, and 3.14 micromamba environments with conda-forge GDAL.

## Running Tests Locally

To run tests locally, follow these steps:

1. Install the required dependencies:

   ```bash
   pip install .[dev]
   ```

2. Run all the test suite using `pytest`:

=== "Run All tests"
    Discover and execute all tests in the `tests` directory.
    ```bash
    pytest
    ```

=== "Run a test file"
    Run a specific test file:
    ```bash
    pytest tests/path/to/test_tools.py
    ```

=== "Run a test function"
    Run a specific test function within a file:
    ```bash
    pytest tests/path/to/test_tools.py::test_function_name
    ```

### PC2Products (R) tests

The PC2Products tools need R (see [Installation](../user/installation.md)). Their sample tiles are in
`tests/data/LiDAR/`; the tools write rasters to `tests/data/LiDAR/Raster_Output/` and point clouds to
`tests/data/LiDAR/Classified_PC/` and `tests/data/LiDAR/Normalized_PC/`, all git-ignored.

| Tests | What they cover | Needs R |
|-------|-----------------|---------|
| `tests/test_r_tools.py` | Runs each LiDAR tool on the sample tiles and checks the output | Yes |
| `tests/test_r_workflow.py` | Runs CSF classification, DTM, DSM, normalization, CHM (from the normalized tiles) and hummock/hollow in sequence, checking each tool's output, then deletes the outputs | Yes |
| `tests/test_r_environment.py` | Installs any missing R packages the tools need, then checks that they load | Yes |
| `tests/test_surface_water.py`, `tests/test_dtw.py`, `tests/test_seismic_line_analysis.py` | Run the raster tools on synthetic inputs with a known answer, built by `tests/synthetic_data.py` | Yes |
| `tests/test_pipeline.py`, `tests/pytest_qt/test_pipeline_panel.py` | Pipeline linking, saving, loading and running, and the Pipeline tab | No |
| `tests/pytest_qt/test_r_tool_forms.py` | GUI forms for each PC2Products tool, and GUI-to-validation round trips | No |

```bash
python -m pytest tests/test_r_tools.py tests/test_r_environment.py -v
```

The first run of the R tests installs the R packages into the environment's R, so it can take a while.

!!! note "Windows: run the R tests from PowerShell or cmd"
    Run the R tests from **PowerShell or cmd, not Git Bash**. Under Git Bash, rpy2's
    `R CMD config` call picks up Git's `sh`, fails, and rpy2 can't start R.

## GitHub Actions

BERA Tools uses GitHub Actions to automate testing and deployment processes. This document describes the various workflows set up in the repository to ensure code quality and streamline releases.

1. **python-compatibility-tests.yml**: This dispatch-only workflow runs `tests/test_workflow.py` through tox under Python 3.12, 3.13, and 3.14 in micromamba environments with conda-forge GDAL and native geospatial libraries.

2. **python-integration-tests.yml**: This automatic workflow runs `tests/test_workflow.py` with terminal coverage on pushes to `main` and qualifying pull requests targeting `main`. It then installs the system GDAL/GEOS/PROJ/udunits libraries and runs `tests/test_r_environment.py`, which installs the R packages into the pixi R, and `tests/test_r_workflow.py`. The job's timeout is 60 minutes to leave room for the R packages.

Refer to the [Maintainer Guide](./maintainer.md#automatic-integration-tests) for more information on these workflows.

## Write Tests

It is required to write tests when contributing to BERA Tools. follow these guidelines to ensure consistency and quality in the test suite.

### conftest.py

The `conftest.py` file in the `tests` directory contains shared fixtures and configurations for the test suite. You can add common setup code here that can be reused across multiple test files.

### Test Organization

Tests are organized in the `tests` directory. Each module or tool should have a corresponding test file. .

### Naming Conventions

Test files should be named with the prefix `test_` which can be detected by pytest automatically. The test file name should be followed by the module or tool name (e.g., `test_tools.py`).

### Writing Tests

When writing tests, use assertions to verify that the code behaves as expected. Utilize fixtures from `conftest.py` for setup and cleanup operations.
