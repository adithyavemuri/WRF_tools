# Simple simulation comparisons

This is a plotting toolbox, not an automatic research study. Supply named,
already-selected results; choose what the experiment means yourself. No PDF or
comparison document is generated. There is no fixed case-count limit; start with
two to four curves per axis for legibility, and split larger experiments yourself.

## Try it without WRF data

From the installed repository:

```bash
.venv/bin/python examples/compare_simulations.py --demo
```

The **explicitly synthetic** example writes time-series and profile overlays,
plus known +1 m/s differences from a baseline, as PNG/SVG plots. It is a software
check, not evidence that a physics scheme is better.

## Compare real runs

```bash
.venv/bin/python examples/compare_simulations.py \
  --case Baseline=/path/to/control/wrf \
  --case MYNN=/path/to/mynn/wrf \
  --domain d02 --latitude 52 --longitude 5 \
  --baseline Baseline --output example_results/my_comparison
```

Add more `--case NAME=PATH` arguments if needed. Use distinct names. The example
plots site 10 m speed over time and profiles at the last common timestamp on a
user-editable common AGL grid. Edit `HEIGHTS_AGL`, `PROFILE_TIME_INDEX` and the
clearly labelled `read_site()` function for other diagnostics.

Each run is read independently, so grids may differ. The example prints the
actual nearest-cell location for each run: you must decide whether these sample
locations and land-use/terrain differences are acceptable. A nearest cell is
returned even for an outside-domain target; inspect those locations. The example
assumes a stationary domain and ordinary WRF U/V/PH/PHB/HGT fields.

Default `--alignment exact` rejects different timestamps. Explicitly choose
`--alignment intersection` to retain only shared timestamps. Neither option
interpolates time. No shared timestamp means an error. Profiles are selected at
the same retained timestamp, not each run's independent final time.

## Use the small plotting API

```python
from wrf_tools.comparison import plot_timeseries, plot_profiles

# Each value is a 1-D xarray.DataArray with units and explicit coordinates.
cases = {"Control": control_series, "Experiment": experiment_series}
figure, axes = plot_timeseries(cases, value_label="Wind speed")
axes.set_title("My physics sensitivity experiment")
figure.savefig("wind_comparison.svg")

# Pass baseline="Control" for experiment-minus-control differences.
# Profiles need common height coordinates with units='m' and reference='AGL'
# or 'MSL'; do not label native eta indexes as physical heights.
figure, axes = plot_profiles(profile_cases, baseline="Control",
                             value_label="Wind speed")
```

Units must match exactly; convert first. These are linear differences, not
circular-direction differences, percentage changes or significance tests.
Researchers choose matching periods, spin-up removal, domains, heights, masks,
and the diagnostic definition. The package does not establish comparability
from a matching variable name. Different horizontal fields are never silently
regridded or subtracted by these 1-D plotting functions. Arbitrary maps, automatic
research interpretation, and comparison PDFs are deliberately outside this API.

## User-controlled averaging

The separate `wrf_tools.averaging` helpers are optional. Nothing is averaged by
the plotting functions themselves. `weighting` is a required user choice:

For a runnable example of **all four reductions**, use
[`average_wrf_fields.py`](../examples/average_wrf_fields.py), rather than the
site-only comparison example:

```bash
.venv/bin/python examples/average_wrf_fields.py --demo
.venv/bin/python examples/average_wrf_fields.py /path/to/wrf/run --domain d02
```

Its editable settings select the field, time period, region, weights and
coordinate reference. It writes separate PNG/SVG plots and reduced NetCDF, not
a report. Horizontal/region profiles and layer-mean maps retain all selected
times in NetCDF. Its time means are equal-sample means; the two time-mean plots
are the time mean of the horizontal profile and of the vertical-layer map.
It deliberately loads selected fields in memory: start with a short period.

```python
from wrf_tools.averaging import layer_thickness, mean, to_height, wrf_cell_area

horizontal = ["south_north", "west_east"]

# Equal finite grid cells at each native model level (NOT equal physical height).
native_profile = mean(field, horizontal, weighting="uniform")

# Cell-area weighting over a researcher-selected boolean mask on this grid.
# Standard conformal WRF grids only; other grids need supplied cell areas.
area_profile = mean(field, horizontal, weighting="area",
                    weights=wrf_cell_area(dataset), mask=region_mask)

# OR FIRST interpolate every column to common physical heights, THEN average.
# height_agl must already be destaggered/co-located, in metres AGL.
at_height = to_height(field, height_agl, [50, 100, 200, 500], reference="AGL")
physical_profile = mean(at_height, horizontal, weighting="area",
                        weights=wrf_cell_area(dataset), mask=region_mask)

# Vertical mean: supply layer thicknesses in metres on the field's mass grid.
# For a bounded physical layer, use the thickness overlapping those bounds.
thickness = layer_thickness(interface_heights_agl, 50, 200)
layer_map = mean(field, "bottom_top", weighting="layer", weights=thickness)

# Time mean of that layer map over the period you selected.
time_map = mean(layer_map, "Time", weighting="uniform")
```

`field`, `dataset`, `region_mask`, `height_agl` and `interface_heights_agl` are the
researcher's selected DataArrays/dataset, not magic package variables.
For a static mask/area field from time zero, drop its Time dimension with
`.isel(Time=0, drop=True)` before reuse. Weights/masks must be co-located; indexed
dimensions must match exactly. Area weights use `DX*DY/MAPFAC_M**2` for standard
Lambert/polar/Mercator grids. No missing-map-factor fallback is made.
See the [WRF technical description](https://doi.org/10.5065/1dfh-6p97) for map
and model-coordinate conventions.

Uniform, area and layer means are distinct; no implicit density/mass weighting
is applied. A layer-weighted average treats each supplied value as representative
of its supplied thickness; it is not an exact continuous integral or an inferred
vertical interpolation. Do not apply vertical averaging to wind direction as a
linear scalar. Mean speed differs from the speed of mean vector components.

Common-height interpolation uses each column's own heights, does not extrapolate,
and does not bridge missing samples. Means exclude non-finite data and renormalize
over valid weights. Consequently coverage can change with height/time: inspect
that coverage or impose a consistent mask for your study. Empty selections return
NaN. The new interpolation helper is eager/in-memory, not a large-data engine.
No automatic multiprocessing, reduction-cache invalidation or pickle loading is
introduced in this milestone. Reduced arrays can already be explicitly saved
with `physical_profile.to_netcdf("profile.nc")` and reopened using xarray.

Coordinate matching and reductions follow xarray's
[alignment](https://docs.xarray.dev/en/stable/generated/xarray.align.html) and
[weighted-computation](https://docs.xarray.dev/en/stable/user-guide/computation.html#weighted-array-reductions)
conventions. Analytical tests check known offsets, shared samples, weighting,
missing cells and native-level versus physical-height averaging. This is not
validation of the simulations against observations.
