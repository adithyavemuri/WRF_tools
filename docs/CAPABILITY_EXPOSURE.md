# Capability access and verification

The connections missing in the earlier audit now have user-facing execution
paths. See [connected workflows](CONNECTED_WORKFLOWS.md) for commands, report
groups, editable recipes and explicit verification boundaries.

- **Report:** all six compatible groups are attempted by default; missing inputs
  and unselected groups are visible. Q criterion and Stull stability/partial
  budget diagnostics were never deleted and are now connected here.
- **Catalog and recipes:** every public top-level algorithm has a discoverable
  ID, signature and execution path. The [full API index](API_CATALOG.md) includes
  readers, writers, station/WPS tools and external-data capabilities.
- **Focused scripts:** averaging, multi-case comparisons, WRF-LES coupling,
  wind animations and actual-data 3-D contours remain available.
  Terrain/ocean isosurfaces have a separate [editable example](ISOSURFACES.md)
  and are exercised by the same capability showcase, not hidden helpers.
- **Correctness:** a Q-gradient ordering defect was fixed with rotation/strain
  tests. The report's nominal Cartesian Q operator still neglects map metrics.
  The optional diagnostic browser has a separate full-grid spherical-coordinate
  reconstruction with wind rotation and explicit limits; it does not silently
  replace the report helper or claim to reproduce WRF's discrete operators.
  The Stull budget is partial; hourly weather variance is not silently called
  turbulent energy.
- **Verification:** discovery, numerical testing, real-WRF execution and
  atmospheric validation are different claims. The workflow guide distinguishes
  them; no claim of real-data validation for every algorithm is made.

The old slideshow source and archived rendered products have been removed.
The new actual-WRF 3-D contour exporter, scene and rendered example are retained.
