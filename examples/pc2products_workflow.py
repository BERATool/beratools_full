"""
Provide a full workflow that turns LiDAR tiles into DTM, CHM/DSM and hummock/hollow rasters.

Usage:
    python examples/pc2products_workflow.py [processes=4] [steps_to_run=[las_info,cellsize,gnd_csf,dtm,chm_dsm,hh]]
"""

import os
import sys
from pathlib import Path

sys.path.append(Path(__file__).resolve().parents[1].as_posix())

import hydra
from beratools.tools.rpy_dtm_by import rpy_dtm
from beratools.tools.rpy_CHM_DSM_by import rpy_chm_dsm_by
from beratools.tools.rpy_las_info import rpy_las_info
from beratools.tools.rpy_PC2hummock_hollow import rpy_hh2raster
from beratools.tools.rpy_gnd_csf import rpy_gnd_csf
from beratools.tools.rpy_find_cellsize import rpy_find_cellsize

from omegaconf import OmegaConf

# Steps run in this order; each one reads its arguments from args_<step> in pc2products_config.yaml.
STEPS = {
    "las_info": ("Running LiDAR data info", rpy_las_info),
    "cellsize": ("Running raster cell size", rpy_find_cellsize),
    "gnd_csf": ("Running CSF ground classification", rpy_gnd_csf),
    "dtm": ("Running DTM", rpy_dtm),
    "chm_dsm": ("Running CHM/DSM", rpy_chm_dsm_by),
    "hh": ("Running hummock and hollow", rpy_hh2raster),
}


def print_message(msg):
    print("\n" + "-" * 50)
    print(msg)
    print("-" * 50)


@hydra.main(version_base=None, config_path=".", config_name="pc2products_config")
def main(cfg):
    print_message("Loaded configuration")
    print(OmegaConf.to_yaml(cfg, resolve=True))

    processes = int(cfg.processes) if cfg.processes else os.cpu_count()
    print(f"Processes: {processes}")

    steps_to_run = set(cfg.steps_to_run) if "steps_to_run" in cfg else set()
    unknown_steps = steps_to_run - STEPS.keys()
    if unknown_steps:
        raise ValueError(f"Unknown steps {sorted(unknown_steps)}; choose from {list(STEPS)}")

    for step, (message, tool) in STEPS.items():
        if step in steps_to_run:
            print_message(message)
            args = dict(cfg[f"args_{step}"])
            args["processes"] = processes
            tool(**args)

    print_message("Workflow completed successfully!")


if __name__ == "__main__":
    main()
