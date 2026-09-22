# Validated nested-hindcast demonstration

`netherlands-nested-hindcast-report.pdf` is the compact scientific report from
the validated `full-test-001` demonstration performed on 22 September 2026.

The six-hour case used hourly ERA5 reanalysis forcing and stationary one-way
nesting with a 9 km outer domain and 3 km inner domain. WPS, `real.exe`,
`wrf.exe`, all fourteen expected hourly domain outputs, report provenance and
the final report passed the workflow validator.

Large runtime products are deliberately excluded: ERA5 GRIB files, WPS
geodata, `met_em`, `wrfinput`, `wrfbdy`, `wrfout`, restart files and compiled
WRF/WPS executables are not stored in Git.
