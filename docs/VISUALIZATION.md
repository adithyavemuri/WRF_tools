# Scientific figures and animations

The hindcast report now includes a wind overview for every domain with the
required fields: a geographic wind map, a matching native grid-row section,
site evolution on physical heights and selected profiles. The overview replaces
the standalone final wind map and old mean-height time-height diagram. Other
meteorological maps, temperature/TKE profiles and diagnostics remain available.

## Create a report

From the WRF_tools repository after its normal local installation:

```bash
.venv/bin/wrf-tools hindcast-report /path/to/wrf/run reports/my_case \
  --domain d02 --latitude 52.0 --longitude 5.0
```

This creates the regular PDF/HTML/JSON report and, for each supported domain:

```text
d02_wind_overview.png    report-ready overview
d02_wind_overview.pdf    standalone figure with vector text/lines
d02_wind_overview.svg    editable figure (coloured fields are rasterized)
d02_wind_overview.json   variables, methods, references and input filenames
```

The report includes a scientific-methods appendix with references. Missing
three-dimensional fields disable only the overview, with the reason recorded
in the domain summary. A missing PBLH field omits the PBL-height line. If rotation
fields are missing, map arrows are omitted and grid-relative direction summaries
are explicitly labelled. Invalid rotation fields cause a clear error.

The PNG used in the PDF is deliberately large enough to keep all four panels
readable. Standalone figure files allow individual reuse in presentations.

## Edit a figure in Python

```python
from wrf_tools.io import discover_wrfout, open_wrf_sequence
from wrf_tools.grid import nearest_grid_point
from wrf_tools.visualization import plot_wind_overview

files = discover_wrfout('/path/to/wrf/run', domain='d02')
with open_wrf_sequence(files) as dataset:
    cell = nearest_grid_point(dataset.XLAT.isel(Time=0),
                              dataset.XLONG.isel(Time=0), 52.0, 5.0)
    figure, methods = plot_wind_overview(
        dataset, cell, domain='d02', time=-1, top=2000,
        # limits=(0, 20),   # optionally impose a fixed wind scale
        # section_row=50,  # optionally use another native grid row
    )
    # Matplotlib axes remain accessible for deliberate customization.
    figure.axes[-1].set_title('My selected wind profiles')
    figure.savefig('my_overview.pdf')
```

Close the figure with `matplotlib.pyplot.close(figure)` when finished. The
returned methods dictionary can be saved with the exported figure. Prefer
`save_wind_overview(..., sources=files)` for automatic PNG/PDF/SVG and JSON export.

## Simple data animation

```bash
.venv/bin/wrf-tools animate-wind /path/to/wrf/run reports/wind_movie \
  --domain d02 --fps 1 --maximum-frames 7
```

Or follow the labelled example:

```bash
.venv/bin/python examples/animate_wrf_wind.py /path/to/wrf/run --domain d02
```

Both produce a GIF, numbered PNG frames and an animation JSON manifest. The
colour limits are fixed across frames. Playback speed is separate from simulation
time; no atmospheric states are invented between actual output times. Use
`--stride 2` to select every second saved time, or `--limits 0 20` for an explicit
wind scale. The manifest records the selection, times, scale and processing.

For a long sequence, an existing FFmpeg installation can write MP4:

```bash
.venv/bin/wrf-tools animate-wind /path/to/wrf/run reports/wind_movie \
  --domain d02 --format mp4 --fps 2
```

Input frames are read individually. GIF encoding still retains rendered images
in memory; MP4 is the preferred long-sequence option. This is a stationary-grid
10 m wind animation, not a generic movie of every WRF diagnostic. Incompatible
grids, moving coordinates and overlapping history times are rejected.

## Optional Manim: actual model contours in 3-D

The presentation/slideshow example has been retired. The replacement renders
**actual field isolines at physical heights**, not PNG maps or teaching cartoons.
It is a stack of horizontal contours, not volumetric isosurfaces or an interactive
viewer. Scientific preparation is separate from rendering:

```bash
.venv/bin/python examples/export_3d_contours.py /path/to/wrf/run --domain d02

WRF_CONTOURS=example_results/contours3d/contours.json \
  .manim-env/bin/manim --renderer cairo --resolution 1600,900 --fps 15 \
  --media_dir example_results/contours3d/render --output_file wrf-3d-wind \
  examples/manim_wrf_contours.py WRFContours
```

Edit the exporter settings to choose wind speed or model TKE, AGL/MSL heights,
fixed contour values, vertical exaggeration and the number of actual records.
The example uses 100/500/1000/1500 m MSL, 4/8/12/16/20 m/s isolines and an
explicit 150× vertical exaggeration. All heights/times use the same colour key.
Interpolation is column-specific and does not extrapolate through terrain or
beyond supported levels. The camera is held fixed while time advances and
rotates only around the final saved state. There is no temporal morphing.

The pale base outline is the model LANDMASK boundary, not high-resolution
cartographic coastlines. Horizontal coordinates are nominal native grid-km;
an AGL stack is an AGL-coordinate display, not a geometric MSL terrain scene.
Thresholds, physical levels, input filenames, unsupported fractions and display
exaggeration are preserved in the JSON geometry export. No geometry is smoothed
or silently decimated. See [TKE diagnosis](TURBULENCE.md) for interpretation limits.

The Linux example was rendered with Manim Community 0.19.0, Python 3.11 and
Cairo using seven actual d02 records. This is a format proof of concept, not an
automatic detector of energy injection. Static contours can reveal where large
values occur; only a suitable energy budget can identify their source.

Manim remains optional. Its native Cairo/Pango dependencies must be available;
see [official installation instructions](https://docs.manim.community/en/stable/installation.html).
With an existing Conda installation, a separate non-root prefix can supply them:

```bash
conda create --prefix .manim-env --override-channels --channel conda-forge \
  python=3.11 manim=0.19.0 --yes
```

The renderer only needs Manim and the geometry file, not xarray or a second WRF
installation. No LaTeX is required. For interactive clipping, isosurfaces and
volume exploration, VAPOR remains a better-suited complementary tool and already
supports native WRF files; a separate converter is not required for those files.

## Scientific processing contract

- Heights use WRF gravity `g=9.81 m/s²`, the mass-level average of `(PH+PHB)/g`,
  and subtraction of HGT for AGL. The cross-section is MSL; site profiles are AGL.
- U and V are averaged from their respective staggered points before a mass-grid
  horizontal magnitude is calculated. Surface arrows are rotated using
  COSALPHA/SINALPHA. Meteorological direction is the direction **from** which
  wind blows; calm samples have no direction and are excluded from the mean.
- Site wind is linearly interpolated in physical height independently at every
  time, without extrapolation below or above the available column. Missing
  supported heights remain blank. A native grid-row section is not a
  constant-latitude transect.
- Profile temperature follows the dry-theta convention with WRF reference
  temperature 300 K and `Rd/cp=2/7`. Check the variable convention of custom
  or modified WRF output.
- Normalization is shared between the overview's coloured panels. Wind roses
  and summary means remain unweighted grid-cell/history-sample statistics,
  not area-weighted or time-weighted climatologies. Speed percentiles are not
  energy-yield P50/P90 values.
- Parameterized TKE, resolved TKE and turbulence intensity retain separate
  meanings. Existing QKE/2 processing assumes the documented twice-TKE variable
  convention; no resolved fluctuations are manufactured from hourly outputs.
- The overview currently rejects antimeridian-crossing maps. Standard Lambert,
  polar stereographic and Mercator metadata are supported; other maps are
  displayed explicitly using geographic XLAT/XLONG coordinates.

Analytical tests check rotation, speed invariance, staggering, known dry
temperature states, time-dependent heights and interpolation boundaries. Output
tests check reference/provenance sidecars, file formats and animation timestamps.
These tests establish processing behavior, not the meteorological accuracy of
the input simulation. See [Scientific methods](SCIENTIFIC_METHODS.md).

VAPOR already imports native WRF output. VAPOR-specific export of additional
derived fields is a later, separate feature; no new 3-D renderer is included.

Simple independent-simulation time-series/profile plots and explicit averaging
choices are available in the [comparison guide](COMPARISON.md). Automatic
multi-simulation reports and managed reduction caches are not included.
