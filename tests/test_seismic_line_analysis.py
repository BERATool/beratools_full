"""Integration tests for Seismic Line Disturbance Analysis (needs R)."""

import csv
from pathlib import Path

import pytest

from synthetic_data import SEISMIC_LINE_EXPECTED
from beratools.tools.rpy_seismic_line_analysis import rpy_seismic_line_analysis


def _class_means(summary_csv):
    with open(summary_csv, newline="", encoding="utf-8") as f:
        return {row["Class"]: row for row in csv.DictReader(f)}


def test_seismic_line_analysis_with_dtw(seismic_line_data, tmp_path):
    out = tmp_path / "analysis"
    rpy_seismic_line_analysis(
        in_segments=f"{seismic_line_data['segments']}|segments",
        in_dtm=seismic_line_data["dtm"],
        in_microform=seismic_line_data["microform"],
        in_dtw=seismic_line_data["dtw"],
        out_folder=out.as_posix(),
    )

    for metric, expected in SEISMIC_LINE_EXPECTED.items():
        rows = _class_means(out / "tables" / f"{metric}_deviation_summary.csv")
        for cls, mean in expected.items():
            assert float(rows[cls]["mean"]) == pytest.approx(mean, abs=1e-5), (metric, cls)
            assert int(rows[cls]["n"]) == 4
        for name in (f"{metric}_kruskal_wilcoxon.csv", f"{metric}_brown_forsythe.csv"):
            assert (out / "tables" / name).is_file()
        assert (out / "plots" / f"{metric}_violin.png").is_file()

    for name in ("microform_barplot.png", "surfacewater_barplot.png"):
        assert (out / "plots" / name).is_file()


def test_seismic_line_analysis_without_dtw_skips_water(seismic_line_data, tmp_path):
    out = tmp_path / "analysis"
    rpy_seismic_line_analysis(
        in_segments=f"{seismic_line_data['segments']}|segments",
        in_dtm=seismic_line_data["dtm"],
        in_microform=seismic_line_data["microform"],
        out_folder=out.as_posix(),
    )

    tables = {p.name for p in Path(out, "tables").iterdir()}
    assert "dtm_deviation_summary.csv" in tables
    assert "hummock_deviation_summary.csv" in tables
    assert not any(name.startswith(("dtw_", "surfacewater_")) for name in tables)
    assert "class_surfacewater_proportions.csv" not in tables
