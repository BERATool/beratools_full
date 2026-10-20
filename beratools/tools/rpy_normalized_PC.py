import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common

def rpy_normalized_PC(in_las_folder,
                      out_folder,
                      style,
                      processes=0,
                      **kwargs, ):

    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR', 'gstat', 'rlas', 'future', 'terra', 'sp','raster','stars','sf']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise
    if not style in ["tin", "idw", "kriging"]:
        print("Warning! invalid algorithm, default algorithm will be used.")
        style = "tin"

    if not os.path.exists(out_folder):
        print("Warning! Cannot locate output folder, It will be created.")
        os.makedirs(out_folder)

    print("Checking input parameters....Done")

    rprocesses = r_common.r_processes(processes)

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    # Loading the function defined in R script.
    if style == "tin":
        r_normalized_PC = r_common.robjects.globalenv['normalized_lidar_tin']
    elif style == "idw":
        r_normalized_PC = r_common.robjects.globalenv['normalized_lidar_knnidw']
    else:
        r_normalized_PC = r_common.robjects.globalenv['normalized_lidar_kriging']
    # Invoking the R function
    r_normalized_PC(in_las_folder, out_folder,  rprocesses)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_normalized_PC")

    rpy_normalized_PC(**kwargs)

    print('Normalization process is done in {} seconds'
          .format(round(time.time() - start_time, 5)))



