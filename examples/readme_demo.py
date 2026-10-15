"""The README demo: a title intro, then the derivative as the limit of a secant.

Render it (720p, Gemini voice Puck, default music bed):
    manim-kit render examples/readme_demo.py ReadmeDemo -q m --voice gemini-flash-tts:Puck
"""

from manim import *
from manim_voiceover import VoiceoverScene

from manim_kit_voice import default_service, subcaptions_wanted

C_ACCENT = YELLOW
C_MUTED = GRAY_B

ROWS = [
    ("new", "scaffold a scene from a template"),
    ("render", "voice, music and subtitles in one call"),
    ("open", "watch the result"),
]


def T(text, size=28, color=WHITE, **kw):
    """Text set at twice the size and scaled down, which avoids Pango's letter-spacing errors."""
    kw.setdefault("font", "DejaVu Sans")
    return Text(text, font_size=size * 2, color=color, **kw).scale(0.5)


class ReadmeDemo(VoiceoverScene):
    def construct(self):
        self.set_speech_service(default_service(), create_subcaption=subcaptions_wanted())
        self.intro()
        self.derivative()
        self.credits()

    def intro(self):
        pre = T("Manim Community · one command", 28, color=C_MUTED)
        title = T("manim-kit", 72, weight=BOLD)
        sub = T("narrated maths animations from one Python file", 32, color=C_ACCENT)
        line = Line(LEFT * 4.5, RIGHT * 4.5, color=C_ACCENT, stroke_width=2)
        VGroup(pre, title, sub, line).arrange(DOWN, buff=0.35).move_to(UP * 0.3)

        with self.voiceover(
            "This is manim-kit. It turns one Python file into a narrated maths animation."
        ) as t:
            self.play(FadeIn(pre), Write(title), run_time=t.duration * 0.45)
            self.play(FadeIn(sub, shift=UP * 0.2), Create(line), run_time=t.duration * 0.35)

        small_title = T("manim-kit", 36, weight=BOLD).to_edge(UP, buff=0.5)
        rows = VGroup()
        for cmd, what in ROWS:
            rows.add(VGroup(T(cmd, 32, color=C_ACCENT, weight=BOLD), T(what, 30)))
        cmd_w = max(r[0].width for r in rows)
        for i, r in enumerate(rows):
            y = 0.9 - i * 0.9
            r[0].set_x(0, direction=LEFT).set_y(y, direction=UP)
            r[1].set_x(cmd_w + 0.6, direction=LEFT).set_y(y, direction=UP)
        rows.move_to(DOWN * 0.3)

        with self.voiceover(
            "You <bookmark mark='r1'/> scaffold a scene, "
            "<bookmark mark='r2'/> render it with a voice and music, "
            "<bookmark mark='r3'/> and open the video."
        ):
            self.play(ReplacementTransform(title, small_title),
                      FadeOut(pre), FadeOut(sub), FadeOut(line), run_time=0.7)
            for i, r in enumerate(rows):
                self.wait_until_bookmark(f"r{i + 1}")
                self.play(FadeIn(r, shift=RIGHT * 0.3), run_time=0.45)

        go = T("Example: the derivative", 44, color=C_ACCENT, weight=BOLD)
        with self.voiceover("Here is what that looks like: the derivative, in half a minute.") as t:
            self.play(FadeOut(rows), FadeOut(small_title), run_time=0.5)
            self.play(FadeIn(go, scale=0.9), run_time=0.6)
            self.wait(max(t.duration - 1.6, 0.1))
            self.play(FadeOut(go), run_time=0.5)

    def derivative(self):
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 9, 2], x_length=6.2, y_length=5.6,
                  axis_config={"include_numbers": True, "font_size": 24},
                  tips=False).to_edge(LEFT, buff=0.7).shift(DOWN * 0.2)
        curve = ax.plot(lambda x: x ** 2, x_range=[0, 3], color=BLUE)
        curve_label = MathTex("y = x^2", color=BLUE).move_to(ax.c2p(1.3, 7.5))

        x0 = 1.0
        h = ValueTracker(1.5)

        def q_x():
            return x0 + h.get_value()

        p_dot = Dot(ax.c2p(x0, x0 ** 2), color=C_ACCENT)
        q_dot = always_redraw(lambda: Dot(ax.c2p(q_x(), q_x() ** 2), color=C_ACCENT))
        p_lab = MathTex("P", font_size=34).next_to(p_dot, UL, buff=0.1)
        q_lab = always_redraw(lambda: MathTex("Q", font_size=34).next_to(q_dot, UL, buff=0.1))

        def secant():
            # clip the line to the axes box, x in [0, 3] and y in [0, 9]
            m = 2 * x0 + h.get_value()
            xa = max(0.0, x0 - x0 ** 2 / m)
            xb = min(3.0, x0 + (9 - x0 ** 2) / m)
            return Line(ax.c2p(xa, x0 ** 2 + m * (xa - x0)), ax.c2p(xb, x0 ** 2 + m * (xb - x0)),
                        color=C_ACCENT, stroke_width=4)

        sec = always_redraw(secant)
        run = always_redraw(lambda: DashedLine(ax.c2p(x0, x0 ** 2), ax.c2p(q_x(), x0 ** 2),
                                               color=C_MUTED))
        rise = always_redraw(lambda: DashedLine(ax.c2p(q_x(), x0 ** 2), ax.c2p(q_x(), q_x() ** 2),
                                                color=C_MUTED))
        h_lab = always_redraw(lambda: MathTex("h", font_size=30, color=C_MUTED)
                              .next_to(run, DOWN, buff=0.1))

        slope_def = MathTex(r"\text{slope} = \frac{(1+h)^2 - 1^2}{h} = 2 + h", font_size=38)
        slope_val = VGroup(MathTex(r"\text{slope} =", font_size=40),
                           DecimalNumber(2 + h.get_value(), num_decimal_places=2, font_size=40,
                                         color=C_ACCENT)).arrange(RIGHT, buff=0.2)
        slope_val[1].add_updater(lambda d: d.set_value(2 + h.get_value()))
        right = VGroup(slope_def, slope_val).arrange(DOWN, buff=0.6, aligned_edge=LEFT)
        right.to_edge(RIGHT, buff=0.6).shift(UP * 0.8)
        result = VGroup(MathTex(r"f'(1) = \lim_{h \to 0} (2 + h) = 2", font_size=38),
                        MathTex(r"f'(x) = 2x", font_size=44, color=C_ACCENT)
                        ).arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        result.next_to(right, DOWN, buff=0.8, aligned_edge=LEFT)
        side = VGroup(right, result)
        if side.width > 5.6:
            side.scale_to_fit_width(5.6)
        side.to_edge(RIGHT, buff=0.6)

        with self.voiceover(
            "Take the curve y equals x squared, and two points on it, a step h apart."
        ) as t:
            self.play(Create(ax), Create(curve), FadeIn(curve_label), run_time=t.duration * 0.5)
            self.play(FadeIn(p_dot, p_lab, q_dot, q_lab), Create(run), Create(rise),
                      FadeIn(h_lab), run_time=t.duration * 0.35)

        with self.voiceover("The line through both points is a secant. Its slope is rise over run.") as t:
            self.play(Create(sec), run_time=t.duration * 0.35)
            self.play(Write(slope_def), FadeIn(slope_val), run_time=t.duration * 0.5)

        with self.voiceover(
            "Now shrink h. <bookmark mark='slide'/> The second point slides toward the first, "
            "and the secant turns into the tangent."
        ) as t:
            self.wait_until_bookmark("slide")
            self.play(h.animate.set_value(0.001), run_time=t.get_remaining_duration(),
                      rate_func=smooth)

        with self.voiceover(
            "The slope settles at two. That limit is the derivative, and for x squared it is two x."
        ) as t:
            self.play(FadeOut(q_lab, h_lab, run, rise), Indicate(slope_val, color=C_ACCENT),
                      run_time=t.duration * 0.3)
            self.play(Write(result[0]), run_time=t.duration * 0.3)
            self.play(Write(result[1]), run_time=t.duration * 0.25)
        self.wait(0.8)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)

    def credits(self):
        made = T("Made with manim-kit", 44, weight=BOLD)
        lines = VGroup(
            T("Voice: Google Gemini TTS, voice Puck (AI-generated)", 24, color=C_MUTED),
            T("Music: “Cylinder Five” by Chris Zabriskie · CC BY 4.0", 24, color=C_MUTED),
        ).arrange(DOWN, buff=0.25)
        card = VGroup(made, lines).arrange(DOWN, buff=0.5)
        self.play(FadeIn(card, shift=UP * 0.2), run_time=0.6)
        self.wait(2.5)
        self.play(FadeOut(card), run_time=0.6)
        self.wait(0.3)
