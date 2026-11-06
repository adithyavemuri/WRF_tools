# Reports for one run or a physics ensemble

## One run

The standard report still includes every domain by default. `--domain` selects
the primary domain; `--report-domains` filters the domains actually evaluated:

```bash
wrf-tools hindcast-report runs/control/wrf reports/control
wrf-tools hindcast-report runs/control/wrf reports/control-d02 --report-domains d02
```

## An ensemble

Give every completed simulation a unique name. This reads existing output;
it does not run, configure or clone WRF simulations:

```bash
wrf-tools ensemble-report reports/ensemble \
  --member control=runs/control/wrf \
  --member alternative=runs/alternative/wrf \
  --report-domains d02 --contour-member mean
```

Add `--member NAME=FOLDER` for additional simulations. Omit `--report-domains`
to evaluate all domains. All reference domains remain visible in the layout
overview even when only d02 is evaluated.

Every variable pairs a time series of **all named members plus a thicker
dashed mean** with a map. Maps default to the ensemble mean. Choose
`--contour-member control` to map that member without hiding other traces.
Use a different output directory to keep both report versions.

Defaults include 10 m wind speed, 2 m temperature, surface pressure, PBL
height, surface heat/radiation fluxes, friction velocity, accumulated
precipitation and model TKE at 100 m AGL when available in every member.
Missing defaults are recorded, not assigned zeros.
`--variables wind_speed_10m,T2,PBLH` chooses a smaller suite; native 2-D
surface/mass-grid scalars are accepted too. Explicit missing fields fail.
Arbitrary 3-D variables need a separate explicit reduction.

Outputs: `ensemble-report.pdf`, `ensemble-report.html`, domain map, paired
PNG figures and `ensemble-summary.json`. JSON stores member and mean site
series, timestamps, units, physics and input filenames, not full datasets
or numeric contour grids. For editable Python settings, use
[create_ensemble_report.py](../examples/create_ensemble_report.py).

## What the mean means

Members receive equal weights. Diagnostics are computed per member before
averaging: mean wind speed is not speed of the mean vector. Native TKE
conventions are identified; PBL and dynamics/SGS energies are not mixed.
100 m TKE uses physical-height interpolation without extrapolation.
NaNs propagate; there is no hidden change in ensemble size.

Contours are equal-history-sample temporal means after member averaging,
except precipitation (final minus initial accumulation). They are not
duration-weighted means for irregular output. Counter resets are rejected.
Site plots use the nearest cell, not an area average. Members need identical
times, coordinates, terrain, projection and resolution: no automatic regridding.

These are model sensitivity diagnostics, not observational validation,
calibrated uncertainty, P50/P90 or annual energy. Review spin-up and short
demonstration periods. Conventions follow the
[WRF ARW technical note](https://doi.org/10.5065/1dfh-6p97).
