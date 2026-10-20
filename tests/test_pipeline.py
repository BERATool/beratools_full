"""Tests for user-built pipelines (beratools.core.pipeline); no R needed."""

import json
import os
import subprocess

import pytest

from beratools.core import pipeline


def _steps(tmp_path=None):
    rasters = (tmp_path / "rasters").as_posix() if tmp_path else "rasters"
    csf = pipeline.new_step("rpy_gnd_csf", {"in_las_folder": "las", "out_folder": "classified"})
    dtm = pipeline.new_step(
        "rpy_dtm_by", {"in_las_folder": "", "out_folder": rasters}, links={"in_las_folder": csf["id"]}
    )
    return [csf, dtm]


def test_link_kinds_come_from_beratools_json():
    assert pipeline.linkable_inputs("rpy_dtm_by") == {"in_las_folder": "las"}
    assert pipeline.linkable_inputs("rpy_seismic_line_analysis") == {
        "in_dtm": "dtm", "in_microform": "microform", "in_dtw": "dtw"
    }
    assert pipeline.produced_kinds("rpy_gnd_csf") == {"las": ("out_folder", [])}
    assert set(pipeline.produced_kinds("rpy_CHM_DSM_by")) == {"chm", "dsm"}
    assert pipeline.produced_kinds("rpy_las_info") == {}


def test_every_accepted_kind_has_a_producer():
    tools = pipeline._tool_params()
    produced = {kind for api in tools for kind in pipeline.produced_kinds(api)}
    accepted = {kind for api in tools for kind in pipeline.linkable_inputs(api).values()}
    assert accepted <= produced


def test_folder_link_resolves_to_output_folder():
    steps = _steps()
    assert pipeline.resolve_step_args(steps, 1) == {"in_las_folder": "classified", "out_folder": "rasters"}
    # resolving doesn't change the stored step
    assert steps[1]["args"]["in_las_folder"] == ""


def test_file_link_picks_first_matching_pattern_newest_first(tmp_path):
    csf, dtm = _steps(tmp_path)
    dtw = pipeline.new_step("rpy_dtw", {"out_folder": "dtw_out"}, links={"in_dtm": dtm["id"]})
    steps = [csf, dtm, dtw]

    with pytest.raises(FileNotFoundError, match="Step 2 wrote no file matching"):
        pipeline.resolve_step_args(steps, 2)

    rasters = tmp_path / "rasters"
    rasters.mkdir()
    (rasters / "tile_TIN_DTM.tif").write_text("")
    (rasters / "Merged_TIN_DSM.tif").write_text("")
    assert pipeline.resolve_step_args(steps, 2)["in_dtm"] == (rasters / "tile_TIN_DTM.tif").as_posix()

    old, new = rasters / "Merged_TIN_DTM.tif", rasters / "Merged_K_DTM.tif"
    old.write_text("")
    new.write_text("")
    os.utime(old, (1, 1))
    assert pipeline.resolve_step_args(steps, 2)["in_dtm"] == new.as_posix()

    assert pipeline.describe_link(steps, dtw, "in_dtm") == f"{rasters.as_posix()}/Merged_*_DTM.tif"


def test_default_links_pick_latest_matching_step():
    csf = pipeline.new_step("rpy_gnd_csf")
    dtm = pipeline.new_step("rpy_dtm_by")
    norm = pipeline.new_step("rpy_normalized_PC")
    hh = pipeline.new_step("rpy_PC2hummock_hollow")
    assert pipeline.default_links([csf, dtm], "rpy_dtm_by") == {"in_las_folder": csf["id"]}
    assert pipeline.default_links([csf, norm, dtm], "rpy_CHM_DSM_by") == {"in_las_folder": norm["id"]}
    assert pipeline.default_links([dtm], "rpy_las_info") == {}
    assert pipeline.default_links([csf, dtm, hh], "rpy_seismic_line_analysis") == {
        "in_dtm": dtm["id"], "in_microform": hh["id"]
    }


def test_mapping_tools_link_to_lines_footprints_and_lidar_chm(tmp_path):
    chm = pipeline.new_step("rpy_CHM_DSM_by", {"in_las_folder": "las", "out_folder": tmp_path.as_posix()})
    seeds = pipeline.new_step("check_seed_line", {"out_line": "lines.gpkg|seed_lines_checked"})
    centerline = pipeline.new_step("centerline", {"out_line": "lines.gpkg|centerline"})
    footprint = pipeline.new_step("canopy_footprint_absolute", {"out_footprint": "lines.gpkg|footprint"})

    assert pipeline.default_links([chm], "check_seed_line") == {"in_raster": chm["id"]}
    assert pipeline.default_links([chm, seeds], "centerline") == {"in_line": seeds["id"], "in_raster": chm["id"]}
    assert pipeline.default_links([chm, seeds, centerline], "canopy_footprint_absolute") == {
        "in_line": centerline["id"], "in_chm": chm["id"]
    }
    assert pipeline.default_links([chm, seeds, centerline, footprint], "ground_footprint") == {
        "in_line": centerline["id"], "in_footprint": footprint["id"]
    }

    # a vector output is passed on as is; a CHM link reads the CHM raster in the output folder
    (tmp_path / "Merged_TIN_CHM.tif").write_text("")
    steps = [chm, seeds, centerline]
    pipeline.relink(steps)
    args = pipeline.resolve_step_args(steps, 2)
    assert args["in_line"] == "lines.gpkg|seed_lines_checked"
    assert args["in_raster"] == (tmp_path / "Merged_TIN_CHM.tif").as_posix()


def test_relink_follows_step_order():
    csf = pipeline.new_step("rpy_gnd_csf")
    chm = pipeline.new_step("rpy_CHM_DSM_by", links={"in_las_folder": csf["id"]})
    norm = pipeline.new_step("rpy_normalized_PC")
    pipeline.relink([csf, norm, chm])
    assert csf["links"] == {}
    assert norm["links"] == {"in_las_folder": csf["id"]}
    assert chm["links"] == {"in_las_folder": norm["id"]}

    pipeline.relink([chm, csf, norm])
    assert chm["links"] == {}
    assert norm["links"] == {"in_las_folder": csf["id"]}


def test_validate_pipeline_reports_bad_links():
    assert pipeline.validate_pipeline([]) == ["The pipeline has no steps."]
    assert pipeline.validate_pipeline(_steps()) == []

    csf, dtm = _steps()
    assert "runs after it" in pipeline.validate_pipeline([dtm, csf])[0]
    assert "no longer exists" in pipeline.validate_pipeline([dtm])[0]

    csf["args"]["out_folder"] = ""
    assert "no 'out_folder' set" in pipeline.validate_pipeline([csf, dtm])[0]

    csf, dtm = _steps()
    dtm["links"] = {"out_folder": csf["id"]}
    assert "can't be linked" in pipeline.validate_pipeline([csf, dtm])[0]

    seismic = pipeline.new_step("rpy_seismic_line_analysis", links={"in_dtm": csf["id"]})
    assert "doesn't produce the dtm" in pipeline.validate_pipeline([csf, seismic])[0]


def test_save_and_load_round_trip(tmp_path):
    steps = _steps()
    path = tmp_path / "my_pipeline.json"
    pipeline.save_pipeline(path, steps)

    assert json.loads(path.read_text())["format"] == pipeline.PIPELINE_FORMAT
    assert pipeline.load_pipeline(path) == steps


def test_load_converts_format_1_links(tmp_path):
    path = tmp_path / "old.json"
    old_steps = [
        {"id": "a", "tool_api": "rpy_gnd_csf", "args": {}, "input_from": None},
        {"id": "b", "tool_api": "rpy_dtm_by", "args": {}, "input_from": "a"},
    ]
    path.write_text(json.dumps({"format": 1, "steps": old_steps}))
    steps = pipeline.load_pipeline(path)
    assert [s["links"] for s in steps] == [{}, {"in_las_folder": "a"}]


def test_load_rejects_unknown_format(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"format": 99, "steps": []}))
    with pytest.raises(ValueError, match="Unsupported pipeline format"):
        pipeline.load_pipeline(path)


def test_tool_command_stringifies_args():
    cmd = pipeline.tool_command("rpy_dtm_by", {"in_las_folder": "las", "cell_size": 0.5}, 4)
    assert cmd[0].endswith("beratools/tools/rpy_dtm_by.py")
    assert json.loads(cmd[2]) == {"in_las_folder": "las", "cell_size": "0.5"}
    assert cmd[3:] == ["-p", "4", "-c", "CLI", "-l", "INFO"]


def test_run_pipeline_runs_steps_in_order_and_stops_on_failure(monkeypatch):
    calls = []

    def fake_run(cmd, env=None):
        calls.append((cmd[1], json.loads(cmd[3])))
        return subprocess.CompletedProcess(cmd, 0 if len(calls) == 1 else 1)

    monkeypatch.setattr(pipeline.subprocess, "run", fake_run)
    steps = _steps() + [pipeline.new_step("rpy_las_info", {"in_las_folder": "las"})]

    with pytest.raises(RuntimeError, match="Step 2"):
        pipeline.run_pipeline(steps)

    assert [c[0].rsplit("/", 1)[1] for c in calls] == ["rpy_gnd_csf.py", "rpy_dtm_by.py"]
    assert calls[1][1]["in_las_folder"] == "classified"
