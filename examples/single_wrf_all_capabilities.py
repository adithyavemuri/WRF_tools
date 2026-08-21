r"""Process one wrfout into diagnostics, plots, reports, and wind files.

This example uses only information present in the supplied wrfout. It does
not invent WPS domains, observations, station files, or OpenFAST results.

Run from the repository root:
    .venv\Scripts\python.exe examples\single_wrf_all_capabilities.py WRFOUT

You can either edit USER SETTINGS below or provide command-line arguments.
Command-line values take precedence over the settings in the file.

Methodology and primary citations are catalogued in
``docs/SCIENTIFIC_METHODS.md``. Spectral -5/3 lines are Kolmogorov inertial-
subrange slope guides (Kolmogorov 1941, doi:10.1098/rspa.1991.0075), not claims
that a short example record resolves an inertial subrange.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from wrf_tools.coupling.openfast import read_bladed_wnd, validate_bts, wind_field_from_components, write_bladed_wnd, write_bts
from wrf_tools.diagnostics import (
    brunt_vaisala_frequency, component_spectra, convective_velocity_scale, diagnose_pbl_height,
    equivalent_potential_temperature, fit_spectral_slope, geopotential_height,
    height_agl, horizontal_kinematics, integral_time_scale, interpolate_height,
    inversion_layers, low_level_jet, potential_temperature, q_criterion,
    precipitation_diagnostics, relative_humidity, resolved_tke,
    rotor_equivalent_wind_speed, rotor_shear_veer, stability_class, tke_budget,
    temperature_from_potential, turbulence_intensity, weibull_fit, wind_direction, wind_power_density,
    wind_speed,
)
from wrf_tools.extract import point, vertical_profile
from wrf_tools.filters import butterworth_spatial, resolved_subfilter, top_hat_coarsen
from wrf_tools.grid import nearest_grid_point, regrid_regular
from wrf_tools.io import open_wrf, validate_wrf_dataset
from wrf_tools.les import load_velocity
from wrf_tools.plotting import cross_section, horizontal, profile, time_height, wind_barbs, wind_rose
from wrf_tools.quality import print_qc_report, quality_control
from wrf_tools.reporting import dataset_summary, provenance, write_html_report, write_json_report, write_pdf_report
from wrf_tools.spectra import coherence, power_spectrum, radial_wavenumber_spectrum
from wrf_tools.spatial import (
    boundary_discontinuity, diurnal_cycle, integral_conservation,
    landuse_statistics, resolution_metrics, rotate_vectors, speed_up_ratio,
    temporal_diagnostics, terrain_metrics,
)


# =============================================================================
# USER SETTINGS
# =============================================================================
# Set this to your wrfout path, or leave it as None and pass the path on the
# command line. A raw string (r"...") is convenient for Windows paths.
WRFOUT_FILE: Path | None = None
# Example:
# WRFOUT_FILE = Path("/path/to/wrfout_d01_2020-01-01_00_00_00")

# Point used for time series, profiles, and wind-field extraction. Leave both
# as None to use the geographical centre grid cell of the WRF domain.
TARGET_LATITUDE: float | None = None
TARGET_LONGITUDE: float | None = None

# All generated files are written here unless --output-dir is supplied.
OUTPUT_DIRECTORY = Path("example_results/single_wrf_example")


def configure_publication_style() -> None:
    """Apply a restrained, high-resolution style suitable for papers."""
    plt.rcParams.update({
        "figure.figsize": (7.2, 4.8), "figure.dpi": 120,
        "savefig.dpi": 300, "savefig.facecolor": "white",
        "font.family": "serif", "font.serif": ["DejaVu Serif"],
        "mathtext.fontset": "dejavuserif", "font.size": 9.5,
        "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.labelsize": 10, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.fontsize": 8.5, "legend.frameon": False,
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "lines.linewidth": 1.7, "lines.markersize": 4.5,
        "grid.alpha": 0.22, "grid.linewidth": 0.6,
    })


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wrfout", nargs="?", type=Path,
                        help="one wrfout NetCDF file; overrides WRFOUT_FILE")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="output directory; overrides OUTPUT_DIRECTORY")
    parser.add_argument("--latitude", type=float, help="analysis latitude; default is domain centre")
    parser.add_argument("--longitude", type=float, help="analysis longitude; default is domain centre")
    args = parser.parse_args()
    args.wrfout = args.wrfout or WRFOUT_FILE
    args.output_dir = args.output_dir or OUTPUT_DIRECTORY
    args.latitude = args.latitude if args.latitude is not None else TARGET_LATITUDE
    args.longitude = args.longitude if args.longitude is not None else TARGET_LONGITUDE
    if args.wrfout is None:
        parser.error("provide WRFOUT on the command line or set WRFOUT_FILE in USER SETTINGS")
    if (args.latitude is None) != (args.longitude is None):
        parser.error("latitude and longitude must be supplied together")
    return args


def save_figure(figure, directory: Path, filename: str) -> None:
    figure.tight_layout()
    figure.savefig(directory / filename, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def main() -> int:
    args = parse_args()
    configure_publication_style()
    source = args.wrfout.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Remove a superseded combined spectrum from older runs into this folder.
    (output / "wind_component_spectra.png").unlink(missing_ok=True)

    # Open the file and choose the requested point (or the domain centre).
    with open_wrf(source) as wrf:
        validate_wrf_dataset(wrf)
        # QC checks important state, surface, water, and precipitation fields.
        qc_names = [name for name in (
            "T2", "PSFC", "Q2", "QVAPOR", "U10", "V10", "PBLH", "RAINC",
            "RAINNC", "QCLOUD", "QRAIN", "QICE", "QSNOW",
        ) if name in wrf]
        qc_issues = quality_control(wrf[qc_names])
        print_qc_report(qc_issues)
        latitude = wrf.XLAT.isel(Time=0)
        longitude = wrf.XLONG.isel(Time=0)
        centre_y, centre_x = np.array(latitude.shape) // 2
        target_lat = args.latitude if args.latitude is not None else float(latitude[centre_y, centre_x])
        target_lon = args.longitude if args.longitude is not None else float(longitude[centre_y, centre_x])
        cell = nearest_grid_point(latitude, longitude, target_lat, target_lon)
        dx, dy = float(wrf.attrs["DX"]), float(wrf.attrs["DY"])

        # Extract a labelled point time series and vertical profile.
        point_data = point(wrf, target_lat, target_lon, variables=["T2", "U10", "V10"])
        point_data.to_netcdf(output / "point_timeseries.nc")
        theta_profile = potential_temperature(vertical_profile(wrf, "T", x=cell.x, y=cell.y))
        z_staggered = np.asarray(geopotential_height(wrf.PH.isel(Time=0), wrf.PHB.isel(Time=0)))
        height = 0.5 * (z_staggered[:-1] + z_staggered[1:])
        height_profile = height[:, cell.y, cell.x]

        # Collocate WRF-LES velocity and select a manageable area around the point.
        u, v, w = load_velocity(wrf)
        nt, nz = min(8, wrf.sizes["Time"]), min(8, wrf.sizes["bottom_top"])
        radius = min(6, cell.x, cell.y, wrf.sizes["west_east"]-1-cell.x, wrf.sizes["south_north"]-1-cell.y)
        region = dict(Time=slice(0, nt), bottom_top=slice(0, nz),
                      south_north=slice(cell.y-radius, cell.y+radius+1),
                      west_east=slice(cell.x-radius, cell.x+radius+1))
        u_sub, v_sub, w_sub = (np.asarray(component.isel(**region)) for component in (u, v, w))
        speed_sub = wind_speed(u_sub, v_sub)
        tke_profile = resolved_tke(u_sub, v_sub, w_sub, axis=(0, 2, 3))
        local_height = height_profile[:nz]

        # Butterworth decomposition and temporal/spatial spectra.
        t2 = np.asarray(wrf.T2.isel(Time=0))
        t2_large = butterworth_spatial(t2, dx=dx, dy=dy, cutoff_wavelength=6*dx, order=4)
        _, t2_small = resolved_subfilter(t2, t2_large)
        radial_k, radial_power = radial_wavenumber_spectrum(t2, dx=dx, dy=dy)
        u10_series = np.asarray(point_data.U10)
        u10, v10 = np.asarray(wrf.U10), np.asarray(wrf.V10)
        point_speed = wind_speed(u10[:, cell.y, cell.x], v10[:, cell.y, cell.x])
        point_direction = wind_direction(u10[:, cell.y, cell.x], v10[:, cell.y, cell.x])
        # XTIME is stored in minutes by WRF. Using hours makes the resulting
        # frequency axis readable for ordinary mesoscale output intervals.
        if "XTIME" in wrf:
            xtime = np.asarray(wrf.XTIME)
            differences = np.diff(xtime)
            if np.issubdtype(xtime.dtype, np.datetime64) or np.issubdtype(xtime.dtype, np.timedelta64):
                spacing_hours = float(np.median(differences / np.timedelta64(1, "h")))
            else:
                spacing_hours = float(np.nanmedian(differences)) / 60.0
        else:
            spacing_hours = 1.0
        frequency, temporal_power = power_spectrum(u10_series, spacing=spacing_hours)

        # Advanced point-profile, PBL, wind-energy, and thermodynamic diagnostics.
        u_point = np.asarray(u.isel(south_north=cell.y, west_east=cell.x))
        v_point = np.asarray(v.isel(south_north=cell.y, west_east=cell.x))
        w_point = np.asarray(w.isel(south_north=cell.y, west_east=cell.x))
        speed_point = wind_speed(u_point, v_point)
        direction_point = wind_direction(u_point, v_point)
        z_point_stag = np.asarray(geopotential_height(
            wrf.PH.isel(south_north=cell.y, west_east=cell.x),
            wrf.PHB.isel(south_north=cell.y, west_east=cell.x)))
        z_point = .5*(z_point_stag[:, :-1]+z_point_stag[:, 1:])
        terrain_point = float(wrf.HGT.isel(Time=0, south_north=cell.y, west_east=cell.x))
        z_agl = height_agl(z_point, terrain_point)
        theta_point = np.asarray(potential_temperature(wrf.T.isel(south_north=cell.y, west_east=cell.x)))
        pressure_point = np.asarray((wrf.P+wrf.PB).isel(south_north=cell.y, west_east=cell.x))
        qv_point = np.asarray(wrf.QVAPOR.isel(south_north=cell.y, west_east=cell.x))
        temperature_point = temperature_from_potential(theta_point, pressure_point)
        rh_point = relative_humidity(temperature_point, pressure_point, qv_point)
        theta_e_point = equivalent_potential_temperature(temperature_point, pressure_point, qv_point)
        n_frequency = brunt_vaisala_frequency(theta_point, z_point, axis=1)
        inversion = inversion_layers(temperature_point, z_point, axis=1)
        diagnosed_pbl = diagnose_pbl_height(theta_point, z_agl, axis=1)
        model_pbl = np.asarray(wrf.PBLH[:, cell.y, cell.x])
        surface_theta = np.asarray(wrf.T2[:, cell.y, cell.x])*(100000/np.asarray(wrf.PSFC[:, cell.y, cell.x]))**(287.05/1004.0)
        surface_density = np.asarray(wrf.PSFC[:, cell.y, cell.x])/(287.05*np.asarray(wrf.T2[:, cell.y, cell.x]))
        kinematic_heat_flux = np.asarray(wrf.HFX[:, cell.y, cell.x])/(surface_density*1004.0)
        denominator = .4*9.80665*kinematic_heat_flux
        obukhov_length = -surface_theta*np.asarray(wrf.UST[:, cell.y, cell.x])**3/np.where(denominator==0,np.nan,denominator)
        surface_stability = stability_class(obukhov_length)
        convective_scale = convective_velocity_scale(np.maximum(kinematic_heat_flux,0), model_pbl, surface_theta)

        rotor_bottom, rotor_top = 40.0, 200.0
        rotor_speed = rotor_equivalent_wind_speed(speed_point, z_agl, rotor_bottom, rotor_top, axis=1)
        rotor_shear, rotor_veer = rotor_shear_veer(speed_point, direction_point, z_agl, rotor_bottom, rotor_top, axis=1)
        weibull_shape, weibull_scale = weibull_fit(point_speed)
        density_surface = np.asarray(wrf.PSFC[:, cell.y, cell.x])/(287.05*np.asarray(wrf.T2[:, cell.y, cell.x]))
        power_density = float(wind_power_density(point_speed, density_surface, axis=0))

        # Component spectra, coherence, cross-point scales, and fitted slope.
        component_frequency, component_power = component_spectra(
            u_point[:, 0], v_point[:, 0], w_point[:, 0], spacing=spacing_hours)
        spectral_slope, _ = fit_spectral_slope(frequency, temporal_power)
        segment = min(8, len(u10_series))
        coherence_frequency, lateral_coherence = coherence(
            u10_series, np.asarray(wrf.U10[:, cell.y, min(cell.x+1, wrf.sizes["west_east"]-1)]),
            sample_rate=1/spacing_hours, nperseg=segment, overlap=segment//2)
        integral_hours, autocorrelation = integral_time_scale(u10_series, spacing_hours)
        integral_length = integral_hours*3600*float(np.nanmean(point_speed))

        # TKE-budget and kinematic diagnostics over the local real-data cube.
        theta_sub = np.asarray(potential_temperature(wrf.T.isel(**region)))
        height_sub = height[:nz, cell.y-radius:cell.y+radius+1, cell.x-radius:cell.x+radius+1]
        budget = tke_budget(u_sub, v_sub, w_sub, theta_sub, height_sub)
        kinematics = horizontal_kinematics(u_sub[0, 0], v_sub[0, 0], dx, dy)
        q_field = q_criterion(u_sub[0], v_sub[0], w_sub[0], dx, dy, float(np.nanmedian(np.diff(local_height))))
        jet = low_level_jet(speed_point[0], z_agl[0])

        # Precipitation, terrain, land-use, resolution, conservation, and time.
        precipitation = precipitation_diagnostics(np.asarray(wrf.RAINC), np.asarray(wrf.RAINNC))
        terrain = np.asarray(wrf.HGT.isel(Time=0)); terrain_result = terrain_metrics(terrain, dx, dy)
        speedup = speed_up_ratio(wind_speed(u10[0],v10[0]), np.nanmean(wind_speed(u10[0],v10[0])))
        landuse = landuse_statistics(t2, np.asarray(wrf.LU_INDEX.isel(Time=0)))
        coarse_t2 = top_hat_coarsen(t2, factor_y=2, trim=True)
        source_x=np.arange(coarse_t2.shape[1])*2; source_y=np.arange(coarse_t2.shape[0])*2
        target_x=np.arange(coarse_t2.shape[1]*2); target_y=np.arange(coarse_t2.shape[0]*2)
        restored_t2 = regrid_regular(coarse_t2, source_x, source_y, target_x, target_y)
        resolution = resolution_metrics(t2[:restored_t2.shape[0], :restored_t2.shape[1]], restored_t2)
        trimmed_t2 = t2[:coarse_t2.shape[0]*2, :coarse_t2.shape[1]*2]
        conservation = integral_conservation(trimmed_t2, coarse_t2, dx*dy, (2*dx)*(2*dy))
        boundary = boundary_discontinuity(t2)
        earth_u, earth_v = rotate_vectors(u10[0], v10[0], np.degrees(np.arctan2(np.asarray(wrf.SINALPHA[0]), np.asarray(wrf.COSALPHA[0]))))
        time_result = temporal_diagnostics(point_speed, spacing_hours)
        if "XTIME" in wrf and np.issubdtype(np.asarray(wrf.XTIME).dtype, np.datetime64):
            hours = np.asarray(wrf.XTIME).astype("datetime64[h]").astype(int) % 24
        else:
            hours = np.arange(len(point_speed))*spacing_hours % 24
        diurnal = diurnal_cycle(point_speed, hours)

        np.savez(output / "diagnostics_and_spectra.npz", t2=t2, t2_large_scale=t2_large,
                 t2_small_scale=t2_small, radial_wavenumber=radial_k,
                 radial_power=radial_power, frequency=frequency,
                 temporal_power=temporal_power, tke_profile=tke_profile,
                 diagnosed_pbl=diagnosed_pbl, rotor_speed=rotor_speed,
                 rotor_shear=rotor_shear, rotor_veer=rotor_veer,
                 component_frequency=component_frequency,
                 component_u=component_power["u"], component_v=component_power["v"],
                 component_w=component_power["w"], coherence_frequency=coherence_frequency,
                 lateral_coherence=lateral_coherence, vertical_vorticity=kinematics["vertical_vorticity"],
                 precipitation_total=precipitation["total"], terrain_slope=terrain_result["slope_degrees"])

        # Labelled plots using actual WRF coordinates and units.
        fig, ax, _ = horizontal(t2, x=longitude, y=latitude, cmap="RdYlBu_r",
            title="WRF 2 m temperature - first output time", xlabel="Longitude (degrees east)",
            ylabel="Latitude (degrees north)", colorbar_label="Temperature (K)")
        ax.plot(target_lon,target_lat,marker="*",ms=9,mec="white",mew=.7,color="#1f1f1f",label="Analysis point"); ax.legend(loc="lower left")
        save_figure(fig, output, "temperature_2m.png")

        fig, ax, _ = horizontal(t2_large, x=longitude, y=latitude, cmap="RdYlBu_r",
            title="Butterworth-filtered 2 m temperature (> 6 grid cells)",
            xlabel="Longitude (degrees east)", ylabel="Latitude (degrees north)",
            colorbar_label="Temperature (K)")
        ax.plot(target_lon,target_lat,marker="*",ms=9,mec="white",mew=.7,color="#1f1f1f")
        save_figure(fig, output, "temperature_2m_filtered.png")

        # Spectral figures omit the zero-frequency component because it cannot
        # be represented on logarithmic axes.
        temporal_mask = (frequency > 0) & (temporal_power > 0)
        positive_frequency = frequency[temporal_mask]
        positive_power = temporal_power[temporal_mask]
        # Normalize the reference at the geometric-middle spectral point. The
        # line is a slope guide, not a regression or claim of an inertial range.
        reference_index = len(positive_frequency) // 2
        reference_frequency = positive_frequency[reference_index]
        reference_power = positive_power[reference_index]
        minus_five_thirds = reference_power * (positive_frequency / reference_frequency) ** (-5.0/3.0)
        fig, ax = plt.subplots()
        ax.loglog(positive_frequency, positive_power, "o-", color="#276FBF", label="U10 periodogram")
        ax.loglog(positive_frequency, minus_five_thirds, "--", color="#303030", linewidth=1.5,
                  label=r"Kolmogorov $f^{-5/3}$ slope guide (1941)")
        ax.set(title=f"Temporal spectrum of U10 at {target_lat:.3f} N, {target_lon:.3f} E",
               xlabel="Frequency (cycles h$^{-1}$)",
               ylabel="Power spectral density ((m s$^{-1}$)$^2$ h)")
        ax.grid(True, which="both", alpha=.3); ax.legend()
        save_figure(fig, output, "u10_temporal_spectrum.png")

        radial_mask = (radial_k > 0) & (radial_power > 0)
        fig, ax = plt.subplots()
        ax.loglog(radial_k[radial_mask]*1000, radial_power[radial_mask], "o-",color="#7A5195",
                  label="Azimuthally averaged T2 spectrum")
        ax.set(title="Radial wavenumber spectrum of 2 m temperature",
               xlabel="Radial wavenumber (cycles km$^{-1}$)",
               ylabel="Temperature spectral power (K$^2$)")
        ax.grid(True, which="both", alpha=.3); ax.legend()
        save_figure(fig, output, "temperature_2m_wavenumber_spectrum.png")

        fig, _, _ = profile(theta_profile, height_profile,
            title=f"Potential-temperature profile at {target_lat:.3f} N, {target_lon:.3f} E",
            xlabel="Potential temperature (K)", ylabel="Height above mean sea level (m)",
            label="First output time")
        save_figure(fig, output, "potential_temperature_profile.png")

        local_centre = radius
        fig, _, _ = time_height(speed_sub[:, :, local_centre, local_centre], np.arange(nt), local_height,
            cmap="viridis", title="Wind-speed evolution at the selected grid cell",
            xlabel="WRF output index", ylabel="Height above mean sea level (m)",
            colorbar_label="Wind speed (m s$^{-1}$)")
        save_figure(fig, output, "wind_speed_time_height.png")

        distance = (np.arange(2*radius+1)-radius)*dx/1000
        section_height = np.nanmean(height[:nz, cell.y, cell.x-radius:cell.x+radius+1], axis=1)
        fig, _, _ = cross_section(speed_sub[0, :, local_centre, :], distance, section_height,
            cmap="viridis", title="Wind-speed cross-section through selected point",
            xlabel="West-east distance from point (km)", ylabel="Height above mean sea level (m)",
            colorbar_label="Wind speed (m s$^{-1}$)")
        save_figure(fig, output, "wind_speed_cross_section.png")

        fig, _ = wind_rose(point_direction, point_speed, title="10 m wind at selected grid cell")
        save_figure(fig, output, "wind_rose_10m.png")

        fig, ax, _ = wind_barbs(u10[0], v10[0], x=np.asarray(longitude), y=np.asarray(latitude), stride=8,
            title="10 m wind vectors - first output time", xlabel="Longitude (degrees east)",
            ylabel="Latitude (degrees north)", length=5,color="#222222")
        ax.plot(target_lon,target_lat,marker="*",ms=9,mec="white",mew=.7,color="#C43C39",label="Analysis point"); ax.legend(loc="lower left")
        save_figure(fig, output, "wind_barbs_10m.png")

        component_mask = component_frequency > 0
        component_colors = {"u":"#276FBF", "v":"#D95F02", "w":"#2E8B57"}
        component_labels = {"u":"Zonal velocity U", "v":"Meridional velocity V", "w":"Vertical velocity W"}
        for name in ("u","v","w"):
            values = component_power[name]
            valid = component_mask & (values > 0)
            frequencies, powers = component_frequency[valid], values[valid]
            middle = len(frequencies)//2; anchor_f, anchor = frequencies[middle], powers[middle]
            reference = anchor*(frequencies/anchor_f)**(-5/3)
            slope, _ = fit_spectral_slope(frequencies,powers)
            fig, ax = plt.subplots()
            ax.loglog(frequencies,powers,"o-",color=component_colors[name],label=f"{component_labels[name]} periodogram")
            ax.loglog(frequencies,reference,"--",color="#303030",linewidth=1.5,
                      label=r"Kolmogorov $f^{-5/3}$ slope guide (1941)")
            ax.set(title=f"{component_labels[name]} spectrum - first model level",
                   xlabel="Frequency (cycles h$^{-1}$)",ylabel="Power spectral density")
            ax.text(.03,.05,fr"Fitted slope: {slope:.2f}",transform=ax.transAxes,ha="left",va="bottom",
                    bbox={"facecolor":"white","edgecolor":"0.75","boxstyle":"round,pad=.25","alpha":.9})
            ax.grid(True,which="both"); ax.legend(loc="upper right")
            save_figure(fig,output,f"{name}_wind_spectrum.png")

        fig, ax = plt.subplots()
        ax.plot(np.arange(len(model_pbl)),model_pbl,"o-",color="#276FBF",label="WRF PBLH")
        ax.plot(np.arange(len(diagnosed_pbl)),diagnosed_pbl,"s--",color="#D95F02",label="0.5 K diagnosed PBL")
        ax.set(title="Boundary-layer height at selected point",xlabel="WRF output index",ylabel="Height AGL (m)")
        ax.grid(True,alpha=.3); ax.legend()
        save_figure(fig, output, "boundary_layer_height.png")

        fig, axes = plt.subplots(1,2,figsize=(12,5))
        terrain_plot=axes[0].contourf(longitude,latitude,terrain,20,cmap="terrain"); fig.colorbar(terrain_plot,ax=axes[0],label="Terrain height (m MSL)")
        axes[0].set(title="WRF terrain",xlabel="Longitude",ylabel="Latitude")
        slope_plot=axes[1].contourf(longitude,latitude,terrain_result["slope_degrees"],20,cmap="magma"); fig.colorbar(slope_plot,ax=axes[1],label="Slope (degrees)")
        axes[1].set(title="Terrain slope",xlabel="Longitude",ylabel="Latitude")
        save_figure(fig,output,"terrain_diagnostics.png")

        fig, axes = plt.subplots(1,2,figsize=(12,5))
        precipitation_plot=axes[0].contourf(longitude,latitude,precipitation["total"],20,cmap="Blues"); fig.colorbar(precipitation_plot,ax=axes[0],label="Accumulated precipitation (mm)")
        axes[0].set(title="Accumulated precipitation",xlabel="Longitude",ylabel="Latitude")
        speedup_plot=axes[1].contourf(longitude,latitude,speedup,20,cmap="coolwarm"); fig.colorbar(speedup_plot,ax=axes[1],label="Speed-up ratio (-)")
        axes[1].set(title="10 m wind speed-up relative to domain mean",xlabel="Longitude",ylabel="Latitude")
        save_figure(fig,output,"precipitation_and_speedup.png")

        fig, axes = plt.subplots(1,2,figsize=(12,5))
        vort=axes[0].contourf(kinematics["vertical_vorticity"],20,cmap="RdBu_r"); fig.colorbar(vort,ax=axes[0],label="Vertical vorticity (s$^{-1}$)")
        axes[0].set(title="Local vertical vorticity",xlabel="West-east index",ylabel="South-north index")
        qplot=axes[1].contourf(q_field[0],20,cmap="PuOr"); fig.colorbar(qplot,ax=axes[1],label="Q criterion (s$^{-2}$)")
        axes[1].set(title="Local Q criterion - lowest level",xlabel="West-east index",ylabel="South-north index")
        save_figure(fig,output,"flow_structure_diagnostics.png")

        fig, axes = plt.subplots(3,1,figsize=(9,9),sharex=True)
        axes[0].plot(rotor_speed,label="Rotor-equivalent speed"); axes[0].set_ylabel("Speed (m s$^{-1}$)"); axes[0].legend(); axes[0].grid(alpha=.3)
        axes[1].plot(rotor_shear,label="Rotor shear exponent"); axes[1].set_ylabel("Shear (-)"); axes[1].legend(); axes[1].grid(alpha=.3)
        axes[2].plot(rotor_veer,label="Rotor veer"); axes[2].set(ylabel="Veer (degrees)",xlabel="WRF output index"); axes[2].legend(); axes[2].grid(alpha=.3)
        fig.suptitle(f"Rotor-layer diagnostics ({rotor_bottom:.0f}-{rotor_top:.0f} m AGL)")
        save_figure(fig,output,"rotor_diagnostics.png")

        # Convert a real WRF-LES vertical/lateral plane to two inflow formats.
        field = wind_field_from_components(
            u_sub[:, :, :, local_centre], v_sub[:, :, :, local_centre], w_sub[:, :, :, local_centre],
            time_axis=0, vertical_axis=1, lateral_axis=2, dt=1.0, dy=dy,
            dz=float(np.nanmedian(np.diff(local_height))),
            hub_height=float(np.nanmean(local_height)), bottom_height=float(local_height[0]))
        bts_path = write_bts(output / "wrf_les_inflow.bts", field)
        wnd_path = write_bladed_wnd(output / "wrf_les_inflow.wnd", field)
        bts_error = float(np.max(np.abs(validate_bts(bts_path, expected=field).velocity-field.velocity)))
        wnd_error = float(np.max(np.abs(read_bladed_wnd(wnd_path, hub_height=field.hub_height).velocity-field.velocity)))

        # Summaries for people and downstream scripts.
        metrics = {
            "source": str(source), "grid_id": int(wrf.attrs.get("GRID_ID", 1)),
            "dimensions": dict(wrf.sizes),
            "selected_point": {"latitude": target_lat, "longitude": target_lon,
                               "x": int(cell.x), "y": int(cell.y)},
            "mean_10m_wind_speed_m_s": float(np.nanmean(point_speed)),
            "maximum_10m_wind_speed_m_s": float(np.nanmax(point_speed)),
            "turbulence_intensity_u10": float(turbulence_intensity(u10_series)),
            "bts_roundtrip_max_error_m_s": bts_error,
            "wnd_roundtrip_max_error_m_s": wnd_error,
            "qc": {"errors": sum(item.severity=="ERROR" for item in qc_issues),
                   "warnings": sum(item.severity=="WARNING" for item in qc_issues),
                   "issues": [item.to_dict() for item in qc_issues]},
            "boundary_layer": {
                "mean_wrf_pblh_m": float(np.nanmean(model_pbl)),
                "mean_wrf_pblh_excluding_zero_m": float(np.nanmean(model_pbl[model_pbl>0])),
                "mean_diagnosed_pblh_m": float(np.nanmean(diagnosed_pbl)),
                "mean_convective_velocity_scale_m_s": float(np.nanmean(convective_scale)),
                "stability_class_counts": {str(name): int(np.sum(surface_stability==name)) for name in np.unique(surface_stability)},
                "diagnostic_method": "First model level at least 0.5 K warmer than the lowest level.",
                "interpretation": "This discrete threshold estimate is constrained by model-level spacing and is not equivalent to WRF PBLH. Negative surface heat flux and predominantly stable classes support a shallow stable boundary layer.",
            },
            "wind_energy": {
                "rotor_bottom_m_agl": rotor_bottom, "rotor_top_m_agl": rotor_top,
                "mean_rotor_equivalent_speed_m_s": float(np.nanmean(rotor_speed)),
                "mean_shear_exponent": float(np.nanmean(rotor_shear)),
                "mean_veer_degrees": float(np.nanmean(rotor_veer)),
                "weibull_shape": weibull_shape, "weibull_scale_m_s": weibull_scale,
                "mean_wind_power_density_w_m2": power_density,
            },
            "spectral_and_coherence": {
                "u10_fitted_log_slope": spectral_slope,
                "integral_time_scale_hours": integral_hours,
                "integral_length_scale_m": integral_length,
                "mean_lateral_u10_coherence": float(np.nanmean(lateral_coherence)),
                "record_length_warning": "Only 25 hourly samples: spectra demonstrate the API but cannot resolve an atmospheric inertial subrange.",
            },
            "thermodynamics": {
                "surface_relative_humidity_percent": float(rh_point[0,0]),
                "maximum_equivalent_potential_temperature_k": float(np.nanmax(theta_e_point)),
                "maximum_brunt_vaisala_frequency_s_1": float(np.nanmax(n_frequency)),
                "inversion_level_count_first_time": int(np.sum(inversion[0])),
            },
            "turbulence_and_flow": {
                "mean_resolved_tke_m2_s2": float(np.nanmean(budget["resolved_tke"])),
                "mean_shear_production_m2_s3": float(np.nanmean(budget["shear_production"])),
                "mean_buoyancy_production_m2_s3": float(np.nanmean(budget["buoyancy_production"])),
                "maximum_absolute_vorticity_s_1": float(np.nanmax(np.abs(kinematics["vertical_vorticity"]))),
                "low_level_jet_detected_first_time": bool(jet["detected"]),
                "jet_core_speed_m_s": float(jet["core_speed"]), "jet_core_height_m_agl": float(jet["core_height"]),
            },
            "precipitation": {
                "domain_mean_total_mm": float(np.nanmean(precipitation["total"])),
                "domain_maximum_interval_mm": float(np.nanmax(precipitation["maximum_interval"])),
            },
            "terrain_landuse_resolution": {
                "maximum_terrain_slope_degrees": float(np.nanmax(terrain_result["slope_degrees"])),
                "landuse_category_statistics": landuse,
                "coarsen_regrid_comparison": resolution,
                "temperature_integral_conservation": conservation,
                "boundary_difference_k": boundary["difference"],
                "vector_rotation_speed_max_error": float(np.nanmax(np.abs(wind_speed(earth_u,earth_v)-wind_speed(u10[0],v10[0])))),
            },
            "temporal": {
                "lag1_persistence": time_result["persistence_lag1"],
                "ramp_threshold_m_s": time_result["ramp_threshold"],
                "ramp_event_count": int(np.sum(time_result["ramp_events"])),
                "diurnal_mean_speed_m_s": {str(hour): float(value) for hour,value in diurnal.items()},
            },
        }
        (output / "summary.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        write_json_report({"dataset": dataset_summary(wrf), "provenance": provenance(inputs=[source])},
                          output / "dataset_report.json")
        report_sections = {
            "case": {"wrfout_file": source.name, "grid_id": metrics["grid_id"],
                     "dimensions": metrics["dimensions"], "selected_point": metrics["selected_point"]},
            "quality_control": metrics["qc"], "surface_wind": {
                "mean_10m_wind_speed_m_s": metrics["mean_10m_wind_speed_m_s"],
                "maximum_10m_wind_speed_m_s": metrics["maximum_10m_wind_speed_m_s"],
                "turbulence_intensity_u10_percent": metrics["turbulence_intensity_u10"]},
            "boundary_layer": metrics["boundary_layer"], "wind_energy": metrics["wind_energy"],
            "spectral_and_coherence": metrics["spectral_and_coherence"],
            "thermodynamics": metrics["thermodynamics"],
            "turbulence_and_flow": metrics["turbulence_and_flow"],
            "precipitation": metrics["precipitation"],
            "terrain_landuse_resolution": metrics["terrain_landuse_resolution"],
            "temporal": {
                "lag1_persistence": metrics["temporal"]["lag1_persistence"],
                "ramp_threshold_m_s": metrics["temporal"]["ramp_threshold_m_s"],
                "ramp_event_count": metrics["temporal"]["ramp_event_count"],
                "minimum_diurnal_mean_speed_m_s": float(min(diurnal.values())),
                "maximum_diurnal_mean_speed_m_s": float(max(diurnal.values())),
                "peak_diurnal_hour": int(max(diurnal,key=diurnal.get)),
            },
            "openfast_conversion": {"bts_roundtrip_max_error_m_s":bts_error,"wnd_roundtrip_max_error_m_s":wnd_error},
        }
        figure_paths=sorted(output.glob("*.png"))
        write_html_report(report_sections,output/"case_report.html",figures=figure_paths)
        write_pdf_report(report_sections,output/"case_report.pdf",figures=figure_paths)

    print(json.dumps(metrics, indent=2))
    print(f"Results written to: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
