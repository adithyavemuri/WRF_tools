"""Actual WRF isolines on stacked physical-height planes, not a slideshow.

First run export_3d_contours.py in the ordinary WRF_tools environment. Then:
    WRF_CONTOURS=example_results/contours3d/contours.json \
      .manim-env/bin/manim -qm examples/manim_wrf_contours.py WRFContours

No WRF/Cartopy dependency is needed in the optional renderer: only Manim and
the exported geometry. Scientific thresholds/heights are set during export.
"""
import json
import os
from pathlib import Path
from manim import (ThreeDScene, ThreeDAxes, Text, VMobject, VGroup, Line,
                   DEGREES, UP, DOWN, LEFT, RIGHT, WHITE)


class WRFContours(ThreeDScene):
    def construct(self):
        data = json.loads(Path(os.environ.get("WRF_CONTOURS",
            "example_results/contours3d/contours.json")).read_text())
        if data.get("schema_version") != 1 or data.get("temporal_interpolation") != "none" or not data["frames"]:
            raise ValueError("Expected an actual-state contour export")
        self.camera.background_color = "#101d2b"
        extent = max(data["x_extent_km"], data["y_extent_km"])
        scale = 6.3 / extent
        zmax = max(data["heights_m"]) / 1000
        exaggeration = data["vertical_exaggeration"]
        axes = ThreeDAxes(x_range=[0, data["x_extent_km"], data["x_extent_km"]/3],
            y_range=[0, data["y_extent_km"], data["y_extent_km"]/3], z_range=[0, zmax, zmax/3],
            x_length=data["x_extent_km"]*scale, y_length=data["y_extent_km"]*scale,
            z_length=zmax*scale*exaggeration, axis_config=dict(include_tip=False, color="#52697d"))
        axes.move_to(LEFT*.8+DOWN*.25)
        self.set_camera_orientation(phi=65*DEGREES, theta=-55*DEGREES, zoom=.72)
        self.add(axes)

        def curve(points, color, width=2.2, opacity=1):
            path = VMobject(stroke_color=color, stroke_width=width, stroke_opacity=opacity)
            path.set_points_as_corners([axes.c2p(*point) for point in points])
            return path

        for height in data["heights_m"]:
            z = height/1000
            border = [[0,0,z], [data["x_extent_km"],0,z],
                [data["x_extent_km"],data["y_extent_km"],z], [0,data["y_extent_km"],z], [0,0,z]]
            self.add(curve(border, "#52697d", .7, .5))
            label = Text(f"{height:g} m", font_size=17, color=WHITE)
            label.move_to(axes.c2p(data["x_extent_km"], 0, z)+RIGHT*.3)
            self.add_fixed_orientation_mobjects(label)
        for points in data["model_land_water_boundaries"]:
            self.add(curve(points, "#b8dbe5", 1.8))

        label = "Horizontal wind speed" if data["variable"] == "wind_speed" else "Model-provided TKE"
        title = Text(f"{data['domain'].upper()} | {label} | physical-height contours", font_size=27, color=WHITE).to_edge(UP)
        footer = Text(f"{data['height_reference']} heights | vertical exaggeration {exaggeration:g}x | no temporal interpolation",
                      font_size=17, color="#b8dbe5").to_edge(DOWN)
        legend = VGroup()
        for value in data["thresholds"]:
            color = data["threshold_colours"][str(float(value))]
            entry = VGroup(Line(LEFT*.18, RIGHT*.18, color=color),
                Text(f"{value:g}", font_size=18, color=color)).arrange(RIGHT, buff=.15)
            legend.add(entry)
        legend.arrange(DOWN, aligned_edge=LEFT, buff=.12).to_edge(RIGHT).shift(UP*.3)
        unit = Text(data["source"]["units"], font_size=17, color=WHITE).next_to(legend, UP)
        note = Text(f"{data['x_extent_km']:g} × {data['y_extent_km']:g} native grid-km | pale base lines: model land/water boundary",
                    font_size=16, color="#b8dbe5").next_to(footer, UP, buff=.1)
        self.add_fixed_in_frame_mobjects(title, footer, legend, unit, note)
        current, stamp = None, None
        # Hold the camera fixed while data changes; rotate ONLY the last state.
        for frame in data["frames"]:
            lines = VGroup(*[curve(item["points_km"], data["threshold_colours"][str(item["value"])])
                             for item in frame["contours"]])
            if current is not None:
                self.remove(current, stamp)
            stamp = Text(frame["time_utc"].replace("T", " ")+" UTC", font_size=22, color=WHITE)
            stamp.next_to(title, DOWN, buff=.12)
            self.add(lines); self.add_fixed_in_frame_mobjects(stamp)
            current = lines
            self.wait(2)
        self.move_camera(theta=-20*DEGREES, run_time=4)
        self.wait(2)
