from manim import *


class {{SCENE}}(Scene):
    """Axes, a plotted function, and a dot that traces it via a ValueTracker."""

    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-1, 9, 2],
            axis_config={"include_numbers": True},
        )
        labels = axes.get_axis_labels(x_label="x", y_label="f(x)")
        graph = axes.plot(lambda x: x**2, color=BLUE)
        graph_label = axes.get_graph_label(graph, label="x^2")

        t = ValueTracker(-3)
        dot = always_redraw(
            lambda: Dot(axes.c2p(t.get_value(), t.get_value() ** 2), color=YELLOW)
        )

        self.play(Create(axes), Write(labels))
        self.play(Create(graph), FadeIn(graph_label))
        self.add(dot)
        self.play(t.animate.set_value(3), run_time=3, rate_func=linear)
        self.wait()
