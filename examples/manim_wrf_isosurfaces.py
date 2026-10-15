"""Real WRF isosurfaces above a terrain/ocean model cutout.

Render exported geometry in a separate Manim environment (no WRF dependency):
    WRF_ISOSURFACES=example_results/isosurfaces3d/geometry.json \
      manim --renderer cairo -qm examples/manim_wrf_isosurfaces.py WRFIsosurfaces

WRF_ISOSURFACE_PREVIEW=1 selects one final-state still for a quick layout check.
All scientific choices are made in export_3d_isosurfaces.py, not in this scene.
"""
import json
import os
from pathlib import Path

import numpy as np
from manim import (ThreeDScene, Polygon, VMobject, VGroup, Text, Line, Dot,
                   Rectangle, DEGREES, UP, DOWN, LEFT, RIGHT, WHITE)


class WRFIsosurfaces(ThreeDScene):
    def construct(self):
        path = Path(os.environ.get("WRF_ISOSURFACES", "example_results/isosurfaces3d/geometry.json"))
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "wrf-tools-isosurfaces" or data.get("schema_version") != 1:
            raise ValueError("Expected WRF_tools isosurface geometry schema v1")
        if data.get("temporal_interpolation") != "none" or not data.get("frames"):
            raise ValueError("Expected actual output states, without temporal morphing")
        Text.set_default(font="DejaVu Sans")
        self.camera.background_color = "#080f1c"
        self.camera.light_source.move_to(np.array([-6., -8., 12.]))
        width, depth = data["x_extent_km"], data["y_extent_km"]
        scale = 7.4/max(width, depth)
        exaggeration = data["vertical_exaggeration"]
        ztop = data["top_metres"]/1000
        origin = np.array([-.2, -.05, -.45])

        def point(value):
            x, y, z = value
            return np.array([(x-width/2)*scale, (y-depth/2)*scale, z*scale*exaggeration])+origin

        def polygon(vertices, colour, opacity=1, stroke=0):
            return Polygon(*[point(v) for v in vertices], fill_color=colour,
                fill_opacity=opacity, stroke_color=colour, stroke_width=stroke,
                shade_in_3d=True)

        def line(vertices, colour="#738998", opacity=.5, stroke=1):
            item = VMobject(stroke_color=colour, stroke_width=stroke, stroke_opacity=opacity,
                            shade_in_3d=True)
            item.set_points_as_corners([point(v) for v in vertices])
            return item

        self.set_camera_orientation(phi=64*DEGREES, theta=-58*DEGREES, zoom=.86)
        terrain = data["terrain"]
        vertices = np.asarray(terrain["vertices_km"])
        # A deliberately unlabelled solid support is a display plinth, not
        # inferred soil layers, seafloor depth or Earth's internal structure.
        bottom = min(-.07, float(vertices[:, 2].min())-.025)
        slab = [[0,0,bottom], [width,0,bottom], [width,depth,bottom], [0,depth,bottom]]
        self.add(polygon(slab, "#102332"))
        ny = len(np.unique(vertices[:, 1])); nx = len(np.unique(vertices[:, 0]))
        grid = vertices.reshape(ny, nx, 3)
        edges = (grid[0], grid[-1], grid[:,0], grid[:,-1])
        for edge in edges:
            for a, b in zip(edge[:-1], edge[1:]):
                self.add(polygon([a,b,[b[0],b[1],bottom],[a[0],a[1],bottom]], "#163548"))
        ground = VGroup(*[polygon(vertices[face], colour) for face, colour in zip(terrain["faces"], terrain["colours"])])
        self.add(ground)
        for coast in terrain["coastlines_km"]:
            self.add(line([[x,y,.002] for x,y,_ in coast], "#b3d4d7", .9, 1.25))

        # A sparse projected-grid cage makes vertical extent and clipping clear.
        for x, y in ((0,0),(width,0),(width,depth),(0,depth)):
            self.add(line([[x,y,0],[x,y,ztop]], opacity=.25, stroke=.65))
        self.add(line([[0,0,ztop],[width,0,ztop],[width,depth,ztop],[0,depth,ztop],[0,0,ztop]], opacity=.35, stroke=.7))
        for z in np.linspace(0, ztop, 5)[1:]:
            self.add(line([[0,depth,z],[width,depth,z]], opacity=.12, stroke=.6))
        self.add(line([[0,0,0],[width,0,0],[width,depth,0],[0,depth,0],[0,0,0]], "#8cb8c3", .8, 1))
        height_note = Text(f"{ztop:g} km MSL", font_size=16, color="#a9bdc8")
        height_note.move_to(point([width, depth, ztop])+RIGHT*.36)
        self.add_fixed_orientation_mobjects(height_note)

        title = Text("WRF  /  THE ATMOSPHERE IN THREE DIMENSIONS", font_size=29, color=WHITE).to_edge(UP, buff=.22)
        variable = "Horizontal wind speed" if data["variable"] == "wind_speed" else "Model-provided TKE"
        subtitle = Text(f"{data['domain'].upper()}   |   {variable} isosurfaces   |   {width:g} x {depth:g} native grid-km",
                        font_size=19, color="#aabfcc").next_to(title, DOWN, buff=.12)
        self.add_fixed_in_frame_mobjects(title, subtitle)
        palette = ["#4fc8cf", "#f2b45e", "#f17467", "#bd99ec"]
        legend = VGroup()
        for index, value in enumerate(data["thresholds"]):
            colour = palette[index % len(palette)]
            swatch = Rectangle(width=.2, height=.2, fill_color=colour, fill_opacity=.9, stroke_width=0)
            label = Text(f"{value:g} {data['source']['units']}", font_size=19, color=colour)
            legend.add(VGroup(swatch,label).arrange(RIGHT, buff=.1))
        legend.arrange(RIGHT, buff=.4).to_edge(RIGHT, buff=.36).shift(UP*2.55)
        self.add_fixed_in_frame_mobjects(legend)
        footer = Text(f"MSL geometry  |  vertical scale x{exaggeration:g}  |  stride {data['horizontal_stride']}  |  actual output states only",
                      font_size=16, color="#b5c4cf").to_edge(DOWN, buff=.18)
        note = Text("WRF terrain + land/water boundary; ocean at sea level. Colours are not satellite imagery.",
                    font_size=15, color="#7f98ab").next_to(footer, UP, buff=.1)
        self.add_fixed_in_frame_mobjects(footer,note)

        frames = data["frames"]
        preview = os.environ.get("WRF_ISOSURFACE_PREVIEW") == "1"
        selected = [len(frames)-1] if preview else range(len(frames))
        # Geometry is replaced at saved times; no false correspondence between
        # triangles is assumed when structures split or merge.
        active, stamp, progress = None, None, None
        for frame_index in selected:
            frame = frames[frame_index]
            pieces = []
            for index, mesh in enumerate(frame["meshes"]):
                coords = np.asarray(mesh["vertices_km"])
                colour = palette[index % len(palette)]
                opacity = .14 if index == 0 and len(frame["meshes"]) > 1 else .55
                pieces.extend(polygon(coords[face], colour, opacity) for face in mesh["faces"])
            if active is not None:
                self.remove(active, stamp, progress)
            active = VGroup(*pieces)
            self.add(active)
            stamp = Text(frame["time_utc"].replace("T", " ")+" UTC", font_size=22, color=WHITE)
            stamp.next_to(subtitle, DOWN, buff=.14).to_edge(LEFT, buff=.45)
            progress = VGroup(*[Dot(radius=.035, color=WHITE if i == frame_index else "#3c5265") for i in range(len(frames))])
            progress.arrange(RIGHT,buff=.14).next_to(note,UP,buff=.14)
            self.add_fixed_in_frame_mobjects(stamp,progress)
            self.wait(.1 if preview else 1.7)
        if not preview:
            self.move_camera(theta=-23*DEGREES, phi=60*DEGREES, run_time=4)
            self.wait(1)
