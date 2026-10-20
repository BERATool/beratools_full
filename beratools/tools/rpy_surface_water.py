import time,os,math
import rasterio
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common
from beratools.utility.spatial_common import decode_file_layer


# Peak memory of one R worker in surface_water_tile: the R session itself, plus about 100 bytes
# per cell of the buffered tile (RGB values, class codes, resampled CHM, patch ids and copies).
# Measured: 535 MB for a 2000 x 2000 tile with CHM and patch removal (estimate 600 MB).
R_WORKER_BYTES = 200e6
TILE_BYTES_PER_CELL = 100


def surface_water_processes(processes, in_ortho, tile_size, min_patch_area):
    """R workers for surface_water_map on this machine: one per CPU core and tile, as far as the
    free memory holds one buffered tile per worker. processes > 0 caps the count."""
    with rasterio.open(in_ortho) as src:
        width, height = src.width, src.height
        cell_area = abs(src.res[0] * src.res[1])
    tile_size = max(1, tile_size)
    buffer = math.ceil(min_patch_area / cell_area) if min_patch_area > 0 else 0
    tile_cells = (min(tile_size, height) + 2 * buffer) * (min(tile_size, width) + 2 * buffer)
    tiles = math.ceil(height / tile_size) * math.ceil(width / tile_size)
    return r_common.r_processes_by_memory(
        processes, R_WORKER_BYTES + TILE_BYTES_PER_CELL * tile_cells, tiles)


def rpy_surface_water(in_ortho,
            in_training,
            out_folder,
            in_chm="",
            max_canopy_height=0.2,
            min_patch_area=0.04,
            points_per_polygon=2,
            seed=1,
            tile_size=2000,
            processes=0,
            **kwargs,):
    """Map surface water from a true-colour orthomosaic with a decision tree.

    Follows Chan, Dabros & McDermid (2026), Forests 17, 489, section 2.4.
    INPUT: orthomosaic (bands 1-3 red, green, blue), training polygons with a 'class' field
           ('water' plus other classes such as 'ground' and 'shadow'), output folder,
           optional CHM, canopy height mask threshold, minimum water patch area,
           training points per polygon, random seed, tile size (cells per side; tiles are
           classified in parallel by `processes` R workers)
    returnValue: surface_water.tif (1 water, 0 not water) and cross-validation tables in out_folder
    """
    training_path, training_layer = decode_file_layer(in_training)
    training_layer = training_layer or ""  # R gets "" for no layer; rpy2 cannot pass None
    in_chm = in_chm or ""
    for label, path in (("orthomosaic", in_ortho), ("training polygons", training_path),
                        ("CHM", in_chm)):
        if path and not os.path.isfile(path):
            raise FileNotFoundError(f"Cannot locate the {label} file: {path}")
    os.makedirs(out_folder, exist_ok=True)

    packages = ['terra', 'rpart']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    rprocesses = surface_water_processes(processes, in_ortho, int(tile_size), float(min_patch_area))

    print("Checking input parameters....Done")
    if not in_chm:
        print("No CHM given: cells under canopy are not masked out.")

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    surface_water_map = r_common.robjects.globalenv['surface_water_map']
    surface_water_map(in_ortho, training_path, training_layer, in_chm,
                      float(max_canopy_height), float(min_patch_area),
                      int(points_per_polygon), int(seed), out_folder,
                      int(tile_size), rprocesses)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_surface_water")

    rpy_surface_water(**kwargs)

    print('Surface water mapping is done in {} seconds'
          .format(round(time.time() - start_time, 5)))