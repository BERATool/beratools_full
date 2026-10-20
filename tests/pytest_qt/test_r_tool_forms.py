"""
Per-tool form fill and round-trip tests using pytest-qt.

For each rpy_* tool in beratools.json: construct ToolWidgets, set all
parameter values programmatically, call get_widgets_arguments(), and verify
the returned dict matches expected values. GUI arguments are then passed
through BTData.validate_tool_params() to check they are converted to the
types the rpy_* scripts expect.
"""

import pytest

from beratools.gui.tool_widgets import (
    BooleanInput,
    FileSelector,
    NumericInput,
    OptionsInput,
)

pytestmark = pytest.mark.gui_qt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_widget_values(tw, values):
    """Set values on ToolWidgets by variable name."""
    for widget in tw.widget_list:
        if widget.variable in values:
            widget.set_value(values[widget.variable])


def _find_widget(tw, variable):
    """Find a widget by its variable name."""
    for w in tw.widget_list:
        if w.variable == variable:
            return w
    return None


def _select_option(widget, text):
    """Select a combobox entry the way a user would."""
    widget.combobox.setCurrentIndex(widget.option_list.index(text))


@pytest.fixture
def las_folder(testdata_dir):
    return str(testdata_dir / "LiDAR")


# ---------------------------------------------------------------------------
# Generate DTM from LiDAR Data (rpy_dtm_by)
# ---------------------------------------------------------------------------


class TestDtm:
    TOOL = "Generate DTM from LiDAR Data"

    def test_widget_types(self, make_tool_widget, btdata):
        tw = make_tool_widget(self.TOOL)
        assert len(tw.widget_list) == len(btdata.get_bera_tool_args(self.TOOL))
        assert isinstance(_find_widget(tw, "in_las_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "out_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "style"), OptionsInput)

    def test_style_options(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        style = _find_widget(tw, "style")
        assert style.option_list == ["tin", "idw", "kriging"]
        assert style.get_value() == {"style": "tin"}

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tmp_path):
        tw = make_tool_widget(self.TOOL)
        _set_widget_values(tw, {"in_las_folder": las_folder, "out_folder": str(tmp_path)})
        _select_option(_find_widget(tw, "style"), "idw")

        args = tw.get_widgets_arguments()
        assert args == {"in_las_folder": las_folder, "out_folder": str(tmp_path), "style": "idw",
                        "cell_size": 0.0}

        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated == args


# ---------------------------------------------------------------------------
# Generate CHM or DSM from LiDAR Data (rpy_CHM_DSM_by)
# ---------------------------------------------------------------------------


class TestChmDsm:
    TOOL = "Generate CHM or DSM from LiDAR Data"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        assert isinstance(_find_widget(tw, "in_las_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "out_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "style"), OptionsInput)

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tmp_path):
        tw = make_tool_widget(self.TOOL)
        _set_widget_values(tw, {"in_las_folder": las_folder, "out_folder": str(tmp_path)})
        _select_option(_find_widget(tw, "style"), "pitfree")

        args = tw.get_widgets_arguments()
        assert args["style"] == "pitfree"
        assert btdata.validate_tool_params(self.TOOL, args)["style"] == "pitfree"

    def test_invalid_style_rejected(self, btdata, las_folder, tmp_path):
        args = {"in_las_folder": las_folder, "out_folder": str(tmp_path), "style": "kriging"}
        with pytest.raises(ValueError, match="style"):
            btdata.validate_tool_params(self.TOOL, args)


# ---------------------------------------------------------------------------
# Normalize LiDAR Data (rpy_normalized_PC)
# ---------------------------------------------------------------------------


class TestNormalize:
    TOOL = "Normalize LiDAR Data"

    def test_widget_types(self, make_tool_widget, btdata):
        tw = make_tool_widget(self.TOOL)
        assert len(tw.widget_list) == len(btdata.get_bera_tool_args(self.TOOL))
        assert isinstance(_find_widget(tw, "in_las_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "out_folder"), FileSelector)
        assert isinstance(_find_widget(tw, "style"), OptionsInput)

    def test_style_options(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        style = _find_widget(tw, "style")
        assert style.option_list == ["tin", "idw", "kriging"]
        assert style.get_value() == {"style": "tin"}

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tmp_path):
        tw = make_tool_widget(self.TOOL)
        _set_widget_values(tw, {"in_las_folder": las_folder, "out_folder": str(tmp_path)})
        _select_option(_find_widget(tw, "style"), "kriging")

        args = tw.get_widgets_arguments()
        assert args == {"in_las_folder": las_folder, "out_folder": str(tmp_path), "style": "kriging"}
        assert btdata.validate_tool_params(self.TOOL, args) == args

    def test_invalid_style_rejected(self, btdata, las_folder, tmp_path):
        args = {"in_las_folder": las_folder, "out_folder": str(tmp_path), "style": "pitfree"}
        with pytest.raises(ValueError, match="style"):
            btdata.validate_tool_params(self.TOOL, args)


# ---------------------------------------------------------------------------
# LiDAR data info (rpy_las_info) / Raster Cell size (rpy_find_cellsize)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["LiDAR data info", "Raster Cell size from LiDAR data"])
class TestFolderOnlyTools:
    def test_single_folder_widget(self, make_tool_widget, tool):
        tw = make_tool_widget(tool)
        assert len(tw.widget_list) == 1
        assert isinstance(_find_widget(tw, "in_las_folder"), FileSelector)

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tool):
        tw = make_tool_widget(tool)
        _set_widget_values(tw, {"in_las_folder": las_folder})

        args = tw.get_widgets_arguments()
        assert args == {"in_las_folder": las_folder}
        assert btdata.validate_tool_params(tool, args) == args

    def test_missing_folder_rejected(self, btdata, tmp_path, tool):
        args = {"in_las_folder": str(tmp_path / "does_not_exist")}
        with pytest.raises(ValueError, match="Directory not found"):
            btdata.validate_tool_params(tool, args)


# ---------------------------------------------------------------------------
# Detect Hummock and Hollow from LiDAR Data (rpy_PC2hummock_hollow)
# ---------------------------------------------------------------------------


class TestHummockHollow:
    TOOL = "Detect Hummock and Hollow from LiDAR Data"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        assert isinstance(_find_widget(tw, "Smooth_by"), OptionsInput)
        assert isinstance(_find_widget(tw, "Min_ws"), NumericInput)
        assert isinstance(_find_widget(tw, "lawn_range"), NumericInput)
        assert isinstance(_find_widget(tw, "cell_size"), NumericInput)

    def test_cell_size_is_advanced_option(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL, show_advanced=False)
        assert _find_widget(tw, "cell_size").isHidden()
        assert not _find_widget(tw, "Min_ws").isHidden()

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tmp_path):
        tw = make_tool_widget(self.TOOL)
        _set_widget_values(
            tw,
            {
                "in_las_folder": las_folder,
                "out_folder": str(tmp_path),
                "Min_ws": 5.0,
                "lawn_range": 0.1,
                "cell_size": 0.5,
            },
        )
        _select_option(_find_widget(tw, "Smooth_by"), "median")

        args = tw.get_widgets_arguments()
        assert args["Smooth_by"] == "median"
        assert args["Min_ws"] == pytest.approx(5.0)
        assert args["lawn_range"] == pytest.approx(0.1)
        assert args["cell_size"] == pytest.approx(0.5)

        validated = btdata.validate_tool_params(self.TOOL, args)
        for key in ("Min_ws", "lawn_range", "cell_size"):
            assert type(validated[key]) is float

    def test_string_numbers_converted(self, btdata, las_folder, tmp_path):
        args = {
            "in_las_folder": las_folder,
            "out_folder": str(tmp_path),
            "Smooth_by": "mean",
            "Min_ws": "3",
            "lawn_range": "0.3",
            "cell_size": "0",
        }
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["Min_ws"] == 3.0 and type(validated["Min_ws"]) is float
        assert validated["lawn_range"] == pytest.approx(0.3)
        assert validated["cell_size"] == 0.0 and type(validated["cell_size"]) is float


# ---------------------------------------------------------------------------
# Ground Classify Using CSF (rpy_gnd_csf)
# ---------------------------------------------------------------------------


class TestGroundCsf:
    TOOL = "Ground Classify Using CSF"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        assert isinstance(_find_widget(tw, "slope"), BooleanInput)
        assert isinstance(_find_widget(tw, "class_threshold"), NumericInput)
        assert isinstance(_find_widget(tw, "cloth_resolution"), NumericInput)
        assert isinstance(_find_widget(tw, "rigidness"), OptionsInput)

    def test_optional_params_hidden_when_advanced_off(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL, show_advanced=False)
        for variable in ("slope", "class_threshold", "cloth_resolution", "rigidness"):
            assert _find_widget(tw, variable).isHidden()

    def test_toggle_slope(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        w = _find_widget(tw, "slope")
        w.set_value(True)
        assert w.get_value() == {"slope": True}
        w.set_value(False)
        assert w.get_value() == {"slope": False}

    def test_round_trip(self, make_tool_widget, btdata, las_folder, tmp_path):
        tw = make_tool_widget(self.TOOL)
        _set_widget_values(
            tw,
            {
                "in_las_folder": las_folder,
                "out_folder": str(tmp_path),
                "slope": True,
                "class_threshold": 0.3,
                "cloth_resolution": 2.0,
            },
        )
        _select_option(_find_widget(tw, "rigidness"), "2")

        args = tw.get_widgets_arguments()
        assert args["slope"] is True
        assert args["class_threshold"] == pytest.approx(0.3)
        assert args["cloth_resolution"] == pytest.approx(2.0)
        # The combobox hands back the option text, not an int
        assert args["rigidness"] == "2"

        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["slope"] is True
        assert validated["rigidness"] == 2 and type(validated["rigidness"]) is int
        assert type(validated["class_threshold"]) is float

    def test_bool_string_converted(self, btdata, las_folder, tmp_path):
        args = {"in_las_folder": las_folder, "out_folder": str(tmp_path), "slope": "false", "rigidness": "3"}
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["slope"] is False
        assert validated["rigidness"] == 3

    def test_rigidness_out_of_range_rejected(self, btdata, las_folder, tmp_path):
        args = {"in_las_folder": las_folder, "out_folder": str(tmp_path), "rigidness": "4"}
        with pytest.raises(ValueError, match="rigidness"):
            btdata.validate_tool_params(self.TOOL, args)


# ---------------------------------------------------------------------------
# Surface Water Mapping (rpy_surface_water)
# ---------------------------------------------------------------------------


class TestSurfaceWater:
    TOOL = "Surface Water Mapping"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        for variable in ("in_ortho", "in_training", "in_chm", "out_folder"):
            assert isinstance(_find_widget(tw, variable), FileSelector)
        for variable in ("max_canopy_height", "min_patch_area", "points_per_polygon", "seed"):
            assert isinstance(_find_widget(tw, variable), NumericInput)

    def test_optional_params_hidden_when_advanced_off(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL, show_advanced=False)
        for variable in ("in_chm", "max_canopy_height", "min_patch_area", "points_per_polygon", "seed"):
            assert _find_widget(tw, variable).isHidden()

    def test_validation_round_trip(self, btdata, surface_water_data, tmp_path):
        args = {
            "in_ortho": surface_water_data["ortho"],
            "in_training": f"{surface_water_data['training']}|training",
            "in_chm": surface_water_data["chm"],
            "out_folder": str(tmp_path / "out"),
            "points_per_polygon": "20",
            "min_patch_area": "0.04",
        }
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["points_per_polygon"] == 20 and type(validated["points_per_polygon"]) is int
        assert type(validated["min_patch_area"]) is float

    def test_geopackage_without_layer_rejected(self, btdata, surface_water_data, tmp_path):
        args = {
            "in_ortho": surface_water_data["ortho"],
            "in_training": surface_water_data["training"],
            "out_folder": str(tmp_path / "out"),
        }
        with pytest.raises(ValueError, match="requires a layer"):
            btdata.validate_tool_params(self.TOOL, args)


# ---------------------------------------------------------------------------
# Depth-to-Water from Surface Water (rpy_dtw)
# ---------------------------------------------------------------------------


class TestDtw:
    TOOL = "Depth-to-Water from Surface Water"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        for variable in ("in_dtm", "in_water", "in_mask", "out_folder"):
            assert isinstance(_find_widget(tw, variable), FileSelector)
        for variable in ("grid_size", "nmax", "kriging_cell_size"):
            assert isinstance(_find_widget(tw, variable), NumericInput)
        assert isinstance(_find_widget(tw, "variogram_model"), OptionsInput)

    def test_optional_params_hidden_when_advanced_off(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL, show_advanced=False)
        for variable in ("in_mask", "grid_size", "nmax", "variogram_model", "kriging_cell_size"):
            assert _find_widget(tw, variable).isHidden()

    def test_validation_round_trip(self, btdata, dtw_data, tmp_path):
        args = {
            "in_dtm": dtw_data["dtm"],
            "in_water": dtw_data["water"],
            "in_mask": f"{dtw_data['mask']}|exclude",
            "out_folder": str(tmp_path / "out"),
            "nmax": "12",
            "variogram_model": "Exp",
        }
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["nmax"] == 12 and type(validated["nmax"]) is int
        assert validated["variogram_model"] == "Exp"

    def test_unknown_variogram_model_rejected(self, btdata, dtw_data, tmp_path):
        args = {
            "in_dtm": dtw_data["dtm"],
            "in_water": dtw_data["water"],
            "out_folder": str(tmp_path / "out"),
            "variogram_model": "Lin",
        }
        with pytest.raises(ValueError, match="variogram_model"):
            btdata.validate_tool_params(self.TOOL, args)


# ---------------------------------------------------------------------------
# Seismic Line Disturbance Analysis (rpy_seismic_line_analysis)
# ---------------------------------------------------------------------------


class TestSeismicLineAnalysis:
    TOOL = "Seismic Line Disturbance Analysis"

    def test_widget_types(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL)
        for variable in ("in_segments", "in_dtm", "in_microform", "in_dtw", "out_folder"):
            assert isinstance(_find_widget(tw, variable), FileSelector)
        assert isinstance(_find_widget(tw, "significance"), NumericInput)

    def test_optional_params_hidden_when_advanced_off(self, make_tool_widget):
        tw = make_tool_widget(self.TOOL, show_advanced=False)
        for variable in ("in_dtw", "significance"):
            assert _find_widget(tw, variable).isHidden()
        for variable in ("in_segments", "in_dtm", "in_microform", "out_folder"):
            assert not _find_widget(tw, variable).isHidden()

    def test_validation_round_trip(self, btdata, seismic_line_data, tmp_path):
        args = {
            "in_segments": f"{seismic_line_data['segments']}|segments",
            "in_dtm": seismic_line_data["dtm"],
            "in_microform": seismic_line_data["microform"],
            "in_dtw": seismic_line_data["dtw"],
            "out_folder": str(tmp_path / "out"),
            "significance": "0.01",
        }
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["in_segments"] == args["in_segments"]
        assert validated["significance"] == pytest.approx(0.01)
        assert type(validated["significance"]) is float

    def test_empty_dtw_allowed(self, btdata, seismic_line_data, tmp_path):
        args = {
            "in_segments": f"{seismic_line_data['segments']}|segments",
            "in_dtm": seismic_line_data["dtm"],
            "in_microform": seismic_line_data["microform"],
            "in_dtw": "",
            "out_folder": str(tmp_path / "out"),
        }
        validated = btdata.validate_tool_params(self.TOOL, args)
        assert validated["in_dtw"] == ""

    def test_geopackage_without_layer_rejected(self, btdata, seismic_line_data, tmp_path):
        args = {
            "in_segments": seismic_line_data["segments"],
            "in_dtm": seismic_line_data["dtm"],
            "in_microform": seismic_line_data["microform"],
            "out_folder": str(tmp_path / "out"),
        }
        with pytest.raises(ValueError, match="requires a layer"):
            btdata.validate_tool_params(self.TOOL, args)
