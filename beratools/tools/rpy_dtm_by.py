import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common

def rpy_dtm(in_las_folder,
            out_folder,
            style,
            cell_size=0.0,
            processes=0,
            **kwargs,):

    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR', 'gstat', 'rlas', 'future', 'terra', 'sp','raster','stars','sf']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise
    if not style in ["tin", "idw", "kriging"]:
        print("[Warning!] invalid algorithm, default algorithm will be used.")
        style = "tin"

    if not os.path.exists(out_folder):
        print("[Warning!] Cannot locate output folder, It will be created.")
        os.makedirs(out_folder)

    print("Checking input parameters....Done")

    rprocesses = r_common.r_processes(processes)

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    if cell_size == 0.0:
        print("[INFO] No cell size given, the cell size will be estimated from the LiDAR data.")
        from rpy2.rinterface_lib import callbacks
        old_print = callbacks.consolewrite_print
        old_warn = callbacks.consolewrite_warnerror
        try:
            callbacks.consolewrite_print = lambda x: None
            callbacks.consolewrite_warnerror = lambda x: None
            find_cellsize_algorithm = r_common.robjects.globalenv['pd2cellsize']
            results = find_cellsize_algorithm(in_las_folder, rprocesses)
        finally:
            callbacks.consolewrite_print = old_print
            callbacks.consolewrite_warnerror = old_warn
        cell_size=float(results.rx2("cell_size")[0])
        map_units = str(results.rx2("map_units")[0])
    is_gnd_classified = [list(r_item)[0] for r_item in r_common.robjects.globalenv['detect_class'](in_las_folder,2)]
    if False in is_gnd_classified:
        print("[Warning!] The LiDAR data is not classified, please run ground classification first.")
        exit()
    is_normalized = bool(r_common.robjects.globalenv['detect_normalized'](in_las_folder)[0])
    if is_normalized:
        print("[INFO]: LiDAR data is normalized, the output will be normalized DTM.")
    else:
        print("[INFO]: LiDAR data is not normalized, the output will be regular DTM.")

    # Loading the function defined in R script.
    if style == "tin":
        r_chm_by_algorithm = r_common.robjects.globalenv['dtm_by_tin']
    elif style == "idw":
        r_chm_by_algorithm = r_common.robjects.globalenv['dtm_by_knnidw']
    else:
        r_chm_by_algorithm = r_common.robjects.globalenv['dtm_by_kriging']
    # Invoking the R function
    r_chm_by_algorithm(in_las_folder, out_folder, cell_size, rprocesses)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_dtm_by")

    rpy_dtm(**kwargs)

    print('DTM process is done in {} seconds'
          .format(round(time.time() - start_time, 5)))



