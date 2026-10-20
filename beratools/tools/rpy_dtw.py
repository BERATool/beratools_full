import time,os,math
import rasterio
from beratools.utility.tool_args import compose_tool_kwargs
from beratools.tools.r_interface import configure_r_environment
configure_r_environment()
import beratools.tools.r_common as r_common
from beratools.utility.spatial_common import decode_file_layer


# Peak memory of one R worker in dtw_tile: the R session itself, plus about 100 bytes per cell of
# the tile (cell coordinates, gstat's prediction table and the kriged values)
R_WORKER_BYTES = 200e6
TILE_BYTES_PER_CELL = 100


def dtw_processes(processes, in_dtm, kriging_cell_size, tile_size):
    """R workers for kriging the water table on this machine: one per CPU core and tile of the
    kriging grid, as far as the free memory holds one tile per worker. processes > 0 caps the count."""
    with rasterio.open(in_dtm) as src:
        width, height, cell_size = src.width, src.height, abs(src.res[0])
    if kriging_cell_size > cell_size:
        fact = max(1, round(kriging_cell_size / cell_size))
        width, height = math.ceil(width / fact), math.ceil(height / fact)
    tile_size = max(1, tile_size)
    tile_cells = min(tile_size, height) * min(tile_size, width)
    tiles = math.ceil(height / tile_size) * math.ceil(width / tile_size)
    return r_common.r_processes_by_memory(
        processes, R_WORKER_BYTES + TILE_BYTES_PER_CELL * tile_cells, tiles)


def rpy_dtw(in_dtm,
            in_water,
            out_folder,
            in_mask="",
            grid_size=10.0,
            nmax=10,
            variogram_model="Ste",
            kriging_cell_size=0.01,
            tile_size=1000,
            processes=0,
            **kwargs,):
    """Krige a water table from surface water elevations and compute depth-to-water.

    Follows Chan, Dabros & McDermid (2026), Forests 17, 489, section 2.4.
    INPUT: DTM, surface water raster (1 water, e.g. from Surface Water Mapping), output folder,
           optional exclusion polygons, grid size, nearest observations, variogram model,
           kriging cell size (0 = DTM cell size), tile size (kriging grid cells per side; tiles
           are kriged in parallel by `processes` R workers)
    returnValue: water_table.tif and dtw.tif (0 on surface water) in out_folder
    """
    mask_path, mask_layer = decode_file_layer(in_mask or "")
    mask_layer = mask_layer or ""  # R gets "" for no layer; rpy2 cannot pass None
    for label, path in (("DTM", in_dtm), ("surface water", in_water), ("mask", mask_path)):
        if path and not os.path.isfile(path):
            raise FileNotFoundError(f"Cannot locate the {label} file: {path}")
    os.makedirs(out_folder, exist_ok=True)

    packages = ['terra', 'gstat']
    try:
        r_common.check_r_packages_installation(packages)
    except Exception as e:
        print(f"Failed to verify R packages: {e}")
        raise

    rprocesses = dtw_processes(processes, in_dtm, float(kriging_cell_size), int(tile_size))

    print("Checking input parameters....Done")

    # assign R script file to local variable
    Beratools_R_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r_scripts_collection.r')
    # Defining the R script and loading the instance in Python
    r_common.r['source'](Beratools_R_script)

    dtw_map = r_common.robjects.globalenv['dtw_map']
    dtw_map(in_dtm, in_water, mask_path, mask_layer, float(grid_size), int(nmax),
            str(variogram_model), float(kriging_cell_size), out_folder,
            int(tile_size), rprocesses)

if __name__ == '__main__':

    start_time = time.time()

    print("Checking input parameters....")
    kwargs = compose_tool_kwargs("rpy_dtw")

    rpy_dtw(**kwargs)

    print('Depth-to-water is done in {} seconds'
          .format(round(time.time() - start_time, 5)))
