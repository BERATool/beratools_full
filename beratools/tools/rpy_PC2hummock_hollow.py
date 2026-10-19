import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common

def rpy_hh2raster(in_las_folder,
            out_folder,
            Smooth_by,
            Min_ws=3.0,
            lawn_range=0.3,
            cell_size=0.0,
            processes=0,
            **kwargs,):
    """Generate a raster of hummock hollows from LiDAR data.
    INPUT: LiDAR folder, output folder, smoothing method, minimum watershed size, lawn range, cell size
    returnValue: raster of hummock hollows
        """
    # cell_size = float(cell_size)
    # Min_ws = float(Min_ws)
    # lawn_range = float(lawn_range)
    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR',  'rlas', 'future', 'terra', 'sp','raster','stars','sf']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

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

    is_gnd_classified = [list(r_item)[0] for r_item in r_common.robjects.globalenv['detect_class'](in_las_folder, 2)]

    if not False in is_gnd_classified:
        hh_function_algorithm=r_common.robjects.globalenv['hh_function']
        hh_function_algorithm(in_las_folder,out_folder, float(cell_size), Smooth_by, float(Min_ws), float(lawn_range), rprocesses)
    else:
        print("[Warning!] The LiDAR data is not classified, please run ground classification first.")
        exit()


if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_PC2hummock_hollow")

    rpy_hh2raster(**kwargs)

    print('Hummock and hollow process is done in {} seconds'
          .format(round(time.time() - start_time, 5)))

