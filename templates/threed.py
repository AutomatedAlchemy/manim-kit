from manim import *


class {{SCENE}}(ThreeDScene):
    """3D axes, a parametric surface, and a slow camera orbit."""

    def construct(self):
        axes = ThreeDAxes()
        surface = Surface(
            lambda u, v: axes.c2p(u, v, np.sin(u) * np.cos(v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(24, 24),
            fill_opacity=0.7,
        )
        surface.set_style(stroke_width=0.5)

        self.set_camera_orientation(phi=65 * DEGREES, theta=-45 * DEGREES)
        self.play(Create(axes))
        self.play(Create(surface), run_time=2)
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(4)
        self.stop_ambient_camera_rotation()
