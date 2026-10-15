# Real-data nested-hindcast demonstration

The [single final report](../../example_results/final-report/hindcast-report.pdf)
is produced from scratch by the documented command-line example. It uses seven
hourly states from each of two stationary domains (9 km and 3 km), for 10 January
2025, 00–06 UTC. No simulation files or machine-specific paths are shipped.

Missing diagnostics are explicit: this YSU case saves no model TKE, and hourly
output is not LES turbulence. Passing tests and producing this PDF do not
establish atmospheric accuracy or observation validation. See
[the audit](../AUDIT.md) and [calculation changes](../CALCULATION_CHANGES.md).

PNG/SVG figures, arrays and processing JSON are generated beside the report;
only the final PDF and one current PNG preview are included as demonstration
artifacts. Earlier reports
are removed, not kept in a release archive.

From the repository root, using your WRF output directory:

```bash
python examples/create_hindcast_report.py /path/to/wrf/run \
  --domain d02 --diagnostics all --output example_results/final-report
```

Use an empty output directory for a fresh demonstration. ERA5, geodata, model
output, restarts and compiled executables are never included in Git.
