import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


def rpy_las_info(in_las_folder,
            processes=0,
            **kwargs,):
    """report las info on:LAS version
        CRS
        EPSG
        Units
        Extent
        Area
        Point count
        Point density
        Number of files
        Normalized / not normalized
        Ground elevation statistics"""
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


    las_info_algorith=r_common.robjects.globalenv['las_info']
    las_info_algorith(in_las_folder,rprocesses)


if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_las_info")

    rpy_las_info(**kwargs)

    print('LiDAR information is done in {} seconds'
          .format(round(time.time() - start_time, 5)))



