# A model cutout: isosurfaces over terrain and ocean

This optional example renders actual three-dimensional diagnostic
surfaces above WRF's terrain and land/water mask. It is separate from the
existing stacked-contour example and from the PDF report. It does not identify
a cyclone automatically or turn a regional simulation into a global model.

## Interactive browser view: rotate and zoom yourself

An MP4 has a predetermined camera path. For an actual interactive figure,
create a standalone HTML file instead:

```bash
python -m pip install -e ".[isosurface,interactive]"
python examples/interactive_isosurfaces.py /path/to/wrf/run --domain d02 \
  --top full --output example_results/diagnostic-explorer
```

Double-click `example_results/diagnostic-explorer/viewer.html` in your file
manager, or open it from your browser. It embeds its JavaScript and geometry:
no server, internet connection or Manim is needed to view it. A WebGL-capable
browser is required. Use [the editable script](../examples/interactive_isosurfaces.py)
to change defaults, or `--geometry /path/to/geometry.json` to reuse an export.

This is a snapshot of saved `wrfout` states, not a real-time WRF connection.
New model outputs are included only when you regenerate the export. The time
slider switches between saved timestamps; no intervening states are invented.
Controls, plot and footer occupy separate responsive rows so the selection bar
does not cover labels or legends. On short windows, scroll the page or the
controls panel; the methods panel also has its own scrollable content.

### Diagnostic selector and movable vertical section

The interactive example now exports five requested diagnostics by default:

| Field | Meaning / units | What it does not establish |
|---|---|---|
| Horizontal wind speed | Mass-grid `hypot(U,V)`, m/s | Turbulence intensity or energy production |
| Vertical velocity | Mass-grid `W`, m/s; positive upward | A turbulent momentum or heat flux |
| Vertical relative vorticity | Radial curl of Earth-relative velocity, s⁻¹ | Planetary vorticity, cyclone identification or a vortex by itself |
| Q criterion | `0.5*(||Omega||²-||S||²)`, s⁻² | Turbulent transport, a complete energy budget or a universal compressible-flow vortex definition |
| Model TKE | Supported native energy; `QKE/2`, or supported `TKE_PBL`/`TKE` directly | Resolved/total TKE; these sources are not added together |

Use **Field** to switch diagnostics, **Saved time** for actual output states,
and **Vertical section** to choose a native x-z or y-z curtain. Move **Position**
to inspect a different sampled row/column. The section uses actual MSL heights,
not a rectangular model-level-as-altitude plot. **Terrain + section only**
removes occluding isosurfaces. Section colours are scalar values; blue/red
negative/positive isosurface colours indicate sign, not a second variable.
Choose **Terrain + surfaces only** to keep terrain and isosurfaces visible
without the vertical section. That choice persists when changing time or field.

Use **Height window (m MSL)** to enter a lower/upper height and click **Apply
height**. For example, `0` to `500` focuses on the lowest 500 metres above sea
level. This is **MSL, not height above local terrain**: elevated ground can lie
outside that window. Limits must lie inside the exported extent. **Full export**
restores that extent; data above an export-time `--top` cannot be recovered by
the browser without re-exporting. The selected band persists across fields,
times and view modes, and the camera is preserved.

**Fit vertical view** (enabled initially) adjusts vertical exaggeration to keep
a shallow layer visible; the scale dropdown displays the actual new factor.
Disable it to preserve your chosen physical aspect exaggeration. This is a
display zoom, not finer model resolution or new turbulence information.

Height limits clip existing mesh triangles and coastline segments to horizontal
MSL planes; no closed caps are invented. Terrain above/below the band is clipped
too, not shifted to a fictitious ground level. Sections linearly interpolate
only within each native column's saved vertical brackets at the two bounds;
wholly unsupported columns remain gaps. Original exported volumes, thresholds
and per-field colour ranges do not change. Empty intersections are reported.
The browser regression includes analytical triangle/line/section checks,
clipping across fields/times, invalid-range rejection and full-height restoration.

For wind-farm inspection, use model TKE if your configuration saved a supported
energy field, and resolved velocity/vorticity/Q for their stated purposes. A
height zoom does not make hourly kilometre-scale output resolve turbine wakes
or make parameterized TKE equivalent to resolved turbulent structures.

Edit the readable `DIAGNOSTICS` mapping in the example for per-field thresholds.
The initial numbers are demonstration choices, not detection standards. Every
field has its own units; thresholds and colour limits remain fixed over the
exported times. Empty threshold intersections are reported, not fabricated.
Missing source fields disable that field and explain why in the methods panel.
Invalid geometry, nonfinite fields and inconsistent units fail visibly.

To export only selected diagnostics:

```bash
python examples/interactive_isosurfaces.py /path/to/wrf/run --domain d02 \
  --diagnostics wind_speed vertical_velocity q_criterion \
  --output example_results/my-diagnostic-explorer
```

Use `--single-variable --thresholds 12 16` for the previous wind-only mode.
Existing schema-v1 JSON exports and the separate Manim movie remain supported.
The diagnostic mode uses schema v2 and is **not** input for the v1 Manim scene.
The standalone HTML embeds selected meshes and sampled scalar volumes, so no
Python server is needed to move a section. It cannot invent a new diagnostic
that was not selected at export. More fields/times and lower stride increase
file size and browser-memory demand; `--maximum-faces` is an explicit budget,
not automatic mesh decimation. The Python figure API gives the initial scene;
`write_isosurface_html` adds the full offline controls.

### Scientific method for the new derivative diagnostics

The existing uniform-Cartesian `diagnostics.advanced.q_criterion` helper is
unchanged. The interactive diagnostic exporter does **not** apply that helper
directly to terrain-following levels or use nominal DX/DY as true distances.

1. Destagger U/V/W onto mass points; obtain MSL height from `(PH+PHB)/9.81`.
2. Rotate U/V to local east/north using COSALPHA/SINALPHA, then express the
   velocity in a shared Earth-fixed Cartesian basis, including radial W.
3. Embed geographic mass points as `X=(R+z)*up(latitude,longitude)` using a
   spherical Earth. The explicit radius defaults to WRF's 6,370,000 m.
4. Differentiate position and velocity in native indices on the **full** grid.
   The chain rule gives `A=dV/dX=(dV/di)*(dX/di)^(-1)`. This accounts for
   sloping/nonuniform vertical coordinates and changing wind basis. Central
   index differences are used inside, one-sided differences at boundaries.
5. Form Q from the symmetric/antisymmetric parts of A; project curl onto local
   radial up for vertical relative vorticity. Only then subsample for display.

This is a finite-difference physical reconstruction on a spherical geometric
embedding, **not WRF's discrete shallow-atmosphere dynamical stencil**, a
conservative flux operator, or an ellipsoidal calculation. In particular,
spherical geometry includes height-dependent radius. Derivative/boundary
errors remain, and destaggering modifies the effective sampling. Singular
grids, missing rotations and nonfinite samples are not silently approximated.
Native x/y display axes still use nominal grid distances; they are presentation
coordinates, distinct from the physical coordinates used for derivatives.

Analytical tests recover arbitrary affine Cartesian velocity tensors on sloped
grids, check rotation/strain/shear/translation independently, and verify the
complete spherical/wind-rotation chain against an exact affine field. They
test equations and coordinate reconstruction, not atmospheric accuracy.

Primary references/conventions:

- [WRF-ARW technical note](https://doi.org/10.5065/1dfh-6p97) for model coordinates.
- [WRF v4.7.1 constants](https://github.com/wrf-model/WRF/blob/v4.7.1/share/module_model_constants.F) for the spherical radius.
- [WRF support: Earth-relative wind rotation](https://forum.mmm.ucar.edu/threads/converting-model-grid-relative-wind-to-earth-relative-wind.179/) for COSALPHA/SINALPHA conventions.
- [Jeong & Hussain (1995)](https://doi.org/10.1017/S0022112095000462) for vortex criteria and their distinctions; Q is a rotation/strain diagnostic, not an energy-production term.

Hourly kilometre-scale output can illustrate resolved weather structures; it
does not substantiate LES-scale eddies or temporal turbulent covariances. W is
not `mean(w' theta')` or `mean(u' w')`. Flux budgets, sea-level-pressure
calculation/overlay, lambda2, swirling strength and arbitrary new derived
variables are **not** added by this viewer. Those require separate methods
and tests; pressure contours are not invented from surface pressure.

The [diagnostic browser acceptance record](validation/diagnostic-viewer-acceptance.json)
records the real-data export and offline interaction checks. To repeat the
optional browser check with an already installed Chrome and Playwright in a
test environment (not required to use the viewer):

```bash
python tests/browser/check_diagnostic_viewer.py /path/to/viewer.html
```

This tests field/time switching, mouse orbit/zoom, stationary terrain, persistent
camera/opacity, both native section orientations and fixed colour limits. The
ordinary pytest suite independently checks the formulas and export contracts.

### Open it, or fix a WebGL error

From the repository root, this opens the already-generated HTML without running
WRF again or regenerating meshes:

```bash
python examples/open_interactive_viewer.py
```

You can supply a different local HTML path as the first argument. If Chrome
says WebGL is unavailable, first visit `chrome://settings/system`, enable
**Use graphics acceleration when available**, and relaunch Chrome. Check
`chrome://gpu` for remaining errors. Do not change graphics drivers or system
packages just to open this example. An HTML file cannot enable browser graphics
or bypass a graphics-driver block, and a web server does not fix disabled WebGL.
The generated HTML now checks graphics before Plotly starts and shows these
instructions when a context cannot be created.

If hardware rendering cannot be used, there is an explicit software fallback:

```bash
python examples/open_interactive_viewer.py --software-webgl
```

This starts Chrome/Chromium with a separate temporary profile; it leaves your
normal profile and settings untouched. Chrome must already be installed; use
`--chrome /path/to/chrome` if automatic discovery fails. Close the isolated
browser window to finish the launcher and clean its temporary profile.

**Security and performance:** SwiftShader renders on the CPU and can be slower.
Chromium documents its opt-in flag as providing lower WebGL security guarantees.
Use this isolated window only for trusted local viewer files, not general
web browsing. Software mode is never enabled automatically. The launcher does
not disable Chrome's sandbox and requires no root access. See
[Chromium's SwiftShader documentation](https://github.com/chromium/chromium/blob/main/docs/gpu/swiftshader.md).

### Inspect the scene

- Drag to rotate; scroll to zoom. Use the pan tool to move the view.
- Select actual timestamps with the slider, or use Play/Pause. Time changes
  update only wind/TKE meshes, never terrain or the camera.
- Select **Terrain only** to inspect the stationary ground without wind
  occlusion. Terrain uses fixed, ambient-only lighting so its colours do not
  change as the camera rotates. Geometry is unchanged by all view controls.
- Select **Vertical scale 1x** for equal physical scales; other settings
  exaggerate vertical appearance. The z axis and hover heights remain km MSL.
- Adjust opacity or click legend entries to hide individual surfaces. Transparent
  WebGL surfaces can still have sorting artifacts; this is not a volume renderer.

The interactive default is **the full saved mass-level column**, not the 4 km
cutout used for the first Manim movie. `--top 4000` explicitly selects that
cutout. Export metadata distinguishes the chosen display ceiling, highest wind
mass level, model-top interface range and P_TOP pressure when present. A count
of vertical levels is not an altitude in kilometres. Wind is not extrapolated
from the highest mass level up to the top interface.

Example: the existing Netherlands demo has 39 mass levels and 40 interfaces,
with a 5000 Pa model top at approximately 20 km MSL. The seven saved states have
top-interface heights of about 19.87-20.17 km and highest wind mass levels of
about 19.55-19.85 km. These are properties of that particular run, not defaults
or limits imposed on other simulations by the visualization package.

Interactive rendering follows the [Plotly mesh contract](https://plotly.com/python/reference/mesh3d/)
and [self-contained HTML export](https://plotly.com/python/interactive-html-export/).
The actual HTML was checked offline in Chrome for mouse orbit, wheel zoom,
time and opacity changes without resetting the camera, terrain-only inspection,
and invariant physical coordinates. Other browser/platform combinations have
not been tested here. JavaScript saves the live WebGL camera before controls
redraw meshes, including zoom that Plotly has not yet committed to its layout.
The [browser acceptance record](validation/interactive-acceptance.json) records
the actual data extent, final artifact hashes and verified interaction controls.

## 1. Install the geometry dependencies

In the ordinary WRF_tools Python environment:

```bash
python -m pip install -e ".[isosurface]"
```

The complete synthetic showcase also needs this optional extra. Manim itself
is separate; see the [visualization guide](VISUALIZATION.md) for its installation.
No model build, root access, new simulation or external map download is needed.

## 2. Prepare your actual model data

From the repository root:

```bash
python examples/export_3d_isosurfaces.py /path/to/wrf/run --domain d02 \
  --thresholds 12 16 --top 4000 --stride 5 \
  --output example_results/isosurfaces3d/geometry.json
```

Edit [the exporter settings](../examples/export_3d_isosurfaces.py) to change:

- **Field:** `wind_speed`, or `model_tke` when a supported TKE field exists.
- **Thresholds:** two surfaces at 12 and 16 m/s in the example; these are display
  choices, not universal storm boundaries. The values stay fixed across times.
- **Top:** 4000 m above mean sea level. Triangles are clipped at this height.
- **Stride:** 5 selects every fifth horizontal point and retains the domain
  edges. Use 1 for the full grid, at considerably greater rendering cost.
- **Vertical exaggeration:** 25 in the example; applied identically to terrain
  and wind geometry and printed in the movie. Use 1 for equal physical scales.
- **Frames:** the first seven actual saved timestamps by default.

The exporter refuses to overwrite a geometry file. Choose a new `--output` for
another experiment. Missing TKE is an error, not a reason to invent turbulence.

## 3. Render with Manim

In your optional Manim environment:

```bash
WRF_ISOSURFACES=example_results/isosurfaces3d/geometry.json \
  manim --renderer cairo --resolution 1600,900 --fps 12 \
  --media_dir example_results/isosurfaces3d/render --output_file wrf-isosurfaces \
  examples/manim_wrf_isosurfaces.py WRFIsosurfaces
```

If Manim lives in a separate local prefix, replace `manim` with its executable
path and ensure that prefix's FFmpeg is on `PATH`. For the existing Linux
example prefix, prepend `PATH="$PWD/.manim-env/bin:$PATH"` and use
`.manim-env/bin/manim`. Windows PowerShell equivalents:

```powershell
$env:WRF_ISOSURFACES = "example_results/isosurfaces3d/geometry.json"
manim --renderer cairo --resolution 1600,900 --fps 12 `
  --media_dir example_results/isosurfaces3d/render --output_file wrf-isosurfaces `
  examples/manim_wrf_isosurfaces.py WRFIsosurfaces
```

The movie is written below `render/videos/manim_wrf_isosurfaces/`. The folder
includes its resolution/frame rate. For a quick final-state layout preview,
set `WRF_ISOSURFACE_PREVIEW=1` and add `-s`; the PNG goes under `render/images/`.
The renderer only needs Manim, NumPy and the exported JSON, not a second WRF
installation or scikit-image environment. Text uses DejaVu Sans when available.

## What you are looking at

- The blue/green base uses **WRF HGT and LANDMASK**. The sea surface is at 0 m
  MSL; below-sea-level land is retained. Colours are illustrative, not satellite
  imagery. The solid plinth is only a display support, not bathymetry or geology.
- Coastlines are extracted from the full-resolution model land mask. The
  sampled base polygons are majority-coloured by land/water coverage and can
  look blocky near coasts; a 3 km model cannot provide a fine coastal survey.
- The cyan/gold meshes are **equal-value surfaces**, not a filled volume or a
  storm outline. Surface holes, splitting and merging follow extracted states.
- The camera stays fixed while actual output timestamps change. It orbits only
  the final state. The movie invents no intermediate atmospheric states.
- Boundaries remain open where the surface leaves the model box, crosses the
  selected top or reaches the lowest mass level. Do not calculate an enclosed
  volume from these open meshes or interpret an opening as a physical vortex.

## Geometry method and scientific limits

U/V are destaggered before calculating horizontal speed. MSL mass height is the
adjacent-interface average of `(PH+PHB)/9.81`. Lewiner marching cubes extracts
geometry in native model-index coordinates; the vertices are mapped to x/y
and trilinearly interpolated physical height. The model's nonuniform vertical
grid and sloping levels are therefore retained, rather than assigning a
constant vertical spacing. Triangle clipping at the top is piecewise linear.

Horizontal axes use nominal native DX/DY, not exact geodesic distances or globe
curvature. Stride is explicit point subsampling, not antialias filtering; small
features can disappear and connectivity can change. No smoothing, extrapolation
or temporal morphing is performed. Nonfinite values, folded height columns,
moving grids and unsupported variables are rejected with clear messages.

Opacity and lighting are aesthetic settings; Cairo sorts polygon depth and
intersecting transparent triangles can show rendering artifacts. Use VAPOR for
interactive inspection or large-volume rendering. The Manim scene is a
reproducible annotated animation, not a replacement for quantitative diagnosis.

References: [WRF technical note](https://doi.org/10.5065/1dfh-6p97),
[scikit-image marching cubes](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.marching_cubes),
[Lewiner et al. (2003)](https://doi.org/10.1080/10867651.2003.10487582),
and [Manim 3-D geometry](https://docs.manim.community/en/stable/reference/manim.mobject.three_d.polyhedra.Polyhedron.html).

Tests check an analytical scalar field on sloping/nonuniform heights, a known
sphere, top clipping, missing values, real timestamp selection, terrain below
sea level, water at MSL, missing fields and explicit mesh-size limits. Synthetic
tests establish those contracts, not atmospheric validation.

The initial local example used seven real d02 Netherlands/North Sea states and
rendered a 1600x900, 12 fps movie with Manim 0.19.0/Cairo on Linux. Geometry and
movie hashes are in the [acceptance record](validation/isosurface-acceptance.json).
Movie/geometry files stay local and are git-ignored; use the commands above to
regenerate them. The Windows command is provided but this new Manim scene has
not been rendered on Windows here. Existing report and contour-stack artifacts
are unchanged, and no new WRF simulation was run for this example.
