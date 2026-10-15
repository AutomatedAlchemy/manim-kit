"""Animate your own simulation: precomputed snapshots, one clock, runs stacked in sync.

1. Simulate. The solver runs outside Manim, in any environment, and saves one .npz per
   run: snapshot times `t`, snapshots `u` (K x H x W), the slow-motion window `t_slow`,
   and a densely logged time series `curve_t`, `curve_y` (optional: `solid`, an H x W
   mask). `wave()` is a toy stand-in; SIM_DATA=DIR animates DIR/*.npz instead.
2. Adapt. `Run` turns one run into what the screen shows: an RGBA frame for any time and
   the curve up to that time. numpy only, because it runs inside manim-kit's venv.
3. Animate. One ValueTracker is the clock. `Run.time` maps it piecewise onto each run's
   own time, so all runs enter and leave slow motion together.
"""
import os
from pathlib import Path

import numpy as np
from manim import *

# The cache hashes a truncated copy of each pixel array and can replay a stale clip once
# the data changes, so data-driven scenes render uncached.
config.disable_caching = True

PHASES = (4.0, 4.0, 5.0)  # seconds on screen: lead-up, slow motion, the rest
NEG, ZERO, POS, SOLID = (np.array(c, float) for c in
                         ((59, 130, 246), (16, 18, 24), (245, 158, 11), (156, 163, 175)))


def wave(c, nx=200, ny=120, f=1 / 8, src_x=22, wall_x=60, slits=(48, 72), steps=640):
    """Toy solver: a plane wave of speed c through a double slit, in grid units."""
    dt = 0.5 / c
    yy, xx = np.mgrid[0:ny, 0:nx]
    solid = (xx >= wall_x) & (xx < wall_x + 3)
    for s in slits:
        solid &= np.abs(yy - s) > 2
    edge = np.minimum.reduce([xx, nx - 1 - xx, yy, ny - 1 - yy])
    damp = 1 - 0.08 * np.clip(1 - edge / 18, 0, 1) ** 2      # absorbing border
    fixed = solid | (edge == 0)                               # u = 0 there; stops np.roll wrapping
    t_hit = (wall_x - src_x) / c                              # the front reaches the slits
    t_slow = (t_hit - 1 / f, t_hit + 4 / f)
    u = prev = np.zeros((ny, nx))
    t, snaps, curve_t, curve_y = [0.0], [u.astype(np.float32)], [0.0], [0.0]
    for n in range(1, steps + 1):
        tn = n * dt
        lap = np.roll(u, 1, 0) + np.roll(u, -1, 0) + np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u
        u, prev = (2 * u - prev + 0.25 * lap) * damp, u
        u[fixed] = 0
        u[:, src_x] = min(tn * f, 1) * np.sin(2 * np.pi * f * tn)
        curve_t.append(tn)
        curve_y.append(u[ny // 2, 150])
        if n % 2 == 0 or t_slow[0] <= tn <= t_slow[1]:        # denser inside the slow window
            t.append(tn)
            snaps.append(u.astype(np.float32))
    return dict(t=np.array(t), u=np.array(snaps), solid=solid, t_slow=np.array(t_slow),
                curve_t=np.array(curve_t), curve_y=np.array(curve_y))


def load_runs() -> dict:
    data = os.environ.get("SIM_DATA")
    if data:
        return {p.stem: dict(np.load(p)) for p in sorted(Path(data).expanduser().glob("*.npz"))}
    return {"wave speed 1.0": wave(1.0), "wave speed 1.5": wave(1.5)}


def paint(u: np.ndarray, solid: np.ndarray) -> np.ndarray:
    """Field -> RGBA uint8: blue below zero, amber above, grey where solid."""
    a = np.clip(u / 0.6, -1, 1)[..., None]
    rgb = np.where(a > 0, ZERO + a * (POS - ZERO), ZERO - a * (NEG - ZERO))
    rgb[solid] = SOLID
    return np.dstack([rgb.astype(np.uint8), np.full(u.shape, 255, np.uint8)])


class Run:
    """One run's data, and the map from the shared clock onto this run's time."""

    def __init__(self, d: dict):
        self.t, self.u = np.asarray(d["t"], float), np.asarray(d["u"], np.float32)
        self.solid = np.asarray(d.get("solid", np.zeros(self.u.shape[1:])), bool)
        self.curve_t, self.curve_y = np.asarray(d["curve_t"]), np.asarray(d["curve_y"])
        self.knots = [0.0, *np.asarray(d["t_slow"], float), float(self.t[-1])]

    def time(self, p: float) -> float:
        """Clock p in 0..3 -> run time: 0-1 lead-up, 1-2 slow motion, 2-3 the rest."""
        return float(np.interp(p, range(len(self.knots)), self.knots))

    def frame(self, t: float) -> np.ndarray:
        """A fresh RGBA array at time t, blended from the two neighbouring snapshots.
        For data that changes in steps (cracks, events), hold the last snapshot instead."""
        k = int(np.clip(np.searchsorted(self.t, t), 1, len(self.t) - 1))
        a = np.clip((t - self.t[k - 1]) / (self.t[k] - self.t[k - 1]), 0, 1)
        return paint((1 - a) * self.u[k - 1] + a * self.u[k], self.solid)

    def curve(self, t: float) -> np.ndarray:
        """The time series up to t as (n, 2) rows, the shape Axes.c2p maps to points."""
        n = max(int(np.searchsorted(self.curve_t, t, side="right")), 2)
        return np.column_stack([self.curve_t[:n], self.curve_y[:n]])


def freeze(scene: Scene) -> None:
    """Stop the clock-driven updaters and give each image its own arrays before a fade."""
    for m in scene.mobjects:
        m.clear_updaters()
        for sub in m.get_family():
            if isinstance(sub, ImageMobject):
                sub.pixel_array = sub.pixel_array.copy()
                sub.orig_alpha_pixel_array = sub.pixel_array[:, :, 3].copy()


class {{SCENE}}(Scene):
    def construct(self):
        runs = {name: Run(d) for name, d in load_runs().items()}
        clock = ValueTracker(0)
        row_h = 7.0 / len(runs)
        for i, (name, run) in enumerate(runs.items()):
            yc = 3.6 - row_h * (i + 0.5)
            img = ImageMobject(run.frame(0.0)).set_height(row_h - 0.8)
            img.move_to([-6.6, yc - 0.2, 0], aligned_edge=LEFT)
            img.add_updater(lambda m, r=run: setattr(m, "pixel_array", r.frame(r.time(clock.get_value()))))
            label = Text(name, font_size=26).next_to(img, UP, buff=0.15, aligned_edge=LEFT)

            span = float(np.abs(run.curve_y).max()) or 1.0
            ax = Axes(x_range=[0, run.knots[-1], run.knots[-1] / 4], y_range=[-span, span, span],
                      x_length=12.0 - img.width, y_length=row_h * 0.45, tips=False,
                      axis_config={"stroke_width": 2, "color": GRAY})
            ax.move_to([img.get_right()[0] + 0.5, yc - 0.2, 0], aligned_edge=LEFT)
            tag = Text("probe behind the slits", font_size=18, color=GRAY)
            tag.next_to(ax, UP, buff=0.1, aligned_edge=LEFT)
            curve = always_redraw(lambda r=run, a=ax: VMobject(stroke_color=YELLOW, stroke_width=3)
                                  .set_points_as_corners(a.c2p(r.curve(r.time(clock.get_value())))))
            # DecimalNumber caches its glyphs, so it updates faster than a Text rebuilt
            # every frame; mob_class=Text keeps it free of LaTeX.
            value = DecimalNumber(0, num_decimal_places=1, mob_class=Text, font_size=20)
            value.add_updater(lambda m, r=run: m.set_value(r.time(clock.get_value())))
            readout = VGroup(Text("t =", font_size=20), value).arrange(RIGHT, buff=0.12)
            readout.next_to(ax, UP, buff=0.1).align_to(ax.get_right() + 1.4 * LEFT, LEFT)
            self.add(img, label, ax, tag, curve, readout)

        slow = Text("slow motion", font_size=22, color=YELLOW).to_corner(UR, buff=0.2)
        slow.add_updater(lambda m: m.set_opacity(1.0 if 1 <= clock.get_value() < 2 else 0.0))
        self.add(slow)
        for p, run_time in enumerate(PHASES, start=1):
            self.play(clock.animate.set_value(p), run_time=run_time, rate_func=linear)
        self.wait(1)
        freeze(self)
        self.play(*[FadeOut(m) for m in self.mobjects])
