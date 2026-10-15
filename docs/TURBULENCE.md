# TKE and diagnosis of model behaviour

The report now detects **model-written** TKE and adds a four-panel diagnostic:
final lowest-mass-level map, site profiles, site evolution at physical AGL
heights, and domain maximum at every native level/time. It also records domain
means per native level and counts negative/non-finite values. PNG/SVG and
JSON methods/statistics files accompany the report. TKE is specific energy,
in m²/s², not total domain energy in joules.

## Which energy is plotted?

| Input | Conversion | Meaning |
|---|---|---|
| `QKE` | Divide by two | MYNN parameterized TKE |
| `TKE_PBL` | Direct | PBL model-provided TKE |
| `TKE` / `tke` | Direct | Model dynamics/SGS TKE |

Names and definitions follow the
[WRF v4.7.1 Registry](https://github.com/wrf-model/WRF/blob/v4.7.1/Registry/Registry.EM_COMMON)
and [WRF PBL documentation](https://www2.mmm.ucar.edu/wrf/users/wrf_users_guide/build/html/physics/pbl.html).
This is a supported-name mapping, not discovery of every scheme's energy variable.
Auto selection prefers QKE, then TKE_PBL, then TKE. Available alternatives are
listed; they are never summed. Select a particular source explicitly:

```bash
wrf-tools hindcast-report /path/to/wrf/run reports/tke --tke-variable QKE
```

Native interface values are averaged onto adjacent mass levels when needed.
This collocation is recorded; it is not an exact energy-conserving remapping.
Negative values are retained rather than clipped away. No universal excessive-
TKE threshold is imposed. Unweighted native-level means/maxima are deliberately
labelled as such, not treated as area-weighted means at common physical heights.

In Python, use `wrf_tools.turbulence.model_tke(dataset, source='QKE')` to retrieve
the converted field. In `average_wrf_fields.py`, select `VARIABLE = 'model_tke'`
to apply the existing horizontal/region/layer/time reductions to supported TKE.
Raw `VARIABLE = 'QKE'` still means raw twice-TKE, not converted TKE.

## What our real demonstration can show

The existing Netherlands d01/d02 demonstration uses YSU (`bl_pbl_physics=1`)
with `km_opt=4`; its files contain no QKE, TKE_PBL or TKE. Its regenerated report
explicitly says **TKE unavailable**, and does not fabricate a turbulence plot.
Positive-path TKE plots/conversions are tested with labelled synthetic fixtures,
not represented as real TKE results. Enabling a history field cannot create
a prognostic quantity that the selected physics does not calculate.

The new 3-D contour example therefore uses **real wind speed**, not invented TKE.
To use TKE, select `VARIABLE='model_tke'` and suitable energy contour thresholds
in `export_3d_contours.py`, with a run that actually writes the required field.
The exporter fails clearly if TKE is missing; it never substitutes wind energy.

## What would establish spurious energy injection?

Large or increasing TKE is a **location/time signal to investigate**, not proof
of a numerical error. Shear and buoyancy can legitimately generate turbulence.
Diagnosis requires appropriate sampling, spin-up/context, comparison runs and,
for attribution, tendencies for production, transport, dissipation and numerical
terms. WRF budget-output fields can be scheme-dependent increments rather than
rates; check their units and implementation before combining them.

The existing `diagnostics.tke_budget` helper returns resolved variance plus
vertical shear and buoyancy terms. Its own implementation omits transport,
pressure correlations, dissipation and SGS terms. It is **not a closed WRF TKE
budget**. It is now connected to the report's `turbulence` group. That group
requires an explicit time-averaging choice and sampling policy in
[diagnostics.toml](../examples/diagnostics.toml); otherwise its unavailability
is stated in the report. See [connected workflows](CONNECTED_WORKFLOWS.md).

Likewise `resolved_tke`, Reynolds fluxes and turbulence intensity need a defined
averaging/decomposition and sufficiently resolved samples. Variance across seven
hourly states includes evolving mesoscale flow and is not an LES turbulence
measurement. Parameterized, resolved, SGS and total TKE remain distinct. See
[Pope (2000)](https://doi.org/10.1017/CBO9780511840531) and
[Stull (1988)](https://doi.org/10.1007/978-94-009-3027-8).
