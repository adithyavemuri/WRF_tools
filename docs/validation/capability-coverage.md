# Complete capability showcase

SYNTHETIC — NOT A WRF SIMULATION OR REAL OBSERVATIONS

Runtime entry-point coverage, not branch coverage or scientific validation. Failures invalidate the run.

Catalog: 211 functions. Counts: {'EXERCISED_SYNTHETIC': 208, 'REQUIRES_EXTERNAL_INPUT': 3}.

| Capability | Status | Chapter / required input |
|---|---|---|
| `animations.read_animation_manifest` | EXERCISED_SYNTHETIC | wrf |
| `animations.create_wind_animation` | EXERCISED_SYNTHETIC | wrf |
| `averaging.mean` | EXERCISED_SYNTHETIC | arrays |
| `averaging.wrf_cell_area` | EXERCISED_SYNTHETIC | wrf |
| `averaging.layer_thickness` | EXERCISED_SYNTHETIC | arrays |
| `averaging.to_height` | EXERCISED_SYNTHETIC | arrays, wrf |
| `comparison.align_cases` | EXERCISED_SYNTHETIC | plots |
| `comparison.plot_timeseries` | EXERCISED_SYNTHETIC | plots |
| `comparison.plot_profiles` | EXERCISED_SYNTHETIC | plots |
| `contours3d.horizontal_contours` | EXERCISED_SYNTHETIC | wrf |
| `contours3d.export_contour_sequence` | EXERCISED_SYNTHETIC | wrf |
| `coupling.openfast.bts.write_bts` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.bts.read_bts` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.bts.validate_bts` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.formats.read_hub_height_binary` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.formats.read_full_field_text` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.formats.read_coherent_points` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.formats.read_bladed_wnd` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.formats.write_bladed_wnd` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.concatenate_fields` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.velocity_at` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.horizontal_plane` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.vertical_profile` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.rotate_velocity` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.constant_field` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.step_field` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.operations.write_uniform_wind` | EXERCISED_SYNTHETIC | files |
| `coupling.openfast.wrf_les.wind_field_from_components` | EXERCISED_SYNTHETIC | files |
| `diagnostic_groups.run_diagnostic_groups` | EXERCISED_SYNTHETIC | wrf |
| `diagnostics.advanced.height_agl` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.advanced.interpolate_height` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.stability_class` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.diagnose_pbl_height` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.convective_velocity_scale` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.rotor_equivalent_wind_speed` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.rotor_shear_veer` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.weibull_fit` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.wind_power_density` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.advanced.component_spectra` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.advanced.premultiplied_spectrum` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.fit_spectral_slope` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.advanced.integral_time_scale` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.advanced.dew_point` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.relative_humidity` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.equivalent_potential_temperature` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.brunt_vaisala_frequency` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.inversion_layers` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.tke_budget` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.horizontal_kinematics` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.q_criterion` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.low_level_jet` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.advanced.precipitation_diagnostics` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.potential_temperature` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.temperature_from_potential` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.virtual_temperature` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.air_density` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.geopotential_height` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.bulk_richardson_number` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.power_law_exponent` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.interval_precipitation` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.reflectivity_to_rain_rate` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.friction_velocity` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.monin_obukhov_length` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.meteorology.circular_mean` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.roughness_length` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.log_wind_profile` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.meteorology.mixing_ratio_to_specific_humidity` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.turbulence.fluctuations` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.turbulence.resolved_tke` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.turbulence.reynolds_flux` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.turbulence.turbulence_intensity` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.wind.wind_speed` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.wind.wind_direction` | EXERCISED_SYNTHETIC | arrays, wrf |
| `diagnostics.wind.wind_speed_direction_to_uv` | EXERCISED_SYNTHETIC | arrays |
| `diagnostics.wind.angle_between` | EXERCISED_SYNTHETIC | arrays |
| `doctor.dependency_status` | EXERCISED_SYNTHETIC | plots |
| `doctor.environment_report` | EXERCISED_SYNTHETIC | plots |
| `doctor.print_environment_report` | EXERCISED_SYNTHETIC | plots |
| `extract.point` | EXERCISED_SYNTHETIC | wrf |
| `extract.vertical_profile` | EXERCISED_SYNTHETIC | wrf |
| `extract.to_levels` | EXERCISED_SYNTHETIC | wrf |
| `extract.variables` | EXERCISED_SYNTHETIC | wrf |
| `extract.horizontal_plane` | EXERCISED_SYNTHETIC | wrf |
| `extract.transect` | EXERCISED_SYNTHETIC | wrf |
| `filters.butterworth_spatial` | EXERCISED_SYNTHETIC | arrays, wrf |
| `filters.top_hat_coarsen` | EXERCISED_SYNTHETIC | arrays, wrf |
| `filters.resolved_subfilter` | EXERCISED_SYNTHETIC | arrays, wrf |
| `filters.butterworth_band` | EXERCISED_SYNTHETIC | arrays, wrf |
| `filters.spectral_downsample` | EXERCISED_SYNTHETIC | arrays, wrf |
| `grid.coordinates.nearest_grid_point` | EXERCISED_SYNTHETIC | wrf |
| `grid.coordinates.subset_by_bounds` | EXERCISED_SYNTHETIC | wrf |
| `grid.destagger.destagger` | EXERCISED_SYNTHETIC | wrf |
| `grid.destagger.destagger_wrf` | EXERCISED_SYNTHETIC | wrf |
| `grid.interpolation.interpolate_to_levels` | EXERCISED_SYNTHETIC | wrf |
| `grid.interpolation.regrid_regular` | EXERCISED_SYNTHETIC | wrf |
| `hindcast.summarize_hindcast` | EXERCISED_SYNTHETIC | wrf |
| `hindcast.create_hindcast_report` | EXERCISED_SYNTHETIC | wrf |
| `interactive.isosurface_figure` | EXERCISED_SYNTHETIC | wrf |
| `interactive.write_isosurface_html` | EXERCISED_SYNTHETIC | wrf |
| `io.datasets.open_wrf` | EXERCISED_SYNTHETIC | wrf |
| `io.datasets.open_wrf_sequence` | EXERCISED_SYNTHETIC | wrf |
| `io.datasets.get_variable` | EXERCISED_SYNTHETIC | wrf |
| `io.discovery.discover_wrfout` | EXERCISED_SYNTHETIC | wrf |
| `io.validation.validate_wrf_dataset` | EXERCISED_SYNTHETIC | wrf |
| `isosurfaces.isosurface_mesh` | EXERCISED_SYNTHETIC | wrf |
| `isosurfaces.export_isosurface_sequence` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.load_velocity` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.calculate_fluxes` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.calculate_total_tke` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.load_sgs_stress` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.sgs_tke` | EXERCISED_SYNTHETIC | wrf |
| `les.diagnostics.filtered_tke` | EXERCISED_SYNTHETIC | wrf |
| `maps.setup_map_data` | REQUIRES_EXTERNAL_INPUT | Explicit network download; showcase is offline/cache-only |
| `maps.add_cached_features` | EXERCISED_SYNTHETIC | plots, wrf |
| `observations.from_columns` | EXERCISED_SYNTHETIC | files |
| `observations.collocate_grid` | EXERCISED_SYNTHETIC | wrf |
| `observations.align` | EXERCISED_SYNTHETIC | files |
| `observations.read_csv` | EXERCISED_SYNTHETIC | files |
| `observations.read_netcdf` | EXERCISED_SYNTHETIC | files |
| `observations.normalize_time` | EXERCISED_SYNTHETIC | files |
| `openfast.read_ascii_output` | EXERCISED_SYNTHETIC | files |
| `openfast.read_binary_output` | EXERCISED_SYNTHETIC | files |
| `openfast.zero_crossing_frequency` | EXERCISED_SYNTHETIC | files |
| `openfast.stress_from_moment` | EXERCISED_SYNTHETIC | files |
| `openfast.rainflow_cycles` | EXERCISED_SYNTHETIC | files |
| `openfast.channel_statistics` | EXERCISED_SYNTHETIC | files |
| `openfast.compare_outputs` | EXERCISED_SYNTHETIC | files |
| `openfast.run_openfast` | REQUIRES_EXTERNAL_INPUT | Needs OpenFAST plus a complete user-reviewed turbine model |
| `openfast_input.read_parameters` | EXERCISED_SYNTHETIC | files |
| `openfast_input.update_parameters` | EXERCISED_SYNTHETIC | files |
| `plotting.horizontal` | EXERCISED_SYNTHETIC | plots |
| `plotting.profile` | EXERCISED_SYNTHETIC | plots |
| `plotting.time_height` | EXERCISED_SYNTHETIC | plots |
| `plotting.wind_rose` | EXERCISED_SYNTHETIC | plots |
| `plotting.cross_section` | EXERCISED_SYNTHETIC | plots |
| `plotting.wind_barbs` | EXERCISED_SYNTHETIC | plots |
| `plotting.nested_domains` | EXERCISED_SYNTHETIC | plots |
| `plotting.validation_scatter` | EXERCISED_SYNTHETIC | plots |
| `plotting.taylor_diagram` | EXERCISED_SYNTHETIC | plots |
| `plotting.animate_fields` | EXERCISED_SYNTHETIC | plots |
| `quality.quality_control` | EXERCISED_SYNTHETIC | wrf |
| `quality.print_qc_report` | EXERCISED_SYNTHETIC | wrf |
| `reporting.dataset_summary` | EXERCISED_SYNTHETIC | plots |
| `reporting.write_json_report` | EXERCISED_SYNTHETIC | plots, wrf |
| `reporting.comparison_report` | EXERCISED_SYNTHETIC | files |
| `reporting.provenance` | EXERCISED_SYNTHETIC | plots, wrf |
| `reporting.write_html_report` | EXERCISED_SYNTHETIC | plots, wrf |
| `reporting.write_pdf_report` | EXERCISED_SYNTHETIC | plots, wrf |
| `spatial.terrain_metrics` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.speed_up_ratio` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.landuse_statistics` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.resolution_metrics` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.boundary_discontinuity` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.integral_conservation` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spatial.rotate_vectors` | EXERCISED_SYNTHETIC | arrays |
| `spatial.temporal_diagnostics` | EXERCISED_SYNTHETIC | arrays |
| `spatial.diurnal_cycle` | EXERCISED_SYNTHETIC | arrays |
| `spectra.power_spectrum` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spectra.welch_spectrum` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spectra.radial_wavenumber_spectrum` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spectra.coherence` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spectra.cross_spectrum` | EXERCISED_SYNTHETIC | arrays, wrf |
| `spectra.log_bin` | EXERCISED_SYNTHETIC | arrays, wrf |
| `timeseries.station.read_station_header` | EXERCISED_SYNTHETIC | files |
| `timeseries.station.read_station_surface` | EXERCISED_SYNTHETIC | files |
| `timeseries.station.read_station_profile` | EXERCISED_SYNTHETIC | files |
| `timeseries.station.read_station_family` | EXERCISED_SYNTHETIC | files |
| `timeseries.tslist.read_tslist` | EXERCISED_SYNTHETIC | files |
| `timeseries.tslist.write_tslist` | EXERCISED_SYNTHETIC | files |
| `turbulence.model_tke_sources` | EXERCISED_SYNTHETIC | wrf |
| `turbulence.model_tke` | EXERCISED_SYNTHETIC | wrf |
| `turbulence.tke_diagnostics_data` | EXERCISED_SYNTHETIC | wrf |
| `turbulence.save_tke_diagnostics` | EXERCISED_SYNTHETIC | wrf |
| `validation.bias` | EXERCISED_SYNTHETIC | arrays, files, wrf |
| `validation.mae` | EXERCISED_SYNTHETIC | arrays, files, wrf |
| `validation.rmse` | EXERCISED_SYNTHETIC | arrays, files, wrf |
| `validation.circular_error` | EXERCISED_SYNTHETIC | arrays |
| `validation.circular_mae` | EXERCISED_SYNTHETIC | arrays |
| `validation.normalized_error` | EXERCISED_SYNTHETIC | arrays |
| `validation.kantorovich_distance` | EXERCISED_SYNTHETIC | arrays |
| `validation.correlation` | EXERCISED_SYNTHETIC | arrays, files, wrf |
| `validation.standard_error` | EXERCISED_SYNTHETIC | arrays |
| `validation.comparison_summary` | EXERCISED_SYNTHETIC | arrays, files, wrf |
| `validation.cluster_profiles` | EXERCISED_SYNTHETIC | arrays |
| `validation.spatial_scores` | EXERCISED_SYNTHETIC | arrays |
| `validation.rank_cases` | EXERCISED_SYNTHETIC | arrays |
| `visualization.history_times` | EXERCISED_SYNTHETIC | wrf |
| `visualization.rotate_wind` | EXERCISED_SYNTHETIC | wrf |
| `visualization.surface_wind` | EXERCISED_SYNTHETIC | wrf |
| `visualization.mass_heights` | EXERCISED_SYNTHETIC | wrf |
| `visualization.temperature_celsius` | EXERCISED_SYNTHETIC | wrf |
| `visualization.interpolate_columns` | EXERCISED_SYNTHETIC | wrf |
| `visualization.wrf_projection` | EXERCISED_SYNTHETIC | plots, wrf |
| `visualization.geographic_axis` | EXERCISED_SYNTHETIC | plots, wrf |
| `visualization.wind_overview_data` | EXERCISED_SYNTHETIC | wrf |
| `visualization.plot_wind_overview` | EXERCISED_SYNTHETIC | wrf |
| `visualization.save_wind_overview` | EXERCISED_SYNTHETIC | wrf |
| `wind_models.kaimal_spectrum` | EXERCISED_SYNTHETIC | arrays |
| `wind_models.von_karman_spectrum` | EXERCISED_SYNTHETIC | arrays |
| `wind_models.exponential_coherence` | EXERCISED_SYNTHETIC | arrays |
| `wind_models.iec_kaimal_spectrum` | EXERCISED_SYNTHETIC | arrays |
| `wind_models.cheynet_spectrum` | EXERCISED_SYNTHETIC | arrays |
| `wind_models.synthetic_wind_field` | EXERCISED_SYNTHETIC | arrays |
| `workflow.aggregate_wrf` | EXERCISED_SYNTHETIC | wrf |
| `workflow.archive_outputs` | EXERCISED_SYNTHETIC | wrf |
| `workflow.convert_grib_to_netcdf` | REQUIRES_EXTERNAL_INPUT | Needs an installed wgrib2 and real GRIB input |
| `wps.domains.domain_geometries` | EXERCISED_SYNTHETIC | files |
| `wps.domains.eta_levels` | EXERCISED_SYNTHETIC | files |
| `wps.domains.geographic_corners` | EXERCISED_SYNTHETIC | files |
| `wps.namelist.read_namelist` | EXERCISED_SYNTHETIC | files |
| `wps.namelist.update_namelist_dates` | EXERCISED_SYNTHETIC | files |
