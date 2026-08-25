from manim import *


class {{SCENE}}(Scene):
    """Shapes, transforms, and a fade-out — the smallest useful scene."""

    def construct(self):
        circle = Circle(color=BLUE, fill_opacity=0.5)
        square = Square(color=ORANGE)

        self.play(Create(circle))
        self.wait(0.5)
        self.play(Transform(circle, square))
        self.wait(0.5)
        self.play(FadeOut(circle))
