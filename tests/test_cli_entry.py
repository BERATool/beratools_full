import pytest

from beratools.cli import entry


@pytest.mark.parametrize("alias", ["bt", "beratools"])
def test_no_arg_alias_prints_basic_cli_info(capsys, alias):
    code = entry.run(argv=[], prog_name=alias)
    assert code == 0

    out = capsys.readouterr().out
    assert "BERATools CLI" in out
    assert "Use 'gui' to launch the GUI." in out
    assert "Use 'list-tools' to list tool subcommands." in out


def test_gui_subcommand_launches_gui(monkeypatch):
    called = {"value": False}

    def _fake_launch_gui():
        called["value"] = True
        return 0

    monkeypatch.setattr(entry, "launch_gui", _fake_launch_gui)
    code = entry.run(argv=["gui"], prog_name="bt")

    assert code == 0
    assert called["value"] is True


def test_help_smoke(capsys):
    with pytest.raises(SystemExit) as exc:
        entry.run(argv=["--help"], prog_name="bt")

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "list-tools" in out
    assert "gui" in out
    assert "check_line" in out


def test_parse_and_dispatch_short_tool(monkeypatch):
    received = {}

    def _fake_tool(**kwargs):
        received.update(kwargs)

    monkeypatch.setattr("beratools.utility.env_checks.configure_gdal_proj_environment", lambda: None)
    monkeypatch.setattr("beratools.utility.env_checks.warn_gdal_proj_env", lambda: None)
    monkeypatch.setattr(entry, "_resolve_tool_function", lambda _api: _fake_tool)

    code = entry.run(
        argv=[
            "check_line",
            "--in_line",
            "input.gpkg|seed_lines",
            "--out_line",
            "out.gpkg|seed_lines_checked",
            "--processes",
            "2",
            "--call_mode",
            "CLI",
            "--log_level",
            "DEBUG",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert received["in_line"] == "input.gpkg|seed_lines"
    assert received["out_line"] == "out.gpkg|seed_lines_checked"
    assert received["processes"] == 2
    assert received["call_mode"] == "CLI"
    assert received["log_level"] == "DEBUG"


def test_alias_parity_no_arg_output(capsys):
    outputs = []
    for alias in ("bt", "beratools"):
        entry.run(argv=[], prog_name=alias)
        outputs.append(capsys.readouterr().out)

    for out in outputs:
        assert "BERATools CLI" in out
        assert "Use '--help' to see all commands." in out
        assert "Use 'list-tools' to list tool subcommands." in out


def test_bare_tool_subcommand_prints_help_not_error(capsys):
    code = entry.run(argv=["centerline"], prog_name="bt")
    assert code == 0

    out = capsys.readouterr().out
    assert "usage: bt centerline" in out
    assert "Required Parameters" in out
    assert "Optional Parameters" in out
    assert "error:" not in out.lower()


# ---------------------------------------------------------------------------
# PC2Products (R) tools
# ---------------------------------------------------------------------------

R_ALIASES = ["dtm", "normalize", "chm_dsm", "las_info", "cellsize", "hh", "gnd_csf", "surface_water", "dtw", "line_analysis"]


@pytest.fixture
def fake_tool(monkeypatch):
    """Replace tool dispatch with a recorder; return the kwargs it received."""
    received = {}

    def _fake_tool(**kwargs):
        received.update(kwargs)

    monkeypatch.setattr("beratools.utility.env_checks.configure_gdal_proj_environment", lambda: None)
    monkeypatch.setattr("beratools.utility.env_checks.warn_gdal_proj_env", lambda: None)
    monkeypatch.setattr(entry, "_resolve_tool_function", lambda _api: _fake_tool)
    return received


def test_help_lists_r_tools(capsys):
    with pytest.raises(SystemExit):
        entry.run(argv=["--help"], prog_name="bt")

    out = capsys.readouterr().out
    for alias in R_ALIASES:
        assert alias in out


def test_list_tools_prints_every_alias(capsys):
    code = entry.run(argv=["list-tools"], prog_name="bt")
    assert code == 0

    out = capsys.readouterr().out
    for alias, tool_api in entry.TOOL_ALIASES.items():
        assert f"- {alias} ({tool_api})" in out


@pytest.mark.parametrize("alias", R_ALIASES)
def test_alias_maps_to_tool_in_beratools_json(alias):
    tools_cfg = entry._load_tools_config()
    tool_api = entry.TOOL_ALIASES[alias]
    assert tool_api in tools_cfg
    assert callable(entry._resolve_tool_function(tool_api))


def test_parse_and_dispatch_dtm(fake_tool):
    code = entry.run(
        argv=[
            "dtm",
            "--in_las_folder",
            "LiDAR",
            "--out_folder",
            "Raster_Output",
            "--style",
            "idw",
            "--processes",
            "2",
            "--call_mode",
            "CLI",
            "--log_level",
            "DEBUG",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool == {
        "in_las_folder": "LiDAR",
        "out_folder": "Raster_Output",
        "style": "idw",
        "cell_size": 0.0,
        "processes": 2,
        "call_mode": "CLI",
        "log_level": "DEBUG",
    }


@pytest.mark.parametrize("alias", ["las_info", "cellsize"])
def test_parse_and_dispatch_folder_only_tools(fake_tool, alias):
    code = entry.run(argv=[alias, "--in_las_folder", "LiDAR"], prog_name="bt")

    assert code == 0
    assert fake_tool["in_las_folder"] == "LiDAR"
    assert fake_tool["processes"] == 0


def test_hh_converts_numbers_and_applies_optional_default(fake_tool):
    code = entry.run(
        argv=[
            "hh",
            "--in_las_folder",
            "LiDAR",
            "--out_folder",
            "Raster_Output",
            "--Smooth_by",
            "median",
            "--Min_ws",
            "5",
            "--lawn_range",
            "0.1",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool["Smooth_by"] == "median"
    assert fake_tool["Min_ws"] == 5.0 and type(fake_tool["Min_ws"]) is float
    assert fake_tool["lawn_range"] == pytest.approx(0.1)
    assert fake_tool["cell_size"] == 0.0


def test_gnd_csf_converts_bool_and_int(fake_tool):
    code = entry.run(
        argv=[
            "gnd_csf",
            "--in_las_folder",
            "LiDAR",
            "--out_folder",
            "Classified_PC",
            "--slope",
            "true",
            "--rigidness",
            "2",
            "--class_threshold",
            "0.3",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool["slope"] is True
    assert fake_tool["rigidness"] == 2 and type(fake_tool["rigidness"]) is int
    assert fake_tool["class_threshold"] == pytest.approx(0.3)
    assert fake_tool["cloth_resolution"] == 1.0


def test_gnd_csf_optional_defaults(fake_tool):
    code = entry.run(argv=["gnd_csf", "--in_las_folder", "LiDAR", "--out_folder", "Classified_PC"], prog_name="bt")

    assert code == 0
    assert fake_tool["slope"] is False
    assert fake_tool["class_threshold"] == 0.5
    assert fake_tool["cloth_resolution"] == 1.0
    assert fake_tool["rigidness"] == 1


@pytest.mark.parametrize(
    "argv",
    [
        ["dtm", "--in_las_folder", "LiDAR", "--out_folder", "out", "--style", "pitfree"],
        ["chm_dsm", "--in_las_folder", "LiDAR", "--out_folder", "out", "--style", "kriging"],
        ["gnd_csf", "--in_las_folder", "LiDAR", "--out_folder", "out", "--rigidness", "4"],
        ["gnd_csf", "--in_las_folder", "LiDAR", "--out_folder", "out", "--slope", "maybe"],
        ["hh", "--in_las_folder", "LiDAR", "--out_folder", "out", "--Smooth_by", "mean", "--Min_ws", "abc"],
    ],
)
def test_invalid_values_rejected(fake_tool, capsys, argv):
    with pytest.raises(SystemExit) as exc:
        entry.run(argv=argv, prog_name="bt")

    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err
    assert fake_tool == {}


def test_missing_required_param_rejected(fake_tool, capsys):
    with pytest.raises(SystemExit) as exc:
        entry.run(argv=["dtm", "--in_las_folder", "LiDAR"], prog_name="bt")

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--out_folder" in err
    assert "--style" in err
    assert fake_tool == {}


@pytest.mark.parametrize("alias", R_ALIASES)
def test_bare_r_tool_subcommand_prints_help_not_error(capsys, alias):
    code = entry.run(argv=[alias], prog_name="bt")
    assert code == 0

    out = capsys.readouterr().out
    assert f"usage: bt {alias}" in out
    assert "Required Parameters" in out
    tool_cfg = entry._load_tools_config()[entry.TOOL_ALIASES[alias]]
    first_required = next(p["variable"] for p in tool_cfg["parameters"] if not p.get("optional"))
    assert f"--{first_required}" in out
    assert "error:" not in out.lower()


@pytest.mark.parametrize("alias", ["hh", "gnd_csf"])
def test_help_shows_optional_parameters_group(capsys, alias):
    entry.run(argv=[alias], prog_name="bt")
    assert "Optional Parameters" in capsys.readouterr().out


def test_line_analysis_converts_significance_and_leaves_dtw_unset(fake_tool):
    code = entry.run(
        argv=[
            "line_analysis",
            "--in_segments",
            "segments.gpkg|segments",
            "--in_dtm",
            "dtm.tif",
            "--in_microform",
            "microform.tif",
            "--out_folder",
            "out",
            "--significance",
            "0.01",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool["in_segments"] == "segments.gpkg|segments"
    assert fake_tool["significance"] == pytest.approx(0.01)
    assert type(fake_tool["significance"]) is float
    assert fake_tool["in_dtw"] is None


def test_line_analysis_requires_microform(capsys):
    with pytest.raises(SystemExit):
        entry.run(
            argv=["line_analysis", "--in_segments", "s.gpkg|s", "--in_dtm", "dtm.tif", "--out_folder", "out"],
            prog_name="bt",
        )
    assert "--in_microform" in capsys.readouterr().err


def test_surface_water_converts_numbers(fake_tool):
    code = entry.run(
        argv=[
            "surface_water",
            "--in_ortho",
            "ortho.tif",
            "--in_training",
            "training.gpkg|training",
            "--out_folder",
            "out",
            "--points_per_polygon",
            "20",
            "--max_canopy_height",
            "0.5",
        ],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool["points_per_polygon"] == 20 and type(fake_tool["points_per_polygon"]) is int
    assert fake_tool["max_canopy_height"] == pytest.approx(0.5)
    assert fake_tool["min_patch_area"] == pytest.approx(0.04)
    assert fake_tool["seed"] == 1
    assert fake_tool["tile_size"] == 2000 and type(fake_tool["tile_size"]) is int
    assert fake_tool["in_chm"] is None


def test_dtw_converts_numbers_and_checks_model(fake_tool):
    code = entry.run(
        argv=["dtw", "--in_dtm", "dtm.tif", "--in_water", "water.tif", "--out_folder", "out",
              "--nmax", "16", "--variogram_model", "Sph"],
        prog_name="bt",
    )

    assert code == 0
    assert fake_tool["nmax"] == 16 and type(fake_tool["nmax"]) is int
    assert fake_tool["variogram_model"] == "Sph"
    assert fake_tool["grid_size"] == pytest.approx(10.0)
    assert fake_tool["kriging_cell_size"] == pytest.approx(0.01)
    assert fake_tool["tile_size"] == 1000 and type(fake_tool["tile_size"]) is int


def test_dtw_rejects_unknown_variogram_model():
    with pytest.raises(SystemExit):
        entry.run(
            argv=["dtw", "--in_dtm", "dtm.tif", "--in_water", "water.tif", "--out_folder", "out",
                  "--variogram_model", "Lin"],
            prog_name="bt",
        )
