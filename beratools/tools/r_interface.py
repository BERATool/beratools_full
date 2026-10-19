"""
Copyright (C) 2025 Applied Geospatial Research Group.

This script is licensed under the GNU General Public License v3.0.
See <https://gnu.org/licenses/gpl-3.0> for full license details.

Author: Maverick Fong

Description:
    This script is helper tools for execute the R scripts.

    Webpage: https://github.com/BERATool/beratools

"""

import os,sys
import shutil
import subprocess
from pathlib import Path


def configure_r_environment():
    """Locate and configure R before importing rpy2."""

    # --------------------------------------------------
    # 1. Existing R_HOME
    # --------------------------------------------------
    r_home = os.environ.get("R_HOME")

    if r_home:
        r_bin = Path(r_home) / "bin"

        if (r_bin / "R.exe").exists() or (r_bin / "R").exists():
            return str(r_home)

    # --------------------------------------------------
    # 2. R on PATH
    # --------------------------------------------------
    r_exe = shutil.which("Rscript") or shutil.which("R")

    if r_exe:
        try:
            # Ask R for its home: on Linux/conda, bin/R is a wrapper script and
            # the real R_HOME is <prefix>/lib/R, not the parent of bin/
            r_home = subprocess.check_output(
                [r_exe, "RHOME"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()

            if r_home:
                os.environ["R_HOME"] = r_home
                return r_home

        except Exception:
            pass

    # --------------------------------------------------
    # 3. Conda / Pixi installed R
    # --------------------------------------------------
    python_exe = Path(sys.executable)
    candidates = [
        # Windows conda/pixi
        python_exe.parent / "Lib" / "R",
    # Linux/macOS conda/pixi
    python_exe.parent.parent / "lib" / "R",
    # Alternate pixi layouts
    Path(sys.prefix) / "lib" / "R",
    Path(sys.prefix) / "Lib" / "R",
    ]
    for candidate in candidates:
        if (
                (candidate / "bin" / "R.exe").exists()
                or
                (candidate / "bin" / "R").exists()
        ):
            os.environ["R_HOME"] = str(candidate)
            return str(candidate)

    # --------------------------------------------------
    # 4. Standard Windows install
    # --------------------------------------------------
    r_root = Path(r"C:\Program Files\R")

    if r_root.exists():
        versions = sorted(r_root.glob("R-*"), reverse=True)

        for version in versions:
            if (version / "bin" / "R.exe").exists():
                os.environ["R_HOME"] = str(version)
                return str(version)
    # --------------------------------------------------
    # 5. Diagnostics
    # --------------------------------------------------
    print("sys.executable =", sys.executable)
    print("sys.prefix =", sys.prefix)
    print("R_HOME =", os.environ.get("R_HOME"))
    print("which R =", shutil.which("R"))
    print("which Rscript =", shutil.which("Rscript"))

    raise RuntimeError(
        "\n"
        "R installation not found.\n\n"
        "Install R from:\n"
        "https://cran.r-project.org/\n\n"
        "Or install in conda:\n"
        "conda install -c conda-forge r-base rpy2\n"
    )


def isolate_env_r_library(r_home):
    """Keep the environment's R from using the user's personal R library.

    R adds the personal library (R_LIBS_USER, e.g. %LOCALAPPDATA%/R/win-library/4.5 on
    Windows) ahead of its own library. For an R installed in the conda/pixi environment,
    that would load packages installed for a separate R and stop the tools from installing
    into the environment. A non-existent R_LIBS_USER is dropped from .libPaths(), leaving
    only the environment's library. A standalone R (outside the environment) is left alone.
    """
    try:
        in_env = Path(r_home).resolve().is_relative_to(Path(sys.prefix).resolve())
    except OSError:
        in_env = False

    if in_env:
        os.environ["R_LIBS_USER"] = "NULL"
        os.environ.pop("R_LIBS", None)

    return in_env


# ------------------------------------------------------
# Configure R BEFORE importing rpy2
# ------------------------------------------------------
R_HOME = configure_r_environment()
R_IN_ENV = isolate_env_r_library(R_HOME)
env_root = Path(sys.executable).parent

conda_r = env_root / "Scripts" / "R.exe"
print("=" * 60)
print("R CONFIGURATION")
print("=" * 60)
print(f"R_HOME      : {os.environ.get('R_HOME')}")
print(f"Conda R.exe : {conda_r}")
print(f"Exists      : {conda_r.exists()}")
print(f"R library   : {'environment only' if R_IN_ENV else 'R defaults (R is outside the environment)'}")
print("=" * 60)


extra_dirs = [
    env_root / "Library" / "bin",
    env_root / "Library" / "mingw-w64" / "bin",
    env_root / "Library" / "usr" / "bin",
    env_root / "Scripts",
    Path(R_HOME) / "bin",
    Path(R_HOME) / "bin" / "x64",
]

for d in extra_dirs:
    if d.exists():
        try:
            os.add_dll_directory(str(d))
        except Exception:
            pass

        os.environ["PATH"] = (
            str(d)
            + os.pathsep
            + os.environ.get("PATH", "")
        )

import os

os.environ["RPY2_CFFI_MODE"] = "ABI"