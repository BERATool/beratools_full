import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


def _split_file_layer(value):
    """Split a 'path|layer' (or 'path::layer') vector input into its path and layer."""
    for sep in ("|", "::"):
        if sep in value:
            path, layer = value.split(sep, 1)
            return path.strip(), layer.strip()
    return value.strip(), ""


def rpy_seismic_line_analysis(in_segments,
            in_dtm,
            in_microform,
            out_folder,
            in_dtw="",
            significance=0.05,
            processes=0,
            **kwargs,):
    """Compare seismic line segments with the adjacent matrix, by disturbance class.

    Adapted from Chan, Dabros & McDermid (2026), Forests 17, 489.
    INPUT: segment polygons (fields new_id, note, Class), DTM raster, microform raster
           (1 hummock, 0 lawn, -1 hollow), optional depth-to-water raster (0 = surface water),
           output folder, significance level
    returnValue: CSV tables and PNG plots in out_folder/tables and out_folder/plots
    """
    segments_path, segments_layer = _split_file_layer(in_segments)
    in_dtw = in_dtw or ""
    for label, path in (("segments", segments_path), ("DTM", in_dtm),
                        ("microform", in_microform), ("depth-to-water", in_dtw)):
        if path and not os.path.isfile(path):
            print(f"Error! Cannot locate the {label} file: {path}")
            exit()
    os.makedirs(out_folder, exist_ok=True)

    packages = ['terra', 'ggplot2']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    print("Checking input parameters....Done")
    if not in_dtw:
        print("No depth-to-water raster given: depth-to-water and surface water are skipped.")

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    seismic_line_analysis = r_common.robjects.globalenv['seismic_line_analysis']
    seismic_line_analysis(segments_path, segments_layer, in_dtm, in_microform, in_dtw,
                          out_folder, float(significance))

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_seismic_line_analysis")

    rpy_seismic_line_analysis(**kwargs)

    print('Seismic line analysis is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
