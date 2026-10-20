"""Synthetic rasters and polygons for the surface water, depth-to-water and seismic line tests."""

from pathlib import Path


# ---------------------------------------------------------------------------
# Synthetic inputs for Seismic Line Disturbance Analysis
# ---------------------------------------------------------------------------

# Per-segment line depression below the matrix (m), four segments per class.
SEISMIC_LINE_DEPTHS = {
    "New Disturbance": [0.08, 0.10, 0.10, 0.12],
    "Old Disturbance": [0.06, 0.11, 0.11, 0.16],
    "Re-disturbance": [0.12, 0.14, 0.14, 0.16],
}
# Rows (of 20) of each line segment marked hummock; matrix segments have 4 of 20 (0.2).
SEISMIC_LINE_HUMMOCK_ROWS = {"New Disturbance": 1, "Old Disturbance": 3, "Re-disturbance": 0}
# Rows (of 20) of each line segment holding surface water (DTW == 0); matrix has none.
SEISMIC_LINE_WATER_ROWS = {"New Disturbance": 0, "Old Disturbance": 6, "Re-disturbance": 6}

# Expected class means of the line-minus-matrix deviations
SEISMIC_LINE_EXPECTED = {
    "dtm": {"New Disturbance": -0.10, "Old Disturbance": -0.11, "Re-disturbance": -0.14},
    "hummock": {"New Disturbance": -0.15, "Old Disturbance": -0.05, "Re-disturbance": -0.20},
    "dtw": {"New Disturbance": -0.10, "Old Disturbance": -0.10, "Re-disturbance": -0.10},
    "surfacewater": {"New Disturbance": 0.0, "Old Disturbance": 0.3, "Re-disturbance": 0.3},
}


def _rectangle_wkb(xmin, ymin, xmax, ymax):
    import struct

    ring = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)]
    wkb = struct.pack("<BIII", 1, 3, 1, len(ring))
    for x, y in ring:
        wkb += struct.pack("<dd", x, y)
    return wkb


def make_seismic_line_data(folder):
    """Write a small DTM, microform, DTW raster and segment GeoPackage to folder.

    Each segment set is one 1 x 10 m line segment with two 1 x 10 m matrix segments
    15 m to either side, on a 0.5 m grid in EPSG:2956.
    """
    import numpy as np
    import rasterio
    from pyogrio.raw import write
    from rasterio.transform import from_origin

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    res, width, height = 0.5, 120, 300
    transform = from_origin(0, height * res, res, res)

    dtm = np.full((height, width), 700.0, dtype="float64")
    microform = np.zeros((height, width), dtype="float64")
    dtw = np.full((height, width), 0.3, dtype="float64")

    def cells(xmin, ymin):
        # Row/column slices for a 1 x 10 m rectangle (2 x 20 cells) at (xmin, ymin)
        col = int(xmin / res)
        row = int((height * res - (ymin + 10)) / res)
        return slice(row, row + 20), slice(col, col + 2)

    geometries, new_ids, notes, classes = [], [], [], []
    set_index = 0
    for cls, depths in SEISMIC_LINE_DEPTHS.items():
        for depth in depths:
            ymin = 2 + set_index * 12
            new_id = f"seg_{set_index}"
            rows, cols = cells(29, ymin)
            dtm[rows, cols] -= depth
            microform[rows.start:rows.start + SEISMIC_LINE_HUMMOCK_ROWS[cls], cols] = 1
            dtw[rows, cols] = 0.2
            dtw[rows.start:rows.start + SEISMIC_LINE_WATER_ROWS[cls], cols] = 0
            geometries.append(_rectangle_wkb(29, ymin, 30, ymin + 10))
            new_ids.append(new_id)
            notes.append("original")
            classes.append(cls)
            for xmin in (14, 44):
                rows, cols = cells(xmin, ymin)
                microform[rows.start:rows.start + 4, cols] = 1
                geometries.append(_rectangle_wkb(xmin, ymin, xmin + 1, ymin + 10))
                new_ids.append(new_id)
                notes.append("matrix")
                classes.append(cls)
            set_index += 1

    paths = {}
    for name, array in (("dtm", dtm), ("microform", microform), ("dtw", dtw)):
        paths[name] = folder / f"{name}.tif"
        with rasterio.open(
            paths[name], "w", driver="GTiff", width=width, height=height, count=1,
            dtype="float64", crs="EPSG:2956", transform=transform,
        ) as dst:
            dst.write(array, 1)

    paths["segments"] = folder / "segments.gpkg"
    write(
        str(paths["segments"]),
        geometry=np.array(geometries, dtype=object),
        field_data=[np.array(new_ids, dtype=object), np.array(notes, dtype=object),
                    np.array(classes, dtype=object)],
        fields=["new_id", "note", "Class"],
        layer="segments",
        driver="GPKG",
        geometry_type="Polygon",
        crs="EPSG:2956",
    )
    return {name: path.as_posix() for name, path in paths.items()}


# ---------------------------------------------------------------------------
# Synthetic inputs for Surface Water Mapping
# ---------------------------------------------------------------------------

# 40 x 40 m scene on a 0.1 m grid. Areas are (xmin, ymin, xmax, ymax) in metres.
SURFACE_WATER_POOL = (5, 5, 15, 15)  # open water: must be mapped as water
SURFACE_WATER_UNDER_TREE = (25, 5, 35, 15)  # water-coloured, under 1.5 m canopy: masked out
SURFACE_WATER_SHADOW = (5, 25, 15, 35)
SURFACE_WATER_SPECK = (30.0, 30.0, 30.1, 30.1)  # one water-coloured cell: removed as too small
SURFACE_WATER_COLOURS = {"water": (40, 60, 120), "ground": (120, 100, 60), "shadow": (30, 30, 25)}


def make_surface_water_data(folder):
    """Write a synthetic RGB orthomosaic, CHM and training polygons to folder."""
    import numpy as np
    import rasterio
    from pyogrio.raw import write
    from rasterio.transform import from_origin

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    res, size = 0.1, 400
    transform = from_origin(0, size * res, res, res)

    def cells(area):
        xmin, ymin, xmax, ymax = area
        rows = slice(int(round((size * res - ymax) / res)), int(round((size * res - ymin) / res)))
        cols = slice(int(round(xmin / res)), int(round(xmax / res)))
        return rows, cols

    rng = np.random.default_rng(0)
    rgb = np.empty((3, size, size), dtype="float64")
    rgb[:] = np.array(SURFACE_WATER_COLOURS["ground"], dtype="float64")[:, None, None]
    for area, colour in ((SURFACE_WATER_POOL, "water"), (SURFACE_WATER_UNDER_TREE, "water"),
                         (SURFACE_WATER_SHADOW, "shadow"), (SURFACE_WATER_SPECK, "water")):
        rows, cols = cells(area)
        rgb[:, rows, cols] = np.array(SURFACE_WATER_COLOURS[colour], dtype="float64")[:, None, None]
    rgb = np.clip(rgb + rng.normal(0, 2, rgb.shape), 0, 255).astype("uint8")

    chm = np.zeros((size, size), dtype="float32")
    rows, cols = cells(SURFACE_WATER_UNDER_TREE)
    chm[rows, cols] = 1.5

    paths = {"ortho": folder / "ortho.tif", "chm": folder / "chm.tif"}
    profile = dict(driver="GTiff", width=size, height=size, crs="EPSG:2956", transform=transform)
    with rasterio.open(paths["ortho"], "w", count=3, dtype="uint8", **profile) as dst:
        dst.write(rgb)
    with rasterio.open(paths["chm"], "w", count=1, dtype="float32", **profile) as dst:
        dst.write(chm, 1)

    training = [
        ((6, 6, 9, 9), "water"), ((11, 11, 14, 14), "Water"),
        ((20, 20, 23, 23), "ground"), ((36, 36, 39, 39), "ground"),
        ((6, 26, 9, 29), "shadow"), ((11, 31, 14, 34), "shadow"),
    ]
    paths["training"] = folder / "training.gpkg"
    write(
        str(paths["training"]),
        geometry=np.array([_rectangle_wkb(*area) for area, _ in training], dtype=object),
        field_data=[np.array([label for _, label in training], dtype=object)],
        fields=["class"],
        layer="training",
        driver="GPKG",
        geometry_type="Polygon",
        crs="EPSG:2956",
    )
    return {name: path.as_posix() for name, path in paths.items()}


# ---------------------------------------------------------------------------
# Synthetic inputs for Depth-to-Water
# ---------------------------------------------------------------------------

DTW_GROUND_HEIGHT = 0.2  # ground sits this far above the water table everywhere off the pools
DTW_EXCLUDED = (80, 80, 100, 100)  # (xmin, ymin, xmax, ymax) masked out of the analysis


def dtw_water_table(x, y):
    """Smooth synthetic water table (m) at map coordinates x, y."""
    import numpy as np

    return 700 + 0.3 * np.sin(x / 30) + 0.3 * np.cos(y / 40)


def make_dtw_data(folder):
    """Write a synthetic DTM, surface water raster and exclusion polygon to folder.

    100 x 100 m on a 0.5 m grid. The DTM is the water table plus DTW_GROUND_HEIGHT, except for
    one 1 x 1 m pool per 10 x 10 m cell, where the DTM equals the water table.
    """
    import numpy as np
    import rasterio
    from pyogrio.raw import write
    from rasterio.transform import from_origin

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    res, size = 0.5, 200
    transform = from_origin(0, size * res, res, res)

    centres = (np.arange(size) + 0.5) * res
    x, y = np.meshgrid(centres, size * res - centres)
    water_table = dtw_water_table(x, y)

    water = np.zeros((size, size), dtype="uint8")
    for row in range(0, size, 20):  # one pool per 10 m cell, at a varying offset inside it
        for col in range(0, size, 20):
            r0, c0 = row + 4 + (col // 20) % 10, col + 4 + (row // 20) % 10
            water[r0:r0 + 2, c0:c0 + 2] = 1
    dtm = np.where(water == 1, water_table, water_table + DTW_GROUND_HEIGHT)

    paths = {"dtm": folder / "dtm.tif", "water": folder / "water.tif"}
    profile = dict(driver="GTiff", width=size, height=size, count=1, crs="EPSG:2956", transform=transform)
    with rasterio.open(paths["dtm"], "w", dtype="float64", **profile) as dst:
        dst.write(dtm, 1)
    with rasterio.open(paths["water"], "w", dtype="uint8", **profile) as dst:
        dst.write(water, 1)

    paths["mask"] = folder / "exclude.gpkg"
    write(
        str(paths["mask"]),
        geometry=np.array([_rectangle_wkb(*DTW_EXCLUDED)], dtype=object),
        field_data=[np.array(["upland"], dtype=object)],
        fields=["name"],
        layer="exclude",
        driver="GPKG",
        geometry_type="Polygon",
        crs="EPSG:2956",
    )
    return {name: path.as_posix() for name, path in paths.items()}
