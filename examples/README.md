# Beginner example: make and extend a WRF report

The script [`create_hindcast_report.py`](create_hindcast_report.py) is a
small, readable starting point. It does not assume that you already know the
variable names inside a WRF output file.

Run all commands from the root of the `WRF_tools` repository after following
the installation instructions in the main README.

## 1. Create the standard report

Replace `/path/to/wrf/run` with the directory containing files such as
`wrfout_d01_...` and `wrfout_d02_...`:

```bash
.venv/bin/python examples/create_hindcast_report.py /path/to/wrf/run \
  --output example_results/my_first_report \
  --domain d02
```

Open `example_results/my_first_report/hindcast-report.pdf` when it finishes.
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
