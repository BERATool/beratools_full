import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common

def rpy_find_cellsize(in_las_folder,
            processes=0,
            **kwargs,):

    r_common.check_las_files_existence(in_las_folder)
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

    find_cellsize_algorith=r_common.robjects.globalenv['pd2cellsize']
    _=find_cellsize_algorith(in_las_folder, rprocesses)


if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_find_cellsize")

    rpy_find_cellsize(**kwargs)

    print('Finding cell size is done in {} seconds'
          .format(round(time.time() - start_time, 5)))



