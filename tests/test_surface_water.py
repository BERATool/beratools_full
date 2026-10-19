"""Integration tests for Surface Water Mapping (needs R)."""

import csv
from pathlib import Path

import numpy as np
import pytest
import rasterio

from synthetic_data import (
    SURFACE_WATER_POOL,
    SURFACE_WATER_SHADOW,
    SURFACE_WATER_SPECK,
    SURFACE_WATER_UNDER_TREE,
)
from beratools.tools.rpy_surface_water import rpy_surface_water


def _area_values(src, area):
    """Values of the cells whose centres fall inside area (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = area
    half = src.res[0] / 2
    row0, col0 = src.index(xmin + half, ymax - half)
    row1, col1 = src.index(xmax - half, ymin + half)
    return src.read(1)[row0:row1 + 1, col0:col1 + 1]


def test_surface_water_with_chm(surface_water_data, tmp_path):
    out = tmp_path / "water"
    rpy_surface_water(
        in_ortho=surface_water_data["ortho"],
        in_training=f"{surface_water_data['training']}|training",
        in_chm=surface_water_data["chm"],
        out_folder=out.as_posix(),
        points_per_polygon=20,
    )

    with rasterio.open(out / "surface_water.tif") as src:
        assert np.all(_area_values(src, SURFACE_WATER_POOL) == 1)
        assert np.all(_area_values(src, SURFACE_WATER_UNDER_TREE) == 0)
        assert np.all(_area_values(src, SURFACE_WATER_SHADOW) == 0)
        assert np.all(_area_values(src, SURFACE_WATER_SPECK) == 0)
        # Only the 10 x 10 m pool is water: 100 m2 of a 1600 m2 scene
        assert src.read(1).mean() == pytest.approx(100 / 1600)

    with open(out / "cv_accuracy.csv", newline="", encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert int(row["n_points"]) == 120  # 6 polygons x 20 points
    assert float(row["cv_overall_accuracy"]) >= 0.95
    for name in ("cv_confusion_matrix.csv", "training_points.gpkg", "decision_tree.txt"):
        assert (out / name).is_file()


def test_surface_water_without_chm_keeps_water_under_canopy(surface_water_data, tmp_path):
    out = tmp_path / "water"
    rpy_surface_water(
        in_ortho=surface_water_data["ortho"],
        in_training=f"{surface_water_data['training']}|training",
        out_folder=out.as_posix(),
        points_per_polygon=20,
        min_patch_area=0,
    )

    with rasterio.open(Path(out, "surface_water.tif")) as src:
        assert np.all(_area_values(src, SURFACE_WATER_UNDER_TREE) == 1)
        # With min_patch_area = 0 the one-cell speck is kept
        assert np.all(_area_values(src, SURFACE_WATER_SPECK) == 1)
