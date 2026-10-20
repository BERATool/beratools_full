"""Integration tests for Depth-to-Water (needs R)."""

import csv

import numpy as np
import pytest
import rasterio

from synthetic_data import DTW_EXCLUDED, DTW_GROUND_HEIGHT, dtw_water_table
from beratools.tools.rpy_dtw import rpy_dtw


def _read(path):
    with rasterio.open(path) as src:
        values = src.read(1, masked=True).astype("float64").filled(np.nan)
        rows, cols = np.indices(values.shape)
        x, y = rasterio.transform.xy(src.transform, rows, cols)
    return values, np.asarray(x).reshape(values.shape), np.asarray(y).reshape(values.shape)


def test_dtw_recovers_water_table(dtw_data, tmp_path):
    out = tmp_path / "dtw"
    rpy_dtw(
        in_dtm=dtw_data["dtm"],
        in_water=dtw_data["water"],
        in_mask=f"{dtw_data['mask']}|exclude",
        out_folder=out.as_posix(),
    )

    with rasterio.open(dtw_data["water"]) as src:
        water = src.read(1) == 1
    dtw, x, y = _read(out / "dtw.tif")
    water_table, _, _ = _read(out / "water_table.tif")

    xmin, ymin, xmax, ymax = DTW_EXCLUDED
    excluded = (x > xmin) & (x < xmax) & (y > ymin) & (y < ymax)
    assert np.all(np.isnan(dtw[excluded]))
    assert np.all(np.isnan(water_table[excluded]))

    kept = ~excluded
    assert np.all(dtw[kept & water] == 0)
    assert np.nanmin(dtw[kept]) >= 0
    # The kriged water table follows the true one closely, so DTW off the pools is ~0.2 m
    assert np.nanmean(np.abs(water_table[kept] - dtw_water_table(x[kept], y[kept]))) < 0.02
    assert np.nanmean(dtw[kept & ~water]) == pytest.approx(DTW_GROUND_HEIGHT, abs=0.02)

    with open(out / "water_table_cv.csv", newline="", encoding="utf-8") as f:
        cv = next(csv.DictReader(f))
    assert int(cv["n_points"]) == 96  # 100 grid cells, 4 inside the excluded corner
    assert float(cv["rmse"]) < 0.05
    for name in ("water_points.gpkg", "variogram_model.csv", "variogram.png"):
        assert (out / name).is_file()


def test_dtw_coarser_kriging_grid(dtw_data, tmp_path):
    out = tmp_path / "dtw"
    rpy_dtw(
        in_dtm=dtw_data["dtm"],
        in_water=dtw_data["water"],
        out_folder=out.as_posix(),
        kriging_cell_size=2.0,
    )

    dtw, x, y = _read(out / "dtw.tif")
    assert not np.isnan(dtw).all()
    # 1% of cells are pools (DTW 0); the rest sit DTW_GROUND_HEIGHT above the water table
    assert np.nanmean(dtw) == pytest.approx(DTW_GROUND_HEIGHT * 0.99, abs=0.03)
