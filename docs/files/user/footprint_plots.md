# Footprint Plots and Subplots

## What does this tool do?

**Footprint Plots and Subplots** splits line footprints into plots and subplots along their centerlines. This is useful for field sampling or for summarizing data along a line in equal-area or equal-length units.

- A **plot** covers both sides of the line. Each side is a separate feature, labelled `0` (left) or `1` (right) relative to the line direction.
- A **subplot** is a smaller unit on one side of the line. Subplots nest inside plots.

The tool is ported from [SegLine](https://github.com/IrinaTerentieva/SegLine) by Irina Terentieva and supports both SegLine segmentation modes:

| | **Fixed area** (`fixed_area`) | **Fixed length** (`fixed_length`) |
|---|---|---|
| **Plots** | Target area, e.g. 100 m² | Fixed spacing along the centerline, e.g. every 50 m |
| **Subplots** | Target area, e.g. 10 m² | Fixed spacing, e.g. every 10 m |
| **Wide vs. narrow lines** | Same area; plots get shorter as the line gets wider | Same length; plot area grows with line width |
| **Use when** | Plots must be comparable by area (e.g. stocking or density per m²) | Plots must line up with distance along the line (e.g. matching field transects) |

## How do I use it?

### Quick Start

1. **Prepare your input files**: footprint polygons, for example the output of [Canopy Footprint](canopy_footprint_abs.md) or [Ground Footprint](ground_footprint.md), and the centerlines of those footprints.
2. **Run the tool** from GUI. The mode and size options are under **Show Advanced Options**:

   ![Footprint Plots and Subplots](../screenshots/tool_footprint_plots.png)

3. **Open the two output files** in your GIS software. Symbolize by `plot_id` and `side` to see the plots.

## What options can I set?

- **Input Footprint**: Path to your input footprint polygon file
- **Input Centerline**: Path to the centerlines of the footprints. Each footprint uses the centerline that overlaps it the most, so the two files don't need a shared ID field.
- **Segmentation mode**: `fixed_area` or `fixed_length` (default: `fixed_area`)
- **Plot area (m2)**: Fixed area mode. Target plot area covering both sides of the line (default: `100`)
- **Subplot area (m2)**: Fixed area mode. Target subplot area on one side of the line (default: `10`)
- **Plot length (m)**: Fixed length mode. Distance between plot boundaries along the centerline (default: `50`)
- **Subplot length (m)**: Fixed length mode. Distance between subplot boundaries along the centerline (default: `10`)
- **Remove overlaps**: Cut overlaps between footprints, such as at line crossings, out of all but one footprint (default: `false`). See [Overlapping footprints](#overlapping-footprints)
- **Output Plots**: Path for the output plots, one feature per plot side
- **Output Subplots**: Path for the output subplots

## How are plots sized?

### Fixed area

The tool estimates the average width of each footprint as its area divided by the length of the centerline inside it. It then spaces cuts along the centerline so that subplots get close to the target area:

- Subplot length along the line = 2 × subplot area ÷ width
- Subplots per side of a plot = plot area ÷ (2 × subplot area), rounded to a whole number

The plot area must be at least 2 × the subplot area. Where the footprint is wider or narrower than average, those subplots are larger or smaller. The mean subplot area still matches the target.

### Fixed length

Plots start every **plot length** along the centerline, and subplots start every **subplot length** within each plot. Subplots restart at each plot boundary, so a plot length that is not a multiple of the subplot length leaves a shorter last subplot in each plot.

In both modes, a piece shorter than half a subplot length joins the previous subplot, for example at the end of a line.

## Overlapping footprints

Footprints often overlap where lines cross. By default, each footprint is split on its own, so plots and subplots of different lines overlap there. Any metric summed or averaged over subplots then counts the crossing twice.

Turn on **Remove overlaps** to count each area only once. One footprint keeps each overlap and the other gives it up. Each overlap is decided on its own, so two lines that cross in one place and meet in another can be decided differently. The footprint that keeps it is chosen in this order:

1. **A line that ends in the overlap always loses it**, as at a T-junction. A line counts as ending in the overlap if its centerline end is within half its footprint width of it (at least 0.5 m), so an end that stops just short of the other line counts too.
2. Where both lines pass through (a crossing) or both end there (a corner), a line running **north-south or east-west** keeps the overlap over a line running in any other direction. A line counts as north-south or east-west if its main direction is within 15° of one of them.
3. Otherwise, for two north-south or east-west lines, or two lines in other directions, the **longer centerline** keeps it. Only the part of the centerline inside its footprint counts.
4. If the lengths are equal, the footprint that comes first in the input keeps it.

The main direction of a line is its length-weighted average direction, so a short bend doesn't change it.

How the losing footprint gives up the overlap depends on whether its line ends there:

- **Line ends in the overlap** (T-junction or corner): the footprint and its centerline are **trimmed** back to the other footprint before splitting. Plots and subplots start or stop at the cut, and `length` covers only the trimmed centerline. Bits of the footprint that poke out beyond the far side of the other footprint are dropped, so no plot holds part of another line's footprint. Fragments of a multipart footprint away from the overlap are kept.
- **Line passes through** (crossing): plot and subplot positions along the line don't change. The overlap is cut out of the pieces at the crossing, which get smaller. If the cut splits a subplot in two, the subplot keeps both pieces, one on each side of the crossing, so every subplot stays between its own cross cuts and both sides of the line are cut at the same places. A subplot that lies entirely inside the overlap is dropped. A plot or subplot the crossing runs through can end up in two pieces, one on each side of the other line. `length` is not changed.

!!! note "Trimming shifts plots when the start of a line is trimmed"
    Line ends are trimmed **before** plots and subplots are created, so the last subplot is a normal size, `length` matches the trimmed centerline, and pieces poking out beyond the other line are cut off cleanly. Plots are laid out from the start of the centerline, so when the trimmed end is the **start** of the line, every plot along it shifts by the trimmed amount (typically a few metres) compared with a run without **Remove overlaps**. Trimming the far end of a line doesn't move any plots.

`area`, `perimeter` and `plot_area` are always measured after the overlap is removed.

## Output attributes

Both outputs keep the footprint attributes, plus any centerline attributes the footprint doesn't already have. The subplot output is the one to use downstream. Its key columns have the same names as in the [SegLine](https://github.com/IrinaTerentieva/SegLine) subplot layer. Some of them are computed differently, see [Differences from SegLine](#differences-from-segline).

| Field | Description |
|---|---|
| `UniqueID` | Line (footprint polygon) ID. An existing unique `UniqueID` column in the footprints is kept; otherwise random IDs are generated, as in SegLine |
| `side` | Side of the centerline: `0` left, `1` right, relative to the line direction |
| `plot_id` | Plot ID. Unique across the output and increasing along each line |
| `subplot_id` | Subplot ID. Unique across the output and increasing along each line (subplots only) |
| `area` | Area of the feature (m²) |
| `length` | Length of the feature along the centerline (m) |
| `perimeter` | Perimeter of the feature (m) |
| `plot_area` | Area of the plot side the feature belongs to (m²) |
| `subplot_area` | Area of the subplot (m², subplots only) |
| `est_width` | Estimated average footprint width (m) |

The plot output has one feature per plot side, with the same columns except `subplot_id` and `subplot_area`.

## Differences from SegLine

The tool follows SegLine's two modes and output columns, but it is not a line-by-line copy. Compared with the output of SegLine's own scripts:

### Output columns

| Column | SegLine | This tool |
|---|---|---|
| `UniqueID` | Always generated as a random ID (4 characters with the default config) | Kept from the footprints if they already have a unique `UniqueID` column; otherwise a random 6-character ID |
| `side` | `0`/`1` from pairing plot pieces, not tied to the line direction | `0` is always left and `1` always right of the line direction |
| `plot_id` | Unique across the output, but not always in order along the line | Unique across the output and increasing from the start of each line |
| `subplot_id` | Unique across the output; all of side `0` along a line, then all of side `1` | Unique across the output; ordered by plot, then side, then along the line |
| `length` | Polygon perimeter (same value as `perimeter`) | Length along the centerline |
| `plot_area` | Fixed area: area of the plot side. Fixed length: the configured `plot_area` value, the same for every feature | Area of the plot side in both modes |
| `subplot_area` | Fixed area: subplot area. Fixed length: the configured `subplot_area` value, the same for every feature | Subplot area in both modes |
| `width` | Input width column, required | Not required. The estimated width is written as `est_width` |
| Temporary columns | `PartID`, `segment_id`, `SubplotPartID`, `centroid_x`, `centroid_y`, `edge_points` | Not written |

### Processing

- **One tool instead of a pipeline.** SegLine runs separate scripts (assign IDs, clean centerlines, smooth, plots, sides, subplots) and writes a file after each step. This tool writes only the plots and the subplots.
- **Centerline cleaning and smoothing are not included.** SegLine's fixed-area mode removes duplicate and overlapping centerlines and can smooth them. Clean the centerlines first, or use [Smooth Centerline](smooth_centerline.md).
- **Matching footprints to centerlines.** SegLine links them with sample points along the centerline. This tool uses the centerline with the longest overlap with each footprint.
- **Width.** SegLine reads the width from a footprint column. This tool estimates it as footprint area divided by centerline length inside the footprint.
- **Sides.** SegLine splits each line into pieces and then pairs them into sides by shared edge points. This tool cuts along the centerline and labels each piece by which side of the line it lies on, so every plot has a consistent left and right side.
- **Overlaps.** SegLine keeps overlaps between footprints. This tool keeps them too by default, and can remove them with **Remove overlaps**.
- **Small pieces.** SegLine merges small fragments and subplots by area (fixed area) or drops pieces smaller than `min_area` (fixed length). This tool joins any piece shorter than half a subplot length to the previous subplot and never drops area: plots and subplots cover each footprint exactly. The only exception is with **Remove overlaps**, where bits of a trimmed footprint that poke out beyond the other footprint are dropped.

### Results on the SegLine sample data

With the default options in both tools:

| | SegLine | This tool |
|---|---|---|
| Fixed area subplots | 1,971, mean 10.0 m², std 0.43 m² | 1,974, mean 10.0 m², std 0.57 m² |
| Fixed area plot sides | 394 | 400 |
| Fixed length subplots | 1,001, median 20.0 m² | 998, median 20.0 m² |
| Fixed length plot sides | 206 | 204 |

Exact geometries differ, because SegLine places cuts from the width column and this tool from the estimated width.

## Tips

- Footprints and centerlines must use the same coordinate reference system (CRS).
- Footprints with no overlapping centerline are skipped. The tool prints how many footprints it matched.
- Plots and subplots cover each footprint exactly, without gaps or overlaps. With **Remove overlaps** on, they cover the union of the footprints instead. Crumbs of 0.001 m² or less, where a cut clips the corner of a tiny footprint fragment, are dropped.
