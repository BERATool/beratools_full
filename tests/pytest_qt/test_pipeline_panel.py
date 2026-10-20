"""
Pipeline panel tests using pytest-qt.

Tests dragging tools into the pipeline, linking, reordering, editing a step in the tool form,
saving/loading, and running the steps one after another.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt5 import QtCore, QtWidgets

from beratools.gui.pipeline_panel import tool_name_from_mime

pytestmark = pytest.mark.gui_qt

CSF = "Ground Classify Using CSF"
DTM = "Generate DTM from LiDAR Data"
INFO = "LiDAR data info"
NORM = "Normalize LiDAR Data"
HH = "Detect Hummock and Hollow from LiDAR Data"
SEISMIC = "Seismic Line Disturbance Analysis"


@pytest.fixture
def panel(main_window):
    main_window.left_tabs.setCurrentWidget(main_window.pipeline_panel)
    return main_window.pipeline_panel


def _labels(panel):
    return [panel.list_widget.item(i).text() for i in range(panel.list_widget.count())]


def test_tool_tree_drag_carries_tool_name(main_window):
    tree = main_window.tree_view
    index = tree.tags_model.mapFromSource(tree.get_tool_index(DTM))
    mime = tree.tags_model.mimeData([index])
    assert tool_name_from_mime(mime) == DTM


def test_added_lidar_tool_links_to_classification(panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.add_tool(INFO)

    assert _labels(panel) == [f"1. {CSF}", f"2. {DTM}   \u2190 step 1", f"3. {INFO}   \u2190 step 1"]
    assert panel.steps[1]["links"] == {"in_las_folder": panel.steps[0]["id"]}


def test_raster_inputs_link_to_matching_steps(panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.add_tool(HH)
    panel.add_tool(SEISMIC)

    csf, dtm, hh, seismic = panel.steps
    assert seismic["links"] == {"in_dtm": dtm["id"], "in_microform": hh["id"]}
    assert _labels(panel)[3] == f"4. {SEISMIC}   \u2190 steps 2, 3"
    # only steps that produce a DTM are offered for in_dtm
    combo = panel.link_combos["in_dtm"]
    assert [combo.itemData(i) for i in range(combo.count())] == [None, dtm["id"]]
    assert set(panel.link_combos) == {"in_dtm", "in_microform", "in_dtw"}


def test_category_drop_is_ignored(panel):
    panel.add_tool("PC2Products")
    assert panel.steps == []


def test_move_and_remove_steps(panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.add_tool(INFO)

    panel.move_step(2, 0)
    assert [s["tool_api"] for s in panel.steps] == ["rpy_las_info", "rpy_gnd_csf", "rpy_dtm_by"]

    panel.list_widget.setCurrentRow(1)
    panel.remove_step()
    assert [s["tool_api"] for s in panel.steps] == ["rpy_las_info", "rpy_dtm_by"]
    # links to the removed step are dropped
    assert all(s["links"] == {} for s in panel.steps)


def test_remove_relinks_to_earlier_step(panel):
    panel.add_tool(CSF)
    panel.add_tool(NORM)
    panel.add_tool(DTM)
    assert panel.steps[2]["links"] == {"in_las_folder": panel.steps[1]["id"]}

    panel.list_widget.setCurrentRow(1)
    panel.remove_step()
    assert panel.steps[1]["links"] == {"in_las_folder": panel.steps[0]["id"]}


def test_insert_and_move_relink_steps(panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.add_tool(INFO, row=1)  # doesn't produce LiDAR, so DTM still reads CSF
    csf, info, dtm = panel.steps
    assert dtm["links"] == {"in_las_folder": csf["id"]}

    panel.add_tool(NORM, row=1)  # DTM now reads the normalized tiles
    norm = panel.steps[1]
    assert norm["links"] == {"in_las_folder": csf["id"]}
    assert info["links"] == dtm["links"] == {"in_las_folder": norm["id"]}

    panel.move_step(1, 4)  # normalize last: the others read CSF again
    assert [s["tool_api"] for s in panel.steps] == ["rpy_gnd_csf", "rpy_las_info", "rpy_dtm_by", "rpy_normalized_PC"]
    assert info["links"] == dtm["links"] == norm["links"] == {"in_las_folder": csf["id"]}


def test_link_combo_unlinks_step(panel, qtbot):
    panel.add_tool(CSF)
    panel.add_tool(DTM)

    combo = panel.link_combos["in_las_folder"]
    assert combo.currentData() == panel.steps[0]["id"]
    panel.link_changed("in_las_folder", combo.findData(None))
    assert panel.steps[1]["links"] == {}
    qtbot.waitUntil(lambda: _labels(panel)[1] == f"2. {DTM}")


def test_selected_step_edits_are_stored(main_window, panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.steps[0]["args"]["out_folder"] = "D:/classified"
    panel.list_widget.setCurrentRow(0)
    panel.list_widget.setCurrentRow(1)

    assert main_window.pipeline_step is panel.steps[1]
    assert main_window.btn_layout_top.itemAt(0).widget().text() == f"Step 2: {DTM}"
    in_widget = main_window.tool_widget.widgets_by_variable["in_las_folder"]
    assert not in_widget.isEnabled()
    assert in_widget.in_file.placeholderText() == "D:/classified"

    main_window.tool_widget.widgets_by_variable["out_folder"].in_file.setText("D:/rasters")
    assert panel.steps[1]["args"]["out_folder"] == "D:/rasters"

    # choosing a tool from the tree stops editing the step
    main_window.set_tool(INFO)
    assert main_window.pipeline_step is None
    assert panel.steps[1]["args"]["out_folder"] == "D:/rasters"


def test_linked_raster_input_shows_file_pattern(main_window, panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.add_tool(HH)
    panel.add_tool(SEISMIC)
    panel.steps[1]["args"]["out_folder"] = "D:/rasters"
    panel.list_widget.setCurrentRow(0)
    panel.list_widget.setCurrentRow(3)

    dtm_widget = main_window.tool_widget.widgets_by_variable["in_dtm"]
    assert not dtm_widget.isEnabled()
    assert dtm_widget.in_file.placeholderText() == "D:/rasters/Merged_*_DTM.tif"
    assert main_window.tool_widget.widgets_by_variable["in_dtw"].isEnabled()


def test_save_and_load(panel, tmp_path):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    path = (tmp_path / "p.json").as_posix()

    with patch("PyQt5.QtWidgets.QFileDialog.getSaveFileName", return_value=(path, "")):
        panel.save()
    saved = [dict(s) for s in panel.steps]

    panel.steps = []
    with patch("PyQt5.QtWidgets.QFileDialog.getOpenFileName", return_value=(path, "")):
        panel.load()
    assert panel.steps == saved
    assert panel.list_widget.currentRow() == 0


def test_clear_asks_first(panel):
    panel.add_tool(CSF)
    no = QtWidgets.QMessageBox.StandardButton.No
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=no):
        panel.clear_steps()
    assert len(panel.steps) == 1

    yes = QtWidgets.QMessageBox.StandardButton.Yes
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=yes):
        panel.clear_steps()
    assert panel.steps == []


def test_invalid_pipeline_is_not_run(main_window, panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.steps[0]["args"]["out_folder"] = ""

    with patch("PyQt5.QtWidgets.QMessageBox.warning") as mock_warning, \
            patch.object(main_window, "_launch_tool") as mock_launch:
        main_window.run_pipeline()
    assert "no 'out_folder' set" in mock_warning.call_args[0][2]
    mock_launch.assert_not_called()


def _finish(main_window, exit_code):
    process = MagicMock()
    process.readAllStandardOutput.return_value = b""
    process.readAllStandardError.return_value = b""
    process.exitStatus.return_value = QtCore.QProcess.NormalExit
    process.exitCode.return_value = exit_code
    main_window.process = process
    main_window.process_finished()


def test_pipeline_runs_steps_in_order(main_window, panel, qtbot):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.steps[0]["args"].update(in_las_folder="D:/las", out_folder="D:/classified")
    panel.steps[1]["args"]["out_folder"] = "D:/rasters"

    with patch.object(main_window, "_launch_tool") as mock_launch:
        main_window.run_pipeline()
        assert mock_launch.call_count == 1
        assert mock_launch.call_args[0][1] == "rpy_gnd_csf"
        assert not panel.btn_run.isEnabled()

        _finish(main_window, 0)
        qtbot.waitUntil(lambda: mock_launch.call_count == 2, timeout=2000)
        assert mock_launch.call_args[0][1] == "rpy_dtm_by"
        assert mock_launch.call_args[0][2]["in_las_folder"] == "D:/classified"

        _finish(main_window, 0)

    assert main_window.pipeline_run is None
    assert panel.btn_run.isEnabled()
    assert "Pipeline completed." in main_window.text_edit.toPlainText()


def test_pipeline_stops_when_a_step_fails(main_window, panel):
    panel.add_tool(CSF)
    panel.add_tool(DTM)
    panel.steps[0]["args"]["out_folder"] = "D:/classified"

    with patch.object(main_window, "_launch_tool") as mock_launch:
        main_window.run_pipeline()
        _finish(main_window, 1)

    assert mock_launch.call_count == 1
    assert main_window.pipeline_run is None
    assert "Pipeline stopped: step 1 failed." in main_window.text_edit.toPlainText()


def test_pipeline_stops_when_linked_file_is_missing(main_window, panel, qtbot, tmp_path):
    panel.add_tool(DTM)
    panel.add_tool("Depth-to-Water from Surface Water")
    panel.steps[0]["args"].update(in_las_folder="D:/las", out_folder=(tmp_path / "empty").as_posix())

    with patch.object(main_window, "_launch_tool") as mock_launch:
        main_window.run_pipeline()
        _finish(main_window, 0)
        qtbot.waitUntil(lambda: main_window.pipeline_run is None, timeout=2000)

    assert mock_launch.call_count == 1
    assert "Pipeline stopped before step 2: Step 1 wrote no file matching" in main_window.text_edit.toPlainText()
