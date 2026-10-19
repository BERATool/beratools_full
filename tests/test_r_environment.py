"""Verify R environment is available."""

import pytest

# Union of the packages the rpy_* tools check for.
REQUIRED = ["lidR", "RCSF", "rlas", "future", "terra", "sp", "raster", "stars", "sf", "gstat",
            "rpart", "ggplot2"]


def test_r_packages():
    # Start R through r_common so R is located and configured before rpy2 loads it.
    # The environment only provides R; install anything missing the same way the tools do.
    from beratools.tools import r_common

    try:
        r_common.initialize_r()
        from rpy2.robjects.packages import importr
    except Exception as exc:
        pytest.fail(f"rpy2 not available: {exc}")

    r_common.check_r_packages_installation(REQUIRED)

    missing = []

    for pkg in REQUIRED:
        try:
            importr(pkg)
        except Exception:
            missing.append(pkg)

    assert not missing, (
        f"Missing R packages: {', '.join(missing)}"
    )
