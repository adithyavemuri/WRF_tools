# Beginner examples: reports, animations and comparisons

The script [`create_hindcast_report.py`](create_hindcast_report.py) is a
small, readable starting point. It does not assume that you already know the
variable names inside a WRF output file.

Run all commands from the root of the `WRF_tools` repository after following
the installation instructions in the main README.

For the complete API rather than only the report, start with the
[chaptered showcase](showcase/README.md):

```bash
python examples/showcase_all_capabilities.py --output example_results/my_showcase
```

It accounts for all public functions, explicitly distinguishes synthetic inputs
from real data, and documents the three real external prerequisites. For your
own observations, use [compare_observations.py](compare_observations.py).

## 1. Create the standard report

Replace `/path/to/wrf/run` with the directory containing files such as
`wrfout_d01_...` and `wrfout_d02_...`:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --output example_results/my_first_report \
  --domain d02
```

Open `example_results/my_first_report/hindcast-report.pdf` when it finishes.
The default attempts all six connected diagnostic groups, including Q criterion
and Stull stability diagnostics. Missing-input reasons are visible. Use
`--diagnostics none` for the compact core or
`--diagnostics thermodynamics,flow_structure` for selected groups.
Edit `DIAGNOSTIC_OPTIONS` near the top of the Python example for numerical
choices; the CLI alternatively accepts [diagnostics.toml](diagnostics.toml).
See [connected workflows](../docs/CONNECTED_WORKFLOWS.md) for the complete guide,
public function catalog and editable recipes for external-data capabilities.
The report includes the new four-panel wind overview for each domain with
3-D wind/height fields, plus an appendix explaining the methods and references.
Its PNG/SVG figures and JSON methods files are saved beside the single complete
PDF. Standalone figure APIs can optionally export individual PDFs separately.
The report automatically includes every WRF domain found in the run directory;
`--domain d02` selects the primary domain for point-based diagnostics.

## 2. Discover what your WRF run contains

Different physics configurations write different variables. Ask the example
to print the variables, dimensions and units actually present in your files:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --domain d02 \
  --list-variables
```

You might see fields such as `PBLH`, `HFX`, `T2`, `PSFC`, `RAINC` and
`RAINNC`. A variable not written by your WRF configuration cannot be plotted
after the simulation.

## 3. Make one extra map

Use a name from the variable list:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --output example_results/pbl_height \
  --domain d02 \
  --plot-variable PBLH \
  --time-index -1
```

This creates `custom_pblh_map.png`. The value `-1` means the final output
time. Other useful two-dimensional examples are:

```bash
--plot-variable HFX
--plot-variable T2
--plot-variable PSFC
--plot-variable RAINNC
```

For a three-dimensional mass-grid field, also choose a model level. This
example maps water-vapour mixing ratio at the lowest model level:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --domain d02 \
  --plot-variable QVAPOR \
  --level-index 0
```

Raw `U`, `V` and `W` use WRF's staggered grid. The beginner map intentionally
rejects those fields because they must be destaggered before they can be
compared or combined correctly.

## 4. Choose a location for vertical profiles

Pass both coordinates together:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --domain d02 \
  --latitude 52.0 \
  --longitude 5.0
```

If coordinates are omitted, WRF_tools uses the centre of each domain.

## What can be changed quickly?

You can immediately change the input directory, output directory, primary
domain, point location, custom variable, time and vertical level. The clearly
labelled `STEP 1` block near the top of the Python script contains the same
settings for users who prefer editing a file and running it from an IDE.

The main PDF currently has a curated layout and set of diagnostics. The
custom-variable option deliberately writes a separate PNG; it does not insert
an arbitrary field into the scientific report or guess how that field should
be interpreted. Changing PDF page composition or adding a new diagnostic still
requires a small code change in `src/wrf_tools/hindcast.py`.

## 5. Animate the actual output times

```bash
.venv/bin/python examples/animate_wrf_wind.py /path/to/wrf/run \
  --domain d02 --maximum-frames 7
```

This writes a fixed-scale GIF, PNG frames and a methods manifest to
`example_results/wind_animation/`. `--fps 1` means one playback frame per second,
not one simulated second. The saved WRF timestamps remain visible.

For optional 3-D Manim contours, editable figure APIs and scientific conventions,
follow [the visualization guide](../docs/VISUALIZATION.md). Manim is not required
for the PDF or GIF and requires its own native rendering dependencies.

The previous slideshow has been removed. Use
[`export_3d_contours.py`](export_3d_contours.py) and
[`manim_wrf_contours.py`](manim_wrf_contours.py) for real contour geometry at
multiple physical heights, fixed thresholds, timestamps and explicit vertical
exaggeration. See the guide for the separate preparation/rendering commands.

## 6. Compare simulations: plots only

Try the clearly labelled synthetic example first; no simulation is launched:

```bash
.venv/bin/python examples/compare_simulations.py --demo
```

Then supply your real runs:

```bash
.venv/bin/python examples/compare_simulations.py \
  --case Control=/path/to/control/wrf --case MYNN=/path/to/mynn/wrf \
  --domain d02 --latitude 52 --longitude 5 --baseline Control
```

This writes PNG/SVG time-series and profile plots, not a PDF. Add more named
`--case` arguments if useful. The script prints the nearest cell selected in
each run. It compares matching timestamps and common physical profile heights.
Different timestamps require an explicit `--alignment intersection` choice.

Edit the labelled `read_site()` function to choose other diagnostics; edit
`HEIGHTS_AGL` and `PROFILE_TIME_INDEX` for profile selection. Plot functions
return Matplotlib axes for your own labels, limits and layouts. Nothing is
automatically averaged or interpreted. See the
[comparison guide](../docs/COMPARISON.md) for explicit uniform/area/layer
weighting and native-level versus common-height settings.

## 7. Horizontal, selected-area, vertical and time means

The site-comparison script above does **not** demonstrate all averaging modes.
Use the separate, editable [`average_wrf_fields.py`](average_wrf_fields.py):

```bash
.venv/bin/python examples/average_wrf_fields.py --demo
# Or use your existing output (no new simulation is launched):
.venv/bin/python examples/average_wrf_fields.py /path/to/wrf/run --domain d02
```

Edit its `STEP 1` settings: variable, start/end times, area weighting, region
bounds, native levels versus physical heights, AGL/MSL reference, vertical
layer bounds, and equal-cell versus layer-thickness weighting.

| Operation | Output |
|---|---|
| Horizontal mean | Full-domain profile at every timestamp; several displayed curves |
| Selected-area mean | Region profiles at every timestamp and a region layer-mean time series |
| Vertical mean | Map averaged within your specified physical layer, at the selected timestamp |
| Time mean | Layer-mean map and horizontal-mean profile over your selected period |

PNG/SVG plots and `averaged_fields.nc` go to `example_results/averaging/` by
default. The NetCDF retains **all selected timestamps** for profiles and layer
maps, even though the example displays only some profile curves and one map.
Reopen it with `xarray.open_dataset()` to replot or supply reduced series/profiles
to the comparison API. `SAVE_REDUCED_DATA = False` disables saving the means.

Time means are explicitly equal-sample means, not duration-weighted means for
irregular output. Vertical means use layer-representative values; physical
boundary layers are clipped by overlap thickness. Model-index plots are labelled
as indexes, not metres. This short-period teaching example loads selected 3-D
fields in memory; it is not an automatic parallel, long-run reduction engine.
