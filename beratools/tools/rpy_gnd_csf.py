import time,os
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common


def rpy_gnd_csf(in_las_folder,
            out_folder,
            slope:bool=False,
            class_threshold=0.3,
            cloth_resolution=1.0,
            rigidness=1,
            processes=1,
            **kwargs,):
    """Generate a raster of hummock hollows from LiDAR data.
    INPUT: LiDAR folder, output folder, smoothing method, minimum watershed size, lawn range, cell size
    returnValue: raster of hummock hollows
        """
    r_common.check_las_files_existence(in_las_folder)
    r_common.check_las_out_folder_existence(out_folder)
    packages = ['lidR', 'RCSF', 'rlas', 'future', 'terra', 'sp','raster','stars','sf']
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

    is_gnd_classified = [list(r_item)[0] for r_item in r_common.robjects.globalenv['detect_class'](in_las_folder, 2)]
    rest = False
    if not False in is_gnd_classified:
        rest=True
        print("Classified LiDAR data detected, process will rest and overwrite existing PC...")
    else:
        print("The LiDAR data will being classified......")
    classify_gnd_csf_algorith = r_common.robjects.globalenv['classify_gnd_csf']
    classify_gnd_csf_algorith(in_las_folder, out_folder, bool(slope), float(class_threshold),
                              float(cloth_resolution),int(rigidness),
                              rprocesses,bool(rest))

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_gnd_csf")

    rpy_gnd_csf(**kwargs)

    print('LiDAR classification is done in {} seconds'
          .format(round(time.time() - start_time, 5)))

